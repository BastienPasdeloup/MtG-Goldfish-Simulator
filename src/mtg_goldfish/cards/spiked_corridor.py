"""Spiked Corridor // Torture Pit — split Room enchantment ({3}{R} per door).
Spiked Corridor: when you unlock this door, create three 1/1 red Devil tokens
with "When this token dies, it deals 1 damage to any target."
Torture Pit: while unlocked, a source you control dealing noncombat damage to an
opponent deals +2 (via `noncombat_damage_bonus` — all noncombat damage routes
through GameState.damage_opponent). Either half can be cast; the other door can
then be unlocked from the battlefield by paying its cost as a sorcery."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register

_ROOM_COST = ManaCost(generic=3, pips=(("R", 1),))


@register
class Devil(Card):
    """Devil token — 1/1; when it dies, it deals 1 damage to any target
    (the opponent, in a goldfish)."""

    card_name = "Devil"

    def on_leave(self, state, permanent):
        state.damage_opponent(1)  # noncombat — Torture Pit amplifies
        state.emit(f"Devil dies: 1 damage to opponent ({state.opponent_life})")


def _make_devils(state):
    for _ in range(3):
        state.make_token(
            "Devil", 1, 1, "Creature — Devil",
            text="When this token dies, it deals 1 damage to any target.")
    state.emit("Spiked Corridor: create three 1/1 Devils")


@register
class SpikedCorridor(Card):
    card_name = "Spiked Corridor // Torture Pit"

    def noncombat_damage_bonus(self, state, perm):
        # Torture Pit door unlocked: your noncombat damage to an opponent is +2.
        return 2 if perm.counters.get("torture") else 0

    def cast_cost(self, state):
        return _ROOM_COST

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        if not can_afford(state, _ROOM_COST):
            return []

        def cast_half(door):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, _ROOM_COST):
                    return None
                if card in st.stack:
                    st.stack.remove(card)
                st.note_event("spell_resolved", card.name)
                st.resolving = ("spell", card.name)
                perm = st.put_on_battlefield(card, fire_etb=False)
                perm.counters[door] = 1
                st.emit(f"{card.name}: enters, unlock {door}")
                if door == "spiked":
                    _make_devils(st)
                else:
                    st.emit("Torture Pit: unlocked (noncombat damage to opponents +2)")
                return None
            return fn

        return [
            CardAction("cast Spiked Corridor (3 Devils)", cast_half("spiked")),
            CardAction("cast Torture Pit", cast_half("torture")),
        ]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if not can_afford(state, _ROOM_COST):
            return []
        acts = []
        for door in ("spiked", "torture"):
            if perm.counters.get(door):
                continue

            def make(door=door):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.counters.get(door) or not pay_cost(st, _ROOM_COST):
                        return False
                    return True

                def resolve(st):
                    p = st.find_permanent(perm.uid)
                    if p is None:
                        return None
                    p.counters[door] = 1
                    if door == "spiked":
                        _make_devils(st)
                    else:
                        st.emit("Torture Pit: unlocked (noncombat damage to opponents +2)")
                    return None
                return pay, resolve

            label = ("unlock Spiked Corridor (3 Devils)" if door == "spiked"
                     else "unlock Torture Pit")
            pay, resolve = make()
            acts.append(CardAction.activated(
                label, pay, resolve, sorcery_speed=True,
                source_name=self.card_name, ability_text=f"Unlock {door} door"))
        return acts
