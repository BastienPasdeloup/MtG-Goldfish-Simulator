"""FastAPI application: deck import, sessions, property compilation, simulation."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..cards import is_implemented, load_all_cards
from ..config import CONFIG
from ..deck import MoxfieldError, ScryfallError, import_moxfield_deck
from ..deck.models import Deck
from ..engine.phases import phase_labels
from ..formats import get_format, list_formats
from ..llm import get_provider
from ..properties import STATE_API_DOC, PropertySpec, compile_condition
from ..session import Session, SessionStore, SimConfig, new_id, now_iso
from .hub import HUB
from .sim_runner import SimulationRunner

_STATIC = Path(__file__).parent / "static"

app = FastAPI(title="MtG Goldfish Simulator")
store = SessionStore()
runner = SimulationRunner(store)


# --------------------------------------------------------------------------
# request/response models
# --------------------------------------------------------------------------
class ImportRequest(BaseModel):
    url: str
    name: str
    format_id: str = "duel_commander"


class PropertiesUpdate(BaseModel):
    properties: list[PropertySpec]
    mulligans: int = 0


class CompileRequest(BaseModel):
    english: str


class SimulateRequest(BaseModel):
    num_games: int = 100
    timeout_per_game_s: float = 5.0
    mulligans: int = 0


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def card_view(deck: Deck) -> list[dict]:
    """Aggregate the deck into per-card rows for the UI (implemented flag,
    image, sort keys)."""
    load_all_cards()
    agg: dict[tuple[str, str], dict] = {}
    for e in deck.entries:
        key = (e.board.value, e.card.name)
        if key in agg:
            agg[key]["quantity"] += e.quantity
            continue
        c = e.card
        agg[key] = {
            "name": c.name,
            "quantity": e.quantity,
            "board": e.board.value,
            "type_line": c.type_line,
            "cmc": c.cmc,
            "colors": c.color_identity or c.colors,
            "image": c.image,
            "implemented": is_implemented(c.name),
            "is_land": c.is_land,
        }
    return list(agg.values())


def session_payload(session: Session) -> dict:
    return {
        "session": session.model_dump(),
        "cards": card_view(session.deck),
    }


# --------------------------------------------------------------------------
# static + meta
# --------------------------------------------------------------------------
@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/api/meta")
def meta() -> dict:
    return {
        "formats": [{"id": f.id, "name": f.name} for f in list_formats()],
        "phases": phase_labels(),
        "property_api_doc": STATE_API_DOC,
        "llm_provider": get_provider().name,
        "llm_is_real": get_provider().is_real,
    }


# --------------------------------------------------------------------------
# deck import (preview) + session creation
# --------------------------------------------------------------------------
@app.post("/api/deck/preview")
def deck_preview(req: ImportRequest) -> dict:
    try:
        result = import_moxfield_deck(req.url, req.name, req.format_id)
    except (MoxfieldError, ScryfallError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    problems = get_format(req.format_id).validate(result.deck)
    return {
        "deck": result.deck.to_public(),
        "cards": card_view(result.deck),
        "warnings": result.warnings,
        "problems": problems,
    }


@app.post("/api/sessions")
def create_session(req: ImportRequest) -> dict:
    try:
        result = import_moxfield_deck(req.url, req.name, req.format_id)
    except (MoxfieldError, ScryfallError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session = Session(
        id=new_id(),
        name=req.name,
        format_id=req.format_id,
        created_at=now_iso(),
        deck=result.deck,
    )
    store.save(session)
    payload = session_payload(session)
    payload["warnings"] = result.warnings
    return payload


@app.get("/api/sessions")
def list_sessions() -> dict:
    return {"sessions": store.list_sessions()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    try:
        session = store.load(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    return session_payload(session)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    store.delete(session_id)
    return {"ok": True}


# --------------------------------------------------------------------------
# properties
# --------------------------------------------------------------------------
@app.put("/api/sessions/{session_id}/properties")
def update_properties(session_id: str, req: PropertiesUpdate) -> dict:
    session = _load(session_id)
    session.properties = req.properties
    session.mulligans = req.mulligans
    store.save(session)
    return {"ok": True, "properties": [p.model_dump() for p in session.properties]}


@app.post("/api/compile")
def compile_one(req: CompileRequest) -> dict:
    """Compile a single English condition to code (for the review step)."""
    try:
        code = compile_condition(req.english)
    except Exception as exc:  # provider/network errors
        raise HTTPException(status_code=502, detail=f"Compilation failed: {exc}") from exc
    return {"code": code}


@app.post("/api/sessions/{session_id}/properties/compile")
def compile_properties(session_id: str) -> dict:
    session = _load(session_id)
    for spec in session.properties:
        if spec.enabled and not spec.code:
            try:
                spec.code = compile_condition(spec.english)
            except Exception as exc:  # noqa: BLE001 - surface per-property
                spec.code = f"# compilation error: {exc}\ndef check(state):\n    return False\n"
    store.save(session)
    return {"properties": [p.model_dump() for p in session.properties]}


# --------------------------------------------------------------------------
# cards
# --------------------------------------------------------------------------
@app.post("/api/cards/{card_name}/implement")
def implement_card(card_name: str) -> dict:
    # Placeholder per spec: the "ask a model to code it" action is wired in the
    # UI but functionality is intentionally not implemented yet.
    raise HTTPException(
        status_code=501,
        detail=f"Auto-implementing {card_name!r} is not wired up yet.",
    )


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------
@app.post("/api/sessions/{session_id}/simulate")
async def simulate(session_id: str, req: SimulateRequest) -> dict:
    session = _load(session_id)
    session.mulligans = req.mulligans
    store.save(session)
    loop = asyncio.get_running_loop()
    config = SimConfig(
        num_games=req.num_games,
        timeout_per_game_s=req.timeout_per_game_s,
        mulligans=req.mulligans,
    )
    try:
        result_id = runner.start(session, config, loop)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "result_id": result_id}


@app.post("/api/sessions/{session_id}/simulate/stop")
def stop_simulation(session_id: str) -> dict:
    runner.stop(session_id)
    return {"ok": True}


@app.websocket("/ws/{session_id}")
async def ws(session_id: str, websocket: WebSocket) -> None:
    await HUB.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; ignore content
    except WebSocketDisconnect:
        HUB.disconnect(session_id, websocket)


# --------------------------------------------------------------------------
def _load(session_id: str) -> Session:
    try:
        return store.load(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc


# Mounted last so /api/* and /ws/* take precedence.
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
