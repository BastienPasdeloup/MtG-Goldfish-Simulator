"""Simulacrum — {1}{B} Instant.
You gain life equal to the damage dealt to you this turn. Simulacrum deals damage
to target creature you control equal to the damage dealt to you this turn.

Gain X life (X = damage taken this turn, via the tracker) and deal X to one of
your creatures (one branch each). Best cast after taking damage — the search gates
naturally on the tracker."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Simulacrum(Card):
    card_name = "Simulacrum"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    x = st.damage_taken_this_turn
                    st.gain_life(x)
                    st.damage_permanent(tgt, x)
                    st.emit(f"Simulacrum: gain {x} life, deal {x} to {nm}")
                    st.check_deaths()
                    return None
                return fn

            acts.append(CardAction(f"cast Simulacrum → {p.name}", make(p.uid, p.name)))
        return acts
