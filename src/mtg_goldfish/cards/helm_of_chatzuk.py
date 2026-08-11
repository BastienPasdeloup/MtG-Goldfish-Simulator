"""Helm of Chatzuk — {1} Artifact.
{1}, {T}: Target creature gains banding until end of turn.

Banding is a combat-only ability (grouping attackers/blockers, assigning combat
damage) — entirely inert in a solitaire goldfish with no opposing blockers — so
the grant has no material effect. The artifact is still cast and enters the
battlefield (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HelmOfChatzuk(Card):
    card_name = "Helm of Chatzuk"
