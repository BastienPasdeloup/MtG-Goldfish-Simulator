"""Player actions and the mana-payment planner.

The simulator asks `legal_actions(state)` for every branch to explore in a main
phase, clones the state, and calls `action.apply(clone)`. Mana is *not* a branch
point: tapping lands for mana is solved deterministically by `plan_payment`,
which keeps the decision tree focused on genuinely meaningful choices (which
spell/land to play, and in what order).
"""
from __future__ import annotations

from dataclasses import dataclass

from .game_state import GameState, Permanent, make_permanent
from .mana import ManaAbility, ManaCost, ManaPool


# --------------------------------------------------------------------------
# Mana
# --------------------------------------------------------------------------
def available_mana_sources(state: GameState) -> list[tuple[Permanent, ManaAbility]]:
    """Untapped permanents that can currently produce mana.

    Creatures with summoning sickness cannot tap for mana (unless they have
    haste, which the slice does not yet model)."""
    sources: list[tuple[Permanent, ManaAbility]] = []
    for perm in state.battlefield:
        if perm.tapped:
            continue
        if perm.card.is_creature and perm.summoning_sick:
            continue
        abilities = perm.impl.mana_abilities(state)
        if abilities:
            sources.append((perm, abilities[0]))
    return sources


def plan_payment(
    cost: ManaCost,
    sources: list[tuple[Permanent, ManaAbility]],
    base_pool: ManaPool,
) -> list[tuple[int, str]] | None:
    """Decide which sources to tap (and for which colour) to pay `cost`.

    Returns a list of (source_index, colour) or None if unaffordable. Greedy:
    cover coloured pips with the least-flexible sources first, then top up
    generic with whatever is left (colourless first).
    """
    pool = base_pool.copy()
    used = [False] * len(sources)
    plan: list[tuple[int, str]] = []

    for color, need in cost.pip_map.items():
        while pool.amounts.get(color, 0) < need:
            candidates = [
                i
                for i, (_, ab) in enumerate(sources)
                if not used[i] and color in ab.choices
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda i: len(sources[i][1].choices))
            i = candidates[0]
            used[i] = True
            pool.add(color, sources[i][1].amount)
            plan.append((i, color))

    while not pool.can_pay(cost):
        candidates = [i for i in range(len(sources)) if not used[i]]
        if not candidates:
            return None

        def generic_key(i: int) -> tuple[int, int]:
            choices = sources[i][1].choices
            return (0 if choices == ("C",) else 1, len(choices))

        candidates.sort(key=generic_key)
        i = candidates[0]
        used[i] = True
        ability = sources[i][1]
        color = "C" if "C" in ability.choices else ability.choices[0]
        pool.add(color, ability.amount)
        plan.append((i, color))

    return plan


def _pay(state: GameState, cost: ManaCost) -> bool:
    """Tap sources and spend `cost` from the pool. Returns False if unaffordable."""
    sources = available_mana_sources(state)
    plan = plan_payment(cost, sources, state.mana_pool)
    if plan is None:
        return False
    for idx, color in plan:
        perm, _ = sources[idx]
        perm.tapped = True
        state.mana_pool.add(color, sources[idx][1].amount)
    return state.mana_pool.pay(cost)


def can_afford(state: GameState, cost: ManaCost) -> bool:
    return plan_payment(cost, available_mana_sources(state), state.mana_pool) is not None


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------
class Action:
    """A single legal decision. `apply` mutates the (already cloned) state."""

    label: str = "action"

    def apply(self, state: GameState) -> None:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class PassPhase(Action):
    label: str = "pass"

    def apply(self, state: GameState) -> None:
        state.emit("pass")


@dataclass
class PlayLand(Action):
    card_name: str

    @property
    def label(self) -> str:
        return f"play land {self.card_name}"

    def apply(self, state: GameState) -> None:
        card = _pop_from_hand(state, self.card_name)
        perm = make_permanent(state, card)
        state.battlefield.append(perm)
        state.lands_played_this_turn += 1
        perm.impl.on_etb(state, perm)
        state.emit(f"play land {card.name}")


def _resolve_spell(state: GameState, card, perm_is_commander: bool = False) -> None:
    state.spells_cast_this_turn += 1
    state.storm_count += 1
    if card.is_creature:
        state.creature_spells_cast_this_turn += 1
    else:
        state.noncreature_spells_cast_this_turn += 1

    if card.is_permanent:
        perm = make_permanent(state, card, is_commander=perm_is_commander)
        state.battlefield.append(perm)
        perm.impl.on_etb(state, perm)
    else:
        perm = make_permanent(state, card)  # for its impl only
        perm.impl.on_resolve(state)
        state.graveyard.append(card)


@dataclass
class CastFromHand(Action):
    card_name: str

    @property
    def label(self) -> str:
        return f"cast {self.card_name}"

    def apply(self, state: GameState) -> None:
        card = _pop_from_hand(state, self.card_name)
        cost = ManaCost.parse(card.mana_cost)
        if not _pay(state, cost):
            # Should not happen: legality is checked before enumeration.
            state.hand.append(card)
            return
        state.emit(f"cast {card.name}")
        _resolve_spell(state, card)


@dataclass
class CastCommander(Action):
    card_name: str

    @property
    def label(self) -> str:
        return f"cast commander {self.card_name}"

    def apply(self, state: GameState) -> None:
        card = _pop_from_zone(state.command_zone, self.card_name)
        tax = 2 * state.commander_cast_count.get(card.name, 0)
        cost = ManaCost.parse(card.mana_cost)
        cost = ManaCost(generic=cost.generic + tax, pips=cost.pips)
        if not _pay(state, cost):
            state.command_zone.append(card)
            return
        state.commander_cast_count[card.name] = state.commander_cast_count.get(card.name, 0) + 1
        state.emit(f"cast commander {card.name} (tax {tax})")
        _resolve_spell(state, card, perm_is_commander=True)


# --------------------------------------------------------------------------
# Legal-action enumeration
# --------------------------------------------------------------------------
def legal_actions(state: GameState) -> list[Action]:
    """All meaningful actions in the current (main) phase, plus passing.

    Choices are de-duplicated by card name so that holding two copies of a card
    (or many basics) does not multiply the branching factor."""
    actions: list[Action] = []
    seen_hand: set[str] = set()

    for card in state.hand:
        if card.name in seen_hand:
            continue
        seen_hand.add(card.name)
        if card.is_land and state.lands_played_this_turn < 1:
            actions.append(PlayLand(card.name))
        elif not card.is_land and can_afford(state, ManaCost.parse(card.mana_cost)):
            actions.append(CastFromHand(card.name))

    seen_cmd: set[str] = set()
    for card in state.command_zone:
        if card.name in seen_cmd:
            continue
        seen_cmd.add(card.name)
        tax = 2 * state.commander_cast_count.get(card.name, 0)
        base = ManaCost.parse(card.mana_cost)
        cost = ManaCost(generic=base.generic + tax, pips=base.pips)
        if can_afford(state, cost):
            actions.append(CastCommander(card.name))

    actions.append(PassPhase())
    return actions


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _pop_from_hand(state: GameState, name: str):
    return _pop_from_zone(state.hand, name)


def _pop_from_zone(zone: list, name: str):
    for i, card in enumerate(zone):
        if card.name == name:
            return zone.pop(i)
    raise ValueError(f"{name!r} not found in zone")
