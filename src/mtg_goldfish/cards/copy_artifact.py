"""Copy Artifact — {1}{U} Enchantment.
You may have this enchantment enter as a copy of any artifact on the battlefield,
except it's an enchantment in addition to its other types.

One ETB branch per distinct artifact to copy (plus declining). The copy is
permanent (it gains the artifact's abilities — e.g. a mana rock's mana)."""
from __future__ import annotations

from ._common import enter_as_copy
from .base import Card
from .registry import register


@register
class CopyArtifact(Card):
    card_name = "Copy Artifact"

    def enter_choices(self, state, perm):
        return enter_as_copy(self, state, perm, lambda p: p.is_artifact)
