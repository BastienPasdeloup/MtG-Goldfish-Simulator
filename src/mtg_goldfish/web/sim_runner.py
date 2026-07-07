"""Runs simulations on a background thread and streams progress over the Hub.

The engine is synchronous and CPU-bound, so each run executes in its own thread.
Progress is pushed to WebSocket clients via `Hub.broadcast_threadsafe`, and the
finished `SimResult` is appended to the session and persisted.
"""
from __future__ import annotations

import asyncio
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
            sample_logs: list[list[str]] = []

            def on_game(outcome: GameOutcome, stats: SimulationStats) -> None:
                if outcome.success and outcome.sample_log and len(sample_logs) < 25:
                    sample_logs.append(outcome.sample_log)
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
                stats=stats.as_dict(),
                sample_success_logs=sample_logs,
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
