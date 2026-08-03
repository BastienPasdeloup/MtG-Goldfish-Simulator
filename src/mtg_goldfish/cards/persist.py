"""Persist — {1}{B} Sorcery. Return target nonlegendary creature card from your
graveyard to the battlefield with a -1/-1 counter on it (modelled as a net
{+1/+1: -1}, which correctly annihilates with any +1/+1 counters)."""
from __future__ import annotations

from ._common import reanimate_branches
from .base import Card
from .registry import register


@register
class Persist(Card):
    card_name = "Persist"

    def on_resolve(self, state):
        return reanimate_branches(
            state,
            pred=lambda c: c.is_creature and "legendary" not in c.type_line.lower(),
            marks={"+1/+1": -1}, note=" with a -1/-1 counter")
