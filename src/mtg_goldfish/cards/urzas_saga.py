"""Urza's Saga — Enchantment Land — Urza's Saga.
Enters with lore counter I (a replacement effect — the counter is on it from
the moment it enters); adds one after each of your draw steps.
I: gains "{T}: Add {C}" (modelled as always-on from chapter I).
II: gains "{2}, {T}: create a 0/0 Construct with +1/+1 per artifact".
III (at the chapter-3 lore bump): search your library for an artifact card
with mana cost {0} or {1}, put it onto the battlefield (branch), then
sacrifice the Saga."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class UrzasSaga(Card):
    card_name = "Urza's Saga"

    def enters_with_counters(self, state):
        # "Enters with a lore counter" — a replacement effect: the counter is
        # on the Saga from the moment it enters; nothing goes on the stack.
        return {"lore": 1}

    def mana_abilities_perm(self, state, perm):
        if perm.counters.get("lore", 0) >= 1:
            return [ManaAbility(amount=1, choices=("C",))]
        return []

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.DRAW or state.turn == 0 or perm.counters.get("lore", 0) + 1 < 3:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.DRAW)

        return [self.stack_ability(
            source_name=perm.name,
            label="Urza's Saga: chapter III",
            resolve=resolve,
            trigger_text="Draw step lore counter reached chapter III",
            ability_text="Search your library for a {0} or {1} artifact, put it onto the battlefield, then sacrifice Urza's Saga",
        )]

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=2)
        # Taps for this ability, so it can't help pay its own {2} cost.
        if (perm.counters.get("lore", 0) < 2 or perm.tapped
                or not can_afford(state, cost, exclude_uids={perm.uid})):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.make_token("Construct", 0, 0, "Token Artifact Creature — Construct")
            st.emit("Urza's Saga: create a Construct token")
            return None

        return [CardAction.activated(
            "Urza's Saga: {2}, {T} — Construct token",
            pay,
            resolve,
            source_name="Urza's Saga",
            ability_text="Create a Construct token",
        )]

    def on_phase(self, state, perm, phase):
        if phase != Phase.DRAW or state.turn == 0:
            return
        perm.counters["lore"] = perm.counters.get("lore", 0) + 1
        if perm.counters["lore"] < 3:
            return
        # Chapter III: fetch a {0}/{1} artifact, then the Saga is sacrificed.
        state.emit("Urza's Saga: chapter III")
        targets = state.search_library(
            lambda c: "artifact" in c.type_line.lower() and not c.is_land and c.cmc <= 1
        )
        state.leaves_battlefield(perm, "graveyard")
        if not targets:
            return
        # Deterministic pick inside a phase trigger (no branch point here):
        # prefer the most expensive match ({1} over {0}).
        target = sorted(targets, key=lambda c: (-c.cmc, c.name))[0]
        card = next(c for c in state.library if c.name == target.name)
        state.take_from_library(card)
        state.shuffle_library()
        state.put_on_battlefield(card)
        state.emit(f"Urza's Saga III: {card.name} onto the battlefield — shuffle")
