"""Conversion — {2}{W}{W} Enchantment.
At the beginning of your upkeep, sacrifice this enchantment unless you pay {W}{W}.
All Mountains are Plains.

"All Mountains are Plains" is modelled as overriding every Mountain's mana to {W}
(applied to Mountains present when it enters and any that enter later; removed
when it leaves). The upkeep tax pays {W}{W} to keep it if able (and there is a
Mountain worth keeping), else it is sacrificed."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card
from .registry import register


def _is_mountain(p):
    return p.is_land and "mountain" in p.type_line.lower()


@register
class Conversion(Card):
    card_name = "Conversion"
    trigger_phase = Phase.UPKEEP

    def on_etb(self, state, permanent):
        for p in state.battlefield:
            if _is_mountain(p):
                p.mana_override = "W"

    def on_other_etb(self, state, perm, entering):
        if _is_mountain(entering):
            entering.mana_override = "W"

    def on_leave(self, state, perm):
        for p in state.battlefield:
            if _is_mountain(p) and p.mana_override == "W":
                p.mana_override = None

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("W", 1), ("W", 1)))
        worth = any(_is_mountain(p) for p in state.battlefield)
        if worth and can_afford(state, cost) and pay_cost(state, cost):
            state.emit("Conversion: pay {W}{W} (kept)")
            return None
        state.emit("Conversion: not paid — sacrifice")
        p = state.find_permanent(perm.uid)
        if p is not None:
            state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None
