"""Lifetap — {U}{U} Enchantment.
Whenever a Forest an opponent controls becomes tapped, you gain 1 life.

Triggers only off an opponent's Forests, of which there are none in a solitaire
goldfish, so the ability is inert. The enchantment is still cast and enters
(counting toward enchantment/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Lifetap(Card):
    card_name = "Lifetap"
