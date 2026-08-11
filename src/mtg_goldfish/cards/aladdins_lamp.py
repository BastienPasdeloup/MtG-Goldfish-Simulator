"""Aladdin's Lamp — {10} Artifact.
{X}, {T}: The next time you would draw a card this turn, instead look at the top X
cards of your library, put all but one of them on the bottom in a random order,
then draw a card. X can't be 0.

Card selection: {X}, {T} to look at the top X cards, keep one (drawn to hand) and
bottom the rest — modelled directly (the "next draw replacement" wrapper is
simplified to digging now). One branch per affordable X (2..) and keep choice."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import dig_choose
from .base import Card, CardAction
from .registry import register


@register
class AladdinsLamp(Card):
    card_name = "Aladdin's Lamp"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import available_mana_sources, can_afford, pay_cost

        if perm.tapped:
            return []
        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(2, max(1, max_mana) + 1):
            if x > len(state.library):
                break
            cost = ManaCost(generic=x)
            if not can_afford(state, cost, exclude_uids={perm.uid}):
                continue

            def make(xx, c=cost):
                def pay(st):
                    me = st.find_permanent(perm.uid)
                    if me is None or me.tapped or not pay_cost(st, c, exclude_uids={perm.uid}):
                        return False
                    me.tapped = True
                    return True

                def resolve(st):
                    return st.settle(dig_choose(st, xx, 1, rest="bottom",
                                                source="Aladdin's Lamp"))
                return pay, resolve

            pay, resolve = make(x)
            acts.append(CardAction.activated(
                f"Aladdin's Lamp: {{{x}}}, {{T}} — look at top {x}, keep 1",
                pay, resolve, source_name="Aladdin's Lamp",
                ability_text="Look at the top X cards, keep one, bottom the rest"))
        return acts
