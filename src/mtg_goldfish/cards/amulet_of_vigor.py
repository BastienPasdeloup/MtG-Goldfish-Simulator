"""Amulet of Vigor — {1} Artifact.
Whenever a permanent you control enters tapped, untap it."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AmuletOfVigor(Card):
    card_name = "Amulet of Vigor"

    def etb_tapped(self, state):
        # An artifact — it never enters tapped. (Its oracle text contains the
        # phrase "enters tapped" only inside its triggered ability, which the
        # base heuristic would otherwise misread.)
        return False

    def on_other_etb(self, state, perm, entering):
        # Untap the permanent only when it actually entered tapped.
        if entering.tapped:
            entering.tapped = False
            state.emit(f"Amulet of Vigor: untap {entering.name}")

    def other_etb_stack_items(self, state, perm, entering):
        if not entering.tapped:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid, name=entering.name):
            source = st.find_permanent(uid)
            target = st.find_permanent(entering_uid)
            if source is None or target is None or not target.tapped:
                return None
            target.tapped = False
            st.emit(f"Amulet of Vigor: untap {name}")
            return None

        return [self.stack_ability(
            source_name=perm.name,
            label=f"Amulet of Vigor: untap {entering.name}",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield tapped",
            ability_text=f"Untap {entering.name}",
        )]
