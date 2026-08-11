"""Animate Artifact — {3}{U} Enchantment — Aura. Enchant artifact.
As long as enchanted artifact isn't a creature, it's an artifact creature with
power and toughness each equal to its mana value.

Attaches to one of your (noncreature) artifacts and animates it — adds the
Creature type with P/T = its mana value (via `becomes`); the animation ends if
the Aura leaves."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class AnimateArtifact(Card):
    card_name = "Animate Artifact"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            if host.is_creature_now:
                return  # "as long as it isn't a creature" — no effect
            mvv = int(host.card.cmc)
            tl = host.type_line
            head, _, tail = tl.partition("—")
            head = head.strip()
            if "creature" not in head.lower():
                head = (head + " Creature").strip()
            tail = tail.strip()
            host.becomes = {
                "type_line": head + (f" — {tail}" if tail else ""),
                "power": mvv, "toughness": mvv, "permanent": True,
            }
            st.emit(f"Animate Artifact: {host.name} becomes a {mvv}/{mvv} artifact creature")

        return aura_enchant_actions(self, state, cost="{3}{U}",
                                    pred=lambda p: p.is_artifact, on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None and host.becomes is not None:
            host.becomes = None  # animation ends when the Aura leaves
