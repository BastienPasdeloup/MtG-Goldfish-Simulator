"""Urza's Bauble — {0} Artifact.
{T}, Sacrifice this artifact: Look at a card at random in target player's hand.
You draw a card at the beginning of the next turn's upkeep.

The "look" is information only (no goldfish effect); the value is the delayed card
draw at your next upkeep (see `pending_upkeep_draws`)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class UrzasBauble(Card):
    card_name = "Urza's Bauble"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            p.tapped = True
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            st.pending_upkeep_draws += 1
            st.emit("Urza's Bauble: draw a card at the next upkeep")
            return None

        return [CardAction.activated(
            "Urza's Bauble: {T}, sacrifice — draw at next upkeep",
            pay, resolve, source_name="Urza's Bauble",
            ability_text="Draw a card at the beginning of the next turn's upkeep")]
