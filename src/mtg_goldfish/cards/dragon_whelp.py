"""Dragon Whelp — {2}{R}{R} Creature — Dragon 2/3. Flying.
{R}: This creature gets +1/+0 until end of turn. If this ability has been
activated four or more times this turn, sacrifice this creature at the beginning
of the next end step.

Firebreathing with the classic drawback: the 4th (or later) activation this turn
marks it to be sacrificed at end step (via the end_step_sac counter)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class DragonWhelp(Card):
    card_name = "Dragon Whelp"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is None:
                return None
            p.temp_power += 1
            n = p.turn_flags.get("whelp_fb", 0) + 1
            p.turn_flags["whelp_fb"] = n
            if n >= 4:
                p.counters["end_step_sac"] = 1
            st.emit(f"Dragon Whelp: +1/+0 (firebreathing #{n})"
                    + (" — will be sacrificed at end step" if n >= 4 else ""))
            return None

        return [CardAction.activated(
            "Dragon Whelp: {R} — +1/+0 until end of turn",
            pay, resolve, source_name="Dragon Whelp",
            ability_text="+1/+0 until end of turn")]
