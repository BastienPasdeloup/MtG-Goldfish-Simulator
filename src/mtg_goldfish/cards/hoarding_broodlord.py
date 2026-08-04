"""Hoarding Broodlord — {5}{B}{B}{B} 7/6 Convoke, Flying. When it enters, search
your library for a card, exile it face down, then shuffle; for as long as that
card remains exiled you may play it. Spells you cast from exile have convoke.

Modelled: the ETB impulse-tutor (branch over each distinct library card → exiled
and playable via `exile_playable`, reusing the Gwen Stacy mechanism). Convoke (a
cost reduction by tapping creatures) is not modelled — an approximation that
makes the Broodlord and its exiled spells slightly more expensive than reality;
the exiled card also stops being playable if the Broodlord leaves (the ruling
keeps it playable, but that edge rarely matters in a goldfish)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class HoardingBroodlord(Card):
    card_name = "Hoarding Broodlord"
    exiles_cards = True

    def link_exiled_card(self, state, perm, card):
        # Exiled with Hoarding Broodlord -> you may play it from exile.
        state.exile_playable.append((perm.uid, card))

    def on_etb(self, state, permanent):
        cands = state.search_library(lambda c: True)
        names = sorted({c.name for c in cands})
        if not names:
            return None

        def fn(st, name):
            c = next((x for x in st.library if x.name == name), None)
            if c is None:
                return None
            st.take_from_library(c)
            st.exile.append(c)
            live = st.find_permanent(permanent.uid)
            st.exile_playable.append(((live.uid if live else permanent.uid), c))
            st.shuffle_library()
            st.emit(f"Hoarding Broodlord: exile {name} face down — you may play it")
            return None

        return branch_over(state, names, fn)
