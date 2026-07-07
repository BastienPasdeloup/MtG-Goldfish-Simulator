"""Deterministic, offline LLM stub.

Used when no ANTHROPIC_API_KEY is configured (and in tests). It cannot truly
understand English, but it recognizes a handful of common property phrasings
via regex and emits working `check(state)` code for them. Anything it can't
parse compiles to `return False` with a comment, so the app still runs and the
user can hand-edit the generated code.

The English condition is located in the prompt after an `ENGLISH:` marker,
which `properties.compiler` always includes.
"""
from __future__ import annotations

import re

from .provider import LLMProvider

_NUM_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _num(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return _NUM_WORDS.get(token)


def _clauses(text: str) -> list[str]:
    # Split on ' and ' / commas so each clause can be matched independently.
    return [c.strip() for c in re.split(r"\band\b|,|;", text) if c.strip()]


def _compile_clause(clause: str) -> str | None:
    c = clause.lower().strip().rstrip(".")

    if "commander" in c and ("play" in c or "battlefield" in c):
        return "state.commander_in_play()"

    m = re.search(r"(\d+|\w+)\s+non-?creature spells?", c)
    if m and _num(m.group(1)) is not None:
        return f"state.noncreature_spells_cast_this_turn >= {_num(m.group(1))}"

    m = re.search(r"(\d+|\w+)\s+creature spells?", c)
    if m and _num(m.group(1)) is not None:
        return f"state.creature_spells_cast_this_turn >= {_num(m.group(1))}"

    m = re.search(r"(\d+|\w+)\s+spells? (?:have been )?cast", c)
    if m and _num(m.group(1)) is not None:
        return f"state.spells_cast_this_turn >= {_num(m.group(1))}"

    m = re.search(r"(\d+|\w+)\s+lands?\b", c)
    if m and _num(m.group(1)) is not None and "play" in c:
        return f"state.lands_in_play() >= {_num(m.group(1))}"

    m = re.search(r"(\d+|\w+)\s+creatures?\b", c)
    if m and _num(m.group(1)) is not None and "play" in c:
        return f"state.creatures_in_play() >= {_num(m.group(1))}"

    m = re.search(r"(\d+|\w+)\s+cards? in (?:your )?hand", c)
    if m and _num(m.group(1)) is not None:
        return f"state.cards_in_hand() >= {_num(m.group(1))}"

    m = re.search(r'"([^"]+)"\s+is in play', clause)
    if m:
        return f"state.has_permanent_named({m.group(1)!r})"

    return None


class StubProvider(LLMProvider):
    is_real = False

    @property
    def name(self) -> str:
        return "stub"

    def generate(self, system: str, prompt: str, *, max_tokens: int = 4096) -> str:
        m = re.search(r"ENGLISH:\s*(.+)", prompt, re.DOTALL)
        english = (m.group(1) if m else prompt).strip()

        exprs = [e for c in _clauses(english) if (e := _compile_clause(c))]
        if exprs:
            body = " and ".join(exprs)
            return (
                "def check(state):\n"
                f"    # Heuristically generated (offline stub) from: {english!r}\n"
                f"    return {body}\n"
            )
        return (
            "def check(state):\n"
            f"    # TODO: offline stub could not parse: {english!r}\n"
            "    # Add an ANTHROPIC_API_KEY for real compilation, or edit this.\n"
            "    return False\n"
        )
