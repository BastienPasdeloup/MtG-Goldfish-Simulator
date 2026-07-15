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
        branches = fn(b, opt)
        if branches is None:
            b.check_deaths()
            out.append(b)
        else:
            out.extend(branches)
    return out


def enter_from_stack_marked(state: "GameState", card: CardData, marks: dict):
    """Stack -> battlefield with pre-set counters (evoked/escaped markers)."""
    from ..engine.actions import resolve_to_battlefield

    return resolve_to_battlefield(state, card, marks=marks)


def enter_battlefield(
    state: "GameState",
    card: CardData,
    *,
    tapped: bool | None = None,
    announce: str | None = None,
):
    """Put a card onto the battlefield from a non-stack effect and queue its
    ETB triggers. The caller settles the resulting stack."""
    perm = state.put_on_battlefield(card, tapped=tapped, fire_etb=False, announce=announce)
    state.queue_entry_triggers([perm])
    return perm


def enter_battlefield_sequence(
    state: "GameState",
    entries: list[tuple[CardData, bool | None, str | None]],
):
    """Put multiple permanents onto the battlefield simultaneously and queue
    all resulting ETB triggers afterwards."""
    permanents = []
    for card, tapped, announce in entries:
        permanents.append(
            state.put_on_battlefield(card, tapped=tapped, fire_etb=False, announce=announce)
        )
    state.queue_entry_triggers(permanents)
    return permanents


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
        def pay(state: "GameState"):
            perm = state.find_permanent(uid)
            if perm is None or perm.tapped or state.life <= 1:
                return False
            perm.tapped = True
            state.life -= 1
            state.emit(f"{perm.name}: tap, pay 1 life, sacrifice")
            state.leaves_battlefield(perm, "graveyard")
            return True

        def resolve(state: "GameState"):
            from ..engine.actions import _apply_etb_mode

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
            state.queue_entry_triggers([newp])
            return None
        return pay, resolve

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
                    pay, resolve = _fetch_fn(perm.uid, target.name, mode)
                    acts.append(CardAction(
                        f"{name}: fetch {target.name}{suffix}",
                        resolve,
                        pre_fn=pay,
                        source_name=name,
                        ability_text=f"Fetch {target.name}{suffix}",
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
            other_lands = sum(1 for p in state.battlefield if p.is_land)
            return other_lands > 2

    _Fast.__name__ = name.replace(" ", "")
    _Fast.__doc__ = f"{name} — taps for {colors}; tapped unless ≤2 other lands."
    return _Fast


def counterspell(
    name: str, *, target: Callable[[CardData], bool] | None = None,
    dest: str = "graveyard", note: str = "",
) -> type[Card]:
    """A counterspell that targets YOUR OWN spell.

    In a solitaire game there are no opponents' spells, and this engine resolves
    spells atomically — but you can still usefully counter your own spell: cast
    the target and the counter together (paying both costs) so the target is
    countered instead of resolving. This puts the target card into your
    graveyard (fuelling graveyard-matters cards) rather than onto the
    battlefield / letting it resolve. `target(card)` restricts legal targets
    (e.g. mana value 1 for Mental Misstep); `dest` is where the countered card
    goes ("graveyard", or "library_top" for Memory Lapse)."""

    def _merge(a: ManaCost, b: ManaCost) -> ManaCost:
        pips: dict[str, int] = dict(a.pip_map)
        for c, n in b.pip_map.items():
            pips[c] = pips.get(c, 0) + n
        return ManaCost(generic=a.generic + b.generic, pips=tuple(pips.items()))

    @register
    class _Counter(Card):
        card_name = name

        def cast_actions(self, state):
            from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

            my_cost = self.cast_cost(state)
            acts: list[CardAction] = []
            seen: set[str] = set()
            for tgt in list(state.hand):
                if tgt.name == name or tgt.name in seen or tgt.is_land:
                    continue
                if target is not None and not target(tgt):
                    continue
                seen.add(tgt.name)
                combined = _merge(my_cost, ManaCost.parse(tgt.mana_cost))
                if not can_afford(state, combined):
                    continue

                def make(target_name: str):
                    def fn(st: "GameState"):
                        counter = next((c for c in st.hand if c.name == name), None)
                        victim = next((c for c in st.hand if c.name == target_name), None)
                        if counter is None or victim is None:
                            return None
                        # Cast the victim (onto the stack), then the counter.
                        if not begin_cast(st, victim, ManaCost.parse(victim.mana_cost)):
                            return None
                        if not begin_cast(st, counter, my_cost):
                            return None
                        # The counter resolves: the victim is countered.
                        resolve_to_graveyard(st, counter)
                        if victim in st.stack:
                            st.stack.remove(victim)
                        if dest == "library_top":
                            st.library.insert(0, victim)
                            st.emit(f"{name}: counter own {target_name} — to top of library")
                        else:
                            st.to_graveyard(victim)
                            st.emit(f"{name}: counter own {target_name} — to graveyard")
                        return None
                    return fn

                acts.append(CardAction(f"cast {name} countering own {tgt.name}", make(tgt.name)))
            return acts

    _Counter.__name__ = name.replace(" ", "").replace("'", "")
    _Counter.__doc__ = f"{name} — counter your own spell to fill the graveyard.{(' ' + note) if note else ''}"
    return _Counter


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

    def pay(st: "GameState"):
        p = st.find_permanent(perm.uid)
        if p is None or p.transformed or not pay_cost(st, cost):
            return False
        return True

    def resolve(st: "GameState"):
        p = st.find_permanent(perm.uid)
        if p is None or p.transformed:
            return None
        p.transformed = True
        st.emit(f"transform into {back_name}")
        return None

    return [CardAction.activated(
        f"transform → {back_name}",
        pay,
        resolve,
        source_name=perm.name,
        ability_text=f"Transform into {back_name}",
    )]


# --------------------------------------------------------------------------
# library-search helpers (all shuffle, like every real search)
# --------------------------------------------------------------------------
def tutor_to_battlefield_branches(
    state: "GameState", pred: Callable, *, tapped: bool | None = True, note: str = "",
) -> list["GameState"] | None:
    """Branches: one per distinct matching library card, put onto the
    battlefield (tapped by default), then shuffle. ETB/landfall triggers fire.
    Returns None when nothing matches (caller keeps the un-branched state)."""
    targets = state.search_library(pred)
    if not targets:
        return None

    def fn(st: "GameState", name: str):
        card = next(c for c in st.library if c.name == name)
        st.take_from_library(card)
        st.shuffle_library()
        enter_battlefield(
            st,
            card,
            tapped=tapped,
            announce=f"search: {card.name} onto battlefield{' tapped' if tapped else ''} — shuffle{note}",
        )
        return None

    return branch_over(state, [t.name for t in targets], fn)


def tutor_to_hand_branches(
    state: "GameState", pred: Callable, *, note: str = "",
) -> list["GameState"] | None:
    """Branches: one per distinct matching library card, revealed to hand,
    then shuffle."""
    targets = state.search_library(pred)
    if not targets:
        return None

    def fn(st: "GameState", name: str):
        card = next(c for c in st.library if c.name == name)
        st.take_from_library(card)
        st.shuffle_library()
        st.hand.append(card)
        st.emit(f"search: {card.name} to hand — shuffle{note}")

    return branch_over(state, [t.name for t in targets], fn)


def any_identity_color(state: "GameState") -> tuple[str, ...]:
    """'Add one mana of any color' — restricted to the commander identity
    (other colours are useless in a Commander goldfish)."""
    return tuple(state.commander_color_identity) or ("W", "U", "B", "R", "G")


def controls_forest(state: "GameState") -> bool:
    """'...unless you control a Forest' — honours Yavimaya, Cradle of Growth
    (which makes every land a Forest)."""
    yavi = any(p.name == "Yavimaya, Cradle of Growth" for p in state.battlefield)
    return any(
        p.is_land and (yavi or perm_has_subtype(p, ("Forest",)))
        for p in state.battlefield
    )


def forest_count(state: "GameState") -> int:
    yavi = any(p.name == "Yavimaya, Cradle of Growth" for p in state.battlefield)
    return sum(
        1 for p in state.battlefield
        if p.is_land and (yavi or perm_has_subtype(p, ("Forest",)))
    )


def aura_on_land_cast_actions(
    self: Card, state: "GameState", *, forests_only: bool = False,
) -> list[CardAction]:
    """Cast an Aura that enchants one of YOUR lands: one branch per distinct
    eligible land. The Aura enters attached to the chosen host."""
    from ..engine.actions import begin_cast, can_afford

    cost = self.cast_cost(state)
    if not can_afford(state, cost):
        return []

    hosts = {}
    for p in state.battlefield:
        if not p.is_land:
            continue
        if forests_only and not (perm_has_subtype(p, ("Forest",))
                                 or any(q.name == "Yavimaya, Cradle of Growth"
                                        for q in state.battlefield)):
            continue
        hosts.setdefault(p.name, p.uid)

    def make(uid: int):
        def fn(st: "GameState"):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            host = st.find_permanent(uid)
            if card is None or host is None or not begin_cast(st, card, cost):
                return None
            if card in st.stack:
                st.stack.remove(card)
            perm = st.put_on_battlefield(card, fire_etb=False)
            perm.attached_to = host.uid
            st.emit(f"{self.card_name} resolves — enchant {host.name}")
            st.check_deaths()
            return None
        return fn

    return [CardAction(f"cast {self.card_name} → {name}", make(uid))
            for name, uid in hosts.items()]


def aura_on_creature_bestow_actions(
    self: Card, state: "GameState", *, bestow_cost: str,
) -> list[CardAction]:
    """Bestow this enchantment-creature onto one of your creatures (branch per
    creature). While bestowed it is an Aura granting +1/+1 via equip_mod."""
    from ..engine.actions import begin_cast, can_afford
    from ..engine.mana import ManaCost

    cost = ManaCost.parse(bestow_cost)
    if not can_afford(state, cost):
        return []

    hosts = {}
    for p in state.battlefield:
        if p.is_creature_now and p.name not in hosts:
            hosts[p.name] = p.uid

    def make(uid: int):
        def fn(st: "GameState"):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            host = st.find_permanent(uid)
            if card is None or host is None or not begin_cast(st, card, cost, tag="bestow"):
                return None
            if card in st.stack:
                st.stack.remove(card)
            perm = st.put_on_battlefield(card, fire_etb=False)
            perm.attached_to = host.uid
            perm.counters["bestowed"] = 1  # it is an Aura, not a creature, now
            st.emit(f"{self.card_name} resolves — bestow onto {host.name}")
            st.check_deaths()
            return None
        return fn

    return [CardAction(f"cast {self.card_name} (bestow) → {name}", make(uid))
            for name, uid in hosts.items()]


def sac_fetch_land(name: str, types: tuple[str, ...]) -> type[Card]:
    """'When this land enters, sacrifice it. When you do, search your library
    for a basic <T1/T2/T3> card, put it onto the battlefield tapped, then
    shuffle and you gain 1 life.' (Brokers Hideout cycle.)"""

    @register
    class _SacFetch(Card):
        card_name = name

        def on_etb(self, state, permanent):
            state.leaves_battlefield(permanent, "graveyard")
            state.emit(f"{name}: sacrifice")
            targets = state.search_library(
                lambda c: "basic" in c.type_line.lower() and has_subtype(c, types)
            )
            if not targets:
                state.shuffle_library()
                state.life += 1
                return None

            def fn(st: "GameState", nm: str):
                card = next(c for c in st.library if c.name == nm)
                st.take_from_library(card)
                st.shuffle_library()
                st.life += 1
                enter_battlefield(
                    st,
                    card,
                    tapped=True,
                    announce=f"{name}: fetch {nm} tapped, gain 1 life — shuffle",
                )
                return None

            return branch_over(state, [t.name for t in targets], fn)

    _SacFetch.__name__ = name.replace(" ", "").replace("'", "")
    _SacFetch.__doc__ = (
        f"{name} — Land. ETB: sacrifice it; search a basic {'/'.join(types)} "
        f"card onto the battlefield tapped, then shuffle; gain 1 life."
    )
    return _SacFetch


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

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return False
            st.leaves_battlefield(p, "none")
            return True

        def resolve(st):
            st.emit("sacrifice Clue — draw a card")
            st.draw(1)
            return None

        return [CardAction.activated(
            "Clue: {2}, sacrifice — draw a card",
            pay,
            resolve,
            source_name="Clue",
            ability_text="Draw a card",
        )]


@register
class TreasureToken(Card):
    """Treasure token — {T}, Sacrifice: add one mana of any color.
    Modelled as a mana source that sacrifices itself when tapped for mana."""

    card_name = "Treasure"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state))]

    def on_tap_for_mana(self, state, permanent, color):
        state.leaves_battlefield(permanent, "none")
        state.emit("sacrifice Treasure for mana")


