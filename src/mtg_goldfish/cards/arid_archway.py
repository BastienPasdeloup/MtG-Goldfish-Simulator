"""Arid Archway — Land — Desert.
Enters tapped. ETB: return a land you control to its owner's hand. {T}: Add
{C}{C}.

The bounce is deterministic rather than branched: `on_etb` runs deep inside
`put_on_battlefield` on tutor/fetch paths, where returned branches are
discarded (so branching would silently return nothing). We return the
least-useful OTHER land — keeping the strongest mana on the battlefield and
handing back a land that can be replayed for another land drop / landfall. With
no other land, Arid Archway returns itself (as the real card requires).
Approximation: the "if another Desert was returned, surveil 1" rider is
ignored.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class AridArchway(Card):
    card_name = "Arid Archway"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=2, choices=("C",))]

    def on_etb(self, state, permanent):
        others = [p for p in state.battlefield
                  if p.uid != permanent.uid and "land" in p.type_line.lower()]
        if not others:
            target = permanent  # no other land — must return Arid Archway itself
        else:
            def keep_value(p):
                abilities = p.impl.mana_abilities_perm(state, p)
                colors = {c for ab in abilities for c in ab.choices}
                return (len(colors), sum(ab.amount for ab in abilities),
                        0 if p.tapped else 1, -p.uid)
            target = sorted(others, key=keep_value)[0]

        state.emit(f"Arid Archway: return {target.name} to hand")
        state.leaves_battlefield(target, "hand")
        return None
