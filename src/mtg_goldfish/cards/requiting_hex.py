"""Requiting Hex — {B} Instant. You may blight 1 as an additional cost (put a
-1/-1 counter on a creature you control). Destroy target creature with mana
value 2 or less; if the additional cost was paid, you gain 2 life.
Modelled as always blighting the (dying) target, so the cast also gains 2 life."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class RequitingHex(Card):
    card_name = "Requiting Hex"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield
                   if p.is_creature_now and p.card.cmc <= 2]

        def effect(st, perm):
            st.life += 2  # blight the dying target -> additional cost paid
            st.emit(f"Requiting Hex: blight + destroy {perm.name}, gain 2 life ({st.life})")
            st.leaves_battlefield(perm, "graveyard", reason="destroy")

        return targeted_instant_casts(self, state, targets, effect, tag="mv≤2, blight")
