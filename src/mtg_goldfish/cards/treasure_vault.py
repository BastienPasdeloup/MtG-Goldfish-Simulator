"""Treasure Vault — Artifact Land.
{T}: Add {C}.
{X}{X}, {T}, Sacrifice this land: Create X Treasure tokens.

The Treasure ability is mana-negative on its own ({X}{X} for X Treasures) but the
Treasures are artifacts — fodder for affinity / Emry / improvise / Sai. One branch
per X (bounded by available mana)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class TreasureVault(Card):
    card_name = "Treasure Vault"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import available_mana_sources, can_afford, pay_cost

        if perm.tapped:
            return []
        # {X}{X}: the most X we could pay for (excluding this land, which taps).
        avail = len(available_mana_sources(state, {perm.uid})) + state.mana_pool.total()
        acts = []
        for x in range(1, avail // 2 + 1):
            cost = ManaCost(generic=2 * x)
            if not can_afford(state, cost, exclude_uids={perm.uid}):
                break

            def build(xx, c=cost):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped:
                        return False
                    p.tapped = True
                    if not pay_cost(st, c, exclude_uids={p.uid}):
                        return False
                    st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    for _ in range(xx):
                        st.make_token("Treasure", 0, 0, "Token Artifact — Treasure")
                    st.emit(f"Treasure Vault: create {xx} Treasure token(s)")
                    return None

                return CardAction.activated(
                    f"Treasure Vault: {{{xx}}}{{{xx}}}, sacrifice — create {xx} Treasure(s)",
                    pay, resolve, source_name="Treasure Vault",
                    ability_text="Create X Treasure tokens")

            acts.append(build(x))
        return acts
