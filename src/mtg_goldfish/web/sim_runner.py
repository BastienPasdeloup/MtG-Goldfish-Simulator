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

from ..engine.simulator import (
    GameOutcome,
    SimulationConfig,
    SimulationStats,
    run_simulation,
)
from ..properties import compile_all
from ..session import Session, SessionStore, SimConfig, SimResult, new_id, now_iso
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

        compiled = compile_all(session.properties)
        if not compiled:
            raise ValueError("No compiled properties to check. Compile them first.")

        handle = RunHandle()
        self._runs[session.id] = handle
        result_id = new_id()

        def worker() -> None:
            sample_runs: list[dict] = []

            def on_game(outcome: GameOutcome, stats: SimulationStats) -> None:
                # Every game gets a row (successes carry their winning line).
                # Trees carry a board snapshot per node, so they are stored
                # gzip+base64 compressed (highly repetitive JSON, ~20x smaller);
                # the frontend inflates them with DecompressionStream.
                tree_gz = None
                if outcome.tree is not None:
                    raw = dumps_tree(outcome.tree).encode()
                    tree_gz = base64.b64encode(gzip.compress(raw, 6)).decode("ascii")
                sample_runs.append({
                    "game_index": outcome.game_index,
                    "success": outcome.success,
                    "timed_out": outcome.timed_out,
                    "node_capped": outcome.node_capped,
                    "hand": outcome.opening_hand,
                    "branches_explored": outcome.branches_explored,
                    "branches_considered": outcome.branches_considered,
                    "tree_gz": tree_gz,
                    "tree_truncated": outcome.tree_truncated,
                    "log": outcome.sample_log if outcome.success else [],
                })
                HUB.broadcast_threadsafe(
                    loop,
                    session.id,
                    {
                        "type": "progress",
                        "result_id": result_id,
                        "stats": stats.as_dict(),
                        "last_game": {
                            "index": outcome.game_index,
                            "success": outcome.success,
                            "timed_out": outcome.timed_out,
                        },
                    },
                )

            sim_config = SimulationConfig(
                num_games=config.num_games,
                timeout_per_game_s=config.timeout_per_game_s,
                mulligans=config.mulligans,
                on_the_play=config.on_the_play,
                base_seed=config.base_seed,
                search_mode=config.search_mode,
            )
            stats = run_simulation(
                session.deck,
                compiled,
                sim_config,
                on_game=on_game,
                should_stop=handle.stop.is_set,
            )

            result = SimResult(
                id=result_id,
                created_at=now_iso(),
                config=config,
                properties=[p.model_copy() for p in session.properties if p.enabled],
                stats=stats.as_dict(),
                sample_runs=sample_runs,
                # Mirror the winning lines into the legacy field so older
                # consumers keep working.
                sample_success_logs=[r["log"] for r in sample_runs if r["success"]],
            )
            # Reload to avoid clobbering concurrent edits, then append + persist.
            fresh = self.store.load(session.id)
            fresh.results.append(result)
            self.store.save(fresh)

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
