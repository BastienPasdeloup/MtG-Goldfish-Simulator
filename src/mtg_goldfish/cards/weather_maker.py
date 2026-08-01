"""Weather Maker — {3} Artifact.
Landfall: put a charge counter on it. {T}: Add one mana of any color.
{T}, Remove three charge counters: it deals 3 damage to any target — modelled
as a repeatable reach/finisher once landfall has built up three charges. (The
minor {T}, remove two charge: add {C}{C} mode is left out — converting charges
to colourless is marginal when {T} already taps for any colour.)"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color, damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class WeatherMaker(Card):
    card_name = "Weather Maker"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state))]

    def battlefield_actions(self, state, perm):
        # {T}, Remove three charge counters: 3 damage to any target.
        if perm.tapped or perm.counters.get("charge", 0) < 3:
            return []
        acts: list[CardAction] = []
        for suffix, apply in damage_any_target_options(state):

            def make(apply=apply):
                def pay(st):
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped or live.counters.get("charge", 0) < 3:
                        return False
                    live.tapped = True
                    live.counters["charge"] -= 3
                    return True

                def resolve(st):
                    apply(st, 3)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Weather Maker: remove 3 charge → 3 damage to {suffix}",
                pay, resolve,
                source_name="Weather Maker",
                ability_text="Deal 3 damage to any target"))
        return acts

    def other_etb_stack_items(self, state, perm, entering):
        if not entering.is_land:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Weather Maker: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Landfall — put a charge counter on Weather Maker",
        )]

    def on_other_etb(self, state, perm, entering):
        if entering.is_land:
            perm.counters["charge"] = perm.counters.get("charge", 0) + 1
