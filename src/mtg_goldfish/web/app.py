"""FastAPI application: deck import, sessions, property compilation, simulation."""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import __version__, __version_base__
from ..cards import is_implemented, load_all_cards
from ..config import CONFIG
from ..deck import MoxfieldError, MTGTop8Error, ScryfallError, import_deck
from ..deck.models import Deck
from ..engine.phases import phase_labels
from ..formats import get_format, list_formats
from ..llm import get_provider
from ..properties import (
    STATE_API_DOC,
    PropertySpec,
    compile_condition,
    compile_condition_detailed,
)
from ..session import (
    FixedConfig, Session, SessionCorrupt, SessionStore, SimConfig, new_id, now_iso,
)
from .hub import HUB
from .sim_runner import SimulationRunner

_STATIC = Path(__file__).parent / "static"
#: Repo root (src/mtg_goldfish/web/app.py -> ../../../). Used for the git-based
#: update check.
_REPO_ROOT = Path(__file__).resolve().parents[3]

app = FastAPI(title="MtG Goldfish Simulator")
store = SessionStore()
runner = SimulationRunner(store)


def _git(*args: str) -> str | None:
    """Run a git command in the repo root; None if git/repo is unavailable."""
    try:
        out = subprocess.run(["git", *args], cwd=_REPO_ROOT,
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout.strip() or None) if out.returncode == 0 else None


def _origin_owner_repo() -> str:
    """`owner/repo` parsed from the git origin remote (so a fork checks itself),
    falling back to the canonical repo."""
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", _git("remote", "get-url", "origin") or "")
    return m.group(1) if m else _GITHUB_REPO


# --------------------------------------------------------------------------
# request/response models
# --------------------------------------------------------------------------
class ImportRequest(BaseModel):
    url: str
    name: str
    # Inferred from the deck source when omitted (the UI no longer asks for it).
    format_id: str | None = None


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
    instant_speed: bool = False  # explore instant-speed plays (see SimConfig)
    fake_shuffle: bool = False  # never really reorder the library (see SimConfig)
    # Fixed-hand mode: force this exact opening hand (card names); None = normal.
    fixed_hand: list[str] | None = None
    # Fixed-hand mode: pad the hand with random cards up to this size (None = no padding).
    fixed_hand_pad_to: int | None = None
    # Fixed-config mode: a fully-specified starting state; None = normal.
    fixed_config: FixedConfig | None = None


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
_COUNTER_STOPWORDS = {"each", "that", "those", "many", "the", "a", "of", "no", "any",
                      "some", "this", "these", "time", "with", "for", "one", "two",
                      "three", "or", "and", "its", "their", "such", "another"}


def _initial_counters(card) -> dict[str, int]:
    """Counters a permanent of `card` ENTERS the battlefield with (planeswalker
    loyalty, Peter Parker's Camera's film, a Saga's first lore counter, ...), so
    the Fixed-config editor can initialise it to the correct count."""
    from ..cards import build_card
    from ..engine.game_state import GameState
    try:
        cs = dict(build_card(card).enters_with_counters(GameState()))
    except Exception:
        cs = {}
    if "saga" in card.type_line.lower():
        cs.setdefault("lore", 1)  # a Saga enters with its first lore counter
    return {k: int(v) for k, v in cs.items() if v}


def _counter_kinds(card) -> list[str]:
    """Counter kinds this card deals in — scanned from its oracle text ("+1/+1
    counters", "lore counter", ...) plus the ones it enters with and the ones
    implied by its type — so the editor's "Add counter" menu can list them."""
    kinds: list[str] = []
    for k in re.findall(r"([+\-]?[A-Za-z0-9/][A-Za-z0-9+\-/]*)\s+counters?",
                        card.oracle_text or "", re.I):
        k = k.strip().lower()
        if k and k not in _COUNTER_STOPWORDS and k not in kinds:
            kinds.append(k)
    head = card.type_line.split("—")[0].lower()
    if "creature" in head:
        for k in ("+1/+1", "-1/-1"):
            if k not in kinds:
                kinds.append(k)
    if "planeswalker" in head and "loyalty" not in kinds:
        kinds.append("loyalty")
    for k in _initial_counters(card):
        if k not in kinds:
            kinds.append(k)
    return kinds


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
                "loyalty": f.loyalty,  # for the Fixed-config editor (flipped planeswalkers)
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
            "loyalty": c.loyalty,  # for the Fixed-config editor (planeswalkers)
            "enters_counters": _initial_counters(c),  # counters it enters play with
            "counter_kinds": _counter_kinds(c),       # counter kinds it can carry
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


