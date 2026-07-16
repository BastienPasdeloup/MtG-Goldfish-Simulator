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


_CARD_TYPES = ("creature", "instant", "sorcery", "land", "artifact",
               "enchantment", "planeswalker", "battle")


def graveyard_card_types(state: "GameState") -> set:
    """The distinct card types among cards in your graveyard (delirium, escape,
    Nethergoyf)."""
    found: set[str] = set()
    for c in state.graveyard:
        tl = c.type_line.lower()
        for t in _CARD_TYPES:
            if t in tl:
                found.add(t)
    return found


def evoke_actions(self: Card, state: "GameState", color: str) -> list[CardAction]:
    """Evoke: cast this creature for free by exiling a `color` card from your
    hand; when it enters, its ETB resolves and then it is sacrificed. Returns a
    single hand action (the fuel card is chosen deterministically — the
    lowest-mana-value eligible card)."""
    from ..engine.actions import begin_cast
    from ..engine.game_state import StackAbility
    from ..engine.mana import ManaCost

    fuel = [c for c in state.hand
            if color in c.colors and c.name != self.card_name]
    if not fuel:
        return []

    def fn(st: "GameState"):
        me = next((c for c in st.hand if c.name == self.card_name), None)
        picks = sorted((c for c in st.hand
                        if color in c.colors and c.name != self.card_name),
                       key=lambda c: c.cmc)
        if me is None or not picks:
            return None
        chosen = picks[0]
        st.hand.remove(chosen)
        st.exile.append(chosen)
        st.emit(f"evoke {me.name}: exile {chosen.name}")
        if not begin_cast(st, me, ManaCost(), tag="evoke"):
            return None
        if me in st.stack:
            st.stack.remove(me)
        st.note_event("spell_resolved", me.name)
        st.resolving = ("spell", me.name)
        perm = st.put_on_battlefield(me, fire_etb=False)
        st.emit(f"{me.name} resolves — enters (evoked)")

        def sac_resolve(s, uid=perm.uid, nm=me.name):
            p = s.find_permanent(uid)
            if p is not None:
                s.emit(f"{nm}: evoke — sacrifice")
                s.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return None

        # Sacrifice resolves AFTER the ETB: push it first (bottom of stack),
        # then the ETB triggers on top.
        st.push_triggered_abilities([StackAbility(
            f"{me.name}: evoke sacrifice", sac_resolve,
            source_name=me.name, kind="triggered",
            trigger_text="Evoke", ability_text="Sacrifice this creature")])
        st.queue_entry_triggers([perm])
        return None  # apply() settles the queued ETB + evoke sacrifice

    # Label starts with "cast " so CardAction.apply runs it as a spell cast
    # (pay + resolve immediately) and settles the result.
    return [CardAction(f"cast {self.card_name} (evoke — exile a {color} card)", fn)]


def damage_any_target_options(state: "GameState", *, players_only: bool = False):
    """Enumerate 'any target' choices for a damage effect: the opponent (a
    crime) plus each distinct creature you control. Returns a list of
    (label_suffix, apply(st, amount)) — the caller wraps each in an action."""
    options: list[tuple[str, Callable]] = []

    def opp(st: "GameState", amount: int):
        st.opponent_life -= amount
        st.note_crime()
        st.emit(f"{amount} damage to opponent ({st.opponent_life})")

    options.append(("opponent", opp))
    if players_only:
        return options
    seen: set[str] = set()
    for p in state.battlefield:
        if not p.is_creature_now or p.name in seen:
            continue
        seen.add(p.name)

        def make(uid: int):
            def apply(st: "GameState", amount: int):
                t = st.find_permanent(uid)
                if t is not None:
                    t.damage += amount
                    st.emit(f"{amount} damage to {t.name}")
                    st.check_deaths()
            return apply

        options.append((p.name, make(p.uid)))
    return options


def amass(state: "GameState", n: int, subtype: str = "Zombie") -> "Permanent":
    """Amass <subtype> N: put N +1/+1 counters on an Army you control; if you
    control none, create a 0/0 black Army creature token of that subtype first.
    The Army also becomes the named subtype (approximated by naming the token)."""
    army = next((p for p in state.battlefield if "army" in p.type_line.lower()), None)
    if army is None:
        army = state.make_token(f"{subtype} Army", 0, 0, f"Creature — {subtype} Army")
    army.counters["+1/+1"] = army.counters.get("+1/+1", 0) + n
    state.emit(f"amass {subtype} {n} — {army.name} is now "
               f"{state.effective_power(army)}/{state.effective_toughness(army)}")
    state.check_deaths()
    return army


