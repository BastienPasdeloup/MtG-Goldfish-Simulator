"""Moonmist — {1}{G} Instant. Transform all Humans. Prevent all combat damage
that would be dealt this turn by creatures other than Werewolves and Wolves.

Every permanent whose ACTIVE face is a Human and that has a back face flips
(transform is a flag toggle — the engine has no "when this transforms"
triggers, matching how Bruce Banner's own transform behaves). The prevention
rider is a real drawback in a goldfish (our own non-Wolf attackers deal no
combat damage this turn): `GameState.prevent_nonwolf_combat_damage`, checked
in deal_combat_damage and reset at untap.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Moonmist(Card):
    card_name = "Moonmist"

    def on_resolve(self, state):
        flipped = []
        for p in state.battlefield:
            if len(p.card.faces) > 1 and "human" in p.type_line.lower():
                p.transformed = not p.transformed
                flipped.append(p.name)  # the NEW (post-flip) face name
        state.prevent_nonwolf_combat_damage = True
        what = f"transform {', '.join(flipped)}" if flipped else "no Humans to transform"
        state.emit(f"Moonmist: {what} — non-Wolf combat damage prevented this turn")
        return None
