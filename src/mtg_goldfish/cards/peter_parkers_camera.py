"""Peter Parker's Camera — {1} Artifact. Enters with three film counters.
{2}, {T}, Remove a film counter: copy target activated or triggered ability you
control. Copying abilities has no generic engine support, so the copy ability is
not modelled — it enters as an inert artifact carrying its film counters."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class PeterParkersCamera(Card):
    card_name = "Peter Parker's Camera"

    def enters_with_counters(self, state):
        return {"film": 3}
