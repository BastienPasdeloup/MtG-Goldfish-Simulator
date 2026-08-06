"""Everflowing Chalice — {0} Artifact.
Multikicker {2} (pay {2} any number of times as you cast it).
Enters with a charge counter for each time it was kicked.
{T}: Add {C} for each charge counter on it.

Branch over the number of times it is kicked (bounded by available mana); the
chosen count enters as charge counters, and it then taps for that much {C}."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class EverflowingChalice(Card):
    card_name = "Everflowing Chalice"

    def cast_actions(self, state):
        from ..engine.actions import available_mana_sources, begin_cast, can_afford, resolve_to_battlefield

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for kicks in range(0, max(0, max_mana) // 2 + 1):
            cost = ManaCost(generic=2 * kicks)  # {0} base + {2} per kick
            if not can_afford(state, cost):
                continue

            def make(k, c=cost):
                def fn(st):
                    card = next((x for x in st.hand if x.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    # "Enters with a charge counter for each time it was kicked" is
                    # a replacement — set the counters as it enters, before ETBs.
                    return resolve_to_battlefield(st, card, marks={"charge": k}) or None
                return fn

            acts.append(CardAction(
                f"cast Everflowing Chalice (multikicker ×{kicks})", make(kicks)))
        return acts

    def mana_abilities_perm(self, state, perm):
        charge = perm.counters.get("charge", 0)
        if charge <= 0:
            return []
        return [ManaAbility(amount=charge, choices=("C",))]
