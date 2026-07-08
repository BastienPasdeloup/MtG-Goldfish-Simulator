"""Miles Morales // Ultimate Spider-Man — {1}{G} Legendary 1/2.
ETB: put a +1/+1 counter on each of up to two target creatures (branches over
pairs/singles/none). {3}{R}{G}{W}: transform (sorcery). The back face's
attack-doubling trigger is combat-facing and not modelled."""
from __future__ import annotations

import itertools

from ..engine.mana import ManaCost
from ._common import branch_over, transform_actions
from .base import Card
from .registry import register


@register
class MilesMorales(Card):
    card_name = "Miles Morales // Ultimate Spider-Man"

    def on_etb(self, state, permanent):
        creatures = [p.uid for p in state.battlefield if p.is_creature_now]
        options: list[tuple[int, ...]] = [()]
        options += [(u,) for u in creatures]
        options += [pair for pair in itertools.combinations(creatures, 2)]

        def apply(st, uids):
            for uid in uids:
                p = st.find_permanent(uid)
                if p is not None:
                    p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 1
            if uids:
                names = [st.find_permanent(u).name for u in uids if st.find_permanent(u)]
                st.emit(f"Miles Morales: +1/+1 counter on {', '.join(names)}")

        if options == [()]:
            return None
        return branch_over(state, options, apply)

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=3, pips=(("R", 1), ("G", 1), ("W", 1))),
            "Ultimate Spider-Man",
        )
