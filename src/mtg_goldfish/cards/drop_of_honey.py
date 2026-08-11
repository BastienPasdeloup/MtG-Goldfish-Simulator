"""Drop of Honey — {G} Enchantment.
At the beginning of your upkeep, destroy the creature with the least power. It
can't be regenerated. If two or more are tied, you choose one.
When there are no creatures on the battlefield, sacrifice this enchantment.

Symmetric edict — in a solitaire goldfish it destroys YOUR lowest-power creature
each upkeep (ties broken by lowest toughness, then arbitrary). With no creatures
on the battlefield it sacrifices itself."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class DropOfHoney(Card):
    card_name = "Drop of Honey"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        creatures = [p for p in state.battlefield if p.is_creature_now]
        if not creatures:
            me = state.find_permanent(perm.uid)
            if me is not None:
                state.emit("Drop of Honey: no creatures — sacrifice")
                state.leaves_battlefield(me, "graveyard", reason="sacrifice")
            return None
        victim = min(creatures, key=lambda c: (state.effective_power(c),
                                               state.effective_toughness(c)))
        victim.counters.pop("regen_shield", None)  # can't be regenerated
        state.emit(f"Drop of Honey: destroy least-power creature {victim.name}")
        state.leaves_battlefield(victim, "graveyard", reason="destroy")
        return None