@register
class FoodToken(Card):
    """Food token — {2}, {T}, Sacrifice: you gain 3 life."""

    card_name = "Food"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            st.leaves_battlefield(p, "none")
            return True

        def resolve(st):
            st.life += 3
            st.emit("sacrifice Food — gain 3 life")
            return None

        return [CardAction.activated(
            "Food: {2}, sacrifice — gain 3 life",
            pay,
            resolve,
            source_name="Food",
            ability_text="Gain 3 life",
        )]


@register
class LanderToken(Card):
    """Lander token — {2}, {T}, Sacrifice: search your library for a basic
    land card, put it onto the battlefield tapped, then shuffle."""

    card_name = "Lander"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost):
            return []

        acts = []
        for target in state.search_library(lambda c: c.is_land and "basic" in c.type_line.lower()):
            def pay(st, name=target.name):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, cost):
                    return False
                st.leaves_battlefield(p, "none")
                return True

            def resolve(st, name=target.name):
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                enter_battlefield(
                    st,
                    card,
                    tapped=True,
                    announce=f"Lander: fetch {name} tapped — shuffle",
                )
                return None
            acts.append(CardAction.activated(
                f"Lander: fetch {target.name}",
                pay,
                resolve,
                source_name="Lander",
                ability_text=f"Fetch {target.name}",
            ))
        return acts


@register
class EldraziSpawnToken(Card):
    """Eldrazi Spawn token — 0/1; Sacrifice: add {C}.
    Modelled as a mana source that sacrifices itself when tapped for mana."""

    card_name = "Eldrazi Spawn"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def on_tap_for_mana(self, state, permanent, color):
        state.leaves_battlefield(permanent, "none")
        state.emit("sacrifice Eldrazi Spawn for {C}")
