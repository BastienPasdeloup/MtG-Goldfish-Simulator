"""Cosmic Spider-Man — {W}{U}{B}{R}{G} 5/5 flying, first strike, trample,
lifelink, haste. "At the beginning of combat on your turn, other Spiders you
control gain flying, first strike, trample, lifelink, and haste until end of
turn." — modelled as temp keywords (cleared at cleanup): haste lets
summoning-sick Spiders attack, lifelink counts on their combat damage. First
strike/trample/flying have no extra effect against a phantom opponent."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register

_GRANTS = ("flying", "first strike", "trample", "lifelink", "haste")


@register
class CosmicSpiderMan(Card):
    card_name = "Cosmic Spider-Man"

    @staticmethod
    def _other_spiders(state, perm):
        return [p for p in state.battlefield
                if p.uid != perm.uid and p.is_creature_now
                and "spider" in p.type_line.lower()]

    def phase_stack_items(self, state, perm, phase):
        # Only at the beginning of combat, and only when there is another
        # Spider to buff (a no-op trigger would just pollute the stack/replay).
        if phase != Phase.BEGIN_COMBAT or not self._other_spiders(state, perm):
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.BEGIN_COMBAT)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: begin_combat trigger",
            resolve=resolve,
            trigger_text="At the beginning of combat on your turn",
            ability_text="Other Spiders you control gain flying, first strike, "
                         "trample, lifelink, and haste until end of turn.",
        )]

    def on_phase(self, state, perm, phase):
        if phase != Phase.BEGIN_COMBAT:
            return
        spiders = self._other_spiders(state, perm)
        if not spiders:
            return
        for p in spiders:
            p.temp_keywords.update(_GRANTS)
        names = ", ".join(p.name for p in spiders)
        state.emit(f"{perm.name}: {names} gain{'s' if len(spiders) == 1 else ''} "
                   "flying, first strike, trample, lifelink, haste until end of turn")
