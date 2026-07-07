"""Lightning Bolt — {R} instant, deals 3 damage.

In a solitaire goldfish there is no real target; it resolves as a no-op. It
exists as a canonical example of a *non-creature spell* so properties like
"N non-creature spells cast this turn" have something to count.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class LightningBolt(Card):
    card_name = "Lightning Bolt"

    def on_resolve(self, state) -> None:
        # No opponent/permanent to damage in a goldfish; nothing to do.
        return None
