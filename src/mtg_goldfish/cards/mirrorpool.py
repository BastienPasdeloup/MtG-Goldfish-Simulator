"""Mirrorpool — Land.
Enters tapped. {T}: Add {C}.
{4}{C}, {T}, Sacrifice this land: Create a token that's a copy of target creature
you control (modelled via GameState.make_token_copy — a full token copy with the
original's P/T, types and abilities; branches over each distinct creature).
The copy-spell mode ({2}{C}, {T}, Sacrifice: copy target instant/sorcery you
control) is not modelled — spells resolve atomically here, so there is never a
spell of yours on the stack to copy (same reasoning as counterspells)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register

_COPY_CREATURE_COST = ManaCost(generic=4, pips=(("C", 1),))


@register
class Mirrorpool(Card):
    card_name = "Mirrorpool"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped:
            return []
        # Mirrorpool taps for the ability ({T}) and is the sacrificed land, so it
        # can never help pay its own {4}{C}.
        if not can_afford(state, _COPY_CREATURE_COST, exclude_uids={perm.uid}):
            return []
        seen: set[str] = set()
        acts: list[CardAction] = []
        for target in state.battlefield:
            if not target.is_creature_now or target.name in seen:
                continue
            seen.add(target.name)

            def make(name=target.name):
                def pay(st):
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped:
                        return False
                    if not pay_cost(st, _COPY_CREATURE_COST, exclude_uids={live.uid}):
                        return False
                    st.emit(f"Mirrorpool: sacrifice itself → copy {name}")
                    st.leaves_battlefield(live, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    src = next((c for c in st.battlefield if c.name == name), None)
                    if src is None:
                        return None
                    st.make_token_copy(src)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Mirrorpool: copy {target.name}", pay, resolve,
                source_name="Mirrorpool",
                ability_text="Create a token that's a copy of target creature you control"))
        return acts
