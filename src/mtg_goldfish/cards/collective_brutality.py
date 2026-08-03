"""Collective Brutality — {1}{B} Sorcery. Escalate—Discard a card. Choose one or
more: (1) opponent discards an instant/sorcery; (2) target creature gets -2/-2;
(3) opponent loses 2 life and you gain 2 life.

Against a phantom opponent modes 1 and 2 do nothing (no hand, no creatures), so
the useful play is mode 3 (drain 2) plus, optionally, escalating by discarding
cards — which in this reanimator deck is pure upside (bin fatties). Modelled as:
drain 2, then optionally discard up to two cards (the escalate cost)."""
from __future__ import annotations

from ._common import discard_branches
from .base import Card, CardAction
from .registry import register


@register
class CollectiveBrutality(Card):
    card_name = "Collective Brutality"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        others = len([c for c in state.hand if c.name != self.card_name])
        acts = []
        for esc in range(0, min(2, others) + 1):
            def make(esc=esc):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.opponent_life -= 2           # life loss, not damage
                    st.life += 2
                    st.note_crime()
                    st.emit(f"Collective Brutality: opponent loses 2, you gain 2 "
                            f"(you {st.life}, opp {st.opponent_life})")
                    if esc > 0:
                        return discard_branches(st, esc,
                                                source="Collective Brutality escalate")
                    return None
                return fn
            label = ("cast Collective Brutality (drain 2)" if esc == 0
                     else f"cast Collective Brutality (drain 2, escalate discard {esc})")
            acts.append(CardAction(label, make()))
        return acts
