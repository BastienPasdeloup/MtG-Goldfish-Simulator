"""Lazotep Quarry — Land — Desert.
{T}: Add {C}.
{X}{2}, {T}, Sacrifice a Desert: Exile target creature card with mana value X
from your graveyard. Create a token that's a copy of it, except it's a 4/4 black
Zombie. Activate only as a sorcery.

Modelled as a graveyard-to-battlefield engine: it sacrifices itself (the Desert)
to make a fresh 4/4 black Zombie body from a graveyard creature. The token is a
COPY, but copying the creature's abilities has no generic engine support, so it
enters as a vanilla 4/4 Zombie (its body + attacks are the useful part). The
sacrifice-a-creature-for-any-colour mana ability is still left out (spending a
real creature for one mana is almost never right)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class LazotepQuarry(Card):
    card_name = "Lazotep Quarry"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped:
            return []
        # One branch per distinct graveyard creature; X = its mana value.
        seen: set[str] = set()
        acts: list[CardAction] = []
        for card in state.graveyard:
            if not card.is_creature or card.name in seen:
                continue
            seen.add(card.name)
            x = int(card.cmc)
            cost = ManaCost(generic=x + 2)
            # Lazotep taps for the ability ({T}) and is the sacrificed Desert, so
            # it can never help pay its own mana cost.
            if not can_afford(state, cost, exclude_uids={perm.uid}):
                continue

            def make(name=card.name, cost=cost):
                def pay(st):
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped:
                        return False
                    if not pay_cost(st, cost, exclude_uids={live.uid}):
                        return False
                    st.emit(f"Lazotep Quarry: sacrifice itself → reanimate {name}")
                    st.leaves_battlefield(live, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    target = next((c for c in st.graveyard if c.name == name), None)
                    if target is None:
                        return None
                    st.graveyard.remove(target)
                    st.exile.append(target)
                    st.make_token(name, 4, 4, "Creature — Zombie", colors=["B"])
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Lazotep Quarry: reanimate {card.name} as a 4/4 Zombie",
                pay, resolve,
                source_name="Lazotep Quarry",
                ability_text="Create a 4/4 black Zombie copy of a graveyard creature"))
        return acts
