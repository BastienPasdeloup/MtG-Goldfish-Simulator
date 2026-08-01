"""Nature's Rhythm — {X}{G}{G} Sorcery.
Search your library for a creature with mana value X or less, put it onto the
battlefield, then shuffle. Branch over affordable X × matching creatures.

Harmonize {X}{G}{G}{G}{G} — you may also cast it from the graveyard (then exile
it) for a second tutor-a-creature-into-play. The "tap a creature to reduce the
cost by its power" discount is NOT modelled (skipping it only ever makes the
harmonize cast harder, never wrongly available — a safe under-approximation)."""
from __future__ import annotations

from ..engine.actions import available_mana_sources, begin_cast, resolve_to_graveyard
from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


def _tutor_creature(st, name, x_label):
    """Pull `name` (a creature) from the library onto the battlefield, shuffle."""
    found = next((c for c in st.library if c.name == name), None)
    if found is None:
        return None
    st.take_from_library(found)
    st.shuffle_library()
    enter_battlefield(
        st, found,
        announce=f"Nature's Rhythm ({x_label}): {name} onto the battlefield — shuffle",
    )
    return None


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

                def make(name, xc=cost, xlabel=f"X={x}"):
                    def fn(st):
                        card = next((c for c in st.hand if c.name == self.card_name), None)
                        if card is None or not begin_cast(st, card, xc):
                            return None
                        resolve_to_graveyard(st, card)
                        return _tutor_creature(st, name, xlabel)
                    return fn

                acts.append(CardAction(f"cast Nature's Rhythm (X={x}) → {target.name}",
                                       make(target.name)))
        return acts

    def graveyard_actions(self, state):
        # Harmonize {X}{G}{G}{G}{G}: cast from the graveyard, then exile the spell.
        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        seen = set()
        for x in range(0, max(0, max_mana - 4) + 1):
            cost = ManaCost(generic=x, pips=(("G", 4),))
            for target in state.search_library(
                lambda c, xx=x: c.is_creature and c.cmc <= xx
            ):
                if target.name in seen:
                    continue
                seen.add(target.name)

                def make(name, xc=cost, xlabel=f"harmonize X={x}"):
                    def fn(st):
                        card = next((c for c in st.graveyard if c.name == self.card_name), None)
                        if card is None or not begin_cast(
                                st, card, xc, zone=st.graveyard, tag="harmonize"):
                            return None
                        # Harmonize exiles the spell (instead of the graveyard).
                        if card in st.stack:
                            st.stack.remove(card)
                        st.exile.append(card)
                        return _tutor_creature(st, name, xlabel)
                    return fn

                acts.append(CardAction(
                    f"cast Nature's Rhythm from graveyard (harmonize X={x}) → {target.name}",
                    make(target.name)))
        return acts
