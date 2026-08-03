"""Emet-Selch, Unsundered // Hades, Sorcerer of Eld — {1}{U}{B} Legendary 2/4,
Vigilance.
Front: Whenever Emet-Selch enters or attacks, draw a card, then discard a card.
At the beginning of your upkeep, if there are fourteen or more cards in your
graveyard, you may transform it.
Back (Hades, 6/6): During your turn you may play cards from your graveyard; if a
card would be put into your graveyard from anywhere, exile it instead (modelled
via the perm-aware `grants_gy_play_all` / `replaces_gy_with_exile` statics)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over, loot
from .base import Card
from .registry import register


@register
class EmetSelchUnsundered(Card):
    card_name = "Emet-Selch, Unsundered"

    # Hades (back face) statics — active only once transformed.
    def grants_gy_play_all_perm(self, perm):
        return perm.transformed

    def replaces_gy_with_exile_perm(self, perm):
        return perm.transformed

    def on_etb(self, state, permanent):
        if permanent.transformed:
            return None
        return loot(state, 1, 1, source="Emet-Selch")

    def on_attack(self, state, perm):
        if perm.transformed:
            return None
        return loot(state, 1, 1, source="Emet-Selch")

    def phase_stack_items(self, state, perm, phase):
        # Upkeep: if 14+ cards in your graveyard, you MAY transform Emet-Selch.
        if (phase != Phase.UPKEEP or perm.transformed
                or len(state.graveyard) < 14):
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None or live.transformed:
                return None

            def fn(s, do):
                p = s.find_permanent(uid)
                if p is None:
                    return None
                if do:
                    p.transformed = True
                    s.emit("Emet-Selch: transform → Hades, Sorcerer of Eld")
                else:
                    s.emit("Emet-Selch: decline to transform")
                return None

            return branch_over(st, [True, False], fn)

        return [self.stack_ability(
            source_name=perm.name, label="Emet-Selch: upkeep — may transform",
            resolve=resolve, trigger_text="At the beginning of your upkeep, if there "
            "are fourteen or more cards in your graveyard",
            ability_text="You may transform Emet-Selch")]
