"""Ironheart, Clever Champion — {4}{U} Legendary Artifact Creature — Human Hero 3/4.
Improvise (its own keyword — read from the card data by the cast planner).
Flying.
Noncreature spells you cast have improvise."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IronheartCleverChampion(Card):
    card_name = "Ironheart, Clever Champion"
    # "Noncreature spells you cast have improvise."
    grants_noncreature_improvise = True
