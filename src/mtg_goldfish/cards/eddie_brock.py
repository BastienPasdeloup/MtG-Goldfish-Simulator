"""Eddie Brock // Venom, Lethal Protector — {2}{B} Legendary Creature 3/3.
ETB: return target creature card with mana value ≤1 from your graveyard to the
battlefield (branch; fizzles with no target). {3}{B}{R}{G}: transform (sorcery).
Venom (back face, 5/5 menace/trample/haste): whenever it attacks you may
sacrifice another creature; if you do, draw X and may put a permanent card with
mana value ≤ X from hand onto the battlefield, where X is the sacrificed
creature's mana value (branch over which creature to sacrifice, then over which
permanent to cheat in)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over, enter_battlefield, transform_actions
from .base import Card
from .registry import register


@register
class EddieBrock(Card):
    card_name = "Eddie Brock // Venom, Lethal Protector"

    def on_etb(self, state, permanent):
        targets = sorted({c.name for c in state.graveyard if c.is_creature and c.cmc <= 1})
        if not targets:
            return None

        def apply(st, name: str):
            card = next(c for c in st.graveyard if c.name == name)
            st.graveyard.remove(card)
            enter_battlefield(
                st,
                card,
                announce=f"Eddie Brock: return {name} to the battlefield",
            )
            return None

        return branch_over(state, targets, apply)

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=3, pips=(("B", 1), ("R", 1), ("G", 1))),
            "Venom, Lethal Protector",
        )

    def on_attack(self, state, perm):
        # Only Venom (the back face) has the attack trigger.
        if not perm.transformed:
            return None
        fodder: dict[str, tuple[int, int]] = {}
        for p in state.battlefield:
            if p.uid == perm.uid or not p.is_creature_now:
                continue
            fodder.setdefault(p.name, (p.uid, int(p.card.cmc)))
        options = ["no sacrifice"] + list(fodder)

        def fn(st, opt):
            if opt == "no sacrifice":
                return None
            uid, x = fodder[opt]
            victim = st.find_permanent(uid)
            if victim is None:
                return None
            st.emit(f"Venom attacks: sacrifice {opt} → draw {x}")
            st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
            if x > 0:
                st.draw(x)
            # ...then you MAY put a permanent card with mana value ≤ X into play.
            puttable = sorted({c.name for c in st.hand if c.is_permanent and c.cmc <= x})

            def put_fn(b, choice):
                if choice == "put nothing":
                    return None
                card = next((c for c in b.hand if c.name == choice), None)
                if card is None:
                    return None
                b.hand.remove(card)
                enter_battlefield(b, card,
                                  announce=f"Venom: put {choice} onto the battlefield")
                return None

            return branch_over(st, ["put nothing"] + puttable, put_fn)

        return branch_over(state, options, fn)
