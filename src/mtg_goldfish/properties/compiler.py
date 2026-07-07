"""Compile an English property condition into Python via the LLM provider."""
from __future__ import annotations

import re

from ..llm import LLMProvider, get_provider
from .api_doc import STATE_API_DOC
from .models import PropertySpec

_SYSTEM = f"""\
You translate a Magic: the Gathering board-state condition, written in plain \
English, into a single Python function.

{STATE_API_DOC}

Rules:
- Output ONLY a Python function, no prose, no markdown fences.
- The function MUST be named `check` and take one argument `state`.
- It MUST return a bool.
- Use ONLY the documented API and Python built-ins. Do NOT import anything.
- If the condition references a specific card, use has_permanent_named or \
count_on_battlefield with a predicate on card.name.

Example:
def check(state):
    return state.commander_in_play() and state.noncreature_spells_cast_this_turn >= 4
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    fence = re.match(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def compile_condition(english: str, provider: LLMProvider | None = None) -> str:
    """Return Python source defining `def check(state): ...` for `english`."""
    provider = provider or get_provider()
    prompt = f"Compile this condition into a `check(state)` function.\n\nENGLISH: {english}"
    raw = provider.generate(_SYSTEM, prompt, max_tokens=1024)
    code = _strip_fences(raw)
    if "def check" not in code:
        # Providers occasionally return a bare expression; wrap it.
        code = f"def check(state):\n    return {code.strip()}\n"
    return code


def compile_property(spec: PropertySpec, provider: LLMProvider | None = None) -> PropertySpec:
    """Return a copy of `spec` with its `code` field populated."""
    code = compile_condition(spec.english, provider=provider)
    return spec.model_copy(update={"code": code})
