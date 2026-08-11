"""Desert Nomads
{2}{R} Creature — Human Nomad 2/2. Desertwalk.
Prevent all damage that would be dealt to this creature by Deserts.

Desertwalk (evasion) and the Desert-damage prevention are inert in a solitaire
goldfish. A 2/2 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DesertNomads(Card):
    card_name = "Desert Nomads"
