"""Channel — {G}{G} Sorcery.
Until end of turn, any time you could activate a mana ability, you may pay 1 life:
add {C}.

Modelled as converting life to colourless mana at resolution: branch over how much
life N you turn into N {C} in your pool (0..life-1). You then spend that mana this
turn (e.g. a big Fireball). A close goldfish approximation of paying life for mana
as needed."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Channel(Card):
    card_name = "Channel"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        cap = min(max(0, state.life - 1), 20)
        for n in range(0, cap + 1):
            def make(nn):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    if nn > 0:
                        st.life -= nn
                        st.mana_pool.add("C", nn)
                        st.emit(f"Channel: pay {nn} life — add {nn} {{C}}")
                    return None
                return fn

            acts.append(CardAction(f"cast Channel (pay {n} life → {n} colorless)", make(n)))
        return acts
