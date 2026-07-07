"""On-disk session store (one JSON file per session under data/sessions/)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import CONFIG
from .models import Session


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class SessionStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        base = data_dir or CONFIG.data_dir
        self.dir = base / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def save(self, session: Session) -> None:
        self._path(session.id).write_text(session.model_dump_json(indent=2))

    def load(self, session_id: str) -> Session:
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"No session {session_id!r}")
        return Session.model_validate_json(path.read_text())

    def exists(self, session_id: str) -> bool:
        return self._path(session_id).exists()

    def delete(self, session_id: str) -> None:
        self._path(session_id).unlink(missing_ok=True)

    def list_sessions(self) -> list[dict]:
        """Lightweight summaries for the session picker."""
        out: list[dict] = []
        for path in sorted(self.dir.glob("*.json")):
            try:
                s = Session.model_validate_json(path.read_text())
            except Exception:
                continue
            out.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "format_id": s.format_id,
                    "created_at": s.created_at,
                    "commanders": [e.card.name for e in s.deck.commanders],
                    "num_properties": len(s.properties),
                    "num_results": len(s.results),
                }
            )
        out.sort(key=lambda d: d["created_at"], reverse=True)
        return out
