"""Urza's Saga — Enchantment Land — Urza's Saga.
Lore counters arrive via chapter triggers ON THE STACK: the first when the
Saga enters, the next at the beginning of each of your draw steps.
I: gains "{T}: Add {C}" (modelled as always-on from chapter I).
II: gains "{2}, {T}: create a 0/0 Construct with +1/+1 per artifact".
III (at the chapter-3 lore bump): search your library for an artifact card
with mana cost {0} or {1}, put it onto the battlefield (branch), then
sacrifice the Saga."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class UrzasSaga(Card):
    card_name = "Urza's Saga"

    def etb_stack_items(self, state, permanent):
        # The first lore counter arrives via a chapter trigger when the Saga
        # enters: it goes on the stack like every later counter.
        def resolve(st, uid=permanent.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            live.counters["lore"] = live.counters.get("lore", 0) + 1
            st.emit(f"Urza's Saga: lore counter added (now at {live.counters['lore']})")
            return None

        return [self.stack_ability(
            source_name=permanent.name,
            label="Urza's Saga: lore counter → chapter I",
            resolve=resolve,
            trigger_text="Urza's Saga entered the battlefield",
            ability_text="Chapter I — {T}: Add {C}",
        )]

    def mana_abilities_perm(self, state, perm):
        if perm.counters.get("lore", 0) >= 1:
            return [ManaAbility(amount=1, choices=("C",))]
        return []

    def phase_stack_items(self, state, perm, phase):
        # After each of your draw steps, a lore counter is put on the Saga. That
        # addition is a triggered (chapter) ability — it goes on the stack, then
        # resolves the reached chapter (I is the entering counter; II grants the
        # Construct ability; III fetches an artifact and sacrifices the Saga).
        if phase != Phase.DRAW or state.turn == 0:
            return []
        lore = perm.counters.get("lore", 0)
        if lore >= 3:
            return []  # completed (the Saga has already left)
        roman = {1: "I", 2: "II", 3: "III"}[lore + 1]

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.DRAW)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"Urza's Saga: lore counter → chapter {roman}",
            resolve=resolve,
            trigger_text="A lore counter is put on Urza's Saga",
            ability_text=(
                "Chapter III — search your library for a {0} or {1} artifact, "
                "put it onto the battlefield, then sacrifice Urza's Saga"
                if lore + 1 == 3 else f"Chapter {roman}"
            ),
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
        lore = perm.counters["lore"]
        if lore < 3:
            # Chapters I & II are modelled as always-on statics gated on the
            # lore count (mana ability at ≥1, the Construct ability at ≥2), so
            # the counter addition itself is the whole effect here.
            state.emit(f"Urza's Saga: lore counter added (now at {lore})")
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
