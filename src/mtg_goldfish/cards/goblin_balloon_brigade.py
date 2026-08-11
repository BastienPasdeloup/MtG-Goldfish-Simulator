"""Goblin Balloon Brigade — {R} Creature — Goblin Warrior 1/1.
{R}: This creature gains flying until end of turn.

Grants flying to itself (temp_keywords) for {R}. Evasion is inert with no
blockers, but the keyword is genuinely granted."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class GoblinBalloonBrigade(Card):
    card_name = "Goblin Balloon Brigade"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if not can_afford(state, cost) or "flying" in perm.temp_keywords:
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.temp_keywords.add("flying")
                st.emit("Goblin Balloon Brigade: gains flying until end of turn")
            return None

        return [CardAction.activated(
            "Goblin Balloon Brigade: {R} — gain flying until end of turn",
            pay, resolve, source_name="Goblin Balloon Brigade",
            ability_text="flying until end of turn")]
