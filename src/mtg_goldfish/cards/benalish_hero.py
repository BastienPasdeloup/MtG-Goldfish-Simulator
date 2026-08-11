"""Benalish Hero — {W} Creature — Human Soldier 1/1. Banding.
Banding is a blocking / combat-damage-assignment ability with no effect in a
solitaire goldfish (you are never blocked by a band, and there are no blockers to
band against on defence) — so this is a plain 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BenalishHero(Card):
    card_name = "Benalish Hero"
