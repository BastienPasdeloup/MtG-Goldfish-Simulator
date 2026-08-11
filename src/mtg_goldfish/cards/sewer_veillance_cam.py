"""Sewer-veillance Cam — {U} Artifact. Flash.
When this artifact enters or leaves the battlefield, you may tap or untap target
creature.
{3}{U}, Sacrifice this artifact: Draw two cards.

The enter/leave "you may tap or untap" is optional and only targets your own
creatures (no worthwhile goldfish use), so it's skipped; the draw-two ability is
the value."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class SewerVeillanceCam(Card):
    card_name = "Sewer-veillance Cam"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3, pips=(("U", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return False
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            st.emit("Sewer-veillance Cam: draw two cards")
            st.draw(2)
            return None

        return [CardAction.activated(
            "Sewer-veillance Cam: {3}{U}, sacrifice — draw two cards",
            pay, resolve, source_name="Sewer-veillance Cam",
            ability_text="Draw two cards")]
