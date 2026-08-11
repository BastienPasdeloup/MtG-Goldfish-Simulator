"""Giant Growth — {G} Instant.
Target creature gets +3/+3 until end of turn.

Cast on one of your creatures (one branch each): temp +3/+3 for the turn. The
search casts it only when it helps (a bigger attacker / surviving a fight)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class GiantGrowth(Card):
    card_name = "Giant Growth"

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
                    tgt.temp_power += 3
                    tgt.temp_toughness += 3
                    st.emit(f"Giant Growth: {nm} gets +3/+3 until end of turn")
                    return None
                return fn

            acts.append(CardAction(f"cast Giant Growth → {p.name}", make(p.uid, p.name)))
        return acts
