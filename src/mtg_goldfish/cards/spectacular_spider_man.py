"""Spectacular Spider-Man — {1}{W} Legendary 3/2, flash.
"{1}: gains flying" and "{1}, Sacrifice: creatures gain hexproof and
indestructible" have no observable effect in a solitaire game (no blockers, no
opposing removal) — deliberately not offered as actions to keep the search
tractable. The body and flash are exact."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SpectacularSpiderMan(Card):
    card_name = "Spectacular Spider-Man"
