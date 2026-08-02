"""Malcolm, Alluring Scoundrel — {1}{U} 2/1 flash, flying.
Whenever Malcolm deals combat damage to a player, put a chorus counter on it,
draw a card, then discard a card. If there are four or more chorus counters on
Malcolm, you may cast the discarded card without paying its mana cost.

The combat-damage trigger BRANCHES (combat damage is now branch-capable): one
line per distinct card that could be discarded, and — at 4+ chorus, for a
castable nonland discard — an extra line that free-casts it from the graveyard."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class MalcolmAlluringScoundrel(Card):
    card_name = "Malcolm, Alluring Scoundrel"

    def on_combat_damage(self, state, perm, damage):
        perm.counters["chorus"] = perm.counters.get("chorus", 0) + 1
        chorus = perm.counters["chorus"]
        state.emit(f"Malcolm: chorus counter ({chorus}), draw a card")
        state.draw(1)
        if not state.hand:
            return None

        # Branch over which card to discard (dedup by name — identical cards are
        # interchangeable). At 4+ chorus a castable nonland discard also spawns a
        # "free-cast it" line.
        def discard(st, name):
            from ..engine.actions import _impl, cast_without_paying

            card = next((c for c in st.hand if c.name == name), None)
            if card is None:
                return None
            st.hand.remove(card)
            st.to_graveyard(card)
            st.emit(f"Malcolm: discard {name}")
            live = st.find_permanent(perm.uid)
            cur = live.counters.get("chorus", 0) if live is not None else chorus
            if cur < 4 or card.is_land or not _impl(card).is_castable(st):
                return None  # the plain discard line

            # Extra branch: cast the discarded card for free from the graveyard.
            free = st.clone()
            gy_card = next((c for c in free.graveyard if c.name == name), None)
            if gy_card is None:
                return None
            free.emit(f"Malcolm: cast {name} for free (4+ chorus)")
            res = cast_without_paying(free, gy_card, zone=free.graveyard,
                                      tag="Malcolm free cast")
            if res is None:
                free.check_deaths()
                return [st, free]              # don't-cast line + cast line
            return [st, *res]

        return branch_over(state, sorted({c.name for c in state.hand}), discard)