def surveil_branches(state: "GameState", n: int, source: str) -> list["GameState"] | None:
    """Surveil `n`: look at the top `n` cards; each may go to the graveyard or
    stay on top. Branch over the 2**n keep/bin outcomes (bounded — surveil
    counts are small). Returns None if the library is empty."""
    top = state.library[:n]
    if not top:
        return None
    outcomes = [()]
    for _ in top:
        outcomes = [combo + (keep,) for combo in outcomes for keep in (True, False)]

    def fn(st: "GameState", combo):
        # Process from the top down; binned cards go to the graveyard, kept
        # cards stay in their original relative order on top.
        binned = []
        keep_stack = []
        for card, keep in zip(st.library[:len(combo)], combo):
            if keep:
                keep_stack.append(card)
            else:
                binned.append(card)
        del st.library[:len(combo)]
        st.library[:0] = keep_stack
        for card in binned:
            st.to_graveyard(card)
        if binned:
            st.emit(f"{source}: surveil {len(combo)} — {', '.join(c.name for c in binned)} to graveyard")
        else:
            st.emit(f"{source}: surveil {len(combo)} — keep all on top")
        return None

    return branch_over(state, outcomes, fn)


def mono_land(name: str, color: str) -> type[Card]:
    """A land that taps for a single colour (also covers artifact lands)."""

    @register
    class _Mono(Card):
        card_name = name

        def mana_abilities(self, state):
            return [ManaAbility(amount=1, choices=(color,))]

    _Mono.__name__ = name.replace(" ", "").replace("'", "").replace(",", "")
    _Mono.__doc__ = f"{name} — Land. {{T}}: Add {{{color}}}."
    return _Mono


def slow_land(name: str, colors: tuple[str, str]) -> type[Card]:
    """Dual that enters tapped unless you control two or more other lands."""

    @register
    class _Slow(Card):
        card_name = name

        def mana_abilities(self, state):
            return [ManaAbility(amount=1, choices=colors)]

        def etb_tapped(self, state):
            other_lands = sum(1 for p in state.battlefield if p.is_land)
            return other_lands < 2

    _Slow.__name__ = name.replace(" ", "").replace("'", "")
    _Slow.__doc__ = f"{name} — taps for {colors}; tapped unless ≥2 other lands."
    return _Slow


def pain_land(name: str, colors: tuple[str, str]) -> type[Card]:
    """'{T}: Add {C}.' and '{T}: Add <A> or <B>. Deals 1 damage to you.'
    Modelled with a free colourless ability and a coloured ability with a
    1-life cost (the payment planner prefers the painless one when it can)."""

    @register
    class _Pain(Card):
        card_name = name

        def mana_abilities(self, state):
            return [
                ManaAbility(amount=1, choices=("C",)),
                ManaAbility(amount=1, choices=colors, life_cost=1),
            ]

    _Pain.__name__ = name.replace(" ", "").replace("'", "")
    _Pain.__doc__ = f"{name} — pain land: {{C}} free, or {colors} for 1 life."
    return _Pain


def filter_land(name: str, colors: tuple[str, str]) -> type[Card]:
    """Filter land (Graven Cairns cycle). Approximation: a free {C} plus a
    coloured ability for either of its two colours (the {B/R} filter input is
    not modelled — in practice the filter fixes the colour of mana you already
    have, so treating it as an extra coloured source is a close goldfish
    approximation)."""

    @register
    class _Filter(Card):
        card_name = name

        def mana_abilities(self, state):
            return [
                ManaAbility(amount=1, choices=("C",)),
                ManaAbility(amount=1, choices=colors),
            ]

    _Filter.__name__ = name.replace(" ", "").replace("'", "")
    _Filter.__doc__ = f"{name} — filter land approximated as {{C}} plus {colors}."
    return _Filter


