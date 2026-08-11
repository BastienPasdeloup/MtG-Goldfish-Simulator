"""Psionic Blast — {2}{U} Instant.
Psionic Blast deals 4 damage to any target and 2 damage to you.

Burn with kickback: 4 to a target (opponent or your creature; one branch each) and
2 to yourself (via damage_self)."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class PsionicBlast(Card):
    card_name = "Psionic Blast"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply, suffix=suffix):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    apply(st, 4)
                    dealt = st.damage_self(2, colors=("U",))
                    st.emit(f"Psionic Blast: {dealt} damage to you")
                    st.check_deaths()
                    return None
                return fn

            acts.append(CardAction(f"cast Psionic Blast → 4 to {suffix}, 2 to you", make()))
        return acts
