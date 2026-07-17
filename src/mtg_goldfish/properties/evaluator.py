"""Turn a `PropertySpec` into a runnable `CompiledProperty` for the simulator.

The compiled code is `exec`'d in a restricted namespace: no imports, only a
small set of safe built-ins. This is a local, single-user deck-testing tool, so
this is a pragmatic sandbox — not a defense against hostile code. The bigger
risk is buggy generated code, which we contain by catching exceptions during
evaluation (the simulator treats a raising property as "not satisfied").
"""
from __future__ import annotations

from ..engine.game_state import GameState
from ..engine.phases import Phase
from .models import PropertySpec

_SAFE_BUILTINS = {
    "len": len, "sum": sum, "any": any, "all": all, "min": min, "max": max,
    "sorted": sorted, "range": range, "abs": abs, "round": round,
    "bool": bool, "int": int, "float": float, "str": str, "set": set,
    "list": list, "dict": dict, "tuple": tuple, "enumerate": enumerate,
    "zip": zip, "filter": filter, "map": map, "True": True, "False": False,
    "None": None,
}


class CompilationError(ValueError):
    pass


class CompiledProperty:
    """Implements the protocol the simulator consumes (see engine.simulator)."""

    def __init__(self, spec: PropertySpec) -> None:
        if not spec.code:
            raise CompilationError(f"Property {spec.id!r} has no compiled code.")
        # The originating spec is kept around: it is picklable (the compiled
        # `check` function is not), so parallel simulation workers recompile
        # from it on their side of the process boundary.
        self.spec = spec
        self.id = spec.id
        self.description = spec.describe()
        self.timing = spec.timing.value
        self.phase = Phase(spec.phase)
        self.turn = spec.turn
        self._check = self._build(spec.code)

    @staticmethod
    def _build(code: str):
        namespace: dict = {"__builtins__": _SAFE_BUILTINS}
        try:
            exec(compile(code, "<property>", "exec"), namespace)  # noqa: S102
        except Exception as exc:  # syntax / name errors at definition time
            raise CompilationError(f"Could not compile property code: {exc}") from exc
        check = namespace.get("check")
        if not callable(check):
            raise CompilationError("Compiled code does not define a callable `check`.")
        return check

    def evaluate(self, state: GameState) -> bool:
        return bool(self._check(state))


def compile_all(specs: list[PropertySpec]) -> list[CompiledProperty]:
    return [CompiledProperty(s) for s in specs if s.enabled and s.code]
