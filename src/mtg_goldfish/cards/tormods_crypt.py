"""Tormod's Crypt — {0} Artifact.
{T}, Sacrifice this artifact: Exile target player's graveyard.

Graveyard hate aimed at opponents. In a solitaire goldfish the only graveyard is
YOURS (which Emry wants to keep), so exiling it is a downside the search avoids —
the ability is offered for completeness; Tormod's Crypt otherwise plays as a free
{0} artifact (artifact count / sacrifice fodder)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class TormodsCrypt(Card):
    card_name = "Tormod's Crypt"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            p.tapped = True
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            n = len(st.graveyard)
            # The Crypt itself is now in the graveyard; it stays (it's the source
            # being sacrificed as a cost, so it isn't part of what's exiled here —
            # but for simplicity we exile the graveyard as it stands minus itself).
            keep = next((c for c in st.graveyard if c.name == "Tormod's Crypt"), None)
            exiled = [c for c in list(st.graveyard) if c is not keep]
            for c in exiled:
                st.graveyard.remove(c)
                st.exile.append(c)
            st.emit(f"Tormod's Crypt: exile your graveyard ({len(exiled)} card(s))")
            return None

        return [CardAction.activated(
            "Tormod's Crypt: {T}, sacrifice — exile a graveyard",
            pay, resolve, source_name="Tormod's Crypt",
            ability_text="Exile target player's graveyard")]
