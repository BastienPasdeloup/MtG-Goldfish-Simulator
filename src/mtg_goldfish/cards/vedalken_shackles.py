"""Vedalken Shackles — {3} Artifact.
You may choose not to untap this artifact during your untap step.
{2}, {T}: Gain control of target creature with power <= the number of Islands you
control, for as long as this artifact remains tapped.

The control ability can only ever target your OWN creatures in a solitaire game
(gaining control of something you already control does nothing), so it has no
goldfish effect — it plays as a {3} artifact for the artifact synergies."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class VedalkenShackles(Card):
    card_name = "Vedalken Shackles"
