"""Winter Moon — {2} Artifact.
Players can't untap more than one nonbasic land during their untap steps.

Symmetric stax (affects you in a solitaire goldfish): limits your own untap step
to one nonbasic land. Modelled via the untap-step nonbasic limit hook."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WinterMoon(Card):
    card_name = "Winter Moon"

    def untap_nonbasic_limit(self, state, perm):
        return 1
