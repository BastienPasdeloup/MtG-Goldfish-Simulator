"""Fork — {R}{R} Instant.
Copy target instant or sorcery spell, except that the copy is red. You may choose
new targets for the copy.

Fork must target a spell ON THE STACK. This engine resolves spells atomically, so
the goldfish models Fork the way it models a counterspell that hits your own spell
(see `_common.counterspell`): cast a hand instant/sorcery AND Fork together, paying
both costs — the target resolves, and Fork's copy resolves its effect once more.

Only spells whose effect is defined by `on_resolve` can be copied (the copy re-runs
it). Spells that bake their effect into `cast_actions` with a chosen mode / X (the
X-burn like Fireball, targeted removal) are NOT offered: a copy would have to
replay that exact choice, which isn't represented on the stack — a genuine
limitation of an atomic-resolution goldfish. Fork copying Ancestral Recall (→ draw
6), Braingeyser-style draws that use on_resolve, Timetwister, Wheel of Fortune,
Dark Ritual, etc. all work."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


def _merge(a: ManaCost, b: ManaCost) -> ManaCost:
    pips = dict(a.pip_map)
    for c, n in b.pip_map.items():
        pips[c] = pips.get(c, 0) + n
    return ManaCost(generic=a.generic + b.generic, pips=tuple(pips.items()))


@register
class Fork(Card):
    card_name = "Fork"

    def cast_actions(self, state):
        from ..cards import build_card
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        my_cost = self.cast_cost(state)
        if not can_afford(state, my_cost):
            return []
        acts = []
        seen: set[str] = set()
        for tgt in list(state.hand):
            if tgt.name == self.card_name or tgt.name in seen:
                continue
            if not (tgt.is_instant or tgt.is_sorcery):
                continue
            impl = build_card(tgt)
            # Only copyable if the effect lives in on_resolve (re-runnable).
            if type(impl).on_resolve is Card.on_resolve:
                continue
            tgt_cost = ManaCost.parse(tgt.mana_cost)
            if not can_afford(state, _merge(my_cost, tgt_cost)):
                continue
            seen.add(tgt.name)

            def make(target_name: str, tcost: ManaCost):
                def fn(st):
                    fork = next((c for c in st.hand if c.name == self.card_name), None)
                    victim = next((c for c in st.hand if c.name == target_name), None)
                    if fork is None or victim is None:
                        return None
                    if not begin_cast(st, victim, tcost):          # target on the stack
                        return None
                    if not begin_cast(st, fork, my_cost):          # Fork on top
                        return None
                    resolve_to_graveyard(st, fork)                 # Fork resolves
                    vimpl = build_card(victim)
                    st.emit(f"Fork: copy {target_name}")
                    vimpl.on_resolve(st)                           # the COPY resolves first
                    if victim in st.stack:
                        st.stack.remove(victim)
                    resolve_to_graveyard(st, victim)               # the ORIGINAL resolves
                    return st.settle(vimpl.on_resolve(st) or None)
                return fn

            acts.append(CardAction(
                f"cast Fork copying own {tgt.name}", make(tgt.name, tgt_cost)))
        return acts
