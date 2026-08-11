"""Mind Twist — {X}{B} Sorcery.
Target player discards X cards at random.

Targets an opponent's hand, which isn't modelled in a solitaire goldfish, so the
spell is inert. It is still cast (counting toward spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MindTwist(Card):
    card_name = "Mind Twist"
