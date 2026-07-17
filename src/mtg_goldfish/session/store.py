"""On-disk session store (one JSON file per session under data/sessions/).

Robustness guarantees (a background run persists progress every couple of
seconds while the UI may save edits — the files are also large, hundreds of MB
with stored search trees, so interrupted/interleaved writes DID happen):

* `save()` is ATOMIC (write to a temp file, then `os.replace`) and serialized
  by a per-store lock — a crash or two concurrent saves can no longer leave a
  half-written or interleaved file behind.
* `load()` SALVAGES a broken file instead of failing, so the user can always
  open their session: trailing bytes left by an interleaved write are cut
  (the leading complete JSON value is used), and results that no longer
  validate (e.g. legacy formats) keep their stats but drop their replay
  payload — or are dropped entirely when unrecoverable. The repaired session
  is immediately saved back, so salvaging is a one-time cost.
* Only when not even a leading JSON value can be parsed does `load()` raise
  `SessionCorrupt`.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import CONFIG
from .models import Session, SimResult


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class SessionCorrupt(ValueError):
    """The session file is damaged beyond what salvaging can recover."""


class SessionStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        base = data_dir or CONFIG.data_dir
        self.dir = base / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._save_lock = threading.Lock()

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def save(self, session: Session) -> None:
        """Atomic, serialized save: the file on disk is always a complete
        dump — readers see either the previous version or the new one."""
        path = self._path(session.id)
        tmp = path.with_name(path.name + ".tmp")
        with self._save_lock:
            try:
                tmp.write_text(session.model_dump_json(indent=2))
                os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)

    def load(self, session_id: str) -> Session:
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"No session {session_id!r}")
        text = path.read_text()
        try:
            return Session.model_validate_json(text)
        except Exception:
            session = self._salvage(session_id, text)
            self.save(session)  # persist the repaired file (one-time)
            return session

    # ---- salvage -------------------------------------------------------------
    def _salvage(self, session_id: str, text: str) -> Session:
        """Recover a session from a damaged file. Raises SessionCorrupt only
        when nothing can be recovered."""
        # Interleaved writes leave a complete JSON value followed by leftover
        # bytes of an older, longer dump: parse the leading value only.
        try:
            data, _ = json.JSONDecoder().raw_decode(text)
        except Exception as exc:
            raise SessionCorrupt(
                f"Session {session_id!r} is damaged beyond repair "
                f"(no leading JSON value: {exc})"
            ) from exc
        if not isinstance(data, dict):
            raise SessionCorrupt(f"Session {session_id!r} is not a JSON object")

        raw_results = data.get("results")
        base = dict(data)
        base["results"] = []
        try:
            session = Session.model_validate(base)
        except Exception as exc:
            raise SessionCorrupt(
                f"Session {session_id!r} is damaged beyond repair "
                f"(deck/properties no longer validate: {exc})"
            ) from exc

        # Re-attach each run: as-is if it validates, without its replay payload
        # (legacy formats) if that fixes it, dropped otherwise.
        dropped = 0
        for raw in raw_results if isinstance(raw_results, list) else []:
            if not isinstance(raw, dict):
                dropped += 1
                continue
            for attempt in (raw, {**raw, "sample_runs": [], "sample_success_logs": []}):
                try:
                    session.results.append(SimResult.model_validate(attempt))
                    break
                except Exception:
                    continue
            else:
                dropped += 1
        print(
            f"[sessions] salvaged {session_id!r}: kept {len(session.results)} "
            f"run(s), dropped {dropped}",
            file=sys.stderr,
        )
        return session

    # ---- misc ----------------------------------------------------------------
    def exists(self, session_id: str) -> bool:
        return self._path(session_id).exists()

    def delete(self, session_id: str) -> None:
        self._path(session_id).unlink(missing_ok=True)

    def list_sessions(self) -> list[dict]:
        """Lightweight summaries for the session picker. Uses the salvaging
        `load`, so a damaged-but-recoverable session still shows up (and gets
        repaired on the way); only unrecoverable files are skipped."""
        out: list[dict] = []
        for path in sorted(self.dir.glob("*.json")):
            try:
                s = self.load(path.stem)
            except Exception as exc:
                print(f"[sessions] skipping {path.name}: {exc}", file=sys.stderr)
                continue
            last_run = max((r.created_at for r in s.results), default=None)
            out.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "format_id": s.format_id,
                    "created_at": s.created_at,
                    "commanders": [{"name": e.card.name, "image": e.card.image}
                                   for e in s.deck.commanders],
                    "num_properties": len(s.properties),
                    "num_results": len(s.results),
                    "last_run": last_run,
                }
            )
        out.sort(key=lambda d: d["created_at"], reverse=True)
        return out
