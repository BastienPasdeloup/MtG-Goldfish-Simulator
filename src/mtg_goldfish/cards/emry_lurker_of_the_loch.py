"""Emry, Lurker of the Loch — {2}{U} Legendary Creature — Merfolk Wizard 1/2.
Affinity for artifacts (this spell costs {1} less to cast for each artifact you
control).
When Emry enters, mill four cards.
{T}: Choose target artifact card in your graveyard. You may cast that card this
turn. (You still pay its costs.)

The tap ability marks the chosen artifact card as castable from the graveyard
this turn (state.gy_castable); casting it is then a normal graveyard cast that
pays its cost. One branch per distinct artifact card in the graveyard."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class EmryLurkerOfTheLoch(Card):
    card_name = "Emry, Lurker of the Loch"

    def cast_cost(self, state):
        base = self.mana_cost  # {2}{U}
        artifacts = sum(1 for p in state.battlefield if p.is_artifact)
        return ManaCost(generic=max(0, base.generic - artifacts), pips=base.pips)

    def on_etb(self, state, permanent):
        state.emit("Emry, Lurker of the Loch: mill four cards")
        state.mill(4)

    def battlefield_actions(self, state, perm):
        # {T} ability: needs an untapped, non-summoning-sick Emry.
        if perm.tapped or (perm.summoning_sick and not state.has_keyword(perm, "Haste")):
            return []

        seen: set[str] = set()
        acts: list[CardAction] = []
        for card in state.graveyard:
            if not card.is_artifact or card.name in seen:
                continue
            seen.add(card.name)

            def build(target_name):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped:
                        return False
                    p.tapped = True
                    return True

                def resolve(st):
                    if target_name not in st.gy_castable:
                        st.gy_castable.append(target_name)
                    st.emit(f"Emry: you may cast {target_name} from your graveyard this turn")
                    return None

                return CardAction.activated(
                    f"Emry: {{T}} — you may cast {target_name} from graveyard",
                    pay, resolve, source_name="Emry, Lurker of the Loch",
                    ability_text="Choose target artifact card in your graveyard; "
                                 "you may cast it this turn")

            acts.append(build(card.name))
        return acts
