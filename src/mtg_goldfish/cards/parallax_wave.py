"""Parallax Wave — {2}{W}{W} Enchantment. Fading 5 (enters with five fade
counters; at your upkeep remove one or sacrifice it). Remove a fade counter:
exile target creature (your own, in solitaire). When it leaves, exiled cards
return to the battlefield (their ETB triggers refire; branching ETBs among
them are applied on their default line — approximation)."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class ParallaxWave(Card):
    card_name = "Parallax Wave"

    def on_etb(self, state, permanent):
        permanent.counters["fade"] = 5
        return None

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.UPKEEP)

        return [self.stack_ability(
            source_name=perm.name,
            label="Parallax Wave: fading",
            resolve=resolve,
            trigger_text="Beginning of your upkeep",
            ability_text="Remove a fade counter; if none remain, sacrifice Parallax Wave",
        )]

    def on_phase(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return
        if perm.counters.get("fade", 0) > 0:
            perm.counters["fade"] -= 1
            state.emit(f"Parallax Wave: fading — remove a fade counter ({perm.counters['fade']} left)")
        else:
            state.emit("Parallax Wave: no fade counters — sacrifice")
            state.leaves_battlefield(perm, "graveyard")

    def battlefield_actions(self, state, perm):
        if perm.counters.get("fade", 0) <= 0:
            return []
        creatures = [p for p in state.battlefield if p.is_creature_now]

        def make(uid: int):
            def fn(st):
                wave = st.find_permanent(perm.uid)
                target = st.find_permanent(uid)
                if wave is None or target is None or wave.counters.get("fade", 0) <= 0:
                    return None
                wave.counters["fade"] -= 1
                st.emit(f"Parallax Wave: exile {target.name} (fade {wave.counters['fade']} left)")
                if not target.is_token:
                    st.battlefield.remove(target)
                    st.permanent_left_battlefield_this_turn = True
                    wave.exiled_with.append(target.card)
                else:
                    st.leaves_battlefield(target, "exile")
                return None
            return fn

        return [CardAction(f"Parallax Wave: exile {c.name}", make(c.uid)) for c in creatures]

    def on_leave(self, state, permanent):
        for card in permanent.exiled_with:
            state.put_on_battlefield(card)
            state.emit(f"Parallax Wave leaves: {card.name} returns to the battlefield")
        permanent.exiled_with.clear()
