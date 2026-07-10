"""Primeval Titan — {4}{G}{G} Creature — Giant 6/6, trample.
Whenever it enters or attacks, you may search your library for up to two land
cards, put them onto the battlefield tapped, then shuffle. Branch over the
(unordered) choice of up to two distinct lands."""
from __future__ import annotations

from itertools import combinations

from ._common import branch_over, enter_battlefield_sequence
from .base import Card
from .registry import register


def _fetch_two(state):
    lands = state.search_library(lambda c: c.is_land)
    names = [land.name for land in lands]
    # Options: none, each single, each unordered pair (by name).
    options: list[tuple] = [()]
    options += [(n,) for n in names]
    options += [tuple(sorted(pair)) for pair in combinations(names, 2)]
    # De-dupe.
    seen, uniq = set(), []
    for o in options:
        if o not in seen:
            seen.add(o)
            uniq.append(o)

    def fn(st, chosen):
        entries = []
        for name in chosen:
            card = next((c for c in st.library if c.name == name), None)
            if card is not None:
                st.take_from_library(card)
                entries.append((card, True, None))
        enter_battlefield_sequence(st, entries)
        if chosen:
            st.shuffle_library()
            st.emit(f"Primeval Titan: fetch {', '.join(chosen)} tapped — shuffle")

    return branch_over(state, uniq, fn)


@register
class PrimevalTitan(Card):
    card_name = "Primeval Titan"

    def on_etb(self, state, permanent):
        return _fetch_two(state)

    def on_attack(self, state, perm):
        # Attacks fire deep in combat; make a deterministic best pick (two
        # distinct lands, preferring nonbasics for utility) rather than branch.
        lands = state.search_library(lambda c: c.is_land)
        lands.sort(key=lambda c: (("basic" in c.type_line.lower()), c.name))
        for card in lands[:2]:
            real = next((c for c in state.library if c.name == card.name), None)
            if real is not None:
                state.take_from_library(real)
                state.put_on_battlefield(real, tapped=True)
        if lands[:2]:
            state.shuffle_library()
            state.emit("Primeval Titan attacks: fetch two lands tapped — shuffle")
