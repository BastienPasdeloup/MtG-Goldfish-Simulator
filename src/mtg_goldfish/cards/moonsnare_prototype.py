"""Moonsnare Prototype — {U} Artifact. Channel.
{T}, Tap an untapped artifact or creature you control: Add {C}.
Channel — {4}{U}, Discard this card: The owner of target nonland permanent puts
it on their choice of the top or bottom of their library.

The mana ability is modelled faithfully as a battlefield action that taps
Moonsnare AND another untapped artifact/creature you control to add {C} (so it's
a real 2-tap cost, not free mana). Channel bounces a permanent — only your own in
solitaire, no worthwhile use — so it isn't modelled."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class MoonsnarePrototype(Card):
    card_name = "Moonsnare Prototype"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        # The extra permanent to tap (an untapped artifact/creature that isn't
        # Moonsnare itself): pick the least useful (non-mana artifact first).
        others = [p for p in state.battlefield
                  if p.uid != perm.uid and not p.tapped
                  and (p.is_artifact or p.is_creature_now)
                  and not (p.is_creature_now and p.summoning_sick
                           and not state.has_keyword(p, "Haste"))]
        if not others:
            return []
        others.sort(key=lambda p: (bool(p.impl.mana_abilities_perm(state, p)),))
        extra = others[0]

        def pay(st):
            p = st.find_permanent(perm.uid)
            other = st.find_permanent(extra.uid)
            if p is None or other is None or p.tapped or other.tapped:
                return False
            p.tapped = True
            other.tapped = True
            return True

        def resolve(st):
            st.mana_pool.add("C", 1)
            st.emit(f"Moonsnare Prototype: tap + tap {extra.name} — add {{C}}")
            return None

        return [CardAction.activated(
            f"Moonsnare Prototype: {{T}}, tap {extra.name} — add {{C}}",
            pay, resolve, source_name="Moonsnare Prototype",
            ability_text="Add {C}")]
