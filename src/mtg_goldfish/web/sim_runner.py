"""Runs simulations on a background thread and streams progress over the Hub.

The engine parallelizes the games across CPU cores (see engine.simulator);
this runner owns the run's lifecycle on a coordinating thread. Progress is
pushed to WebSocket clients via `Hub.broadcast_threadsafe`, and the run's
entry in the session is re-persisted after every completed game, so a crash
never loses more than the games in flight — the partial run stays loadable
(and resumable) from "Previous runs".
"""
from __future__ import annotations

import asyncio
import threading
import time
import traceback

from ..cards import is_implemented, load_all_cards
from ..deck.models import DeckBoard
from ..engine.simulator import (
    GameOutcome,
    SimulationConfig,
    SimulationStats,
    compress_tree,
    dumps_tree,  # noqa: F401 - re-exported (historical home of this helper)
    run_simulation,
)
from ..properties import compile_all
from ..session import Session, SessionCorrupt, SessionStore, SimConfig, SimResult, new_id, now_iso
from .hub import HUB


class RunHandle:
    def __init__(self) -> None:
        self.stop = threading.Event()
        # Skip the CURRENT game (abandon it as a failure and move on). Cleared at
        # the start of each game; set by the "skip" endpoint.
        self.skip = threading.Event()
        self.thread: threading.Thread | None = None


