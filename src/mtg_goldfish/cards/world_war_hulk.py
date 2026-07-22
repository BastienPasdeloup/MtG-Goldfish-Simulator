"""World War Hulk — {3}{G}{G} Enchantment — Saga.
I  — The next red or green creature spell you cast this turn can be cast without
     paying its mana cost.
II — Put three +1/+1 counters on target creature you control.
III— Choose target creature you control. Until end of turn, double its power and
     toughness and it gains trample. (Then the Saga is sacrificed.)

Lore counters arrive as chapter triggers ON THE STACK — the first when the Saga
enters, the next after each of your draw steps — exactly like Urza's Saga.
Chapters II and III branch over the target creature."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class WorldWarHulk(Card):
    card_name = "World War Hulk"

    def etb_stack_items(self, state, permanent):
        def resolve(st, uid=permanent.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            live.counters["lore"] = live.counters.get("lore", 0) + 1
            return live.impl._chapter(st, live, live.counters["lore"])

        return [self.stack_ability(
            source_name=permanent.name,
            label="World War Hulk: lore counter → chapter I",
            resolve=resolve,
            trigger_text="World War Hulk entered the battlefield",
            ability_text="Chapter I — next red/green creature spell is free this turn",
        )]

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.DRAW or state.turn == 0:
            return []
        lore = perm.counters.get("lore", 0)
        if lore >= 3:
            return []
        roman = {1: "I", 2: "II", 3: "III"}[lore + 1]

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            live.counters["lore"] = live.counters.get("lore", 0) + 1
            return live.impl._chapter(st, live, live.counters["lore"])

        return [self.stack_ability(
            source_name=perm.name,
            label=f"World War Hulk: lore counter → chapter {roman}",
            resolve=resolve,
            trigger_text="A lore counter is put on World War Hulk",
            ability_text=f"Chapter {roman}",
        )]

    def _own_creature_uids(self, state):
        uids: list[int] = []
        seen: set[str] = set()
        for p in state.battlefield:
            if p.is_creature_now and p.name not in seen:
                seen.add(p.name)
                uids.append(p.uid)
        return uids

    def _chapter(self, state, perm, n: int):
        from ._common import branch_over

        if n == 1:
            state.free_casts.append({
                "colors": ("R", "G"), "creature": True,
                "label": "World War Hulk I — without paying its mana cost",
            })
            state.emit("World War Hulk I: your next red or green creature spell "
                       "this turn can be cast without paying its mana cost")
            return None

        if n == 2:
            uids = self._own_creature_uids(state)
            if not uids:
                state.emit("World War Hulk II: no creature to target")
                return None

            def do(b, uid):
                tp = b.find_permanent(uid)
                if tp is not None:
                    tp.counters["+1/+1"] = tp.counters.get("+1/+1", 0) + 3
                    b.emit(f"World War Hulk II: three +1/+1 counters on {tp.name}")
                return None

            return branch_over(state, uids, do)

        # Chapter III — double a creature's P/T + trample, then sacrifice the Saga.
        saga_uid = perm.uid
        uids = self._own_creature_uids(state)

        def do(b, uid):
            tp = b.find_permanent(uid)
            if tp is not None:
                p = b.effective_power(tp)
                t = b.effective_toughness(tp)
                tp.temp_power += p          # doubles the current effective P/T
                tp.temp_toughness += t
                tp.temp_keywords.add("trample")
                b.emit(f"World War Hulk III: double {tp.name} to "
                       f"{b.effective_power(tp)}/{b.effective_toughness(tp)}, trample")
            saga = b.find_permanent(saga_uid)
            if saga is not None:
                b.leaves_battlefield(saga, "graveyard", reason="sacrifice")
                b.emit("World War Hulk: sacrificed after chapter III")
            return None

        if not uids:
            saga = state.find_permanent(saga_uid)
            if saga is not None:
                state.leaves_battlefield(saga, "graveyard", reason="sacrifice")
                state.emit("World War Hulk III: no creature; sacrificed after chapter III")
            return None

        return branch_over(state, uids, do)
