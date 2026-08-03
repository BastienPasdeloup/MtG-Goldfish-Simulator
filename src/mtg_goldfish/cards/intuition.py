"""Intuition — {2}{U} Instant. Search your library for three cards; an opponent
chooses one for your hand, the rest to your graveyard; shuffle. Against a phantom
opponent the choice is modelled generously (the searcher picks the split — the
codebase convention for "an opponent chooses"): branch over three-card subsets
and over which of the three goes to hand (the other two to the graveyard). Pool
capped (creatures by mana value first) to bound branching."""
from __future__ import annotations

from itertools import combinations

from ._common import branch_over, mv
from .base import Card
from .registry import register


@register
class Intuition(Card):
    card_name = "Intuition"

    def on_resolve(self, state):
        cards = state.search_library(lambda c: True)
        by_name = {}
        for c in cards:
            by_name.setdefault(c.name, c)
        # Prefer creatures (reanimation targets), then higher mana value.
        names = sorted(by_name,
                       key=lambda n: (not by_name[n].is_creature, -mv(by_name[n])))[:6]
        if len(names) < 1:
            return None
        k = min(3, len(names))

        def fn(st, chosen):
            picked = [next((x for x in st.library if x.name == nm), None) for nm in chosen]
            picked = [c for c in picked if c is not None]
            if not picked:
                return None
            to_hand = picked[0]
            st.take_from_library(to_hand)
            st.hand.append(to_hand)
            for c in picked[1:]:
                st.take_from_library(c)
                st.to_graveyard(c)
            st.shuffle_library()
            st.emit(f"Intuition: {to_hand.name} to hand, "
                    f"{', '.join(c.name for c in picked[1:]) or 'none'} to graveyard — shuffle")
            return None

        branches = []
        for combo in combinations(names, k):
            # rotate which of the k goes to hand
            for i in range(len(combo)):
                ordered = (combo[i],) + combo[:i] + combo[i + 1:]
                branches.extend(branch_over(state, [ordered], fn))
        return branches
