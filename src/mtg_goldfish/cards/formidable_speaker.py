"""Formidable Speaker — {2}{G} Creature — Elf Druid 2/4.
ETB: you may discard a card to search your library for a creature card and
put it into your hand (one branch per creature target, plus declining).
Approximation: the discarded card is chosen deterministically (first nonland
in hand, else first card). {1}, {T}: untap another target permanent (branch
over your tapped permanents)."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from ._common import branch_over, discard
from .base import Card, CardAction
from .registry import register


@register
class FormidableSpeaker(Card):
    card_name = "Formidable Speaker"

    def on_etb(self, state, permanent):
        pick = next((c for c in state.hand if not c.is_land), None) or \
            (state.hand[0] if state.hand else None)
        if pick is None:
            return None
        targets = state.search_library(lambda c: c.is_creature)
        if not targets:
            return None

        def fn(st, name):
            if name is None:
                return
            tossed = next((c for c in st.hand if not c.is_land), None) or \
                (st.hand[0] if st.hand else None)
            if tossed is None:
                return
            discard(st, tossed)
            card = next((c for c in st.library if c.name == name), None)
            if card is None:
                return
            st.take_from_library(card)
            st.shuffle_library()
            st.hand.append(card)
            st.emit(f"Formidable Speaker: search {name} to hand — shuffle")

        return branch_over(state, [t.name for t in targets] + [None], fn)

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=1)
        if perm.tapped or perm.summoning_sick or not can_afford(state, cost):
            return []
        tapped = {}
        for p in state.battlefield:
            if p.uid != perm.uid and p.tapped and p.name not in tapped:
                tapped[p.name] = p.uid
        acts = []
        for name, uid in tapped.items():
            def pay(st, target_uid=uid):
                p = st.find_permanent(perm.uid)
                t = st.find_permanent(target_uid)
                if p is None or p.tapped or t is None or not pay_cost(st, cost):
                    return False
                p.tapped = True
                return True

            def resolve(st, target_uid=uid):
                t = st.find_permanent(target_uid)
                if t is None:
                    return None
                t.tapped = False
                st.emit(f"Formidable Speaker: untap {t.name}")
                return None

            acts.append(CardAction.activated(
                f"Formidable Speaker: untap {name}",
                pay,
                resolve,
                source_name="Formidable Speaker",
                ability_text=f"Untap {name}",
            ))
        return acts
