"""Candelabra of Tawnos — {1} Artifact.
{X}, {T}: Untap X target lands.

Untap up to X of your tapped lands (paying {X}). Comboes with lands that produce
more than one mana — one branch per X (1..tapped lands you can afford)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class CandelabraOfTawnos(Card):
    card_name = "Candelabra of Tawnos"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped:
            return []
        tapped_lands = [p.uid for p in state.battlefield if p.is_land and p.tapped]
        if not tapped_lands:
            return []
        acts = []
        for x in range(1, len(tapped_lands) + 1):
            cost = ManaCost(generic=x)
            if not can_afford(state, cost, exclude_uids={perm.uid}):
                break

            def build(x=x, cost=cost):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped or not pay_cost(st, cost, exclude_uids={src.uid}):
                        return False
                    src.tapped = True
                    return True

                def resolve(st):
                    lands = [p for p in st.battlefield if p.is_land and p.tapped]
                    for p in lands[:x]:
                        p.tapped = False
                    st.emit(f"Candelabra of Tawnos: untap {min(x, len(lands))} land(s)")
                    return None
                return pay, resolve

            pay, resolve = build()
            acts.append(CardAction.activated(
                f"Candelabra of Tawnos: {{{x}}}, {{T}} — untap {x} land(s)",
                pay, resolve, source_name="Candelabra of Tawnos",
                ability_text="Untap X target lands"))
        return acts
