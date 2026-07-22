"""Atraxa, Grand Unifier — {3}{G}{W}{U}{B} Legendary Creature — Phyrexian Angel.
7/7 flying, vigilance, deathtouch, lifelink (all auto from the keyword list).

When Atraxa enters, reveal the top ten cards of your library. For each card
type, you MAY put a card of that type from among them into your hand. Put the
rest on the bottom of your library in a random order.

Modelled as a BRANCHING ETB. Because a card in hand strictly beats one on the
bottom of the library for a goldfish, the model always takes one card of EACH
card type present among the ten, branching only over WHICH card when a type has
several distinct names (a multi-type card may satisfy any one of its types).
The un-taken cards go to the bottom of the library."""
from __future__ import annotations

from .base import Card
from .registry import register

# The eight card types Atraxa's reminder text enumerates.
_CARD_TYPES = ("artifact", "battle", "creature", "enchantment",
               "instant", "land", "planeswalker", "sorcery")
# Safety valve: an unusually type-diverse top ten could enumerate a huge number
# of distinct hands. Cap the branch count (and note it) rather than explode.
_MAX_BRANCHES = 64


@register
class AtraxaGrandUnifier(Card):
    card_name = "Atraxa, Grand Unifier"

    def on_etb(self, state, permanent):
        from ._common import branch_over

        top = state.library[:10]
        if not top:
            return None
        for c in top:
            state.library.remove(c)
        state.emit(f"Atraxa, Grand Unifier: reveal top {len(top)} — "
                   f"{', '.join(c.name for c in top)}")

        def types_of(idx):
            head = top[idx].type_line.split("—")[0].lower()
            return {t for t in _CARD_TYPES if t in head}

        # For a goldfish, a card in hand strictly beats a card on the bottom of
        # the library, so the model always takes one card of EACH present type;
        # it only branches over WHICH card when a type has several distinct
        # names. Work with POSITIONS (not card objects): identical copies of a
        # card share one CardData object, so an id/value set can't tell "take one
        # of the four Swamps" apart from "take all four".
        #
        # candidates[t] = distinct-name revealed positions of type t (present
        # types only). A cross-product picks one position per type; a multi-type
        # card picked for two types is naturally counted once (index set).
        import itertools

        candidates: list[list[int]] = []
        for t in _CARD_TYPES:
            names: set[str] = set()
            idxs: list[int] = []
            for i in range(len(top)):
                if t in types_of(i) and top[i].name not in names:
                    names.add(top[i].name)
                    idxs.append(i)
            if idxs:
                candidates.append(idxs)

        hands: list[tuple[int, ...]] = []
        seen: set[tuple[int, ...]] = set()
        for combo in itertools.product(*candidates) if candidates else [()]:
            key = tuple(sorted(set(combo)))
            if key in seen:
                continue
            seen.add(key)
            hands.append(key)
            if len(hands) >= _MAX_BRANCHES:
                break
        truncated = len(hands) >= _MAX_BRANCHES

        def apply(st, chosen):
            for i, c in enumerate(top):
                if i in chosen:
                    # put_in_hand (not draw): records a "put_in_hand" event
                    # attributed to Atraxa's triggered ability, so the property
                    # helper cards_put_in_hand_by("Atraxa", ...) can count it.
                    st.put_in_hand(c)
                else:
                    st.library.append(c)  # bottom of the library
            if chosen:
                st.emit("Atraxa, Grand Unifier: to hand — "
                        + ", ".join(top[i].name for i in chosen))
            else:
                st.emit("Atraxa, Grand Unifier: take nothing")
            if truncated:
                st.emit("Atraxa: (branch cap reached — some hand choices pruned)")
            return None

        return branch_over(state, hands, apply)
