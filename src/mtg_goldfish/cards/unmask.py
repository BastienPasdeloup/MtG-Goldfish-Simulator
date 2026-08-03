"""Unmask — {3}{B} Sorcery. You may exile a black card from your hand rather than
pay the mana cost. Target player reveals their hand; you choose a nonland card;
that player discards it. Aim at yourself to bin a nonland."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import discard_spell_actions
from .base import Card, CardAction
from .registry import register


@register
class Unmask(Card):
    card_name = "Unmask"

    def cast_actions(self, state):
        acts = discard_spell_actions(self, state, pred=lambda c: not c.is_land)
        # Alternative cost: exile a black card from hand instead of paying mana.
        from ..engine.actions import begin_cast
        blacks = {c.name for c in state.hand
                  if c.name != self.card_name and "B" in (c.colors or [])}
        for bname in sorted(blacks):
            def make(bname=bname):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    pitch = next((c for c in st.hand if c.name == bname), None)
                    if card is None or pitch is None:
                        return None
                    st.hand.remove(pitch)
                    st.exile.append(pitch)
                    if not begin_cast(st, card, ManaCost()):
                        return None
                    from ..engine.actions import resolve_to_graveyard
                    resolve_to_graveyard(st, card)
                    st.emit(f"Unmask: exile {bname} instead of paying; opponent has no hand")
                    return None
                return fn
            acts.append(CardAction(f"cast Unmask (exile {bname})", make()))
        return acts
