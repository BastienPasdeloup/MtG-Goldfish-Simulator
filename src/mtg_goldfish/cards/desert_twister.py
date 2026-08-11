"""Desert Twister — {4}{G}{G} Sorcery. Destroy target permanent.

Only your own permanents are available in a solitaire goldfish (one branch per
distinct permanent). Respects indestructible."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class DesertTwister(Card):
    card_name = "Desert Twister"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.emit(f"Desert Twister: destroy {nm}")
                    st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None
                return fn

            acts.append(CardAction(f"cast Desert Twister → destroy {p.name}", make(p.uid, p.name)))
        return acts
