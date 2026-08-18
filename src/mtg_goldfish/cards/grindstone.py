"""Grindstone — {1} Artifact.
{3}, {T}: Target player mills two cards. If two cards that share a color were
milled this way, repeat this process.

With no opponent, "target player" is you — a self-mill that fills your graveyard
(feeding Emry). The share-a-colour loop is resolved exactly: keep milling pairs
while each milled pair shares a colour and the library holds another pair."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import artifact_ability_cost, painter_colors
from .base import Card, CardAction
from .registry import register


@register
class Grindstone(Card):
    card_name = "Grindstone"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = artifact_ability_cost(state, ManaCost(generic=3), perm)
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st):
            milled = 0
            while len(st.library) >= 2:
                a = st.library.pop(0)
                b = st.library.pop(0)
                st.to_graveyard(a)
                st.to_graveyard(b)
                milled += 2
                # Painter's Servant makes every card its chosen colour too, so
                # any two cards then "share a colour" (mills the whole library).
                pc = painter_colors(st)
                shared = bool((set(a.colors or []) | pc) & (set(b.colors or []) | pc))
                st.emit(f"Grindstone: mill {a.name} + {b.name}"
                        + (" — share a colour, repeat" if shared else ""))
                if not shared:
                    break
            else:
                # Fewer than two cards remain: mill the last one (no pair to share).
                if st.library:
                    last = st.library.pop(0)
                    st.to_graveyard(last)
                    milled += 1
                    st.emit(f"Grindstone: mill {last.name}")
            st.emit(f"Grindstone: milled {milled} card(s)")
            return None

        return [CardAction.activated(
            "Grindstone: {3}, {T} — mill two (repeat on shared colour)",
            pay, resolve, source_name="Grindstone",
            ability_text="Target player mills two cards; repeat on a shared colour")]
