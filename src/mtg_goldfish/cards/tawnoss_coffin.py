"""Tawnos's Coffin — {4} Artifact.
You may choose not to untap this artifact during your untap step.
{3}, {T}: Exile target creature and all Auras attached to it. When this artifact
leaves the battlefield or becomes untapped, return that exiled card to the
battlefield under its owner's control tapped, then return the exiled Auras attached
to it.

Blinks one of your creatures (and its Auras): exile on activation, then return it
tapped when the Coffin next untaps (your upkeep) — re-firing the creature's ETB.
The Coffin taps to activate, so it comes back untapped next turn and the creature
returns then. Noted counters are not preserved (the exile store carries only card
identities). One branch per distinct creature you control."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class TawnossCoffin(Card):
    card_name = "Tawnos's Coffin"
    exiles_cards = True
    trigger_phase = Phase.UPKEEP

    def _return_exiled(self, state, perm):
        # First card in exiled_with is the creature, the rest are its Auras.
        cards = list(perm.exiled_with)
        perm.exiled_with.clear()
        if not cards:
            return
        creature, auras = cards[0], cards[1:]
        for c in (creature, *auras):
            if c in state.exile:
                state.exile.remove(c)
        host = state.put_on_battlefield(creature, tapped=True)
        state.emit(f"Tawnos's Coffin: {creature.name} returns tapped")
        for a in auras:
            aura = state.put_on_battlefield(a, fire_etb=False)
            aura.attached_to = host.uid
            state.emit(f"Tawnos's Coffin: {a.name} returns attached to {host.name}")

    def on_phase(self, state, perm, phase):
        # It becomes untapped in the untap step just before upkeep → return now.
        p = state.find_permanent(perm.uid)
        if p is not None and not p.tapped and p.exiled_with:
            self._return_exiled(state, p)
        return None

    def on_leave(self, state, permanent):
        self._return_exiled(state, permanent)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if perm.tapped or perm.exiled_with or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_creature_now and not p.is_token and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            tname = state.find_permanent(tuid).name

            def make(tuid=tuid):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    tgt = st.find_permanent(tuid)
                    if src is None or tgt is None or src.tapped or not pay_cost(st, cost, exclude_uids={src.uid}):
                        return False
                    src.tapped = True
                    return True

                def resolve(st):
                    src = st.find_permanent(perm.uid)
                    tgt = st.find_permanent(tuid)
                    if src is None or tgt is None:
                        return None
                    auras = [a for a in list(st.battlefield)
                             if a.attached_to == tgt.uid and "aura" in a.type_line.lower()]
                    st.emit(f"Tawnos's Coffin: exile {tgt.name}"
                            + (f" + {len(auras)} Aura(s)" if auras else ""))
                    st.battlefield.remove(tgt)
                    st.permanent_left_battlefield_this_turn = True
                    src.exiled_with.append(tgt.card)
                    for a in auras:
                        st.battlefield.remove(a)
                        src.exiled_with.append(a.card)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Tawnos's Coffin: {{3}}, {{T}} → exile {tname} (returns next untap)",
                pay, resolve, source_name="Tawnos's Coffin",
                ability_text="Exile target creature and its Auras; return it when this untaps/leaves"))
        return acts
