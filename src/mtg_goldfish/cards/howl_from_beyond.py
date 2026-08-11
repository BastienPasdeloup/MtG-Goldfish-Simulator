"""Howl from Beyond — {X}{B} Instant.
Target creature gets +X/+0 until end of turn.

Cast on one of your creatures (one branch per creature × affordable X): temp
+X/+0 for the turn."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class HowlFromBeyond(Card):
    card_name = "Howl from Beyond"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        creatures = []
        seen: set[str] = set()
        for p in state.battlefield:
            if p.is_creature_now and p.name not in seen:
                seen.add(p.name)
                creatures.append((p.uid, p.name))
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("B", 1),))
            if not can_afford(state, cost):
                continue
            for uid, nm in creatures:
                def make(xx, c, u, n):
                    def fn(st):
                        card = next((k for k in st.hand if k.name == self.card_name), None)
                        tgt = st.find_permanent(u)
                        if card is None or tgt is None or not begin_cast(st, card, c):
                            return None
                        resolve_to_graveyard(st, card)
                        tgt.temp_power += xx
                        st.emit(f"Howl from Beyond: {n} gets +{xx}/+0 until end of turn")
                        return None
                    return fn

                acts.append(CardAction(
                    f"cast Howl from Beyond (X={x}) → {nm}", make(x, cost, uid, nm)))
        return acts
