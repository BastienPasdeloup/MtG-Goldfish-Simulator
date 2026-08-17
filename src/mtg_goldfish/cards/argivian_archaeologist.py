"""Argivian Archaeologist — {1}{W}{W} Creature — Human Artificer 1/1.
{W}{W}, {T}: Return target artifact card from your graveyard to your hand.

One branch per distinct artifact card in your graveyard; taps."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class ArgivianArchaeologist(Card):
    card_name = "Argivian Archaeologist"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("W", 2),))
        if perm.tapped or not can_afford(state, cost):
            return []
        names, seen = [], set()
        for c in state.graveyard:
            if c.is_artifact and c.name not in seen:
                seen.add(c.name)
                names.append(c.name)
        acts = []
        for name in names:
            def make(name=name):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped or not pay_cost(st, cost):
                        return False
                    p.tapped = True
                    return True

                def resolve(st):
                    for i, c in enumerate(st.graveyard):
                        if c.name == name and c.is_artifact:
                            st.hand.append(st.graveyard.pop(i))
                            st.emit(f"Argivian Archaeologist: return {name} to hand")
                            break
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Argivian Archaeologist: {{W}}{{W}}, {{T}} → return {name} to hand",
                pay, resolve, source_name="Argivian Archaeologist",
                ability_text="Return target artifact card from your graveyard to your hand"))
        return acts
