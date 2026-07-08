"""Bruce Banner // The Incredible Hulk — {U} Legendary Creature 1/1.
{X}{X}, {T}: Draw X cards (sorcery; X values are branches).
{2}{R}{R}{G}{G}: Transform into The Incredible Hulk (8/8 reach trample).
The Hulk's Enrage (combat-facing) is not modelled — no opponent damages him."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import transform_actions
from .base import Card, CardAction
from .registry import register


@register
class BruceBanner(Card):
    card_name = "Bruce Banner // The Incredible Hulk"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        actions = []
        if not perm.transformed and not perm.tapped and not perm.summoning_sick:
            for x in range(1, 8):
                cost = ManaCost(generic=2 * x)
                if not can_afford(state, cost):
                    break

                def make(xx: int, cst: ManaCost):
                    def fn(st):
                        p = st.find_permanent(perm.uid)
                        if p is None or p.tapped or p.transformed or not pay_cost(st, cst):
                            return None
                        p.tapped = True
                        st.emit(f"Bruce Banner: {{X={xx}}}{{X}}, {{T}} — draw {xx}")
                        st.draw(xx)
                        return None
                    return fn

                actions.append(CardAction(f"Bruce Banner: draw {x} (X={x})", make(x, cost)))
        actions.extend(transform_actions(
            state, perm,
            ManaCost(generic=2, pips=(("R", 2), ("G", 2))),
            "The Incredible Hulk",
        ))
        return actions
