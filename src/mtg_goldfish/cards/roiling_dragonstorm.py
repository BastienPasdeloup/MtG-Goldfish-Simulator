"""Roiling Dragonstorm — {1}{U} Enchantment. When it enters, draw two cards,
then discard a card. When a Dragon you control enters, return this to hand
(letting you recast it for more looting)."""
from __future__ import annotations

from ._common import loot
from .base import Card
from .registry import register


@register
class RoilingDragonstorm(Card):
    card_name = "Roiling Dragonstorm"

    def on_etb(self, state, permanent):
        return loot(state, 2, 1, source="Roiling Dragonstorm")

    def other_etb_stack_items(self, state, perm, entering):
        if entering is None or "dragon" not in entering.type_line.lower():
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            st.leaves_battlefield(live, "hand")
            st.emit("Roiling Dragonstorm: a Dragon entered — return to hand")
            return None

        return [self.stack_ability(
            source_name=perm.name, label="Roiling Dragonstorm: Dragon entered",
            resolve=resolve, trigger_text="A Dragon you control entered",
            ability_text="Return Roiling Dragonstorm to its owner's hand")]
