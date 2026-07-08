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


# Comparator phrases, checked in order; default is ">=".
_COMPARATORS = [
    (r"at least|no fewer than|no less than|or more|minimum of|>=", ">="),
    (r"at most|no more than|or fewer|or less|maximum of|<=", "<="),
    (r"more than|greater than|over|>", ">"),
    (r"fewer than|less than|under|<", "<"),
    (r"exactly|equal to|==|=", "=="),
]


def _find_num(c: str) -> int | None:
    # Prefer an explicit digit (e.g. "power 5") over an article like "a"/"an".
    m = re.search(r"-?\d+", c)
    if m:
        return int(m.group())
    for token in re.findall(r"\b[a-z]+\b", c):
        n = _num(token)
        if n is not None:
            return n
    return None


def _comparator(c: str) -> str:
    for pat, op in _COMPARATORS:
        if re.search(pat, c):
            return op
    return ">="


# Ordered (regex over the clause) -> int-valued state expression. First match wins.
_INT_METRICS: list[tuple[str, str]] = [
    (r"non-?creature spells?", "state.noncreature_spells_cast_this_turn"),
    (r"creature spells?", "state.creature_spells_cast_this_turn"),
    (r"spells? (?:have been )?cast|spells? cast", "state.spells_cast_this_turn"),
    (r"storm( count)?", "state.storm_count"),
    (r"cards? in (?:your |the )?graveyard|graveyard", "state.cards_in_graveyard()"),
    (r"drawn", "__DRAWN__"),
    (r"cards? in (?:your |the )?hand|hand size", "state.cards_in_hand()"),
    (r"lands? played", "state.lands_played_this_turn"),
    (r"lands?", "state.lands_in_play()"),
    (r"total toughness|combined toughness", "state.total_toughness()"),
    (r"total power|combined power", "state.total_power()"),
    (r"toughness", "state.total_toughness()"),
    (r"permanents?", "state.permanents_in_play()"),
    (r"creatures?", "state.creatures_in_play()"),
    (r"life( total)?", "state.life"),
]


def _compile_clause(clause: str) -> str | None:
    c = clause.lower().strip().rstrip(".")

    # ---- boolean clauses -------------------------------------------------
    if "commander" in c and ("play" in c or "battlefield" in c):
        return "state.commander_in_play()"

    m = re.search(r'"([^"]+)"\s+is in (?:play|the battlefield)', clause)
    if m:
        return f"state.has_permanent_named({m.group(1)!r})"

    op, n = _comparator(c), _find_num(c)

    # ---- "a creature with power N" (compares power, not a count) ----------
    if "creature" in c and "power" in c and "total" not in c and "combined" not in c and n is not None:
        return f"state.creatures_with_power_at_least({n}) >= 1"

    # ---- generic <metric> <comparator> <number> --------------------------
    if n is not None:
        for pat, expr in _INT_METRICS:
            if re.search(pat, c):
                if expr == "__DRAWN__":
                    expr = "state.cards_drawn_this_turn" if "this turn" in c else "state.cards_drawn"
                return f"{expr} {op} {n}"

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
