"""Aang, Swift Savior // Aang and La, Ocean's Fury — {1}{W}{U} Legendary Creature.

Front (Aang, Swift Savior) — 2/3, Flash, Flying (both handled by the engine):
  * When Aang enters, airbend up to one OTHER target creature or spell (exile
    it; for as long as it stays exiled, its owner may cast it for {2}). Against
    a phantom opponent there are no enemy creatures, and spells resolve
    atomically so none is ever on the stack at this trigger — but airbending
    your OWN creature IS a real option: the exiled card may be recast for {2},
    which re-triggers its ETB and, for a modal card, lets ANY face that has a
    mana cost be cast for {2} (e.g. the expensive side of an MDFC for {2}).
    Modelled as a branching ETB: airbend nothing, or exile one other creature
    you control (registered for the {2} recast — see GameState.airbend_exile
    and actions._airbend_cast_actions). Land faces (no mana cost) are excluded.
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
from ._common import branch_over, transform_actions
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

    def on_etb(self, state, permanent):
        # Airbend up to one OTHER target creature you control: exile it and let
        # its owner recast it for {2}. "Up to one" → the "airbend nothing"
        # branch is always offered. Distinct by name to bound the branching.
        targets = []
        seen = set()
        for p in state.battlefield:
            if p.uid == permanent.uid or not p.is_creature_now:
                continue
            if p.name in seen:
                continue
            seen.add(p.name)
            targets.append(p.uid)
        if not targets:
            return None  # no legal target → "up to one" does nothing (no branch)
        options = [None, *targets]

        def fn(st, uid):
            if uid is None:
                st.emit("airbend nothing")
                return None
            target = st.find_permanent(uid)
            if target is None:
                return None
            card = target.card
            st.emit(f"airbend {target.name} — exile, may recast for {{2}}")
            st.leaves_battlefield(target, "exile")
            # Keep it in exile (zone display) AND register the {2} recast.
            st.airbend_exile.append(card)
            return None

        return branch_over(state, options, fn)

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
