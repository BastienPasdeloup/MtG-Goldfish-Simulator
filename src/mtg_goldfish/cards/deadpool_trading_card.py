"""Deadpool, Trading Card — {2}{B}{R} Legendary Creature — Mutant Mercenary Hero 5/3.

"As Deadpool enters, you may exchange his text box and another creature's."
— an AS-ENTERS replacement (never on the stack), branching over each other
creature in play plus declining. Exchanging swaps the two permanents'
behaviours (impl), rules text and keywords: Deadpool behaves as the other
creature's text, and the other creature behaves as written on Deadpool:

  * "At the beginning of your upkeep, you lose 3 life."
  * "{3}, Sacrifice this creature: Each other player draws a card."
    (the opponent's draw is irrelevant in a goldfish game)

House rules of the exchange:
  * Name, types and power/toughness are NOT part of the text box and stay put
    — including P/T set by a characteristic-defining ability, which stays
    anchored to its original permanent (`Permanent.pt_impl`).
  * A flipped (transformed) creature exchanges only its CURRENT side: the
    active face's text and keywords move to Deadpool, and Deadpool's
    `transformed` view is aligned so the swapped impl keeps behaving as that
    face. The other creature keeps its own face (name/types/P&T unchanged).
  * Power-up: "Activate only once" is tracked PER PERMANENT, so a gained
    power-up is fresh — Deadpool may use it even when the other creature had
    already powered up. The original creature keeps its "powered_up" badge;
    Deadpool shows none until he powers up himself. The exchanged creature is
    marked with a "deadpool" badge.
"""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


def _active_text(perm) -> str:
    """The rules text of the permanent's ACTIVE face."""
    return perm.face.oracle_text or perm.card.oracle_text


def _active_keywords(perm) -> list[str]:
    """The keywords that belong to the ACTIVE face. Scryfall keywords are
    card-wide, so for a double-faced card keep only those the active face's
    text actually mentions."""
    kws = list(perm.card.keywords)
    if len(perm.card.faces) > 1:
        text = _active_text(perm).lower()
        kws = [k for k in kws if k.lower() in text]
    return kws


def _with_swapped_text(card, transformed: bool, text: str, keywords: list[str]):
    """A copy of `card` whose (active-face) rules text and keywords are the
    incoming text box."""
    update = {"oracle_text": text, "keywords": list(keywords)}
    if card.faces:
        idx = 1 if transformed and len(card.faces) > 1 else 0
        faces = list(card.faces)
        faces[idx] = faces[idx].model_copy(update={"oracle_text": text})
        update["faces"] = faces
    return card.model_copy(update=update)


@register
class DeadpoolTradingCard(Card):
    card_name = "Deadpool, Trading Card"

    # ---- as-enters text-box exchange (part of entering, not a trigger) ----
    def enter_choices(self, state, perm):
        others = [p for p in state.battlefield
                  if p.uid != perm.uid and p.is_creature_now]
        if not others:
            return None

        def fn(st, uid):
            if uid is None:
                return  # decline the exchange
            me = st.find_permanent(perm.uid)
            other = st.find_permanent(uid)
            if me is None or other is None:
                return
            # P/T stays put: any P/T-defining behaviour keeps reading from the
            # permanent's ORIGINAL impl even after the text box moves.
            me.pt_impl = me.pt_impl or me.impl
            other.pt_impl = other.pt_impl or other.impl
            # Only the CURRENT side of a flipped card is exchanged: take the
            # active face's text/keywords, and align Deadpool's `transformed`
            # view so the swapped impl keeps behaving as that face. The other
            # creature keeps its own face (name/types/P&T stay put).
            me_text, other_text = _active_text(other), _active_text(me)
            me_kws, other_kws = _active_keywords(other), _active_keywords(me)
            me.impl, other.impl = other.impl, me.impl
            me.card = _with_swapped_text(me.card, me.transformed, me_text, me_kws)
            other.card = _with_swapped_text(other.card, other.transformed,
                                            other_text, other_kws)
            me.transformed = other.transformed
            # Power-up: "Activate only once" is tracked PER PERMANENT, so the
            # gained power-up is fresh — Deadpool may activate it even if the
            # other creature had already used its own. The original creature
            # keeps its "powered_up" badge (part of its history); Deadpool
            # only gets one once HE powers up. Enforce the entry invariant:
            # Deadpool NEVER enters with a powered-up marker of his own.
            me.counters.pop("powered_up", None)
            me.counters.pop("_powered_up", None)
            # Board-viz marker: the chosen creature shows a "deadpool" badge
            # (its text box is now Deadpool's).
            other.counters["deadpool"] = 1
            st.emit(f"Deadpool enters: exchange text boxes with {other.name}")

        # Exchange targets first, declining last (nicer first-found replays).
        return branch_over(state, [p.uid for p in others] + [None], fn)

    # ---- Deadpool's printed text box (moves with the exchange) ----
    def phase_stack_items(self, state, perm, phase):
        # Deadpool's printed text triggers at the UPKEEP only — no stack item
        # at any other phase (also holds for whoever received his text box).
        if phase != Phase.UPKEEP:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.UPKEEP)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: upkeep trigger",
            resolve=resolve,
            trigger_text="At the beginning of your upkeep",
            ability_text="You lose 3 life.",
        )]

    def on_phase(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return
        state.life -= 3
        state.emit(f"{perm.name}: lose 3 life ({state.life} left)")

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=3)
        if not can_afford(state, cost):
            return []

        def pay(st, uid=perm.uid):
            p = st.find_permanent(uid)
            if p is None or not pay_cost(st, cost):
                return False
            return True

        def resolve(st, uid=perm.uid):
            p = st.find_permanent(uid)
            if p is None:
                return None
            st.leaves_battlefield(p, "graveyard")
            st.emit(f"{p.name}: sacrificed — each other player draws a card")
            return None

        return [CardAction.activated(
            f"{perm.name}: {{3}}, sacrifice — each other player draws",
            pay,
            resolve,
            source_name=perm.name,
            ability_text="{3}, Sacrifice this creature: Each other player draws a card.",
        )]
