"""Spellskite — {2} Artifact Creature — Phyrexian Horror 0/4.
{U/P}: Change a target of target spell or ability to this creature.

Redirection only matters against an opponent's spells/abilities (none in a
solitaire goldfish), so the ability has no effect here — it plays as a 0/4
artifact-creature blocker that counts for the artifact synergies."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Spellskite(Card):
    card_name = "Spellskite"
