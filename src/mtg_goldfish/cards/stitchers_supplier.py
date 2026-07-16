"""Stitcher's Supplier — {B} Creature 1/1. When it enters or dies, mill three."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class StitchersSupplier(Card):
    card_name = "Stitcher's Supplier"

    def on_etb(self, state, permanent):
        state.emit("Stitcher's Supplier enters: mill 3")
        state.mill(3)

    def on_leave(self, state, permanent):
        state.emit("Stitcher's Supplier dies: mill 3")
        state.mill(3)
