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
    When instant-speed play is enabled (state.instant_speed), airbend can ALSO
    hit a spell you are casting: Aang has flash, so — like the counterspell
    "counter your own spell" niche — we model casting a hand spell (paying its
    cost, onto the stack) and airbending it before it resolves, exiling it and
    registering the {2} recast. The pay-off is the modal recast (cast a cheap
    face, airbend it, recast the expensive face for {2}).
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
from .registry import build_card, register


@register
class AangSwiftSavior(Card):
    card_name = "Aang, Swift Savior // Aang and La, Ocean's Fury"

    def link_exiled_card(self, state, perm, card):
        # Airbent by Aang -> its owner may recast it for {2}.
        state.airbend_exile.append(card)

    def battlefield_actions(self, state, perm):
        # Waterbend {8}: Transform (front face only — the helper returns nothing
        # once transformed).
        return transform_actions(
            state, perm, ManaCost(generic=8), "Aang and La, Ocean's Fury")

    def on_etb(self, state, permanent):
        # Airbend up to one OTHER target creature you control (always), or — with
        # instant-speed play on — a spell you are casting. Exile the target and
        # let its owner recast it for {2}. "Up to one" → the "airbend nothing"
        # branch is always offered. Distinct by name to bound the branching.
        from ..engine.actions import can_afford

        options = []  # ("creature", uid) | ("spell", card_name)
        seen = set()
        for p in state.battlefield:
            if p.uid == permanent.uid or not p.is_creature_now:
                continue
            if p.name in seen:
                continue
            seen.add(p.name)
            options.append(("creature", p.uid))

        if state.instant_speed:
            seen_s = set()
            for c in state.hand:
                if c.is_land or c.name in seen_s:
                    continue
                seen_s.add(c.name)
                impl = build_card(c)
                if impl.is_castable(state) and can_afford(state, impl.cast_cost(state)):
                    options.append(("spell", c.name))

        if not options:
            return None  # no legal target → "up to one" does nothing (no branch)
        options = [None, *options]

        def fn(st, opt):
            if opt is None:
                st.emit("airbend nothing")
                return None
            kind, ref = opt
            if kind == "creature":
                target = st.find_permanent(ref)
                if target is None:
                    return None
                card = target.card
                st.emit(f"airbend {target.name} — exile, may recast for {{2}}")
                st.leaves_battlefield(target, "exile")
                # Keep it in exile (zone display) AND register the {2} recast.
                st.airbend_exile.append(card)
                return None
            # A spell you are casting: cast it (onto the stack, paying its cost),
            # then airbend it before it resolves — exile, recastable for {2}.
            from ..engine.actions import begin_cast

            card = next((c for c in st.hand if c.name == ref), None)
            if card is None:
                return None
            if not begin_cast(st, card, build_card(card).cast_cost(st),
                              tag="airbend target"):
                return None
            if card in st.stack:
                st.stack.remove(card)
            st.exile.append(card)
            st.airbend_exile.append(card)
            st.emit(f"airbend {card.name} (spell on the stack) — exile, "
                    f"may recast for {{2}}")
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
