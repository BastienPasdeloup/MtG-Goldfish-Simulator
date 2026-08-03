"""Emeritus of Ideation // Ancestral Recall — {3}{U}{U} 5/5 Flying, ward {2}.
Modelled as its front-face body: a 5/5 flying ward creature (and a reanimation
target). The "prepared" mechanic and the Ancestral Recall back face (draw three)
are not modelled — "prepared" has no board-state effect a goldfish exploits, and
the back is only reachable through that mechanic. The attack ability (exile eight
cards from your graveyard) is likewise skipped as a pure downside here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class EmeritusOfIdeation(Card):
    card_name = "Emeritus of Ideation"
