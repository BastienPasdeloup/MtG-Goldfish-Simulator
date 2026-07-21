"""Aang, Swift Savior // Aang and La, Ocean's Fury — {1}{W}{U} Legendary Creature.

Front (Aang, Swift Savior) — 2/3, Flash, Flying (both handled by the engine):
  * When Aang enters, airbend up to one OTHER target creature or spell (exile
    it; its owner may recast it for {2}). Airbend is removal aimed at the
    opponent; against a phantom opponent there are no enemy creatures or spells,
    and airbending your own permanent is never advantageous in a goldfish, so
    "up to one" resolves choosing zero targets — a no-op ETB (not modelled).
  * Waterbend {8}: Transform Aang.  ({8} generic, instant-speed activated
    ability; disappears once transformed.)

Back (Aang and La, Ocean's Fury) — 5/5, Reach, Trample (P/T + types come from
the active face automatically on transform):
  * Whenever Aang and La attacks, put a +1/+1 counter on each tapped creature
    you control. Attackers are tapped before their attack triggers resolve, so
    the attacking creatures (Aang and La included) get a counter too.
"""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import transform_actions
from .base import Card
from .registry import register


@register
class AangSwiftSavior(Card):
    card_name = "Aang, Swift Savior // Aang and La, Ocean's Fury"

    def battlefield_actions(self, state, perm):
        # Waterbend {8}: Transform (front face only — the helper returns nothing
        # once transformed).
        return transform_actions(
            state, perm, ManaCost(generic=8), "Aang and La, Ocean's Fury")

    def attack_stack_items(self, state, perm):
        # Only the back face (Aang and La) has an attack trigger.
        if not perm.transformed:
            return []
        return super().attack_stack_items(state, perm)

    def on_attack(self, state, perm):
        if not perm.transformed:
            return None
        boosted = []
        for p in state.battlefield:
            if p.tapped and p.is_creature_now:
                p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 1
                boosted.append(p.name)
        if boosted:
            state.emit(f"Aang and La attacks: +1/+1 counter on {', '.join(boosted)}")
        return None
