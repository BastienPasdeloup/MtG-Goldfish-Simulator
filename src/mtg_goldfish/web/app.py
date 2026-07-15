"""FastAPI application: deck import, sessions, property compilation, simulation."""
from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
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
from ..session import Session, SessionCorrupt, SessionStore, SimConfig, new_id, now_iso
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
    search_mode: str = "best_first"  # see engine.simulator.SEARCH_MODES
    # Fixed-hand mode: force this exact opening hand (card names); None = normal.
    fixed_hand: list[str] | None = None
    # Fixed-hand mode: pad the hand with random cards up to this size (None = no padding).
    fixed_hand_pad_to: int | None = None


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


def deck_flags(deck: Deck) -> dict:
    """Deck-level mechanics the board header adapts to: whether any card has
    the Storm keyword or produces/spends energy counters ({E})."""
    import re as _re

    storm = energy = False
    for e in deck.entries:
        text = e.card.oracle_text or ""
        # The Storm keyword appears as its own (reminder-texted) line; a plain
        # word-boundary match also catches it without matching names like
        # "Brainstorm" (names aren't in oracle_text).
        if not storm and _re.search(r"\bstorm\b", text, _re.I):
            storm = True
        if not energy and "{E}" in text:
            energy = True
        if storm and energy:
            break
    return {"storm": storm, "energy": energy}


def session_payload(session: Session) -> dict:
    return {
        "session": session.model_dump(),
        "cards": card_view(session.deck),
        "deck_flags": deck_flags(session.deck),
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
        "github_issues_url": f"https://github.com/{_GITHUB_REPO}/issues/new",
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
    session = _load(session_id)
    # A result still marked "running" while no simulation is live is a FAILED
    # run (the app or the run crashed mid-flight): drop it so the session
    # always loads clean instead of showing a ghost run forever.
    if not runner.is_running(session_id):
        alive = [r for r in session.results if r.status != "running"]
        if len(alive) != len(session.results):
            session.results = alive
            store.save(session)
    return session_payload(session)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    store.delete(session_id)
    return {"ok": True}


@app.get("/api/sessions/{session_id}/deck-check")
def deck_check(session_id: str) -> dict:
    """Compare the stored deck against its Moxfield source: has it changed
    since it was imported? Called asynchronously by the UI (network-bound)."""
    from ..deck.moxfield import deck_signature, fetch_deck_signature

    session = _load(session_id)
    url = session.deck.source_url
    if not url:
        return {"checked": False}
    try:
        current = fetch_deck_signature(url)
    except MoxfieldError as exc:
        return {"checked": False, "error": str(exc)}
    return {"checked": True, "changed": current != deck_signature(session.deck)}


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
# bug reports -> GitHub issues
# --------------------------------------------------------------------------
_GITHUB_REPO = os.environ.get("MTG_GITHUB_REPO", "BastienPasdeloup/MtG-Goldfish-Simulator")


@app.get("/api/sessions/{session_id}/bug-report-file")
def bug_report_file(session_id: str, result_id: str | None = None) -> Response:
    """Download a bug-report file: the session (deck + properties) and the
    current run in full (search trees stripped — they can reach tens of MB).
    Served as .txt so it can be dragged straight into a GitHub issue."""
    session = _load(session_id)
    result = next((r for r in session.results if r.id == result_id), None)
    run = None
    if result is not None:
        run = result.model_dump(exclude={"sample_success_logs"})
        for r in run.get("sample_runs", []):
            r.pop("tree_gz", None)
    payload = {
        "generated_at": now_iso(),
        "session": {
            "name": session.name,
            "format": session.format_id,
            "created_at": session.created_at,
            "deck_url": session.deck.source_url,
            "deck": [f"{e.quantity}x {e.card.name} [{e.board.value}]"
                     for e in session.deck.entries],
            "properties": [p.model_dump() for p in session.properties],
        },
        "run": run,
    }
    fname = f"mtg-goldfish-bug-report-{session.id}-{result_id or 'no-run'}.txt"
    return Response(
        content=json.dumps(payload, indent=1, ensure_ascii=False),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
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
        fixed_hand=(req.fixed_hand or None),
        fixed_hand_pad_to=(req.fixed_hand_pad_to if req.fixed_hand else None),
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
    except SessionCorrupt as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
