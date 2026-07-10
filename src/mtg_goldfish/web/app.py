"""FastAPI application: deck import, sessions, property compilation, simulation."""
from __future__ import annotations

import asyncio
import random
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
    on_the_play: bool = True
    base_seed: int | None = None  # random when omitted
    search_mode: str = "dfs_heuristic"  # see engine.simulator.SEARCH_MODES


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
        faces = [
            {
                "name": f.name,
                "image": f.image_normal,
                "mana_cost": f.mana_cost,
                "type_line": f.type_line,
            }
            for f in c.faces
        ] if len(c.faces) > 1 else []
        agg[key] = {
            "name": c.name,
            "quantity": e.quantity,
            "board": e.board.value,
            "type_line": c.type_line,
            "cmc": c.cmc,
            "mana_cost": c.mana_cost,
            "colors": c.colors,
            "color_identity": c.color_identity,
            "image": c.image,
            "faces": faces,
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
    return FileResponse(_STATIC / "index.html", headers={"Cache-Control": "no-cache"})


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
# LLM backend selection (stub / local Ollama / Anthropic API)
# --------------------------------------------------------------------------
class LLMSelect(BaseModel):
    model_id: str
    api_key: str | None = None


@app.get("/api/llm")
def llm_status() -> dict:
    from ..llm.catalog import load_selection, option_dicts, stored_api_key
    from ..llm.ollama_provider import installed_models, ollama_available

    available = ollama_available()
    installed = installed_models() if available else set()
    options = []
    for opt in option_dicts():
        opt = dict(opt)
        if opt["kind"] == "local":
            opt["ollama_running"] = available
            opt["installed"] = opt["ollama_model"] in installed
            opt["pull_cmd"] = f"ollama pull {opt['ollama_model']}"
        options.append(opt)
    return {
        "options": options,
        "selected": load_selection(),
        "ollama_running": available,
        "has_api_key": bool(stored_api_key()),
    }


@app.post("/api/llm")
def llm_select(req: LLMSelect) -> dict:
    from ..llm import reset_provider
    from ..llm.catalog import CATALOG_BY_ID, save_selection

    opt = CATALOG_BY_ID.get(req.model_id)
    if opt is None:
        raise HTTPException(status_code=400, detail=f"Unknown model {req.model_id!r}.")
    if opt.needs_key and not (req.api_key or _existing_key()):
        raise HTTPException(status_code=400, detail="This model requires an API key.")
    save_selection(req.model_id, api_key=req.api_key)
    reset_provider()
    return {"ok": True, "selected": req.model_id}


def _existing_key() -> bool:
    from ..llm.catalog import stored_api_key

    return bool(stored_api_key())


# --------------------------------------------------------------------------
# cards — auto-implementation via the selected model
# --------------------------------------------------------------------------
def _card_data(session: Session, card_name: str):
    for e in session.deck.entries:
        if e.card.name == card_name:
            return e.card
    return None


def _implement_one(session: Session, card_name: str) -> dict:
    from ..llm.card_codegen import CodegenError, generate_card

    card = _card_data(session, card_name)
    if card is None:
        raise HTTPException(status_code=404, detail=f"{card_name!r} is not in this deck.")
    if is_implemented(card_name):
        return {"name": card_name, "ok": True, "already": True}
    try:
        module = generate_card(card)
        return {"name": card_name, "ok": True, "module": module}
    except CodegenError as exc:
        return {"name": card_name, "ok": False, "error": str(exc)}


@app.post("/api/sessions/{session_id}/cards/{card_name}/implement")
def implement_card(session_id: str, card_name: str) -> dict:
    """Ask the selected model to write and register this card's behaviour."""
    result = _implement_one(_load(session_id), card_name)
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.post("/api/sessions/{session_id}/cards/implement-all")
def implement_all_cards(session_id: str) -> dict:
    """Ask the selected model to implement every unimplemented card in the
    deck. Returns a per-card report (some may fail — those stay unimplemented
    and keep their vanilla approximation)."""
    session = _load(session_id)
    names = []
    seen = set()
    for e in session.deck.entries:
        if e.card.name in seen or is_implemented(e.card.name):
            continue
        seen.add(e.card.name)
        names.append(e.card.name)
    results = [_implement_one(session, n) for n in names]
    return {
        "total": len(results),
        "implemented": sum(1 for r in results if r["ok"]),
        "results": results,
    }


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------
@app.post("/api/sessions/{session_id}/simulate")
async def simulate(session_id: str, req: SimulateRequest) -> dict:
    session = _load(session_id)
    session.mulligans = req.mulligans
    store.save(session)
    loop = asyncio.get_running_loop()
    seed = req.base_seed if req.base_seed is not None else random.randrange(1_000_000_000)
    from ..engine.simulator import SEARCH_MODES

    if req.search_mode not in SEARCH_MODES:
        raise HTTPException(status_code=400, detail=f"Unknown search mode: {req.search_mode}")
    config = SimConfig(
        num_games=req.num_games,
        timeout_per_game_s=req.timeout_per_game_s,
        mulligans=req.mulligans,
        on_the_play=req.on_the_play,
        base_seed=seed,
        search_mode=req.search_mode,
    )
    try:
        result_id = runner.start(session, config, loop)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "result_id": result_id, "seed": seed}


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


class _NoCacheStaticFiles(StaticFiles):
    """Static assets must revalidate on every load: the board-snapshot format
    and app.js evolve together, and a heuristically-cached stale app.js
    renders the new frames as grey "[object Object]" tiles."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Mounted last so /api/* and /ws/* take precedence.
app.mount("/static", _NoCacheStaticFiles(directory=_STATIC), name="static")
