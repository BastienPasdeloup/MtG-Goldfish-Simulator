"""Buried Alive — {2}{B} Sorcery. Search your library for up to three creature
cards, put them into your graveyard, then shuffle. The KEY reanimator enabler.
Branches over which creatures to bin (modelled as exactly min(3, available)
distinct creatures; the pool is capped at the 8 highest mana values to bound
branching — those are the reanimation targets you actually want)."""
from __future__ import annotations

from itertools import combinations

from ._common import branch_over, mv
from .base import Card
from .registry import register


@register
class BuriedAlive(Card):
    card_name = "Buried Alive"

    def on_resolve(self, state):
        creatures = state.search_library(lambda c: c.is_creature)
        by_name = {}
        for c in creatures:
            by_name.setdefault(c.name, c)
        names = sorted(by_name, key=lambda n: -mv(by_name[n]))[:8]
        if not names:
            return None
        k = min(3, len(names))

        def fn(st, chosen):
            for name in chosen:
                c = next((x for x in st.library if x.name == name), None)
                if c is not None:
                    st.take_from_library(c)
                    st.to_graveyard(c)
            st.shuffle_library()
            st.emit(f"Buried Alive: {', '.join(chosen)} to graveyard — shuffle")
            return None

        return branch_over(state, list(combinations(names, k)), fn)
