"""Summon: Bahamut — {9} Enchantment Creature — Saga Dragon, 9/9 Flying.
I, II — Destroy up to one target nonland permanent.
III   — Draw two cards.
IV    — Mega Flare — deals damage equal to the total mana value of other
        permanents you control to each opponent.
Being also a creature, it is NOT sacrificed after chapter IV — it stays a 9/9
flying Dragon. Chapters I and II are no-ops against a phantom opponent (no
permanents worth destroying)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import mv
from .base import Card
from .registry import register


@register
class SummonBahamut(Card):
    card_name = "Summon: Bahamut"

    def etb_stack_items(self, state, permanent):
        return [self._lore_trigger(permanent, "I")]

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.DRAW or state.turn == 0:
            return []
        lore = perm.counters.get("lore", 0)
        if lore >= 4:
            return []
        roman = {1: "II", 2: "III", 3: "IV"}[lore + 1]
        return [self._lore_trigger(perm, roman)]

    def _lore_trigger(self, perm, roman):
        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            live.counters["lore"] = live.counters.get("lore", 0) + 1
            return live.impl._chapter(st, live, live.counters["lore"])

        return self.stack_ability(
            source_name=perm.name, label=f"Summon: Bahamut — chapter {roman}",
            resolve=resolve, trigger_text="A lore counter is put on Summon: Bahamut",
            ability_text=f"Chapter {roman}")

    def _chapter(self, state, perm, n: int):
        if n in (1, 2):
            state.emit(f"Summon: Bahamut {'I' * n}: no nonland permanent worth "
                       "destroying (phantom opponent)")
            return None
        if n == 3:
            state.draw(2)
            state.emit(f"Summon: Bahamut III: draw two ({len(state.hand)} in hand)")
            return None
        # IV — Mega Flare: damage = total mana value of OTHER permanents you control.
        total = sum(mv(p.card) for p in state.battlefield if p.uid != perm.uid)
        dealt = state.damage_opponent(total)
        state.emit(f"Summon: Bahamut IV — Mega Flare: {dealt} damage to opponent "
                   f"(opp {state.opponent_life}). Remains a 9/9 flying Dragon.")
        return None
