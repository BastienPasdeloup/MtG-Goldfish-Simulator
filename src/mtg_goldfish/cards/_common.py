"""Shared helpers and class factories for card implementations.

Not a card module (leading underscore => skipped by the registry loader);
imported by the individual card files.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable

from ..deck.models import CardData
from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register

if TYPE_CHECKING:
    from ..engine.game_state import GameState, Permanent

BASIC_TYPES = ("Plains", "Island", "Swamp", "Mountain", "Forest")
TYPE_COLOR = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}


# --------------------------------------------------------------------------
# predicates / small utilities
# --------------------------------------------------------------------------
def has_subtype(card: CardData, subtypes: Iterable[str]) -> bool:
    tl = card.type_line.lower()
    return any(s.lower() in tl for s in subtypes)


def perm_has_subtype(perm: "Permanent", subtypes: Iterable[str]) -> bool:
    """Like has_subtype but honours chosen types (Multiversal Passage)."""
    if perm.chosen and any(s.lower() == perm.chosen.lower() for s in subtypes):
        return True
    return any(s.lower() in perm.type_line.lower() for s in subtypes)


def mv(card: CardData) -> int:
    return int(card.cmc)


def type_matches(card: CardData, *words: str) -> bool:
    tl = card.type_line.lower()
    return any(w.lower() in tl for w in words)


def basic_types_in_play(state: "GameState") -> int:
    """Domain: number of basic land types among lands you control."""
    return sum(
        1 for t in BASIC_TYPES
        if any(perm_has_subtype(p, (t,)) for p in state.battlefield)
    )


def branch_over(state: "GameState", options: list, fn: Callable) -> list:
    """Clone the state once per option, apply `fn(clone, option)`, return the
    clones. The standard way card hooks enumerate a resolution choice."""
    out = []
    for opt in options:
        b = state.clone()
        fn(b, opt)
        b.check_deaths()
        out.append(b)
    return out


def enter_from_stack_marked(state: "GameState", card: CardData, marks: dict):
    """Stack -> battlefield with pre-set counters (evoked/escaped markers)."""
    from ..engine.actions import resolve_to_battlefield

    return resolve_to_battlefield(state, card, marks=marks)


def discard(state: "GameState", card: CardData) -> None:
    state.hand.remove(card)
    state.to_graveyard(card)
    state.emit(f"discard {card.name}")


def targeted_instant_casts(
    self: Card,
    state: "GameState",
    target_uids: list[int],
    effect: Callable,
    *,
    cost: ManaCost | None = None,
    extra_life: int = 0,
    tag: str = "",
) -> list[CardAction]:
    """Cast actions for an instant/sorcery needing a battlefield target: one
    branch per target. `effect(st, perm)` applies the resolution."""
    from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

    cost = cost if cost is not None else self.cast_cost(state)
    if not can_afford(state, cost, extra_life=extra_life):
        return []

    def make(uid: int):
        def fn(st: "GameState"):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            perm = st.find_permanent(uid)
            if card is None or perm is None:
                return None
            if not begin_cast(st, card, cost, extra_life=extra_life, tag=tag):
                return None
            resolve_to_graveyard(st, card)
            effect(st, perm)
            return None
        return fn

    out = []
    for uid in target_uids:
        perm = state.find_permanent(uid)
        if perm is not None:
            suffix = f", {tag}" if tag else ""
            out.append(CardAction(f"cast {self.card_name} → {perm.name}{suffix}", make(uid)))
    return out


# --------------------------------------------------------------------------
# factories for the land cycles
# --------------------------------------------------------------------------
def fetch_land(name: str, subtypes: tuple[str, str]) -> type[Card]:
    """'{T}, Pay 1 life, Sacrifice: search for a <A> or <B> card, put it onto
    the battlefield, then shuffle.' The choice of target (and its own enter
    mode, e.g. a fetched shockland) is a branch."""

    def _fetch_fn(uid: int, target_name: str, mode: dict | None):
        def fn(state: "GameState"):
            from ..engine.actions import _apply_etb_mode

            perm = state.find_permanent(uid)
            if perm is None or perm.tapped or state.life <= 1:
                return None
            perm.tapped = True
            state.life -= 1
            state.emit(f"{perm.name}: tap, pay 1 life, sacrifice")
            state.leaves_battlefield(perm, "graveyard")
            target = next((c for c in state.library if c.name == target_name), None)
            if target is None:
                return None
            if mode and mode.get("life") and state.life <= mode["life"]:
                return None
            state.take_from_library(target)
            newp = state.put_on_battlefield(target, fire_etb=False)
            _apply_etb_mode(state, newp, mode)
            state.shuffle_library()
            suffix = f" ({mode['label']})" if mode and mode.get("label") else ""
            state.emit(f"fetched {target.name}{suffix} — shuffle")
            branches = newp.impl.on_etb(state, newp)
            state.check_deaths()
            return branches
        return fn

    @register
    class _Fetch(Card):
        card_name = name

        def battlefield_actions(self, state, perm):
            if perm.tapped or state.life <= 1:
                return []
            from .registry import build_card

            acts: list[CardAction] = []
            for target in state.search_library(lambda c: c.is_land and has_subtype(c, subtypes)):
                modes = build_card(target).etb_modes(state) or [None]
                for mode in modes:
                    suffix = f" ({mode['label']})" if mode and mode.get("label") else ""
                    acts.append(CardAction(
                        f"{name}: fetch {target.name}{suffix}",
                        _fetch_fn(perm.uid, target.name, mode),
                    ))
            return acts

    _Fetch.__name__ = name.replace(" ", "").replace("'", "")
    _Fetch.__doc__ = (
        f"{name} — Land. {{T}}, Pay 1 life, Sacrifice: search your library for a "
        f"{subtypes[0]} or {subtypes[1]} card, put it onto the battlefield, then shuffle."
    )
    return _Fetch


def shock_land(name: str, colors: tuple[str, str]) -> type[Card]:
    """Dual that may enter untapped for 2 life."""

    @register
    class _Shock(Card):
        card_name = name

        def mana_abilities(self, state):
            return [ManaAbility(amount=1, choices=colors)]

        def etb_modes(self, state):
            modes = []
            if state.life > 2:
                modes.append({"label": "pay 2 life, untapped", "tapped": False, "life": 2})
            modes.append({"label": "tapped", "tapped": True, "life": 0})
            return modes

    _Shock.__name__ = name.replace(" ", "")
    _Shock.__doc__ = f"{name} — taps for {colors}; enters tapped unless you pay 2 life."
    return _Shock


def fast_land(name: str, colors: tuple[str, str]) -> type[Card]:
    """Dual that enters tapped unless you control two or fewer other lands."""

    @register
    class _Fast(Card):
        card_name = name

        def mana_abilities(self, state):
            return [ManaAbility(amount=1, choices=colors)]

        def etb_tapped(self, state):
            other_lands = sum(1 for p in state.battlefield if "land" in p.type_line.lower())
            return other_lands > 2

    _Fast.__name__ = name.replace(" ", "")
    _Fast.__doc__ = f"{name} — taps for {colors}; tapped unless ≤2 other lands."
    return _Fast


def uncastable_spell(name: str, reason: str) -> type[Card]:
    """A spell with no legal use in a solitaire game (counterspells etc.).
    Fully implemented: its exact behaviour in a goldfish is 'never castable'."""

    @register
    class _Spell(Card):
        card_name = name

        def is_castable(self, state):
            return False

    _Spell.__name__ = name.replace(" ", "").replace("'", "")
    _Spell.__doc__ = f"{name} — never castable in a solitaire game: {reason}"
    return _Spell


def transform_actions(
    state: "GameState", perm: "Permanent", cost: ManaCost, back_name: str,
) -> list[CardAction]:
    """'{cost}: Transform ~. Activate only as a sorcery.'"""
    from ..engine.actions import can_afford, pay_cost

    if perm.transformed or not can_afford(state, cost):
        return []

    def fn(st: "GameState"):
        p = st.find_permanent(perm.uid)
        if p is None or p.transformed or not pay_cost(st, cost):
            return None
        p.transformed = True
        st.emit(f"transform into {back_name}")
        return None

    return [CardAction(f"transform → {back_name}", fn)]


# --------------------------------------------------------------------------
# token implementations
# --------------------------------------------------------------------------
@register
class ClueToken(Card):
    """Clue token — {2}, Sacrifice: draw a card."""

    card_name = "Clue"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        def fn(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return None
            st.leaves_battlefield(p, "none")
            st.emit("sacrifice Clue — draw a card")
            st.draw(1)
            return None

        return [CardAction("Clue: {2}, sacrifice — draw a card", fn)]
