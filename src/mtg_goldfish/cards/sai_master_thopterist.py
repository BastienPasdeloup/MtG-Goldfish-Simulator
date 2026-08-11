"""Sai, Master Thopterist — {2}{U} Legendary Creature — Human Artificer 1/4.
Whenever you cast an artifact spell, create a 1/1 colorless Thopter artifact
creature token with flying.
{1}{U}, Sacrifice two artifacts: Draw a card.

The Thopter's flying is cosmetic in a goldfish (it just counts as an artifact,
which is the point — Thopter fodder for the draw ability). The draw ability
sacrifices the two least valuable artifacts (tokens first)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import mv
from .base import Card, CardAction
from .registry import register


@register
class SaiMasterThopterist(Card):
    card_name = "Sai, Master Thopterist"

    def on_cast_other(self, state, perm, card):
        if card.is_artifact:
            state.make_token("Thopter", 1, 1, "Token Artifact Creature — Thopter",
                             text="Flying")
            state.emit("Sai: create a 1/1 flying Thopter")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("U", 1),))
        # Artifacts we can sacrifice (Sai itself is not an artifact). Prefer
        # tokens, then lowest mana value — keep the good artifacts.
        arts = [p for p in state.battlefield if p.is_artifact]
        if len(arts) < 2 or not can_afford(state, cost):
            return []
        arts.sort(key=lambda p: (not p.is_token, mv(p.card), p.name))
        fodder = arts[:2]
        fuids = [p.uid for p in fodder]
        fnames = ", ".join(p.name for p in fodder)

        def pay(st):
            perms = [st.find_permanent(u) for u in fuids]
            if any(p is None for p in perms) or not pay_cost(st, cost):
                return False
            for p in perms:
                st.emit(f"Sai: sacrifice {p.name}")
                st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            st.emit("Sai: draw a card")
            st.draw(1)
            return None

        return [CardAction.activated(
            f"Sai: {{1}}{{U}}, sacrifice two artifacts ({fnames}) — draw a card",
            pay, resolve, source_name="Sai, Master Thopterist",
            ability_text="Sacrifice two artifacts: draw a card")]
