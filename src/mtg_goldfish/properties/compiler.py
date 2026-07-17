"""Compile an English property condition into Python via the LLM provider."""
from __future__ import annotations

import json
import re

from ..llm import LLMProvider, get_provider
from .api_doc import STATE_API_DOC
from .models import PropertySpec

_SYSTEM = f"""\
You translate a Magic: the Gathering board-state condition, written in plain \
English, into a single Python function.

{STATE_API_DOC}

Rules:
- The function MUST be named `check`, take one argument `state`, and return a bool.
- Use ONLY the documented API and Python built-ins. Do NOT import anything.
- If the condition references a specific card, use has_permanent_named / \
count_on_battlefield / the history helpers with the card's EXACT full name.
- RESOLVE APPROXIMATE CARD NAMES to the exact full name of a card in the deck \
(a list is provided). E.g. "Nick Fury" -> "Nick Fury, Agent of S.H.I.E.L.D.", \
"Bolt" -> "Lightning Bolt". If a referenced card matches no deck card, or an \
approximate name is ambiguous between several deck cards, say so in `notes` and \
lower your confidence.
- DISTINGUISH the player's ACTION from a permanent ENTERING the battlefield.
  "plays / casts X", "X is played/cast" -> played_on / cast_on.
  "X enters / comes into play / is put onto the battlefield / you get X" \
-> entered_battlefield (or permanents_put_by / cards_put_by).
  These are NOT interchangeable: a fetched land or a token ENTERS but is not \
"played/cast"; a countered spell was "cast" but never entered. Read the \
English literally. Only use has_permanent_named/state.turn for "X is on the \
battlefield right now"; for anything that HAPPENED on/by/before a turn, use the \
game-history helpers above.
- For "an ability activated / resolved / found something", use \
ability_activated / trigger_resolved / ability_succeeded / cards_put_by / \
cards_drawn_by, or count_events for anything else.
- When the English says an ability DID something — "X uses its <ability>, which \
puts a creature into play", "X's ability draws two cards" — BIND the outcome to \
that ability in ONE assertion via the source + via_kind, e.g. \
permanents_put_by(source, via_kind="activated"/"triggered", creature=True) or \
cards_put_by(source, via_kind=...) / cards_drawn_by(source). Do NOT split it \
into "the ability was activated" AND a separate board/global check (e.g. \
ability_activated(X) and creatures_in_play() >= 1): that passes even when some \
OTHER effect produced the result. The property is that THIS ability caused it. \
"uses / activates its ability" -> via_kind="activated"; "its triggered ability / \
when ... triggers" -> via_kind="triggered".
- Commander leaving play / the command zone: "the commander leaves play / dies / \
is exiled" -> commander_left_play(...); "the commander leaves play AND returns \
to the command zone" (or just "returns to the command zone") -> \
commander_returned_to_command_zone(...). Do NOT invent has_permanent-in-command-zone \
checks for this — use these helpers.

OUTPUT FORMAT — respond with ONLY a single JSON object, no prose, no markdown:
{{"code": "def check(state):\\n    return ...\\n",
  "confidence": "high" | "medium" | "low",
  "notes": "<one short line: resolved card names, and/or what extra detail \
would remove ambiguity — empty string if the translation is unambiguous>"}}

Set confidence to:
- "high"  — the English is unambiguous and every card name resolved cleanly.
- "medium"— you made a reasonable interpretation of a slightly vague condition.
- "low"   — the condition is ambiguous, under-specified, or names a card not in \
the deck; explain in `notes` what detail is needed.

Example output:
{{"code": "def check(state):\\n    return state.commander_in_play() and state.noncreature_spells_cast_this_turn >= 4\\n", "confidence": "high", "notes": ""}}
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    fence = re.match(r"```(?:python|json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _normalize_code(code: str) -> str:
    """Ensure we have a `def check(state): ...` function."""
    code = _strip_fences(code).strip()
    if "def check" not in code:
        # A bare expression — wrap it.
        code = f"def check(state):\n    return {code}\n"
    return code


def _extract_json(raw: str) -> dict | None:
    """Best-effort parse of a single JSON object from the model output (which
    may be fenced or have leading/trailing prose)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        text = text[start:end + 1]
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _build_prompt(english: str, card_names: list[str] | None) -> str:
    parts = ["Compile this condition into a `check(state)` function."]
    if card_names:
        listing = ", ".join(sorted(set(card_names)))
        parts.append(
            "\nCards in the deck (resolve any approximate card name in the "
            f"condition to the EXACT name from this list):\n{listing}"
        )
    # The ENGLISH line MUST come last: the offline stub reads everything after
    # the `ENGLISH:` marker as the condition.
    parts.append(f"\nENGLISH: {english}")
    return "\n".join(parts)


def compile_condition_detailed(
    english: str,
    card_names: list[str] | None = None,
    provider: LLMProvider | None = None,
) -> dict:
    """Compile `english`, resolving approximate card names against `card_names`.
    Returns {"code", "confidence", "notes"}. `confidence`/`notes` are None when
    the provider doesn't report them (e.g. the offline stub)."""
    provider = provider or get_provider()
    raw = provider.generate(_SYSTEM, _build_prompt(english, card_names), max_tokens=1024)
    obj = _extract_json(raw)
    if obj and obj.get("code"):
        conf = (obj.get("confidence") or "").strip().lower() or None
        if conf not in (None, "high", "medium", "low"):
            conf = None
        notes = (obj.get("notes") or obj.get("note") or "").strip() or None
        return {"code": _normalize_code(str(obj["code"])), "confidence": conf, "notes": notes}
    # No JSON (offline stub, or a model that ignored the format): treat the
    # whole output as code, with confidence unknown.
    return {"code": _normalize_code(raw), "confidence": None, "notes": None}


def compile_condition(
    english: str,
    card_names: list[str] | None = None,
    provider: LLMProvider | None = None,
) -> str:
    """Return Python source defining `def check(state): ...` for `english`."""
    return compile_condition_detailed(english, card_names, provider)["code"]


def compile_property(
    spec: PropertySpec,
    card_names: list[str] | None = None,
    provider: LLMProvider | None = None,
) -> PropertySpec:
    """Return a copy of `spec` with its `code`/`confidence`/`compile_note` set."""
    r = compile_condition_detailed(spec.english, card_names, provider=provider)
    return spec.model_copy(update={
        "code": r["code"], "confidence": r["confidence"], "compile_note": r["notes"],
    })
