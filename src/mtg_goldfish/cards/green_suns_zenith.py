"""Green Sun's Zenith — {X}{G} Sorcery.
Search your library for a green creature with mana value X or less, put it
onto the battlefield, then shuffle (Zenith shuffles back in — ignored: it
leaves the goldfish library either way). Branch over affordable X values ×
matching green creatures."""
from __future__ import annotations

from ..engine.actions import available_mana_sources, begin_cast, resolve_to_graveyard
from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class GreenSunsZenith(Card):
    card_name = "Green Sun's Zenith"

    def cast_actions(self, state):
        # Crude mana ceiling: number of untapped mana sources (+ current pool).
        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        seen = set()
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("G", 1),))
            for target in state.search_library(
                lambda c, xx=x: c.is_creature and "G" in c.color_identity and c.cmc <= xx
            ):
                key = target.name
                if key in seen:
                    continue
                seen.add(key)

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
                        enter_battlefield(
                            st,
                            found,
                            announce=f"Green Sun's Zenith: {name} onto the battlefield — shuffle",
                        )
                        return None
                    return fn

                acts.append(CardAction(f"cast Green Sun's Zenith (X={x}) → {target.name}",
                                       make(target.name)))
        return acts
