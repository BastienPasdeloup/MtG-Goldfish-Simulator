"""Bitter Triumph — {1}{B} Instant. As an additional cost, discard a card or pay
3 life. Destroy target creature or planeswalker.

Against a phantom opponent there are no enemy permanents, so the useful line is
destroying one of YOUR OWN creatures (rarely wanted on its own) while the
additional discard cost bins a card — i.e. a "sacrifice a creature and pitch a
card to the graveyard" play. Branches over the target creature × the additional
cost (discard which card / pay 3 life)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class BitterTriumph(Card):
    card_name = "Bitter Triumph"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        targets = [(p.uid, p.name) for p in state.battlefield
                   if p.is_creature_now or "planeswalker" in p.type_line.lower()]
        # dedup targets by name
        seen_t, uniq_t = set(), []
        for uid, name in targets:
            if name not in seen_t:
                seen_t.add(name)
                uniq_t.append((uid, name))
        if not uniq_t:
            return []

        acts = []

        def build(uid, tname, pay_life):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                victim = st.find_permanent(uid)
                if card is None or victim is None:
                    return None
                if pay_life:
                    if st.life <= 3 or not begin_cast(st, card, cost):
                        return None
                    st.life -= 3
                else:
                    if not begin_cast(st, card, cost):
                        return None
                resolve_to_graveyard(st, card)
                # discard additional cost handled below (for the discard variant)
                v = st.find_permanent(uid)
                if v is not None:
                    st.leaves_battlefield(v, "graveyard", reason="destroy")
                st.emit(f"Bitter Triumph: destroy {tname}")
                return None
            return fn

        def build_discard(uid, tname, dname):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                victim = st.find_permanent(uid)
                pitch = next((c for c in st.hand if c.name == dname), None)
                if card is None or victim is None or pitch is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                st.discard(pitch)
                v = st.find_permanent(uid)
                if v is not None:
                    st.leaves_battlefield(v, "graveyard", reason="destroy")
                st.emit(f"Bitter Triumph: destroy {tname} (discarded {dname})")
                return None
            return fn

        for uid, tname in uniq_t:
            if state.life > 3:
                acts.append(CardAction(
                    f"cast Bitter Triumph → {tname} (pay 3 life)", build(uid, tname, True)))
            seen_d = set()
            for c in state.hand:
                if c.name == self.card_name or c.name in seen_d:
                    continue
                seen_d.add(c.name)
                acts.append(CardAction(
                    f"cast Bitter Triumph → {tname} (discard {c.name})",
                    build_discard(uid, tname, c.name)))
        return acts
