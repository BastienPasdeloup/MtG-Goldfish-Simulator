"""Tiller Engine — {2} Artifact Creature — Construct 1/3.
Whenever a land you control enters tapped, you may untap it (the opponent-tap
mode is irrelevant). Modelled as: untap any land that enters tapped."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TillerEngine(Card):
    card_name = "Tiller Engine"

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower() and entering.tapped:
            entering.tapped = False
            state.emit(f"Tiller Engine: untap {entering.name}")

    def other_etb_stack_items(self, state, perm, entering):
        if "land" not in entering.type_line.lower() or not entering.tapped:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid, name=entering.name):
            source = st.find_permanent(uid)
            target = st.find_permanent(entering_uid)
            if source is None or target is None or not target.tapped:
                return None
            target.tapped = False
            st.emit(f"Tiller Engine: untap {name}")
            return None

        return [self.stack_ability(
            source_name=perm.name,
            label=f"Tiller Engine: untap {entering.name}",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield tapped",
            ability_text=f"Untap {entering.name}",
        )]
