"""Zuran Orb — {0} Artifact.
Sacrifice a land: you gain 2 life. Free, any number of times. The land
sacrificed is chosen deterministically (a tapped land if any, else the
first) — pure lifegain, no meaningful branch."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class ZuranOrb(Card):
    card_name = "Zuran Orb"

    def battlefield_actions(self, state, perm):
        lands = [p for p in state.battlefield if "land" in p.type_line.lower()]
        if not lands:
            return []
        pick = next((p for p in lands if p.tapped), lands[0])

        def fn(st):
            sac = next((p for p in st.battlefield
                        if p.uid == pick.uid), None) or next(
                (p for p in st.battlefield if "land" in p.type_line.lower()), None)
            if sac is None:
                return None
            st.leaves_battlefield(sac, "graveyard")
            st.life += 2
            st.emit(f"Zuran Orb: sacrifice {sac.name} — gain 2 life")
            return None

        return [CardAction("Zuran Orb: sacrifice a land — gain 2 life", fn)]
