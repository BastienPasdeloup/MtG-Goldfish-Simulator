"""Property model.

A property is a user-authored assertion checked at a specific trigger moment:
"{before|at} {phase} of turn {N}, <English condition>". The English is compiled
to Python (`code`) by the LLM compiler; the evaluator turns a spec into a
runnable `CompiledProperty` for the simulator.
"""
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class Timing(str, enum.Enum):
    BEFORE = "before"
    AT = "at"


class PropertySpec(BaseModel):
    id: str
    timing: Timing = Timing.AT
    phase: str = "precombat_main"  # Phase.value
    turn: int = 1
    english: str = ""
    code: str | None = None  # compiled `def check(state): ...`
    enabled: bool = True
    # Set by the LLM compiler: how sure it is the code matches the English
    # ("high" | "medium" | "low"), and a short note — resolved card names, or
    # what extra detail would make the translation unambiguous.
    confidence: str | None = None
    compile_note: str | None = None

    def describe(self) -> str:
        return f"{self.timing.value} {self.phase} of turn {self.turn}: {self.english}"
