"""Paralyze — {B} Enchantment — Aura. Enchant creature.
When this Aura enters, tap enchanted creature.
Enchanted creature doesn't untap during its controller's untap step.
At the beginning of the upkeep of enchanted creature's controller, that player may
pay {4}. If the player does, untap the creature.

Enchant one of your creatures (a downside on your own creature, but a real
effect): it enters tapped, is held tapped by the prevents_untap broadcast, and each
of your upkeeps offers a branch to pay {4} and untap it."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import aura_enchant_actions, branch_over
from .base import Card
from .registry import register


@register
class Paralyze(Card):
    card_name = "Paralyze"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            host.tapped = True

        return aura_enchant_actions(self, state, cost="{B}", on_attach=on_attach)

    def prevents_untap(self, state, source, perm):
        return perm.uid == source.attached_to

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is None or not host.tapped:
            return None
        cost = ManaCost(generic=4)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            h = st.find_permanent(perm.attached_to) if perm.attached_to else None
            if opt == "untap" and h is not None and pay_cost(st, cost):
                h.tapped = False
                st.emit("Paralyze: pay {4}, untap enchanted creature")
            return None

        return branch_over(state, ["decline", "untap"], fn)
