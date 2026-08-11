"""City in a Bottle — {2} Artifact.
Whenever one or more OTHER nontoken permanents with a name originally printed in
the Arabian Nights expansion are on the battlefield, their controllers sacrifice
them.
Players can't cast spells or play lands with a name originally printed in Arabian
Nights.

"Originally printed in Arabian Nights" is detected by the card's set code
(`card.set == "arn"`). While City in a Bottle is in play it sacrifices every other
nontoken Arabian Nights permanent (on entry and as they enter), and makes Arabian
Nights spells uncastable (a huge `cast_cost_increase`). NOTE: the set code is only
present on cards fetched after the `set`-field change — re-import old decks for
this to see their AN cards."""
from __future__ import annotations

from .base import Card
from .registry import register

_AN = "arn"


def _is_an(perm) -> bool:
    return not perm.is_token and getattr(perm.card, "set", "") == _AN


@register
class CityInABottle(Card):
    card_name = "City in a Bottle"

    def cast_cost_increase(self, state, card):
        # Can't cast Arabian Nights spells (make them prohibitively expensive).
        return 10 ** 6 if getattr(card, "set", "") == _AN else 0

    def _sacrifice_all(self, state, perm):
        for p in list(state.battlefield):
            if p.uid != perm.uid and _is_an(p):
                state.emit(f"City in a Bottle: sacrifice {p.name} (Arabian Nights)")
                state.leaves_battlefield(p, "graveyard", reason="sacrifice")

    def on_etb(self, state, permanent):
        self._sacrifice_all(state, permanent)

    def on_other_etb(self, state, perm, entering):
        if entering.uid != perm.uid and _is_an(entering):
            state.emit(f"City in a Bottle: sacrifice {entering.name} (Arabian Nights)")
            state.leaves_battlefield(entering, "graveyard", reason="sacrifice")
