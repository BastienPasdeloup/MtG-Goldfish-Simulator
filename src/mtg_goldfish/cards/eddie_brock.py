"""Eddie Brock // Venom, Lethal Protector — {2}{B} Legendary Creature 3/3.
ETB: return target creature card with mana value ≤1 from your graveyard to the
battlefield (branch; fizzles with no target). {3}{B}{R}{G}: transform (sorcery).
Venom's attack trigger (sacrifice → draw) is combat/branching-heavy and is not
modelled — documented approximation."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over, enter_battlefield, transform_actions
from .base import Card
from .registry import register


@register
class EddieBrock(Card):
    card_name = "Eddie Brock // Venom, Lethal Protector"

    def on_etb(self, state, permanent):
        targets = sorted({c.name for c in state.graveyard if c.is_creature and c.cmc <= 1})
        if not targets:
            return None

        def apply(st, name: str):
            card = next(c for c in st.graveyard if c.name == name)
            st.graveyard.remove(card)
            enter_battlefield(
                st,
                card,
                announce=f"Eddie Brock: return {name} to the battlefield",
            )
            return None

        return branch_over(state, targets, apply)

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=3, pips=(("B", 1), ("R", 1), ("G", 1))),
            "Venom, Lethal Protector",
        )
