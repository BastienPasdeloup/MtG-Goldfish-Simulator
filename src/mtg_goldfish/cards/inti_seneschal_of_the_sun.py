"""Inti, Seneschal of the Sun — {1}{R} Legendary Creature 2/2.
Whenever you attack, you may discard a card. When you do, put a +1/+1 counter on
target attacking creature; it gains trample until end of turn.
Whenever you discard one or more cards, exile the top card of your library; you
may play that card until your next end step (approximated as while Inti lives)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class IntiSeneschalOfTheSun(Card):
    card_name = "Inti, Seneschal of the Sun"
    exiles_cards = True

    def link_exiled_card(self, state, perm, card):
        # Exiled with Inti -> you may play it from exile.
        state.exile_playable.append((perm.uid, card))

    def on_you_attack(self, state, perm):
        attackers = [p for p in state.battlefield
                     if p.uid in state.attackers and p.is_creature_now]
        if not attackers or not state.hand:
            return None
        target = max(attackers, key=lambda p: state.effective_power(p))
        options = [("decline", None)] + [("discard " + n, n)
                                         for n in sorted({c.name for c in state.hand})]

        def fn(st, opt):
            _label, name = opt
            if name is None:
                st.emit("Inti: decline to discard")
                return None
            c = next((x for x in st.hand if x.name == name), None)
            if c is None:
                return None
            st.discard(c)  # fires Inti's own discard trigger (impulse)
            tgt = st.find_permanent(target.uid)
            if tgt is not None:
                tgt.counters["+1/+1"] = tgt.counters.get("+1/+1", 0) + 1
                tgt.temp_keywords.add("trample")
                st.emit(f"Inti: discard {name} → +1/+1 & trample on {tgt.name}")
            return None

        return branch_over(state, options, fn)

    def on_you_discard(self, state, perm, count):
        if not state.library:
            return
        card = state.library.pop(0)
        state.exile.append(card)
        state.exile_playable.append((perm.uid, card))
        state.emit(f"Inti: exile {card.name} — may play it")
