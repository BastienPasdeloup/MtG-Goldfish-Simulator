"""Red Elemental Blast — {R} Instant.
Choose one — counter target blue spell; OR destroy target blue permanent.

No opponent blue spell/permanent exists in a solitaire goldfish, but the destroy
mode is still a real ability: it can destroy a BLUE permanent (only your own are
available). One branch per distinct blue permanent you control."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class RedElementalBlast(Card):
    card_name = "Red Elemental Blast"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen = set()
        for p in state.battlefield:
            if "U" not in p.colors or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.emit(f"Red Elemental Blast: destroy {nm}")
                    st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None
                return fn

            acts.append(CardAction(f"cast Red Elemental Blast → destroy {p.name}",
                                   make(p.uid, p.name)))
        return acts
