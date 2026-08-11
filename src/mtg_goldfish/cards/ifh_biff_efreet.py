"""Ifh-Bíff Efreet — {2}{G}{G} Creature — Efreet 3/3. Flying.
{G}: This creature deals 1 damage to each creature with flying and each player.
Any player may activate this ability.

A repeatable symmetric flyer-pinger: {G} deals 1 to each flyer (via
damage_permanent) and 1 to each player (you via damage_self, the opponent via
damage_opponent) — including itself and you."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class IfhBiffEfreet(Card):
    card_name = "Ifh-Bíff Efreet"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("G", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            for p in list(st.battlefield):
                if p.is_creature_now and st.has_keyword(p, "Flying"):
                    st.damage_permanent(p, 1)
            st.damage_self(1, colors=("G",))
            st.damage_opponent(1)
            st.note_crime()
            st.emit("Ifh-Bíff Efreet: 1 damage to each flyer and each player")
            st.check_deaths()
            return None

        return [CardAction.activated(
            "Ifh-Bíff Efreet: {G} — 1 to each flyer and each player",
            pay, resolve, source_name="Ifh-Bíff Efreet",
            ability_text="Deal 1 damage to each creature with flying and each player")]
