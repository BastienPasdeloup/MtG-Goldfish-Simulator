"""Conjurer's Bauble — {1} Artifact.
{T}, Sacrifice this artifact: Put up to one target card from your graveyard on
the bottom of your library. Draw a card.

One branch per distinct graveyard card you could recycle (plus recycling
nothing). Targets are chosen when the ability is activated — the Bauble itself,
sacrificed as a cost, is therefore not a legal target."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class ConjurersBauble(Card):
    card_name = "Conjurer's Bauble"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        # Distinct graveyard cards that can be recycled (chosen before the sac).
        recyclable: dict[str, str] = {}
        for c in state.graveyard:
            recyclable.setdefault(c.name, c.name)

        def sac(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            p.tapped = True
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def make(target_name):
            def pay(st):
                return sac(st)

            def resolve(st):
                if target_name is not None:
                    card = next((c for c in st.graveyard if c.name == target_name), None)
                    if card is not None:
                        st.graveyard.remove(card)
                        st.library.append(card)  # bottom of library
                        st.emit(f"Conjurer's Bauble: put {target_name} on the bottom of library")
                st.emit("Conjurer's Bauble: draw a card")
                st.draw(1)
                return None

            label = ("Conjurer's Bauble: sacrifice — draw a card" if target_name is None
                     else f"Conjurer's Bauble: sacrifice — recycle {target_name}, draw")
            return CardAction.activated(
                label, pay, resolve, source_name="Conjurer's Bauble",
                ability_text="Recycle a graveyard card, draw a card")

        return [make(None)] + [make(n) for n in recyclable]
