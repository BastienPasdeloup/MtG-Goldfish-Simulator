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

        def pay(st):
            # Cost: sacrifice a land (paid at activation, before the ability
            # goes on the stack).
            p = st.find_permanent(perm.uid)
            if p is None:
                return False
            sac = st.find_permanent(pick.uid) or next(
                (q for q in st.battlefield if "land" in q.type_line.lower()), None)
            if sac is None or "land" not in sac.type_line.lower():
                return False
            st.leaves_battlefield(sac, "graveyard")
            st.emit(f"Zuran Orb: sacrifice {sac.name}")
            return True

        def resolve(st):
            st.life += 2
            st.emit("Zuran Orb: gain 2 life")
            return None

        return [CardAction.activated(
            "Zuran Orb: sacrifice a land — gain 2 life",
            pay,
            resolve,
            source_name="Zuran Orb",
            ability_text="Sacrifice a land: You gain 2 life",
        )]
