"""Whir of Invention — {X}{U}{U}{U} Instant. Improvise.
Search your library for an artifact card with mana value X or less, put it onto
the battlefield, then shuffle.

Tutors any affordable artifact straight into play (untapped). One branch per
distinct artifact you could fetch, at X = that artifact's mana value, paying the
generic X with improvise (tapping artifacts) as well as real mana."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class WhirOfInvention(Card):
    card_name = "Whir of Invention"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford_with_improvise, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for target in state.search_library(lambda c: c.is_artifact):
            if target.name in seen:
                continue
            x = int(target.cmc)
            cost = ManaCost(generic=x, pips=(("U", 3),))
            if not can_afford_with_improvise(state, cost):
                continue
            seen.add(target.name)

            def make(name, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c, improvise=True):
                        return None
                    resolve_to_graveyard(st, card)
                    found = next((k for k in st.library if k.name == name), None)
                    if found is None:
                        return None
                    st.take_from_library(found)
                    st.shuffle_library()
                    enter_battlefield(
                        st, found, tapped=False,
                        announce=f"Whir of Invention: {name} onto the battlefield — shuffle")
                    return None
                return fn

            acts.append(CardAction(
                f"cast Whir of Invention (X={x}) → {target.name}", make(target.name)))
        return acts
