"""Wilderness Reclamation — {3}{G} Enchantment. At the beginning of your end
step, untap all lands you control."""
from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class WildernessReclamation(Card):
    card_name = "Wilderness Reclamation"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        n = 0
        for p in state.battlefield:
            if p.is_land and p.tapped:
                p.tapped = False
                n += 1
        if n:
            state.emit(f"Wilderness Reclamation: untap {n} land(s)")
