"""Lotus Field — Land.
Enters tapped. ETB: sacrifice two OTHER lands (all of them if two or fewer are
in play). {T}: add three mana of one color (G here; hexproof is a no-op).

The sacrifice is deterministic rather than branched: `on_etb` runs deep inside
`put_on_battlefield` (tutor / fetch paths) where returned branches are
discarded, so branching would silently sacrifice nothing on those paths. To
keep the goldfish's mana as strong as possible we sacrifice the two
*least-useful* other lands (fewest colors produced, tapped before untapped),
which is a well-defined single line on every entry path.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class LotusField(Card):
    card_name = "Lotus Field"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=3, choices=("G",))]

    def on_etb(self, state, permanent):
        others = [p for p in state.battlefield
                  if p.uid != permanent.uid and p.is_land]
        lands = [p for p in state.battlefield if p.is_land]
        if len(lands) <= 2:
            victims = lands  # two or fewer total lands: sacrifice all of them
        else:
            def keep_value(p):
                abilities = p.impl.mana_abilities_perm(state, p)
                colors = {c for ab in abilities for c in ab.choices}
                return (len(colors), sum(ab.amount for ab in abilities),
                        0 if p.tapped else 1, -p.uid)
            # Sacrifice the two lowest-value lands (keep the most useful mana).
            victims = sorted(others, key=keep_value)[:2]

        for p in victims:
            state.emit(f"Lotus Field: sacrifice {p.name}")
            state.leaves_battlefield(p, "graveyard")
        return None
