"""Blue Elemental Blast — {U} Instant.
Choose one — counter target red spell; OR destroy target red permanent.

No opponent red spell/permanent exists in a solitaire goldfish, but the destroy
mode is still a real ability: it can destroy a RED permanent (only your own are
available — rarely useful, but the ability is offered). One branch per distinct
red permanent you control."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class BlueElementalBlast(Card):
    card_name = "Blue Elemental Blast"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen = set()
        for p in state.battlefield:
            if "R" not in p.colors or p.name in seen:
                continue
            seen.add(p.name)

            def make(uid, nm):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    tgt = st.find_permanent(uid)
                    if card is None or tgt is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.emit(f"Blue Elemental Blast: destroy {nm}")
                    st.leaves_battlefield(tgt, "graveyard", reason="destroy")
                    return None
                return fn

            acts.append(CardAction(f"cast Blue Elemental Blast → destroy {p.name}",
                                   make(p.uid, p.name)))
        return acts
