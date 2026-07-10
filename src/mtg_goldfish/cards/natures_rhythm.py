"""Nature's Rhythm — {X}{G}{G} Sorcery.
Search your library for a creature with mana value X or less, put it onto the
battlefield, then shuffle. Branch over affordable X × matching creatures.
Approximation: harmonize (casting from the graveyard) is not modelled."""
from __future__ import annotations

from ..engine.actions import available_mana_sources, begin_cast, resolve_to_graveyard
from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class NaturesRhythm(Card):
    card_name = "Nature's Rhythm"

    def cast_actions(self, state):
        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        seen = set()
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("G", 2),))
            for target in state.search_library(
                lambda c, xx=x: c.is_creature and c.cmc <= xx
            ):
                if target.name in seen:
                    continue
                seen.add(target.name)

                def make(name, xc=cost):
                    def fn(st):
                        card = next((c for c in st.hand if c.name == self.card_name), None)
                        if card is None or not begin_cast(st, card, xc):
                            return None
                        resolve_to_graveyard(st, card)
                        found = next((c for c in st.library if c.name == name), None)
                        if found is None:
                            return None
                        st.take_from_library(found)
                        st.shuffle_library()
                        st.put_on_battlefield(found)
                        st.emit(f"Nature's Rhythm: {name} onto the battlefield — shuffle")
                        return None
                    return fn

                acts.append(CardAction(f"cast Nature's Rhythm (X={x}) → {target.name}",
                                       make(target.name)))
        return acts
