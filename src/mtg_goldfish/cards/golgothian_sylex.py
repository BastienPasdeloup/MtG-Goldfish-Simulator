"""Golgothian Sylex — {4} Artifact.
{1}, {T}: Each nontoken permanent with a name originally printed in the Antiquities
expansion is sacrificed by its controller.

A symmetric sweeper of Antiquities-name permanents. In a goldfish it can only
sacrifice YOUR OWN Antiquities permanents (and itself), so activating it is always
a net loss — the exhaustive search would never choose it. Registered as a fixed
artifact; the strictly-negative ability is left inert rather than bloating the
search (and hardcoding the ~85-card Antiquities name set for a never-used line)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GolgothianSylex(Card):
    card_name = "Golgothian Sylex"
