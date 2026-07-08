"""Cosmic Spider-Man — {W}{U}{B}{R}{G} 5/5 flying, first strike, trample,
lifelink, haste. His combat-start buff grants keywords (not stats) to other
Spiders; with no blockers, only the granted lifelink could matter — not
modelled (documented approximation). His own lifelink/haste are exact."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CosmicSpiderMan(Card):
    card_name = "Cosmic Spider-Man"
