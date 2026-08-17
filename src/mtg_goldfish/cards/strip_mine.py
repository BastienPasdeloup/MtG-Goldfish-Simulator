"""Strip Mine — Land.
{T}: Add {C}.
{T}, Sacrifice this land: Destroy target land.

A colourless source whose land-destruction targets your own lands in a goldfish
(the phantom opponent has none) — offered but rarely the line the search wants."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class StripMine(Card):
    card_name = "Strip Mine"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_land and p.uid != perm.uid and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            tname = state.find_permanent(tuid).name

            def make(tuid=tuid):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped:
                        return False
                    src.tapped = True
                    st.leaves_battlefield(src, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        st.emit(f"Strip Mine: destroy {t.name}")
                        st.leaves_battlefield(t, "graveyard", reason="destroy")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Strip Mine: {{T}}, sacrifice — destroy {tname}",
                pay, resolve, source_name="Strip Mine",
                ability_text="Destroy target land"))
        return acts
