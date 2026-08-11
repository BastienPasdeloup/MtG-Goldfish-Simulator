"""Deathgrip
{B}{B} Enchantment — {B}{B}: Counter target green spell.
No opponent spells to counter in a solitaire goldfish — no effect (a {B}{B}
enchantment permanent)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Deathgrip(Card):
    card_name = "Deathgrip"
