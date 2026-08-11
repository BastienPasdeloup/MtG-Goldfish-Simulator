"""Ice Storm — {2}{G} Sorcery.
Destroy target land.

Only your own lands exist in a solitaire goldfish, so this destroys one of them
(one branch each) — faithful and rarely good. Respects indestructible."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class IceStorm(Card):
    card_name = "Ice Storm"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for p in state.battlefield:
            if not p.is_land or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    st.emit(f"Ice Storm: destroy {nm}")
                    return None
                return fn

            acts.append(CardAction(f"cast Ice Storm → {p.name}", make(p.uid, p.name)))
        return acts
