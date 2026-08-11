"""Twiddle — {U} Instant.
You may tap or untap target artifact, creature, or land.

The useful mode in a solitaire goldfish is to UNTAP one of your tapped permanents
(freeing a land/artifact to be used again this turn) — one branch per distinct
tapped artifact/creature/land. Tapping your own permanent is never beneficial, so
that mode isn't offered."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Twiddle(Card):
    card_name = "Twiddle"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.tapped or p.name in seen:
                continue
            if not (p.is_artifact or p.is_creature_now or p.is_land):
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    tgt.tapped = False
                    st.emit(f"Twiddle: untap {nm}")
                    return None
                return fn

            acts.append(CardAction(f"cast Twiddle → untap {p.name}", make(p.uid, p.name)))
        return acts
