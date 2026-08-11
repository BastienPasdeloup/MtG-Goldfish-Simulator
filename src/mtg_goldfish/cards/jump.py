"""Jump — {U} Instant. Target creature gains flying until end of turn.

Grants flying (temp_keywords) to one of your creatures (one branch each). Evasion
is inert with no blockers, but the keyword is genuinely granted."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Jump(Card):
    card_name = "Jump"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_creature_now or p.name in seen or "flying" in p.temp_keywords:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    tgt.temp_keywords.add("flying")
                    st.emit(f"Jump: {nm} gains flying until end of turn")
                    return None
                return fn

            acts.append(CardAction(f"cast Jump → {p.name}", make(p.uid, p.name)))
        return acts