def verge_land(name: str, main_color: str, second_color: str,
               required_types: tuple[str, ...]) -> type[Card]:
    """Verge cycle: '{T}: Add <main>.' and '{T}: Add <second>. Activate only if
    you control a <T1> or a <T2>.' (Blazemire Verge, ...)."""

    @register
    class _Verge(Card):
        card_name = name

        def mana_abilities_perm(self, state, perm):
            abilities = [ManaAbility(amount=1, choices=(main_color,))]
            if any(p.is_land and perm_has_subtype(p, required_types)
                   for p in state.battlefield):
                abilities.append(ManaAbility(amount=1, choices=(second_color,)))
            return abilities

    _Verge.__name__ = name.replace(" ", "").replace("'", "")
    _Verge.__doc__ = (
        f"{name} — verge: {{{main_color}}} always; {{{second_color}}} only with a "
        f"{'/'.join(required_types)}.")
    return _Verge


def animate_land_action(
    self: Card, state: "GameState", perm: "Permanent", *,
    cost: ManaCost, type_line: str, power: int, toughness: int,
    keywords: Iterable[str] = (), label: str | None = None,
) -> list[CardAction]:
    """'<cost>: Until end of turn, this land becomes a P/T creature ...
    It's still a land.' Sets `perm.becomes` (cleared at cleanup); granted
    keywords go on `temp_keywords`. Instant speed."""
    from ..engine.actions import can_afford, pay_cost

    # The land can't tap itself for mana to pay its own animation cost (it would
    # end up tapped and unable to attack) — exclude it from the payment.
    if perm.becomes is not None or not can_afford(state, cost, exclude_uids={perm.uid}):
        return []
    kws = tuple(k.lower() for k in keywords)

    def pay(st: "GameState"):
        p = st.find_permanent(perm.uid)
        if p is None or p.becomes is not None or not pay_cost(st, cost, exclude_uids={perm.uid}):
            return False
        return True

    def resolve(st: "GameState"):
        p = st.find_permanent(perm.uid)
        if p is None:
            return None
        p.becomes = {"type_line": type_line, "power": power, "toughness": toughness}
        p.temp_keywords.update(kws)
        st.emit(f"{perm.name} becomes a {power}/{toughness} creature until end of turn")
        return None

    return [CardAction.activated(
        label or f"{self.card_name}: animate ({power}/{toughness})",
        pay,
        resolve,
        source_name=self.card_name,
        ability_text=f"Becomes a {power}/{toughness} creature until end of turn",
    )]


def sacrifice_outlet_actions(
    self: Card, state: "GameState", perm: "Permanent", *,
    cost: ManaCost | None, effect: Callable, label: str,
    can_sac: Callable[["Permanent"], bool] | None = None,
    tap: bool = False, sac_self_ok: bool = True,
) -> list[CardAction]:
    """A 'Sacrifice a creature[/permanent]: <effect>' outlet: one branch per
    distinct sacrificeable permanent. `effect(st, source_perm)` applies the
    result after the sacrifice. `can_sac(perm)` filters what may be sacrificed
    (default: any creature you control)."""
    from ..engine.actions import can_afford, pay_cost

    if perm.tapped and tap:
        return []
    if cost is not None and not can_afford(state, cost):
        return []
    pred = can_sac or (lambda p: p.is_creature_now)
    victims: dict[str, int] = {}
    for p in state.battlefield:
        if not pred(p):
            continue
        if not sac_self_ok and p.uid == perm.uid:
            continue
        victims.setdefault(p.name, p.uid)

    def make(vuid: int):
        def pay(st: "GameState"):
            src = st.find_permanent(perm.uid)
            victim = st.find_permanent(vuid)
            if src is None or victim is None:
                return False
            if tap:
                if src.tapped:
                    return False
                src.tapped = True
            if cost is not None and not pay_cost(st, cost):
                return False
            st.emit(f"sacrifice {victim.name}")
            st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
            return True

        def resolve(st: "GameState"):
            src = st.find_permanent(perm.uid)
            return effect(st, src)

        vname = state.find_permanent(vuid).name if state.find_permanent(vuid) else vuid
        return CardAction.activated(
            f"{label} (sac {vname})",
            pay,
            resolve,
            source_name=self.card_name,
            ability_text=label,
        )

    return [make(uid) for uid in victims.values()]


