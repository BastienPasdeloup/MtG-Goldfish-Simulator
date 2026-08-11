"""Sunglasses of Urza
{3} Artifact.
You may spend white mana as though it were red mana.

A mana-filtering effect (spend W as R) that is a marginal fixing benefit; the
"spend-as-though" replacement isn't modelled. The artifact is still cast and
enters (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SunglassesOfUrza(Card):
    card_name = "Sunglasses of Urza"