_TOKEN_LIST_CACHE: dict[tuple, list[dict]] = {}
_TOKEN_SEARCH_CACHE: dict[str, list[dict]] = {}


def _int_or_none(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def deck_tokens(deck: Deck) -> list[dict]:
    """The token permanents the deck's cards can create, resolved from Scryfall's
    `all_parts` (authoritative name / type / P/T / colour / SCAN image). Cards
    cached before token_parts existed are re-fetched once. Cached per deck; the
    "Add token…" prompt still covers anything not found."""
    from ..deck.scryfall import ScryfallClient

    sig = tuple(sorted(e.card.name for e in deck.entries))
    if sig in _TOKEN_LIST_CACHE:
        return _TOKEN_LIST_CACHE[sig]

    sc = ScryfallClient()
    seen: dict[tuple, dict] = {}
    for e in deck.entries:
        card = e.card
        if "token" not in (card.oracle_text or "").lower():
            continue
        parts = card.token_parts
        if not parts:  # cached before token_parts existed — refresh once
            try:
                parts = sc.get_named(card.name, refresh=True).token_parts
            except Exception:
                parts = []
        for tp in parts:
            tok = sc.get_by_id(tp.get("scryfall_id"))
            if tok is not None:
                is_creature = "creature" in tok.type_line.split("—")[0].lower()
                spec = {"name": tok.name, "type_line": tok.type_line,
                        "power": _int_or_none(tok.power) if is_creature else None,
                        "toughness": _int_or_none(tok.toughness) if is_creature else None,
                        "colors": list(tok.colors or []), "image": tok.image}
            else:  # no image, but keep the name/type from all_parts
                spec = {"name": tp.get("name") or "Token",
                        "type_line": tp.get("type_line") or "Token",
                        "power": None, "toughness": None, "colors": [], "image": None}
            key = (spec["name"], spec["power"], spec["toughness"], tuple(spec["colors"]))
            seen.setdefault(key, spec)

    result = sorted(seen.values(), key=lambda t: t["name"])
    _TOKEN_LIST_CACHE[sig] = result
    return result


def session_payload(session: Session) -> dict:
    data = session.model_dump()
    # The per-run search trees (`tree_gz`) can total well over 1 GB across all
    # results — far more than a browser can JSON.parse (strings are capped near
    # 512 MB, so a huge payload fails to open with an opaque error). Strip them
    # here and expose a `has_tree` flag; the tree viewer fetches a single run's
    # tree on demand via the results/{id}/runs/{i}/tree endpoint.
    for result in data.get("results", []):
        for run in result.get("sample_runs", []):
            run["has_tree"] = bool(run.get("tree_gz") or run.get("tree"))
            run.pop("tree_gz", None)
    return {
        "session": data,
        "cards": card_view(session.deck),
        "deck_flags": deck_flags(session.deck),
        "tokens": deck_tokens(session.deck),
    }


# --------------------------------------------------------------------------
# static + meta
# --------------------------------------------------------------------------
@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    """Fallback for pages without a <link rel="icon"> (e.g. the tree viewer
    tabs opened via document.write): browsers then request /favicon.ico from
    the site root, and every modern browser accepts an SVG there as long as
    the media type says so."""
    return FileResponse(_STATIC / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/tokens/search")
def token_search(q: str = "") -> dict:
    """Search Scryfall for token cards matching a name, so the fixed-config
    "Add token…" popup can offer real candidates (with scans / P·T / colours).
    Returns distinct tokens deduped by name + P/T + colours."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"tokens": []}
    key = q.lower()
    if key in _TOKEN_SEARCH_CACHE:
        return {"tokens": _TOKEN_SEARCH_CACHE[key]}

    import httpx

    from ..deck.scryfall import SCRYFALL_API, card_data_from_scryfall

    out: list[dict] = []
    try:
        resp = httpx.get(
            f"{SCRYFALL_API}/cards/search",
            params={"q": f"type:token {q}", "unique": "cards"},
            headers={"User-Agent": "MtGGoldfishSimulator/0.1 (personal deck-testing tool)"},
            timeout=15,
        )
        if resp.status_code == 200:
            seen: set[tuple] = set()
            for raw in resp.json().get("data", []):
                card = card_data_from_scryfall(raw)
                is_creature = "creature" in card.type_line.split("—")[0].lower()
                spec = {
                    "name": card.name,
                    "type_line": card.type_line,
                    "power": _int_or_none(card.power) if is_creature else None,
                    "toughness": _int_or_none(card.toughness) if is_creature else None,
                    "colors": list(card.colors or []),
                    "image": card.image,
                }
                k = (spec["name"], spec["power"], spec["toughness"], tuple(spec["colors"]))
                if k in seen:
                    continue
                seen.add(k)
                out.append(spec)
                if len(out) >= 40:
                    break
    except Exception:
        out = []
    _TOKEN_SEARCH_CACHE[key] = out
    return {"tokens": out}


@app.get("/api/meta")
def meta() -> dict:
    return {
        "version": __version__,
        "formats": [{"id": f.id, "name": f.name} for f in list_formats()],
        "phases": phase_labels(),
        "property_api_doc": STATE_API_DOC,
        "llm_provider": get_provider().name,
        "llm_is_real": get_provider().is_real,
        "github_issues_url": f"https://github.com/{_GITHUB_REPO}/issues/new",
    }


@app.get("/api/version-check")
def version_check() -> dict:
    """Is the repository's `main` ahead of this checkout? Since the version is
    derived from the git commit count (not a literal in the code), this compares
    the local git HEAD to `main` via GitHub's compare API. Returns
    `checked=False` for a non-git install (ZIP download), an unpushed local
    commit, or when GitHub is unreachable, so the UI simply shows nothing."""
    import httpx

    local_sha = _git("rev-parse", "HEAD")
    if not local_sha:
        return {"checked": False}  # not a git checkout (e.g. a ZIP download)
    owner_repo = _origin_owner_repo()
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{owner_repo}/compare/{local_sha}...main",
            headers={"User-Agent": "mtg-goldfish-simulator",
                     "Accept": "application/vnd.github+json"},
            timeout=6.0,
        )
    except Exception:  # offline, DNS, timeout…
        return {"checked": False}
    if resp.status_code != 200:  # e.g. the local commit isn't on GitHub yet
        return {"checked": False}
    behind = int(resp.json().get("behind_by") or 0)
    local_count = _git("rev-list", "--count", "HEAD")
    remote = (f"{__version_base__}.{int(local_count) + behind}"
              if local_count and local_count.isdigit() else __version__)
    return {
        "checked": True,
        "update_available": behind > 0,
        "local": __version__,
        "remote": remote,
        "repo_url": f"https://github.com/{owner_repo}",
        "download_url": f"https://github.com/{owner_repo}/archive/refs/heads/main.zip",
    }


# --------------------------------------------------------------------------
# deck import (preview) + session creation
# --------------------------------------------------------------------------
@app.post("/api/deck/preview")
def deck_preview(req: ImportRequest) -> dict:
    try:
        result = import_deck(req.url, req.name, req.format_id)
    except (MoxfieldError, MTGTop8Error, ScryfallError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    problems = get_format(result.deck.format_id).validate(result.deck)
    return {
        "deck": result.deck.to_public(),
        "cards": card_view(result.deck),
        "warnings": result.warnings,
        "problems": problems,
    }


@app.post("/api/sessions")
def create_session(req: ImportRequest) -> dict:
    try:
        result = import_deck(req.url, req.name, req.format_id)
    except (MoxfieldError, MTGTop8Error, ScryfallError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session = Session(
        id=new_id(),
        name=req.name,
        format_id=result.deck.format_id,
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
    # A result still marked "running" while no simulation is live means the
    # app (or the run) crashed mid-flight. The run is persisted after every
    # completed game, so KEEP what was saved: mark it "interrupted" — it stays
    # loadable from "Previous runs" and can be resumed.
    if not runner.is_running(session_id):
        changed = False
        for r in session.results:
            if r.status == "running":
                r.status = "interrupted"
                changed = True
        if changed:
            store.save(session)
    return session_payload(session)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    store.delete(session_id)
    return {"ok": True}


@app.delete("/api/sessions/{session_id}/results")
def delete_all_results(session_id: str) -> dict:
    """Remove every stored run of the session."""
    if runner.is_running(session_id):
        raise HTTPException(status_code=409,
                            detail="A simulation is running — stop it first.")
    session = _load(session_id)
    session.results = []
    store.save(session)
    return {"ok": True, "num_results": 0}


@app.delete("/api/sessions/{session_id}/results/{result_id}")
def delete_result(session_id: str, result_id: str) -> dict:
    """Remove one stored run of the session."""
    session = _load(session_id)
    target = next((r for r in session.results if r.id == result_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if target.status == "running" and runner.is_running(session_id):
        raise HTTPException(status_code=409,
                            detail="This run is still in progress — stop it first.")
    session.results = [r for r in session.results if r.id != result_id]
    store.save(session)
    return {"ok": True, "num_results": len(session.results)}


@app.get("/api/sessions/{session_id}/results/{result_id}/runs/{game_index}/tree")
def run_tree(session_id: str, result_id: str, game_index: int) -> dict:
    """One game's gzip+base64 search tree, fetched on demand when the user opens
    the tree viewer. Kept out of the session payload because these blobs can be
    huge (see `session_payload`)."""
    session = _load(session_id)
    result = next((r for r in session.results if r.id == result_id), None)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run = next((sr for sr in result.sample_runs
                if sr.get("game_index") == game_index), None)
    if run is None or not run.get("tree_gz"):
        raise HTTPException(status_code=404, detail="No search tree for this game")
    return {"tree_gz": run["tree_gz"], "tree_truncated": run.get("tree_truncated", False)}


@app.get("/api/sessions/{session_id}/deck-check")
def deck_check(session_id: str) -> dict:
    """Compare the stored deck against its source (Moxfield/MTGTop8): has it
    changed since it was imported? Called asynchronously by the UI."""
    from ..deck import deck_signature, fetch_deck_signature

    session = _load(session_id)
    url = session.deck.source_url
    if not url:
        return {"checked": False}
    try:
        current = fetch_deck_signature(url, session.deck.format_id)
    except (MoxfieldError, MTGTop8Error) as exc:
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


def _deck_card_names(deck: Deck) -> list[str]:
    """Distinct card names in the deck (commanders + mainboard) so the compiler
    can resolve approximate names in a condition to their exact full name."""
    return sorted({e.card.name for e in deck.entries})


@app.post("/api/sessions/{session_id}/properties/compile")
def compile_properties(session_id: str) -> dict:
    session = _load(session_id)
    names = _deck_card_names(session.deck)
    warnings: list[str] = []
    for i, spec in enumerate(session.properties, 1):
        if not spec.enabled:
            continue
        if not spec.english.strip():
            # An empty condition: don't fabricate placeholder code — leave it
            # uncompiled and tell the user (the run simply ignores it).
            spec.code = None
            spec.confidence = None
            spec.compile_note = None
            spec.manual = False
            warnings.append(
                f"Property {i} ({spec.timing.value} {spec.phase} of turn "
                f"{spec.turn}) has no condition — nothing was compiled for it."
            )
            continue
        if not spec.code:
            try:
                r = compile_condition_detailed(spec.english, names)
                spec.code = r["code"]
                spec.confidence = r["confidence"]
                spec.compile_note = r["notes"]
            except Exception as exc:  # noqa: BLE001 - surface per-property
                spec.code = f"# compilation error: {exc}\ndef check(state):\n    return False\n"
                spec.confidence = "low"
                spec.compile_note = f"compilation failed: {exc}"
            # Freshly generated (not hand-edited): the UI shows model confidence.
            spec.manual = False
    store.save(session)
    return {"properties": [p.model_dump() for p in session.properties], "warnings": warnings}


@app.post("/api/sessions/{session_id}/properties/{prop_id}/compile")
def compile_one_property(session_id: str, prop_id: str) -> dict:
    """Compile a SINGLE property from its English (the per-property Compile
    button). Only the targeted property is touched; a click means "recompile
    this one", so it overwrites any existing (incl. hand-edited) code."""
    session = _load(session_id)
    spec = next((s for s in session.properties if s.id == prop_id), None)
    if spec is None:
        raise HTTPException(status_code=404, detail="Property not found.")
    warnings: list[str] = []
    if not spec.english.strip():
        spec.code = None
        spec.confidence = None
        spec.compile_note = None
        spec.manual = False
        warnings.append("This property has no condition — nothing was compiled.")
    else:
        try:
            r = compile_condition_detailed(spec.english, _deck_card_names(session.deck))
            spec.code = r["code"]
            spec.confidence = r["confidence"]
            spec.compile_note = r["notes"]
        except Exception as exc:  # noqa: BLE001 - surface per-property
            spec.code = f"# compilation error: {exc}\ndef check(state):\n    return False\n"
            spec.confidence = "low"
            spec.compile_note = f"compilation failed: {exc}"
        spec.manual = False  # freshly generated, not hand-edited
    store.save(session)
    return {"property": spec.model_dump(), "warnings": warnings}


@app.post("/api/sessions/{session_id}/properties/validate")
def validate_properties(session_id: str) -> dict:
    """Check that every enabled property has valid, runnable code — WITHOUT
    recompiling (so hand-edited code is checked as-is). Called when the user
    clicks Run: the run is only allowed to start when `ok` is true.

    Returns per-property validity (keyed by id) plus human-readable `warnings`
    for anything that would block the run."""
    from ..properties import CompiledProperty

    session = _load(session_id)
    results: dict[str, dict] = {}
    warnings: list[str] = []
    enabled = 0
    for i, spec in enumerate(session.properties, 1):
        if not spec.enabled:
            continue
        enabled += 1
        label = (f"Property {i} ({spec.timing.value} {spec.phase} of turn "
                 f"{spec.turn})")
        if not (spec.code and spec.code.strip()):
            results[spec.id] = {"valid": False, "problem": "no code"}
            warnings.append(
                f"{label} has no code — compile it or write the code manually "
                f"before running.")
            continue
        try:
            CompiledProperty(spec)  # compiles the code and checks `check` exists
            results[spec.id] = {"valid": True, "problem": None}
        except Exception as exc:  # noqa: BLE001 - surface per-property
            results[spec.id] = {"valid": False, "problem": str(exc)}
            warnings.append(f"{label}: the code is invalid — {exc}")
    if enabled == 0:
        warnings.append("Add at least one enabled property before running.")
    ok = enabled > 0 and not any(not r["valid"] for r in results.values())
    return {"ok": ok, "results": results, "warnings": warnings}


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
        instant_speed=req.instant_speed,
        fake_shuffle=req.fake_shuffle,
        fixed_hand=(req.fixed_hand or None),
        fixed_hand_pad_to=(req.fixed_hand_pad_to if req.fixed_hand else None),
        fixed_config=req.fixed_config,
    )
    try:
        result_id = runner.start(session, config, loop)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "result_id": result_id, "seed": seed}


@app.post("/api/sessions/{session_id}/results/{result_id}/resume")
async def resume_simulation(session_id: str, result_id: str) -> dict:
    """Continue a stopped or interrupted run: re-runs exactly the games that
    never completed, appending to the stored entry (same seeds, same config)."""
    session = _load(session_id)
    loop = asyncio.get_running_loop()
    try:
        runner.resume(session, result_id, loop)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = next(r for r in session.results if r.id == result_id)
    return {"ok": True, "result_id": result_id, "seed": result.config.base_seed}


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
