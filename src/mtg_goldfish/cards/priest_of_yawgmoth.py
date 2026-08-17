"""Priest of Yawgmoth — {1}{B} Creature — Phyrexian Human Cleric 1/2.
{T}, Sacrifice an artifact: Add an amount of {B} equal to the sacrificed
artifact's mana value.

One branch per distinct artifact you control (the mana value differs per
artifact, so the choice matters); taps."""
from __future__ import annotations

from ._common import mv
from .base import Card, CardAction
from .registry import register


@register
class PriestOfYawgmoth(Card):
    card_name = "Priest of Yawgmoth"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        arts = {}
        for p in state.battlefield:
            if p.is_artifact:
                arts.setdefault(p.name, p)
        acts = []
        for name, art in arts.items():
            def make(auid=art.uid, amt=mv(art.card), aname=name):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    victim = st.find_permanent(auid)
                    if src is None or victim is None or src.tapped:
                        return False
                    src.tapped = True
                    st.emit(f"Priest of Yawgmoth: sacrifice {victim.name}")
                    st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    if amt > 0:
                        st.mana_pool.add("B", amt)
                        st.emit(f"Priest of Yawgmoth: add {amt} {{B}}")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Priest of Yawgmoth: {{T}}, sac {name} — add {mv(art.card)} {{B}}",
                pay, resolve, source_name="Priest of Yawgmoth",
                ability_text="Add {B} equal to the sacrificed artifact's mana value"))
        return acts
