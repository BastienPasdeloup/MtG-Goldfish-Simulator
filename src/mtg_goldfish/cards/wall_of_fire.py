"""Wall of Fire — 0/5 Wall, Defender.
{R}: This creature gets +1/+0 until end of turn.

Firebreathing-style pump on itself (temp +1/+0 per {R}). Defender is auto
(it can't attack), so the pump matters only for blocking — inert here — but the
ability is genuinely offered."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class WallOfFire(Card):
    card_name = "Wall of Fire"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.temp_power += 1
                st.emit("Wall of Fire: +1/+0 until end of turn")
            return None

        return [CardAction.activated(
            "Wall of Fire: {R} — +1/+0 until end of turn",
            pay, resolve, source_name="Wall of Fire",
            ability_text="+1/+0 until end of turn")]
