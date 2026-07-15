"""Elvish Reclaimer — {G} Creature — Elf Warrior 1/2.
+2/+2 while your graveyard holds three or more land cards.
{2}, {T}, Sacrifice a land: search your library for a land card, put it onto
the battlefield tapped, then shuffle. Approximation: the land sacrificed is
chosen deterministically (a basic Forest if possible, else the first land) —
only the search target is a branch point."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


def _sac_pick(state):
    lands = [p for p in state.battlefield if p.is_land]
    basics = [p for p in lands if "basic" in p.type_line.lower()]
    return (basics or lands or [None])[0]


@register
class ElvishReclaimer(Card):
    card_name = "Elvish Reclaimer"

    def dynamic_power(self, state, perm):
        gy_lands = sum(1 for c in state.graveyard if c.is_land)
        return 3 if gy_lands >= 3 else 1

    def dynamic_toughness(self, state, perm):
        gy_lands = sum(1 for c in state.graveyard if c.is_land)
        return 4 if gy_lands >= 3 else 2

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=2)
        if perm.tapped or perm.summoning_sick or not can_afford(state, cost):
            return []
        if _sac_pick(state) is None:
            return []

        def make(name):
            def pay(st):
                p = st.find_permanent(perm.uid)
                sac = _sac_pick(st)
                if p is None or p.tapped or sac is None or not pay_cost(st, cost):
                    return False
                p.tapped = True
                st.emit(f"Elvish Reclaimer: sacrifice {sac.name}")
                st.leaves_battlefield(sac, "graveyard")
                return True

            def resolve(st):
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                enter_battlefield(
                    st,
                    card,
                    tapped=True,
                    announce=f"Elvish Reclaimer: fetch {name} tapped — shuffle",
                )
                return None
            return CardAction.activated(
                f"Elvish Reclaimer: fetch {name}",
                pay,
                resolve,
                source_name="Elvish Reclaimer",
                ability_text=f"Fetch {name}",
            )

        return [make(t.name) for t in state.search_library(lambda c: c.is_land)]
