"""Illusionary Mask — {2} Artifact.
{X}: You may choose a creature card in your hand whose mana cost could be paid by
{X}, and cast it face down as a 2/2 creature spell without paying its mana cost.
It's turned face up when it would assign/deal/be dealt damage or become tapped.

Modelled pragmatically: {X} (= the chosen creature's mana value, paid in generic)
deploys a creature from your hand onto the battlefield FACE DOWN as a 2/2 (its ETB
is not fired while face down). The "turn face up on interaction" clause is not
modelled — it stays a 2/2 — so this is a simplification of the real card. One
branch per distinct hand creature."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class IllusionaryMask(Card):
    card_name = "Illusionary Mask"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost
        from ..engine.simulator import _make_face_down

        acts = []
        seen: set[str] = set()
        for card in list(state.hand):
            if not card.is_creature or card.name in seen:
                continue
            seen.add(card.name)
            mv = int(card.cmc or 0)
            cost = ManaCost(generic=max(1, mv))
            if not can_afford(state, cost):
                continue

            def make(target=card, c=cost, mv=mv):
                def pay(st):
                    return target in st.hand and pay_cost(st, c)

                def resolve(st):
                    if target not in st.hand:
                        return None
                    st.hand.remove(target)
                    p = st.put_on_battlefield(target, fire_etb=False)
                    _make_face_down(p, "facedown")
                    st.emit(f"Illusionary Mask: deploy a face-down 2/2 (a hidden {target.name})")
                    return None

                return CardAction.activated(
                    f"Illusionary Mask: {{{max(1, mv)}}} — cast {card.name} face down (2/2)",
                    pay, resolve, source_name="Illusionary Mask",
                    ability_text="Cast a creature face down as a 2/2")

            acts.append(make())
        return acts
