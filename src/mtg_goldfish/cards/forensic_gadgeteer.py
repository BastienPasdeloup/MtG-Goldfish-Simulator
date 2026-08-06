"""Forensic Gadgeteer — {2}{U} Creature — Vedalken Artificer Detective 2/3.
Whenever you cast an artifact spell, investigate (create a Clue token: "{2},
Sacrifice this token: Draw a card.").
Activated abilities of artifacts you control cost {1} less to activate. This
effect can't reduce the mana in that cost to less than one mana."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ForensicGadgeteer(Card):
    card_name = "Forensic Gadgeteer"
    # Artifact activated abilities cost {1} less (applied via artifact_ability_cost).
    artifact_ability_discount = 1

    def on_cast_other(self, state, perm, card):
        # "Whenever you cast an artifact spell, investigate."
        if card.is_artifact:
            state.make_token("Clue", 0, 0, "Token Artifact — Clue")
            state.emit("Forensic Gadgeteer: investigate — create a Clue")
