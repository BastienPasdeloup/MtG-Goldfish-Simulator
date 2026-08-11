"""Regeneration — {1}{G} Enchantment — Aura. Enchant creature.
{G}: Regenerate enchanted creature.

A repeatable regeneration source on the host: {G} banks a regen shield (consumed
by the next destroy / lethal damage — see GameState._survives_destruction)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import aura_enchant_actions
from .base import Card, CardAction
from .registry import register


@register
class Regeneration(Card):
    card_name = "Regeneration"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{G}")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        cost = ManaCost(pips=(("G", 1),))
        if host is None or host.counters.get("regen_shield") or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            h = st.find_permanent(perm.attached_to)
            if h is not None:
                h.counters["regen_shield"] = 1
                st.emit(f"Regeneration: shield on {h.name}")
            return None

        return [CardAction.activated(
            "Regeneration: {G} — regenerate enchanted creature",
            pay, resolve, source_name="Regeneration",
            ability_text="Regenerate enchanted creature")]
