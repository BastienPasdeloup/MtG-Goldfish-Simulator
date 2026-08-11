"""World Map — {1} Artifact.
{1}, {T}, Sacrifice this artifact: Search your library for a basic land card,
reveal it, put it into your hand, then shuffle.
{3}, {T}, Sacrifice this artifact: Search your library for a land card, reveal
it, put it into your hand, then shuffle.

Two tutor-to-hand modes (basic for {1}, any land for {3}); one branch per
distinct matching land."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class WorldMap(Card):
    card_name = "World Map"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped:
            return []
        acts: list[CardAction] = []

        def mode(cost, pred, label):
            if not can_afford(state, cost):
                return
            seen: set[str] = set()
            for target in state.search_library(pred):
                if target.name in seen:
                    continue
                seen.add(target.name)

                def build(name, c=cost):
                    def pay(st):
                        p = st.find_permanent(perm.uid)
                        if p is None or p.tapped or not pay_cost(st, c):
                            return False
                        p.tapped = True
                        st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                        return True

                    def resolve(st):
                        card = next((k for k in st.library if k.name == name), None)
                        if card is None:
                            return None
                        st.take_from_library(card)
                        st.hand.append(card)
                        st.shuffle_library()
                        st.emit(f"World Map: search up {name} to hand — shuffle")
                        return None

                    return CardAction.activated(
                        f"World Map: {label} → {name}", pay, resolve,
                        source_name="World Map", ability_text="Search for a land, put it into your hand")

                acts.append(build(target.name))

        mode(ManaCost(generic=1),
             lambda c: c.is_land and "basic" in c.type_line.lower(),
             "{1}, {T}, sacrifice — basic land")
        mode(ManaCost(generic=3), lambda c: c.is_land,
             "{3}, {T}, sacrifice — any land")
        return acts
