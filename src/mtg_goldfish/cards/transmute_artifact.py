"""Transmute Artifact — {U}{U} Sorcery.
Sacrifice an artifact. If you do, search your library for an artifact card. If
that card's mana value is <= the sacrificed artifact's, put it onto the
battlefield. If greater, you may pay {X} (the difference) to put it onto the
battlefield; otherwise it goes to the graveyard. Then shuffle.

Every (artifact to sacrifice) × (artifact to fetch) choice is enumerated — the
sacrifice is a real decision the search makes, not an auto-optimised one. When the
fetched card costs more than the sacrificed one, BOTH outcomes are offered: pay
the difference to put it onto the battlefield, OR let it go to the graveyard
(worthwhile in this deck — Emry can recast an artifact from the graveyard on a
later turn). The fetched artifact enters untapped; the difference is paid during
resolution."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield, mv
from .base import Card, CardAction
from .registry import register


@register
class TransmuteArtifact(Card):
    card_name = "Transmute Artifact"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        my_cost = ManaCost(pips=(("U", 1), ("U", 1)))  # {U}{U}
        if not can_afford(state, my_cost):
            return []
        # Distinct artifacts you could sacrifice (same name = same mana value).
        sac_choices: dict[str, int] = {}
        for p in state.battlefield:
            if p.is_artifact:
                sac_choices.setdefault(p.name, mv(p.card))
        if not sac_choices:
            return []

        def make(sname, tname, ex, to_gy):
            def fn(st):
                card = next((k for k in st.hand if k.name == self.card_name), None)
                sac = next((p for p in st.battlefield
                            if p.is_artifact and p.name == sname), None)
                if card is None or sac is None or not begin_cast(st, card, my_cost):
                    return None
                resolve_to_graveyard(st, card)
                st.emit(f"Transmute Artifact: sacrifice {sname}")
                st.leaves_battlefield(sac, "graveyard", reason="sacrifice")
                found = next((k for k in st.library if k.name == tname), None)
                if found is None:
                    return None
                st.take_from_library(found)
                st.shuffle_library()
                # Graveyard line (decline to pay the difference), or battlefield —
                # paying the difference when the fetched card costs more.
                if to_gy or (ex > 0 and not _pay_generic(st, ex)):
                    st.to_graveyard(found)
                    st.emit(f"Transmute Artifact: {tname} to the graveyard")
                    return None
                enter_battlefield(
                    st, found, tapped=False,
                    announce=f"Transmute Artifact: {tname} onto the battlefield — shuffle")
                return None
            return fn

        targets = state.search_library(lambda c: c.is_artifact)
        acts = []
        for sac_name, sac_mv in sac_choices.items():
            seen: set[str] = set()
            for target in targets:
                if target.name in seen:
                    continue
                seen.add(target.name)
                extra = max(0, int(target.cmc) - sac_mv)
                if extra == 0:
                    # MV <= sacrificed MV: it always enters the battlefield.
                    acts.append(CardAction(
                        f"cast Transmute Artifact (sac {sac_name}) → {target.name}",
                        make(sac_name, target.name, 0, False)))
                    continue
                # MV greater: you MAY pay the difference to put it onto the
                # battlefield, OR let it go to the graveyard.
                total = ManaCost(generic=my_cost.generic + extra, pips=my_cost.pips)
                if can_afford(state, total):
                    acts.append(CardAction(
                        f"cast Transmute Artifact (sac {sac_name}) → {target.name} [pay {{{extra}}}]",
                        make(sac_name, target.name, extra, False)))
                acts.append(CardAction(
                    f"cast Transmute Artifact (sac {sac_name}) → {target.name} [to graveyard]",
                    make(sac_name, target.name, extra, True)))
        return acts


def _pay_generic(state, amount: int) -> bool:
    from ..engine.actions import pay_cost
    return pay_cost(state, ManaCost(generic=amount))
