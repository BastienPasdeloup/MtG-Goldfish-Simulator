"""Solitude — {3}{W}{W} 3/2 flash, lifelink. ETB: exile up to one other target
creature; its controller gains life equal to its power (your creatures — or
none — in solitaire; each choice is a branch). Evoke: exile a white card from
your hand instead of paying (branch per distinct white card); sacrificed after
its ETB trigger."""
from __future__ import annotations

from ._common import branch_over
from .base import Card, CardAction
from .registry import register


def _etb_options(state, permanent):
    others = [p.uid for p in state.battlefield
              if p.is_creature_now and p.uid != permanent.uid]
    # Exile choices first, declining last (nicer first-found replay lines).
    return others + [None]


def _etb_apply(st, uid):
    if uid is None:
        st.emit("Solitude: no creature exiled")
        return
    p = st.find_permanent(uid)
    if p is not None:
        gained = max(0, st.effective_power(p))
        st.leaves_battlefield(p, "exile")
        st.life += gained
        st.emit(f"Solitude: exile {p.name}, gain {gained} life")


def _sac_evoked(st) -> None:
    for p in st.battlefield:
        if p.card.name == "Solitude" and p.counters.get("evoked"):
            st.emit("Solitude: evoke — sacrificed")
            st.leaves_battlefield(p, "graveyard")
            break


@register
class Solitude(Card):
    card_name = "Solitude"

    def on_etb(self, state, permanent):
        options = _etb_options(state, permanent)
        evoked = bool(permanent.counters.get("evoked"))

        def apply(st, uid):
            _etb_apply(st, uid)
            if evoked:
                _sac_evoked(st)

        if options == [None]:
            apply(state, None)
            return None
        return branch_over(state, options, apply)

    def hand_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_battlefield
        from ..engine.mana import ManaCost

        whites = sorted({c.name for c in state.hand
                         if "W" in c.colors and c.name != self.card_name})

        def make(white_name: str):
            def pay(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                pitch = next((c for c in st.hand if c.name == white_name), None)
                if card is None or pitch is None:
                    return False
                st.hand.remove(pitch)
                st.exile.append(pitch)
                st.emit(f"evoke Solitude: exile {white_name} from hand")
                if not begin_cast(st, card, ManaCost(), tag="evoke"):
                    return False
                return True

            def resolve(st):
                card = next((c for c in st.stack if c.name == self.card_name), None)
                if card is None:
                    return None
                return resolve_to_battlefield(st, card, marks={"evoked": 1}) or None

            return CardAction.activated(
                f"evoke Solitude (exile {white_name})",
                pay,
                resolve,
                source_name="Solitude",
                ability_text=f"Evoke — exile {white_name} from your hand",
            )

        return [make(w) for w in whites]