def counterspell(
    name: str, *, target: Callable[[CardData], bool] | None = None,
    dest: str = "graveyard", note: str = "",
) -> type[Card]:
    """A counterspell: it can only be cast with a valid target — a spell ON THE
    STACK.

    In this solitaire engine there is no opponent and spells resolve atomically,
    so at any priority window the stack holds no spell to counter; a counterspell
    is therefore not castable by default. When instant-speed exploration is
    enabled (`state.instant_speed`), it additionally offers the niche play of
    countering your OWN spell — casting a hand spell and the counter together so
    it goes to the graveyard/library instead of resolving. `target(card)`
    restricts legal targets (e.g. mana value 1 for Mental Misstep); `dest` is
    where the countered card goes ("graveyard", or "library_top" for Memory Lapse)."""

    @register
    class _Counter(Card):
        card_name = name

        def cast_actions(self, state):
            from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

            my_cost = self.cast_cost(state)
            if not can_afford(state, my_cost):
                return []
            acts: list[CardAction] = []
            seen: set[str] = set()
            # A counterspell needs a spell on the stack to target. (Spells
            # resolve atomically here, so this list is normally empty and the
            # counter is not offered — exactly "can't be cast without a spell on
            # the stack".)
            for victim in list(state.stack):
                if not isinstance(victim, CardData) or victim.name == name:
                    continue
                if victim.name in seen or (target is not None and not target(victim)):
                    continue
                seen.add(victim.name)

                def make(victim_name: str):
                    def fn(st: "GameState"):
                        counter = next((c for c in st.hand if c.name == name), None)
                        victim = next((c for c in st.stack if isinstance(c, CardData)
                                       and c.name == victim_name), None)
                        if counter is None or victim is None:
                            return None
                        if not begin_cast(st, counter, my_cost):
                            return None
                        resolve_to_graveyard(st, counter)  # the counter resolves
                        if victim in st.stack:
                            st.stack.remove(victim)
                        if dest == "library_top":
                            st.library.insert(0, victim)
                            st.emit(f"{name}: counter {victim_name} — to top of library")
                        else:
                            st.to_graveyard(victim)
                            st.emit(f"{name}: counter {victim_name} — to graveyard")
                        return None
                    return fn

                acts.append(CardAction(f"cast {name} countering {victim.name}", make(victim.name)))

            # Instant-speed niche play: counter your OWN spell. Cast a spell from
            # hand and the counter together (paying both costs) so it never
            # resolves — it goes to the graveyard / library instead. Only offered
            # when instant-speed exploration is enabled (see GameState.instant_speed).
            if getattr(state, "instant_speed", False):
                def _merge(a: ManaCost, b: ManaCost) -> ManaCost:
                    pips = dict(a.pip_map)
                    for c, n in b.pip_map.items():
                        pips[c] = pips.get(c, 0) + n
                    return ManaCost(generic=a.generic + b.generic, pips=tuple(pips.items()))

                for tgt in list(state.hand):
                    if tgt.name == name or tgt.name in seen or tgt.is_land:
                        continue
                    if target is not None and not target(tgt):
                        continue
                    seen.add(tgt.name)
                    if not can_afford(state, _merge(my_cost, ManaCost.parse(tgt.mana_cost))):
                        continue

                    def make_own(target_name: str):
                        def fn(st: "GameState"):
                            counter = next((c for c in st.hand if c.name == name), None)
                            victim = next((c for c in st.hand if c.name == target_name), None)
                            if counter is None or victim is None:
                                return None
                            if not begin_cast(st, victim, ManaCost.parse(victim.mana_cost)):
                                return None
                            if not begin_cast(st, counter, my_cost):
                                return None
                            resolve_to_graveyard(st, counter)  # the counter resolves
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

                    acts.append(CardAction(f"cast {name} countering own {tgt.name}", make_own(tgt.name)))
            return acts

    _Counter.__name__ = name.replace(" ", "").replace("'", "")
    _Counter.__doc__ = (
        f"{name} — counterspell. Targets a spell on the stack (never present in a "
        f"goldfish, so normally uncastable); with instant-speed exploration on, can "
        f"counter your own spell to fill the graveyard.{(' ' + note) if note else ''}"
    )
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
