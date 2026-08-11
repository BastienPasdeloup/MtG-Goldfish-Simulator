"""Earthbind — {R} Enchantment — Aura. Enchant creature.
When this Aura enters, if enchanted creature has flying, this Aura deals 2 damage
to that creature and it loses flying.

Anti-flyer removal (aimed at an opponent's flyer); with only your own creatures
to target it is rarely useful, but modelled faithfully: on attach, if the host
has flying it takes 2 and loses flying (via removed_keywords)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Earthbind(Card):
    card_name = "Earthbind"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            if st.has_keyword(host, "Flying"):
                host.removed_keywords.add("flying")
                st.damage_permanent(host, 2)
                st.emit(f"Earthbind: {host.name} loses flying and takes 2 damage")
                st.check_deaths()

        return aura_enchant_actions(self, state, cost="{R}", on_attach=on_attach)
