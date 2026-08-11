"""Instill Energy — {G} Enchantment — Aura. Enchant creature.
Enchanted creature can attack as though it had haste.
{0}: Untap enchanted creature. Activate only during your turn and only once each
turn.

Grants haste to the host (extra_keywords — the closest model for "attack as though
it had haste", so a summoning-sick creature can attack). The free {0} untap (once
per turn) is offered from the Aura — useful to re-tap the host for a {T} ability."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class InstillEnergy(Card):
    card_name = "Instill Energy"

    def cast_actions(self, state):
        from ._common import aura_enchant_actions

        def on_attach(st, aura, host):
            host.extra_keywords.add("haste")

        return aura_enchant_actions(self, state, cost="{G}", on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.extra_keywords.discard("haste")

    def battlefield_actions(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is None or not host.tapped or perm.turn_flags.get("instill_untap"):
            return []

        def pay(st):
            return True  # {0}

        def resolve(st):
            a = st.find_permanent(perm.uid)
            h = st.find_permanent(perm.attached_to) if perm.attached_to else None
            if a is not None:
                a.turn_flags["instill_untap"] = True
            if h is not None:
                h.tapped = False
                st.emit(f"Instill Energy: untap {h.name}")
            return None

        return [CardAction.activated(
            "Instill Energy: {0} — untap enchanted creature",
            pay, resolve, source_name="Instill Energy",
            ability_text="untap enchanted creature")]
