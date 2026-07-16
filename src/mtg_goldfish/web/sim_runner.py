"""Runs simulations on a background thread and streams progress over the Hub.

The engine is synchronous and CPU-bound, so each run executes in its own thread.
Progress is pushed to WebSocket clients via `Hub.broadcast_threadsafe`, and the
finished `SimResult` is appended to the session and persisted.
"""
from __future__ import annotations

import asyncio
import base64
import gzip
import json
import threading
import time

from ..cards import is_implemented, load_all_cards
from ..deck.models import DeckBoard
from ..engine.simulator import (
    GameOutcome,
    SimulationConfig,
    SimulationStats,
    run_simulation,
)
from ..properties import compile_all
from ..session import Session, SessionCorrupt, SessionStore, SimConfig, SimResult, new_id, now_iso
from .hub import HUB


def dumps_tree(root: dict) -> str:
    """Compact-JSON-encode a search tree iteratively.

    The tree can be thousands of nodes deep (DFS lines), and `json.dumps`
    recurses one C frame per nesting level — deep trees blow the recursion
    limit. Every node field is shallow except "children" (the only recursive
    link), so we dump each node's shallow fields with `json.dumps` and stitch
    the `children` nesting together with an explicit stack."""
    parts: list[str] = []
    # LIFO of work items: ("open", node) emits a node; ("raw", s) emits text.
    stack: list[tuple] = [("open", root)]
    while stack:
        kind, val = stack.pop()
        if kind == "raw":
            parts.append(val)
            continue
        node = val
        shallow = {k: v for k, v in node.items() if k != "children"}
        head = json.dumps(shallow, separators=(",", ":"))
        children = node.get("children") or []
        # Re-append "children" as the final key of the object.
        open_obj = ('{"children":[' if head == "{}"
                    else head[:-1] + ',"children":[')
        if not children:
            parts.append(open_obj + "]}")
            continue
        parts.append(open_obj)
        stack.append(("raw", "]}"))
        # Push children reversed with commas so they emit as c0,c1,...,cN.
        for i in range(len(children) - 1, -1, -1):
            stack.append(("open", children[i]))
            if i > 0:
                stack.append(("raw", ","))
    return "".join(parts)


class RunHandle:
    def __init__(self) -> None:
        self.stop = threading.Event()
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

    def start(
        self,
        session: Session,
        config: SimConfig,
        loop: asyncio.AbstractEventLoop,
    ) -> str:
        if self.is_running(session.id):
            raise RuntimeError("A simulation is already running for this session.")

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

        compiled = compile_all(session.properties)
        if not compiled:
            raise ValueError("No compiled properties to check. Compile them first.")

        handle = RunHandle()
        self._runs[session.id] = handle
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

        def worker() -> None:
            sample_runs: list[dict] = []
            last_stats: dict = initial.stats
            last_save = time.monotonic()

            def persist(status: str) -> None:
                # Reload to avoid clobbering concurrent edits, then update the
                # entry in place and save.
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

            def on_game(outcome: GameOutcome, stats: SimulationStats) -> None:
                # Every game gets a row (successes carry their winning line).
                # Trees carry a board snapshot per node, so they are stored
                # gzip+base64 compressed (highly repetitive JSON, ~20x smaller);
                # the frontend inflates them with DecompressionStream.
                nonlocal last_stats, last_save
                tree_gz = None
                if outcome.tree is not None:
                    raw = dumps_tree(outcome.tree).encode()
                    tree_gz = base64.b64encode(gzip.compress(raw, 6)).decode("ascii")
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
                # Persist progress (throttled — the session file is sizeable).
                if time.monotonic() - last_save > 2.0:
                    last_save = time.monotonic()
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

            sim_config = SimulationConfig(
                num_games=config.num_games,
                timeout_per_game_s=config.timeout_per_game_s,
                mulligans=config.mulligans,
                on_the_play=config.on_the_play,
                base_seed=config.base_seed,
                search_mode=config.search_mode,
                instant_speed=config.instant_speed,
                fixed_hand=config.fixed_hand,
                fixed_hand_pad_to=config.fixed_hand_pad_to,
            )
            status = "stopped"
            try:
                stats = run_simulation(
                    session.deck,
                    compiled,
                    sim_config,
                    on_game=on_game,
                    should_stop=handle.stop.is_set,
                )
                last_stats = stats.as_dict()
                status = "stopped" if handle.stop.is_set() else "done"
            finally:
                # Final (or crash/cancel) state of the entry.
                persist(status)

            result = SimResult(
                id=result_id,
                created_at=initial.created_at,
                config=config,
                status=status,
                properties=initial.properties,
                stats=last_stats,
                sample_runs=sample_runs,
                sample_success_logs=[r["log"] for r in sample_runs if r["success"]],
            )
            HUB.broadcast_threadsafe(
                loop,
                session.id,
                {
                    "type": "done",
                    "result": result.model_dump(),
                    "stopped": handle.stop.is_set(),
                },
            )

        handle.thread = threading.Thread(target=worker, daemon=True)
        handle.thread.start()
        return result_id