class SimulationRunner:
    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self._runs: dict[str, RunHandle] = {}

    def is_running(self, session_id: str) -> bool:
        h = self._runs.get(session_id)
        return bool(h and h.thread and h.thread.is_alive())

    def stop(self, session_id: str) -> None:
        h = self._runs.get(session_id)
        if h:
            h.stop.set()

    def skip(self, session_id: str) -> None:
        """Abandon the game currently being searched (it becomes a failure)."""
        h = self._runs.get(session_id)
        if h:
            h.skip.set()

    def _check_deck_implemented(self, session: Session) -> None:
        # Every card that can enter the game must have a real implementation;
        # unimplemented cards would silently play as vanilla approximations and
        # skew the results. Sideboard cards never enter the game, so ignore them.
        load_all_cards()
        missing = sorted({
            e.card.name for e in session.deck.entries
            if e.board != DeckBoard.SIDEBOARD and not is_implemented(e.card.name)
        })
        if missing:
            preview = ", ".join(missing[:12])
            more = f" (+{len(missing) - 12} more)" if len(missing) > 12 else ""
            raise ValueError(
                f"{len(missing)} card(s) are not implemented yet — implement them "
                f"before running a simulation: {preview}{more}"
            )

    def start(
        self,
        session: Session,
        config: SimConfig,
        loop: asyncio.AbstractEventLoop,
    ) -> str:
        if self.is_running(session.id):
            raise RuntimeError("A simulation is already running for this session.")
        self._check_deck_implemented(session)

        compiled = compile_all(session.properties)
        if not compiled:
            raise ValueError("No compiled properties to check. Compile them first.")

        result_id = new_id()
        # The run appears in "previous runs" the moment it starts (seed is
        # decided): create + persist the entry NOW, then keep updating it for
        # as long as the run is running.
        initial = SimResult(
            id=result_id,
            created_at=now_iso(),
            config=config,
            status="running",
            properties=[p.model_copy() for p in session.properties if p.enabled],
            stats={"total_games": config.num_games, "games_run": 0, "successes": 0,
                   "timeouts": 0, "success_rate": 0.0, "per_property": {}},
        )
        fresh = self.store.load(session.id)
        fresh.results.append(initial)
        self.store.save(fresh)

        self._launch(session, config, result_id, initial.created_at,
                     initial.properties, sample_runs=[], initial_stats=initial.stats,
                     game_indices=None, loop=loop)
        return result_id

    def resume(
        self,
        session: Session,
        result_id: str,
        loop: asyncio.AbstractEventLoop,
    ) -> str:
        """Continue a stopped / interrupted run: re-run exactly the games that
        never completed (per-game seeds depend only on the game index, so each
        resumed game is identical to what it would have been), appending to the
        stored entry."""
        if self.is_running(session.id):
            raise RuntimeError("A simulation is already running for this session.")
        result = next((r for r in session.results if r.id == result_id), None)
        if result is None:
            raise ValueError("Run not found.")
        if result.status == "running":
            raise ValueError("This run is still in progress.")
        self._check_deck_implemented(session)

        # Compile the RUN's property snapshot (not the session's current
        # properties): a resumed run must check exactly what it started with.
        compiled = compile_all(result.properties)
        if not compiled:
            raise ValueError("This run has no compiled properties to resume with.")

        done = {r.get("game_index") for r in result.sample_runs}
        remaining = [i for i in range(result.config.num_games) if i not in done]
        if not remaining:
            raise ValueError("This run is already complete — nothing to resume.")

        # Mark it running again and persist so the UI reflects it immediately.
        fresh = self.store.load(session.id)
        stored = next((r for r in fresh.results if r.id == result_id), None)
        if stored is None:
            raise ValueError("Run not found.")
        stored.status = "running"
        self.store.save(fresh)

        self._launch(session, result.config, result_id, result.created_at,
                     result.properties, sample_runs=list(result.sample_runs),
                     initial_stats=dict(result.stats), game_indices=remaining,
                     loop=loop, compiled=compiled)
        return result_id

    def _launch(
        self,
        session: Session,
        config: SimConfig,
        result_id: str,
        created_at: str,
        properties: list,
        *,
        sample_runs: list[dict],
        initial_stats: dict,
        game_indices: list[int] | None,
        loop: asyncio.AbstractEventLoop,
        compiled: list | None = None,
    ) -> None:
        compiled = compiled if compiled is not None else compile_all(session.properties)
        handle = RunHandle()
        self._runs[session.id] = handle

        def worker() -> None:
            last_stats: dict = initial_stats
            last_save = time.monotonic()
            save_cost = 0.0  # duration of the last persist (adaptive back-off)

            def persist(status: str) -> None:
                # Reload to avoid clobbering concurrent edits, then update the
                # entry in place and save.
                nonlocal last_save, save_cost
                t0 = time.monotonic()
                try:
                    fresh = self.store.load(session.id)
                except (FileNotFoundError, SessionCorrupt):
                    return  # session deleted (or unrecoverable) mid-run
                for r in fresh.results:
                    if r.id == result_id:
                        r.stats = last_stats
                        r.sample_runs = sample_runs
                        # Mirror the winning lines into the legacy field so
                        # older consumers keep working.
                        r.sample_success_logs = [x["log"] for x in sample_runs if x["success"]]
                        r.status = status
                        break
                self.store.save(fresh)
                last_save = time.monotonic()
                save_cost = last_save - t0

            def on_game(outcome: GameOutcome, stats: SimulationStats) -> None:
                # Every game gets a row (successes carry their winning line).
                # Trees carry a board snapshot per node, so they are stored
                # gzip+base64 compressed (highly repetitive JSON, ~20x smaller);
                # the frontend inflates them with DecompressionStream. Parallel
                # workers pre-compress the tree; sequential games compress here.
                nonlocal last_stats
                tree_gz = outcome.tree_gz
                if tree_gz is None and outcome.tree is not None:
                    tree_gz = compress_tree(outcome.tree)
                run = {
                    "game_index": outcome.game_index,
                    "success": outcome.success,
                    "timed_out": outcome.timed_out,
                    "hand": outcome.opening_hand,
                    "branches_explored": outcome.branches_explored,
                    "branches_considered": outcome.branches_considered,
                    "tree_gz": tree_gz,
                    "tree_truncated": outcome.tree_truncated,
                    "bugs": outcome.bugs,
                    "log": outcome.sample_log if outcome.success else [],
                }
                sample_runs.append(run)
                last_stats = stats.as_dict()
                # Persist after EVERY completed game, so a crash never loses
                # more than the games in flight — backing off only when saving
                # itself is slow (huge sessions): wait at least 2x the last
                # save's own cost before saving again.
                if time.monotonic() - last_save >= 2 * save_cost:
                    persist("running")
                HUB.broadcast_threadsafe(
                    loop,
                    session.id,
                    {
                        "type": "progress",
                        "result_id": result_id,
                        "stats": last_stats,
                        # The finished game's full row, so the table can be
                        # populated live while the search keeps running.
                        "run": run,
                    },
                )

            def on_game_start(game_index: int, hand: list) -> None:
                # A fresh game begins: clear any pending skip, and push a
                # "running" row (with its opening hand) so the table shows it live.
                handle.skip.clear()
                HUB.broadcast_threadsafe(loop, session.id, {
                    "type": "game_start", "result_id": result_id,
                    "game_index": game_index, "hand": hand,
                })

            sim_config = SimulationConfig(
                num_games=config.num_games,
                timeout_per_game_s=config.timeout_per_game_s,
                mulligans=config.mulligans,
                on_the_play=config.on_the_play,
                base_seed=config.base_seed,
                search_mode=config.search_mode,
                instant_speed=config.instant_speed,
                fake_shuffle=config.fake_shuffle,
                fixed_hand=config.fixed_hand,
                fixed_hand_pad_to=config.fixed_hand_pad_to,
                fixed_config=(config.fixed_config.model_dump()
                              if config.fixed_config is not None else None),
            )
            status = "stopped"
            try:
                stats = run_simulation(
                    session.deck,
                    compiled,
                    sim_config,
                    on_game=on_game,
                    should_stop=handle.stop.is_set,
                    should_skip=handle.skip.is_set,
                    on_game_start=on_game_start,
                    game_indices=game_indices,
                    initial_stats=initial_stats,
                )
                last_stats = stats.as_dict()
                status = "stopped" if handle.stop.is_set() else "done"
            except Exception:  # noqa: BLE001 - the run must NEVER die silently
                # An unexpected crash: keep the games persisted so far and mark
                # the run interrupted (shown as "failed", resumable) — and still
                # fall through to the done broadcast so the UI recovers.
                traceback.print_exc()
                status = "interrupted"

            result = SimResult(
                id=result_id,
                created_at=created_at,
                config=config,
                status=status,
                properties=properties,
                stats=last_stats,
            )
            # Tell the UI the run has ended FIRST — before the final persist,
            # which reloads + rewrites the whole session file and can take
            # seconds on a huge session. On Stop that write is what made the run
            # feel slow to halt; the games were already persisted incrementally,
            # so the durability cost of saving after the broadcast is nil.
            # LEAN done message: the per-game rows (incl. their compressed
            # search trees) were already streamed one by one as the games
            # finished — resending them all here can reach hundreds of MB on a
            # long run and crash the browser tab (which also swallowed the
            # UI's stop/Resume handling, since it lives in this handler).
            HUB.broadcast_threadsafe(
                loop,
                session.id,
                {
                    "type": "done",
                    "result": result.model_dump(exclude={"sample_runs", "sample_success_logs"}),
                    "stopped": handle.stop.is_set(),
                },
            )
            # Final (or crash/cancel) state of the entry — persisted after the
            # broadcast so the UI is not blocked on the (slow) disk write.
            try:
                persist(status)
            except Exception:  # noqa: BLE001 - never block the done signal
                traceback.print_exc()

        handle.thread = threading.Thread(target=worker, daemon=True)
        handle.thread.start()
