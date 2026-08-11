"""Gaea's Liege — {3}{G}{G}{G} Creature — Avatar */*.
As long as Gaea's Liege isn't attacking, its power and toughness each equal the
number of Forests you control. As long as it is attacking, they each equal the
number of Forests the defending player controls.
{T}: Target land becomes a Forest until this creature leaves the battlefield.

Dynamic P/T = your Forest count (via forest_count); while attacking, the
"defending player" is the phantom opponent (0 Forests), so it becomes 0/0. The
{T} ability turns one of your lands into a Forest (mana_override "G") — one branch
per land; it does not revert on leave (a minor simplification)."""
from __future__ import annotations

from ._common import forest_count
from .base import Card, CardAction
from .registry import register


@register
class GaeasLiege(Card):
    card_name = "Gaea's Liege"

    def _attacking(self, state, perm):
        return perm.uid in state.attackers

    def dynamic_power(self, state, perm):
        return 0 if self._attacking(state, perm) else forest_count(state)

    def dynamic_toughness(self, state, perm):
        return 0 if self._attacking(state, perm) else forest_count(state)

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        seen: set[str] = set()
        for land in state.battlefield:
            if not land.is_land or land.mana_override == "G" or land.name in seen:
                continue
            seen.add(land.name)

            def make(uid, nm):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped:
                        return False
                    p.tapped = True
                    return True

                def resolve(st):
                    tgt = st.find_permanent(uid)
                    if tgt is not None:
                        tgt.mana_override = "G"
                        st.emit(f"Gaea's Liege: {nm} becomes a Forest")
                    return None

                return CardAction.activated(
                    f"Gaea's Liege: {{T}} — {nm} becomes a Forest",
                    pay, resolve, source_name="Gaea's Liege",
                    ability_text="target land becomes a Forest")

            acts.append(make(land.uid, land.name))
        return acts
