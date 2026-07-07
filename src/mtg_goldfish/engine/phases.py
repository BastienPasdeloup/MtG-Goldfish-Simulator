"""Turn structure.

The ordered steps of a Magic turn. Property triggers reference these by name,
so the ordering here defines what "before/at <phase> of turn N" means and lets
the simulator compare two moments in time.
"""
from __future__ import annotations

import enum


class Phase(str, enum.Enum):
    UNTAP = "untap"
    UPKEEP = "upkeep"
    DRAW = "draw"
    PRECOMBAT_MAIN = "precombat_main"
    BEGIN_COMBAT = "begin_combat"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    COMBAT_DAMAGE = "combat_damage"
    END_COMBAT = "end_combat"
    POSTCOMBAT_MAIN = "postcombat_main"
    END_STEP = "end_step"
    CLEANUP = "cleanup"


#: Canonical turn order.
TURN_ORDER: tuple[Phase, ...] = tuple(Phase)

#: Steps in which the active player receives priority to take main-phase actions.
MAIN_PHASES = (Phase.PRECOMBAT_MAIN, Phase.POSTCOMBAT_MAIN)


def phase_index(phase: Phase) -> int:
    return TURN_ORDER.index(phase)


#: User-facing labels, in turn order, for the property builder dropdown.
def phase_labels() -> list[dict[str, str]]:
    pretty = {
        Phase.UNTAP: "Untap",
        Phase.UPKEEP: "Upkeep",
        Phase.DRAW: "Draw step",
        Phase.PRECOMBAT_MAIN: "Precombat main phase",
        Phase.BEGIN_COMBAT: "Beginning of combat",
        Phase.DECLARE_ATTACKERS: "Declare attackers",
        Phase.DECLARE_BLOCKERS: "Declare blockers",
        Phase.COMBAT_DAMAGE: "Combat damage",
        Phase.END_COMBAT: "End of combat",
        Phase.POSTCOMBAT_MAIN: "Postcombat main phase",
        Phase.END_STEP: "End step",
        Phase.CLEANUP: "Cleanup",
    }
    return [{"value": p.value, "label": pretty[p]} for p in TURN_ORDER]
