"""Player actions and the mana-payment planner.

The simulator asks `legal_actions(state)` for every branch to explore in a main
phase, clones the state, and calls `action.apply(clone)`. `apply` mutates in
place, or returns a list of branch states for in-resolution choices.

Mana is *not* a branch point: tapping sources for mana is solved
deterministically by `plan_payment`, which keeps the decision tree focused on
genuinely meaningful choices (which spell/land to play, targets, modes).
Card-specific choices are enumerated by the card implementations themselves via
`CardAction` (see `cards.base`).
"""
from __future__ import annotations

from dataclasses import dataclass

from .game_state import GameState, Permanent
from .mana import ManaAbility, ManaCost, ManaPool


# --------------------------------------------------------------------------
# Mana
# --------------------------------------------------------------------------
def available_mana_sources(
    state: GameState, exclude_uids: set[int] | None = None
) -> list[tuple[Permanent, ManaAbility]]:
    """(permanent, ability) pairs currently usable. A permanent may contribute
    several entries (alternative abilities); the planner uses at most one.

    `exclude_uids` omits specific permanents — used when an activated ability
    that taps the source must pay its OWN mana cost (the source can't also help
    pay it, e.g. Castle Garenbrig's {2}{G}{G},{T}: add six {G})."""
    exclude_uids = exclude_uids or set()
    # Mana abilities GRANTED to every untapped artifact you control (Urza, Lord
    # High Artificer: "Tap an untapped artifact you control: Add {U}.").
    artifact_grants = [
        g for p in state.battlefield
        for g in (p.impl.artifact_mana_grant(state, p),) if g is not None
    ]
    sources: list[tuple[Permanent, ManaAbility]] = []
    for perm in state.battlefield:
        if perm.tapped or perm.uid in exclude_uids:
            continue
        if perm.is_creature_now and perm.summoning_sick and not state.has_keyword(perm, "Haste"):
            continue
        # Auras like Wild Growth add mana whenever the host is tapped for mana.
        bonus = sum(
            att.impl.attached_mana_amount_bonus(state, att, perm)
            for att in state.battlefield if att.attached_to == perm.uid
        )
        # Gauntlet of Might: each Mountain taps for an extra {R} per Gauntlet.
        if perm.is_land and "mountain" in perm.type_line.lower():
            bonus += sum(o.impl.mountain_mana_bonus(state, o) for o in state.battlefield)
        # Mana Flare: every land taps for one extra mana of the colour it produces.
        if perm.is_land:
            bonus += sum(o.impl.land_mana_bonus(state, perm) for o in state.battlefield)
        if perm.mana_override:
            # "Enchanted land is a Swamp" / "Mountains are Plains": the land taps
            # for one mana of the overridden colour instead of its printed ability.
            abilities = [ManaAbility(amount=1, choices=(perm.mana_override,))]
        else:
            abilities = list(perm.impl.mana_abilities_perm(state, perm))
        if artifact_grants and perm.is_artifact:
            abilities.extend(artifact_grants)  # each untapped artifact can tap for the grant
        for ability in abilities:
            if ability.life_cost and state.life <= ability.life_cost:
                continue
            if bonus:
                ability = ManaAbility(
                    amount=ability.amount + bonus, choices=ability.choices,
                    life_cost=ability.life_cost,
                )
            sources.append((perm, ability))
    return sources


def plan_payment(
    cost: ManaCost,
    sources: list[tuple[Permanent, ManaAbility]],
    base_pool: ManaPool,
    *,
    allow: frozenset = frozenset(),
) -> list[tuple[int, str]] | None:
    """Decide which sources to tap (and for which colour) to pay `cost`.

    Returns a list of (source_index, colour) or None if unaffordable. Greedy:
    cover coloured pips with the least-flexible, lowest-life-cost sources
    first, then top up generic. At most one ability per permanent. `allow` is the
    payment-purpose set: a restricted source (Mishra's Workshop) is usable only if
    its restriction permits one of those purposes."""
    from .mana import usable_restrictions
    codes = usable_restrictions(allow)
    pool = base_pool.copy()
    used_perms: set[int] = set()
    plan: list[tuple[int, str]] = []

    def candidates(pred) -> list[int]:
        return [
            i for i, (perm, ab) in enumerate(sources)
            if perm.uid not in used_perms
            and (not ab.restriction or ab.restriction in codes)
            and pred(ab)
        ]

    for color, need in cost.pip_map.items():
        while pool.available(color, allow=allow) < need:
            cands = candidates(lambda ab: color in ab.choices)
            if not cands:
                return None
            cands.sort(key=lambda i: (sources[i][1].life_cost, len(sources[i][1].choices)))
            i = cands[0]
            used_perms.add(sources[i][0].uid)
            pool.add_restricted(color, sources[i][1].amount, sources[i][1].restriction)
            plan.append((i, color))

    while not pool.can_pay(cost, allow=allow):
        cands = candidates(lambda ab: True)
        if not cands:
            return None

        def generic_key(i: int) -> tuple[int, int, int]:
            ab = sources[i][1]
            return (ab.life_cost, 0 if ab.choices == ("C",) else 1, len(ab.choices))

        cands.sort(key=generic_key)
        i = cands[0]
        used_perms.add(sources[i][0].uid)
        ability = sources[i][1]
        color = "C" if "C" in ability.choices else ability.choices[0]
        pool.add_restricted(color, ability.amount, ability.restriction)
        plan.append((i, color))

    return plan


def _pool_str(pool: ManaPool) -> str:
    parts = [f"{n}{c}" for c, n in pool.amounts.items() if n]
    parts += [f"{n}{c}@{code}" for code, cols in pool.restricted.items()
              for c, n in cols.items() if n]
    return "{" + " ".join(parts) + "}" if parts else "{empty}"


def pay_cost(state: GameState, cost: ManaCost, extra_life: int = 0,
             exclude_uids: set[int] | None = None,
             allow: frozenset = frozenset()) -> bool:
    """Tap sources and spend `cost` (plus optional life). False if unaffordable.
    `exclude_uids` omits permanents from the payment (see available_mana_sources).
    `allow` is the payment-purpose set (e.g. {"artifact_spell"}) enabling restricted
    mana (Mishra's Workshop) — empty means only unrestricted mana may be used."""
    if extra_life and state.life <= extra_life:
        return False
    sources = available_mana_sources(state, exclude_uids)
    plan = plan_payment(cost, sources, state.mana_pool, allow=allow)
    if plan is None:
        return False
    taps: list[str] = []
    for idx, color in plan:
        perm, ability = sources[idx]
        perm.tapped = True
        state.mana_pool.add_restricted(color, ability.amount, ability.restriction)
        if ability.life_cost:
            state.life -= ability.life_cost
        perm.impl.on_tap_for_mana(state, perm, color)  # e.g. pain-land damage
        if perm.is_land:  # broadcast: Manabarbs / Psychic Venom watch land taps
            for watcher in list(state.battlefield):
                watcher.impl.on_land_tapped_for_mana(state, watcher, perm, color)
        if perm.is_artifact:  # broadcast: Haunting Wind / Artifact Possession
            for watcher in list(state.battlefield):
                watcher.impl.on_artifact_tapped_for_mana(state, watcher, perm)
        taps.append(f"{perm.name}→{color}")
    if taps:
        state.emit(f"tap for mana: {', '.join(taps)}  pool={_pool_str(state.mana_pool)}")
    ok = state.mana_pool.pay(cost, allow=allow)
    if extra_life:
        state.life -= extra_life
    return ok


def can_afford(state: GameState, cost: ManaCost, extra_life: int = 0,
               exclude_uids: set[int] | None = None,
               allow: frozenset = frozenset()) -> bool:
    if extra_life and state.life <= extra_life:
        return False
    return plan_payment(
        cost, available_mana_sources(state, exclude_uids), state.mana_pool, allow=allow
    ) is not None


# --------------------------------------------------------------------------
# Convoke — tap untapped creatures to pay {1} or a matching-colour pip. We tap
# the MINIMUM number of creatures needed to make the rest of the cost affordable
# with mana (so a spell you can already pay for taps none), which is always a
# safe payment option.
# --------------------------------------------------------------------------
def _convoke_reduce_once(cost: ManaCost, creature) -> tuple[ManaCost, bool]:
    pips = dict(cost.pips)
    for color in (creature.card.colors or []):
        if pips.get(color, 0) > 0:
            pips[color] -= 1
            return ManaCost(generic=cost.generic,
                            pips=tuple((c, n) for c, n in pips.items() if n > 0)), True
    if cost.generic > 0:
        return ManaCost(generic=cost.generic - 1, pips=cost.pips), True
    return cost, False


def _convoke_plan(state: GameState, cost: ManaCost, exclude_uids):
    creatures = [c for c in state.battlefield if c.is_creature_now and not c.tapped
                 and c.uid not in (exclude_uids or set())]
    used, reduced = [], cost
    while not can_afford(state, reduced, exclude_uids=exclude_uids) and creatures:
        best = None
        for cr in creatures:
            new, helped = _convoke_reduce_once(reduced, cr)
            if helped:
                best = (cr, new)
                if new.pips != reduced.pips:  # prefer reducing a coloured pip
                    break
        if best is None:
            break
        cr, reduced = best
        used.append(cr)
        creatures.remove(cr)
    if not can_afford(state, reduced, exclude_uids=exclude_uids):
        return None
    return used, reduced


def can_afford_with_convoke(state, cost, extra_life=0, exclude_uids=None):
    if extra_life and state.life <= extra_life:
        return False
    return _convoke_plan(state, cost, exclude_uids) is not None


def pay_cost_with_convoke(state, cost, extra_life=0, exclude_uids=None):
    plan = _convoke_plan(state, cost, exclude_uids)
    if plan is None:
        return False
    used, reduced = plan
    for cr in used:
        cr.tapped = True
        state.emit(f"convoke: tap {cr.name}")
    return pay_cost(state, reduced, extra_life=extra_life, exclude_uids=exclude_uids)


# --------------------------------------------------------------------------
# Improvise — tap untapped artifacts, each paying {1} of GENERIC cost only
# (never a coloured pip). We tap the minimum number of artifacts needed to make
# the rest affordable with mana, preferring artifacts that DON'T tap for mana so
# a mana rock is kept for real mana. A spell you can already pay for taps none.
# --------------------------------------------------------------------------
def _improvise_plan(state: GameState, cost: ManaCost, exclude_uids=None):
    base_exclude = set(exclude_uids or set())
    arts = [
        p for p in state.battlefield
        if p.is_artifact and not p.tapped and p.uid not in base_exclude
        and not (p.is_creature_now and p.summoning_sick
                 and not state.has_keyword(p, "Haste"))
    ]
    # Non-mana artifacts first (keep mana rocks for mana), then fewest choices.
    arts.sort(key=lambda p: (bool(p.impl.mana_abilities_perm(state, p)),))

    def eff(k: int) -> ManaCost:
        return ManaCost(generic=max(0, cost.generic - k), pips=cost.pips)

    def afford(k: int) -> bool:
        excl = base_exclude | {p.uid for p in arts[:k]}
        return can_afford(state, eff(k), exclude_uids=excl)

    limit = min(len(arts), cost.generic)
    k = 0
    while not afford(k) and k < limit:
        k += 1
    if not afford(k):
        return None
    return arts[:k], eff(k)


def can_afford_with_improvise(state, cost, extra_life=0, exclude_uids=None):
    if extra_life and state.life <= extra_life:
        return False
    return _improvise_plan(state, cost, exclude_uids) is not None


def pay_cost_with_improvise(state, cost, extra_life=0, exclude_uids=None):
    plan = _improvise_plan(state, cost, exclude_uids)
    if plan is None:
        return False
    used, reduced = plan
    for art in used:
        art.tapped = True
        state.emit(f"improvise: tap {art.name}")
    return pay_cost(state, reduced, extra_life=extra_life, exclude_uids=exclude_uids)


def card_has_improvise(state: GameState, card) -> bool:
    """Whether casting `card` from hand uses improvise: the card itself has the
    Improvise keyword, or a permanent grants improvise to your noncreature spells
    (Ironheart, Clever Champion)."""
    if any(str(k).lower() == "improvise" for k in (card.keywords or [])):
        return True
    if not card.is_creature and any(
        p.impl.grants_noncreature_improvise for p in state.battlefield
    ):
        return True
    return False


# --------------------------------------------------------------------------
# Casting helpers (used by generic actions AND by card implementations)
# --------------------------------------------------------------------------
def _effective_cast_cost(state: GameState, card, base: ManaCost) -> ManaCost:
    """`base` cast cost plus any global increase from permanents in play
    (Gloom: white spells cost {3} more). Applied on the generic cast path."""
    inc = sum(p.impl.cast_cost_increase(state, card) for p in state.battlefield)
    if inc:
        return ManaCost(generic=base.generic + inc, pips=base.pips)
    return base


def begin_cast(
    state: GameState, card, cost: ManaCost, *,
    zone: list | None = None, extra_life: int = 0, tag: str = "", convoke: bool = False,
    improvise: bool = False, target: str = "",
) -> bool:
    """Pay the cost, move the card from `zone` (default: hand) to the stack,
    bump the cast counters, and fire cast triggers. Returns False if unpaid.
    `convoke` lets untapped creatures pay part of the cost (Hoarding Broodlord;
    spells cast from exile under it); `improvise` lets untapped artifacts pay the
    generic part (Kappa Cannoneer, Ironheart). `target` names what the spell
    targets, so the replay's stack shows "→ target"."""
    zone = state.hand if zone is None else zone
    # Casting an ARTIFACT spell may use artifact-only restricted mana (Mishra's
    # Workshop, a Powerstone token); other spells and all abilities may not.
    allow = frozenset({"artifact_spell"}) if getattr(card, "is_artifact", False) else frozenset()
    if improvise:
        ok = pay_cost_with_improvise(state, cost, extra_life=extra_life)
    elif convoke:
        ok = pay_cost_with_convoke(state, cost, extra_life=extra_life)
    else:
        ok = pay_cost(state, cost, extra_life=extra_life, allow=allow)
    if not ok:
        return False
    zone.remove(card)
    state.stack.append(card)
    if target:
        state.stack_targets[id(card)] = target
    state.spells_cast_this_turn += 1
    state.storm_count += 1
    if card.is_creature:
        state.creature_spells_cast_this_turn += 1
    else:
        state.noncreature_spells_cast_this_turn += 1
    # Property-visible event: the player CAST this spell (put it on the stack).
    # This is distinct from the card entering the battlefield — a spell can be
    # cast and then countered (never enters), and a permanent can enter without
    # being cast (fetched, reanimated, a token). `played_on`/`cast_on` read this.
    # `storm` = spells cast this turn INCLUDING this one (storm_count was just
    # bumped), so a property can ask "cast when the storm count was >= N" — the
    # value AT cast time, which can't be reached AFTER it resolves.
    state.note_event("cast", card.name, card=card, storm=state.storm_count,
                     is_creature=card.is_creature, is_land=card.is_land)
    state.emit(f"cast {card.name}{f' ({tag})' if tag else ''}"
               f"{f' → {target}' if target else ''} (on the stack)")
    state.queue_cast_triggers(card)
    state.settle_nonbranching(f"cast triggers for {card.name}")
    return True


def resolve_to_battlefield(
    state: GameState, card, *, is_commander: bool = False, marks: dict | None = None,
):
    """Move a spell from the stack onto the battlefield. Returns the ETB
    branches (list of states) or None. `marks` pre-sets counters on the
    permanent before ETB triggers fire (e.g. {'escaped': 1})."""
    if card in state.stack:
        state.stack.remove(card)
    state.stack_targets.pop(id(card), None)  # left the stack — drop its target
    state.note_event("spell_resolved", card.name)
    # Effects until control returns to the search (its own entry included) are
    # attributed to this spell; ETB triggers override with their own context.
    state.resolving = ("spell", card.name)
    perm = state.put_on_battlefield(card, is_commander=is_commander, fire_etb=False)
    if marks:
        perm.counters.update(marks)
    # Announce the enter BEFORE ETB triggers fire (Amulet / Tezzeret / landfall)
    # so the replay shows the permanent entering first, effects after.
    state.emit(f"{card.name} resolves — enters the battlefield")
    # "As it enters" choices that fan out (Deadpool's text-box exchange) apply
    # BEFORE the ETB triggers are queued, so the queued ETBs reflect the choice.
    branches = perm.impl.enter_choices(state, perm)
    if branches is None:
        state.queue_entry_triggers([perm])
        return None
    for b in branches:
        live = b.find_permanent(perm.uid)
        if live is not None:
            b.queue_entry_triggers([live])
    return branches


def resolve_to_graveyard(state: GameState, card) -> None:
    if card in state.stack:
        state.stack.remove(card)
    state.stack_targets.pop(id(card), None)  # left the stack — drop its target
    state.note_event("spell_resolved", card.name)
    # The spell's `on_resolve` effects run right after this; attribute them to
    # the spell ("Cultivate put 2 lands into play") until settle() clears it.
    state.resolving = ("spell", card.name)
    state.to_graveyard(card)
    state.emit(f"{card.name} resolves")


# --------------------------------------------------------------------------
# Generic actions
# --------------------------------------------------------------------------
def _front_is_land(card) -> bool:
    """Whether the card's FRONT face is a land — i.e. it can be played as your
    land drop from the front. A modal DFC whose front is a spell but whose back
    is a land (Waterlogged Teachings — "Instant // Land") is NOT a front land:
    the combined `card.is_land` is True (it contains "Land"), but its front is
    cast and its back land is played via the card's own hand_actions."""
    tl = card.faces[0].type_line if card.faces else card.type_line
    return "land" in tl.split("—")[0].lower()


def _is_instant_speed(card) -> bool:
    """Whether a card can be cast at instant speed (an instant, or any spell
    with the Flash keyword). Sorceries, creatures and other permanents without
    Flash are sorcery-speed. Uses the `keywords` list (not an oracle-text scan,
    which would false-match "Flashback")."""
    if card.is_instant:
        return True
    return any(k.lower() == "flash" for k in card.keywords)


class Action:
    """A single legal decision. `apply` mutates the (already cloned) state in
    place, or returns a list of branch states.

    `sorcery_speed` gates WHEN the action may be taken: sorcery-speed actions
    (lands, sorceries, most permanents) are only offered in a main phase with
    the stack empty; instant-speed ones (instants, flash, most activated
    abilities) are also offered in the instant-speed windows of other steps."""

    label: str = "action"
    sorcery_speed: bool = True

    def apply(self, state: GameState):  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class PassPhase(Action):
    label: str = "pass"
    sorcery_speed: bool = False  # passing priority is always available

    def apply(self, state: GameState) -> None:
        state.emit("pass")


class PlayLand(Action):
    def __init__(self, card_name: str, mode: dict | None = None, zone: str = "hand") -> None:
        self.card_name = card_name
        self.mode = mode
        self.zone = zone  # "hand" | "graveyard" (Icetill Explorer)
        suffix = f" ({mode['label']})" if mode and mode.get("label") else ""
        origin = " from graveyard" if zone == "graveyard" else ""
        self.label = f"play land {card_name}{suffix}{origin}"

    def apply(self, state: GameState):
        src = state.hand if self.zone == "hand" else state.graveyard
        card = _find_in_zone(src, self.card_name)
        src.remove(card)
        state.lands_played_this_turn += 1
        # Property-visible event: the player PLAYED this land (a land drop).
        # Distinct from the land entering the battlefield — a land fetched or
        # otherwise put into play was NOT "played". `played_on` reads this.
        state.note_event("play_land", card.name, card=card, is_land=True)
        state.resolving = ("land_drop", card.name)  # cleared by the final settle
        perm = state.put_on_battlefield(card, fire_etb=False)
        perm.turn_flags["played_as_land"] = 1
        _apply_etb_mode(state, perm, self.mode)
        # "As it enters" replacements that depend on the chosen mode (Vesuva
        # entering as a copy) — applied before the frame, never on the stack.
        perm.impl.on_enter_choice(state, perm)
        # The mode may have chosen "enters tapped" (e.g. a shockland); re-apply
        # the "enters untapped" replacements so the announced frame reflects it.
        state.apply_entry_statics(perm)
        state.emit(self.label)  # announce the land entering BEFORE its triggers
        state.queue_entry_triggers([perm])  # landfall / Amulet, after the enter mode
        return state.settle()


def _apply_etb_mode(state: GameState, perm, mode: dict | None) -> None:
    if mode is None:
        return
    if mode.get("life"):
        state.life -= mode["life"]
    perm.tapped = bool(mode.get("tapped", perm.tapped))
    if mode.get("choice") is not None:
        perm.chosen = mode["choice"]


class CastDefault(Action):
    """Engine-default cast: pay, stack, resolve (permanent enters / spell to
    graveyard after `on_resolve`)."""

    def __init__(self, card_name: str, improvise: bool = False) -> None:
        self.card_name = card_name
        self.improvise = improvise
        self.label = f"cast {card_name}"

    def apply(self, state: GameState):
        card = _find_in_zone(state.hand, self.card_name)
        impl = _impl(card)
        cost = _effective_cast_cost(state, card, impl.cast_cost(state))
        if not begin_cast(state, card, cost, improvise=self.improvise):
            return None
        if card.is_permanent:
            result = resolve_to_battlefield(state, card)
            return state.settle(result)
        # Move to the graveyard first so branch clones made inside on_resolve
        # already have the spell there.
        resolve_to_graveyard(state, card)
        return state.settle(impl.on_resolve(state) or None)


class CastCommander(Action):
    def __init__(self, card_name: str) -> None:
        self.card_name = card_name
        self.label = f"cast commander {card_name}"

    def apply(self, state: GameState) -> None:
        card = _find_in_zone(state.command_zone, self.card_name)
        impl = _impl(card)
        tax = 2 * state.commander_cast_count.get(card.name, 0)
        base = impl.cast_cost(state)
        cost = ManaCost(generic=base.generic + tax, pips=base.pips)
        if not begin_cast(state, card, cost, zone=state.command_zone,
                          tag=f"commander, tax {tax}"):
            return
        state.commander_cast_count[card.name] = state.commander_cast_count.get(card.name, 0) + 1
        state.commander_cast_this_game = True
        result = resolve_to_battlefield(state, card, is_commander=True)
        return state.settle(result)


# --------------------------------------------------------------------------
# Legal-action enumeration
# --------------------------------------------------------------------------
def _mark(actions: list[Action], instant: bool) -> list[Action]:
    """Stamp a cast/play's speed (a cast of an instant/flash card is
    instant-speed, everything else sorcery-speed)."""
    for a in actions:
        a.sorcery_speed = not instant
    return actions


def legal_actions(state: GameState, *, sorcery_speed_ok: bool = True) -> list[Action]:
    """Meaningful actions available with priority right now, plus passing.
    Choices are de-duplicated by card name so duplicates don't multiply the
    branching factor.

    `sorcery_speed_ok` is True in a main phase (empty stack): sorcery-speed
    plays (lands, sorceries, most permanents, equip) are allowed. It is False
    in the instant-speed windows of other steps, where only instant-speed
    actions (instants, flash, most activated abilities) — and passing — are
    offered."""
    actions: list[Action] = []
    seen: set[str] = set()
    land_drop_ok = state.lands_played_this_turn < state.max_land_drops()

    # --- from hand ---
    for card in list(state.hand):
        if card.name in seen:
            continue
        seen.add(card.name)
        impl = _impl(card)

        # Route by the FRONT face, not the combined `is_land`: a modal DFC whose
        # front is a spell but whose back is a land (Waterlogged Teachings —
        # "Instant // Land") reads as `is_land` because "Land" is in the combined
        # type line, which would wrongly offer a generic land drop that enters
        # the FRONT (spell) face. Its back land is played via its own
        # `hand_actions` (which flips the permanent); its front is cast.
        front_is_land = _front_is_land(card)
        if front_is_land and land_drop_ok:
            modes = impl.etb_modes(state)
            if modes:
                actions.extend(PlayLand(card.name, mode=m) for m in modes)
            else:
                actions.append(PlayLand(card.name))
        elif not front_is_land:
            # Teferi, Time Raveler +1: sorcery spells may be cast as though they
            # had flash — treat them as instant-speed so they appear in the
            # search's instant-speed windows.
            inst = _is_instant_speed(card) or (state.cast_sorcery_as_flash and card.is_sorcery)
            custom = impl.cast_actions(state)
            if custom is not None:
                actions.extend(_mark(list(custom), inst))
            elif impl.is_castable(state):
                improvise = card_has_improvise(state, card)
                eff = _effective_cast_cost(state, card, impl.cast_cost(state))
                afford = (can_afford_with_improvise(state, eff)
                          if improvise else can_afford(state, eff))
                if afford:
                    actions.append(
                        _mark([CastDefault(card.name, improvise=improvise)], inst)[0])
        actions.extend(impl.hand_actions(state))

    # --- commander(s) from the command zone ---
    seen_cmd: set[str] = set()
    for card in state.command_zone:
        if card.name in seen_cmd:
            continue
        seen_cmd.add(card.name)
        # Only one commander may be cast per game: once one has been cast, a
        # partner that was never cast is no longer castable (the already-cast
        # commander may still be re-cast from the command zone under its tax).
        if state.commander_cast_this_game and not state.commander_cast_count.get(card.name):
            continue
        impl = _impl(card)
        tax = 2 * state.commander_cast_count.get(card.name, 0)
        base = impl.cast_cost(state)
        cost = ManaCost(generic=base.generic + tax, pips=base.pips)
        if can_afford(state, cost):
            actions.append(_mark([CastCommander(card.name)], _is_instant_speed(card))[0])

    # --- from the graveyard (escape, bestow, ...) ---
    seen_gy: set[str] = set()
    for card in state.graveyard:
        if card.name in seen_gy:
            continue
        seen_gy.add(card.name)
        actions.extend(_impl(card).graveyard_actions(state))

    # --- play/cast ANYTHING from the graveyard (Yawgmoth's Will, Emet-Selch //
    #     Hades): during your turn you may play lands and cast spells from it ---
    if state.graveyard_plays_enabled():
        seen_gyall: set[str] = set()
        for card in list(state.graveyard):
            if card.name in seen_gyall:
                continue
            seen_gyall.add(card.name)
            impl = _impl(card)
            if _front_is_land(card):
                if land_drop_ok:
                    modes = impl.etb_modes(state)
                    if modes:
                        actions.extend(PlayLand(card.name, mode=m, zone="graveyard")
                                       for m in modes)
                    else:
                        actions.append(PlayLand(card.name, zone="graveyard"))
            else:
                cost = impl.cast_cost(state)
                if impl.is_castable(state) and can_afford(state, cost):
                    actions.extend(_mark(_gy_cast_actions(state, card, cost),
                                         _is_instant_speed(card)))

    # --- specific artifact cards you may cast from the graveyard this turn
    #     (Emry, Lurker of the Loch). You still pay their costs. ---
    if state.gy_castable:
        seen_gyc: set[str] = set()
        for card in list(state.graveyard):
            if card.name not in state.gy_castable or card.name in seen_gyc:
                continue
            seen_gyc.add(card.name)
            impl = _impl(card)
            if _front_is_land(card):
                continue  # Emry marks artifact (nonland) cards only
            improvise = card_has_improvise(state, card)
            cost = impl.cast_cost(state)
            afford = (can_afford_with_improvise(state, cost) if improvise
                      else can_afford(state, cost))
            if impl.is_castable(state) and afford:
                actions.extend(_mark(_gy_cast_actions(state, card, cost, improvise=improvise),
                                     _is_instant_speed(card)))

    # --- land plays from the graveyard (Icetill Explorer) ---
    if land_drop_ok and any(p.impl.grants_gy_land_plays for p in state.battlefield):
        seen_gyl: set[str] = set()
        for card in state.graveyard:
            impl = _impl(card)
            if not impl.is_land or card.name in seen_gyl:
                continue
            seen_gyl.add(card.name)
            modes = impl.etb_modes(state)
            if modes:
                actions.extend(PlayLand(card.name, mode=m, zone="graveyard") for m in modes)
            else:
                actions.append(PlayLand(card.name, zone="graveyard"))

    # --- exile "you may play it" cards (Gwen Stacy) ---
    seen_ex: set[str] = set()
    for source_uid, card in list(state.exile_playable):
        # Whether the exiled card stays playable after its source leaves depends
        # on the SOURCE card's text (exile_play_requires_source): "as long as you
        # control ~" (Gwen/Inti) needs the source in play; "for as long as that
        # card remains exiled" (Hoarding Broodlord) does not. A Fixed-config
        # phantom source (negative uid, an exiler not in play — e.g. an opponent's
        # Aang) is never "in play", so only cards that DON'T need the source stay
        # playable through it.
        if state.exile_play_needs_source.get(source_uid, True) and \
                state.find_permanent(source_uid) is None:
            continue  # source left; no longer playable
        if card.name in seen_ex:
            continue
        seen_ex.add(card.name)
        actions.extend(_exile_play_actions(state, source_uid, card))

    # --- airbended cards: cast any modal face for {2} (Aang, Swift Savior) ---
    seen_air: set[str] = set()
    for card in list(state.airbend_exile):
        if card.name in seen_air:
            continue
        seen_air.add(card.name)
        actions.extend(_mark(_airbend_cast_actions(state, card),
                             _face_instant_speed(card)))

    # --- activated abilities on the battlefield (impls check tapped/sick) ---
    for perm in list(state.battlefield):
        actions.extend(perm.impl.battlefield_actions(state, perm))

    # --- free casts ("cast without paying its mana cost", World War Hulk I) ---
    actions.extend(_free_cast_actions(state))

    # --- alternative casting statics (Dream Halls) ---
    for perm in list(state.battlefield):
        actions.extend(perm.impl.alt_cast_actions(state, perm))

    if not sorcery_speed_ok:
        actions = [a for a in actions if not a.sorcery_speed]
    actions.append(PassPhase())
    return actions


def _grant_matches(grant: dict, card) -> bool:
    """Whether a free-cast grant applies to `card`."""
    name = grant.get("name")
    if name is not None:  # a grant tied to one specific card (Urza's {5} impulse)
        return card.name == name
    if grant.get("creature") and not card.is_creature:
        return False
    colors = grant.get("colors")
    if colors and not (set(colors) & set(card.colors)):
        return False
    return True


def _gy_cast_actions(state: GameState, card, cost: ManaCost, improvise: bool = False) -> list:
    """Cast a card from the graveyard paying its cost (Yawgmoth's Will, Hades,
    Emry). Uses the default resolution (permanent → battlefield, else on_resolve),
    so a spell whose effect lives in a custom `cast_actions` (targeted removal)
    casts as its plain on_resolve here — an accepted simplification for gy replay."""
    from ..cards.base import CardAction

    def fn(st: GameState):
        c = _find_in_zone(st.graveyard, card.name)
        if c is None or not begin_cast(st, c, cost, zone=st.graveyard, improvise=improvise):
            return None
        if c.is_permanent:
            return resolve_to_battlefield(st, c) or None
        resolve_to_graveyard(st, c)
        return _impl(c).on_resolve(st) or None

    return [CardAction(f"cast {card.name} from graveyard", fn)]


def cast_without_paying(state: GameState, card, *, zone: list | None = None,
                        is_commander: bool = False, tag: str = "") -> object:
    """Cast `card` from `zone` (default hand) paying NO mana cost, then resolve
    it. Used by "cast without paying its mana cost" effects and Dream Halls (the
    caller pays the alternative cost — e.g. a discard — first). Returns the ETB /
    on_resolve branches (or None), so the caller can `state.settle(...)` them."""
    zone = state.hand if zone is None else zone
    if not begin_cast(state, card, ManaCost(), zone=zone, tag=tag):
        return None
    if is_commander:
        state.commander_cast_count[card.name] = state.commander_cast_count.get(card.name, 0) + 1
        state.commander_cast_this_game = True
    if card.is_permanent:
        return resolve_to_battlefield(state, card, is_commander=is_commander)
    resolve_to_graveyard(state, card)
    return _impl(card).on_resolve(state) or None


def _free_cast_actions(state: GameState) -> list[Action]:
    """One "cast for free" action per (grant, matching distinct hand spell).
    A free cast consumes the grant it uses."""
    from ..cards.base import CardAction

    out: list[Action] = []
    if not state.free_casts:
        return out
    seen: set[tuple[int, str]] = set()
    for gi, grant in enumerate(state.free_casts):
        for card in list(state.hand):
            if card.is_land or not _grant_matches(grant, card):
                continue
            impl = _impl(card)
            if not impl.is_castable(state):
                continue
            key = (gi, card.name)
            if key in seen:
                continue
            seen.add(key)

            def fn(st: GameState, card_name=card.name, grant=grant):
                c = _find_in_zone(st.hand, card_name)
                if c is None:
                    return None
                if grant in st.free_casts:
                    st.free_casts.remove(grant)
                return cast_without_paying(st, c, tag="without paying its mana cost")

            label = grant.get("label", "free")
            act = CardAction(f"cast {card.name} ({label})", fn,
                             sorcery_speed=not _is_instant_speed(card))
            out.append(act)
    return out


def _has_instant_actions(state: GameState) -> bool:
    """Whether any instant-speed play (beyond passing) is available now — used
    to decide if a non-main step is worth stopping at as a decision point."""
    return len(legal_actions(state, sorcery_speed_ok=False)) > 1


def _exile_play_actions(state: GameState, source_uid: int, card) -> list[Action]:
    from ..cards.base import CardAction

    impl = _impl(card)
    out: list[Action] = []
    # "Spells you cast from exile have convoke" (Hoarding Broodlord).
    convoke = any(p.impl.grants_exile_convoke for p in state.battlefield)

    def make_play(c):
        def fn(st: GameState):
            entry = next((e for e in st.exile_playable if e[0] == source_uid and e[1].name == c.name), None)
            if entry is None:
                return None
            if _impl(c).is_land:
                if st.lands_played_this_turn >= st.max_land_drops():
                    return None
                st.exile_playable.remove(entry)
                if c in st.exile:
                    st.exile.remove(c)
                st.lands_played_this_turn += 1
                st.note_event("play_land", c.name, card=c, is_land=True)
                perm = st.put_on_battlefield(c, fire_etb=False)
                perm.turn_flags["played_as_land"] = 1
                st.queue_entry_triggers([perm])
                st.emit(f"play {c.name} from exile")
                return None
            cvk = any(p.impl.grants_exile_convoke for p in st.battlefield)
            if not begin_cast(st, c, _impl(c).cast_cost(st), zone=_ExileZone(st, entry),
                              tag="from exile", convoke=cvk):
                return None
            if c.is_permanent:
                return resolve_to_battlefield(st, c) or None
            resolve_to_graveyard(st, c)
            return _impl(c).on_resolve(st) or None
        return fn

    affordable = (can_afford_with_convoke(state, impl.cast_cost(state)) if convoke
                  else can_afford(state, impl.cast_cost(state)))
    if impl.is_land:
        if state.lands_played_this_turn < 1:
            out.append(CardAction(f"play {card.name} from exile", make_play(card)))
    elif impl.is_castable(state) and affordable:
        out.append(CardAction(f"cast {card.name} from exile", make_play(card)))
    return out


class _ExileZone:
    """Adapter so begin_cast can 'remove' a card from the exile-playable list."""

    def __init__(self, state: GameState, entry) -> None:
        self.state, self.entry = state, entry

    def remove(self, card) -> None:
        self.state.exile_playable.remove(self.entry)
        if card in self.state.exile:
            self.state.exile.remove(card)


def _castable_faces(card) -> list[tuple[int, "object"]]:
    """The faces of `card` that could be cast (have a mana cost). Returns
    (face_index, face) pairs. A single-faced card is one face at index 0; a
    modal card contributes every face carrying a mana cost (a land face has no
    mana cost, so it is excluded — a land is played, not cast)."""
    faces = card.faces if len(card.faces) > 1 else []
    if not faces:
        return [(0, card)] if card.mana_cost else []
    out = []
    for i, face in enumerate(faces):
        if face.mana_cost:
            out.append((i, face))
    return out


def _face_instant_speed(card) -> bool:
    """Whether casting `card` (any of its castable faces) is instant-speed. A
    modal card is instant-speed only if the face being offered is an instant;
    we mark the whole airbend batch at instant speed when ANY castable face is
    an instant (the individual actions still resolve the specific face)."""
    for _, face in _castable_faces(card):
        tl = getattr(face, "type_line", "") or ""
        if "instant" in tl.split("—")[0].lower():
            return True
    return False


class _AirbendZone:
    """Adapter so begin_cast can 'remove' an airbended card from both the
    airbend-recast list and the exile zone."""

    def __init__(self, state: GameState, card) -> None:
        self.state, self.card = state, card

    def remove(self, card) -> None:
        if self.card in self.state.airbend_exile:
            self.state.airbend_exile.remove(self.card)
        if card in self.state.exile:
            self.state.exile.remove(card)


def _airbend_cast_actions(state: GameState, card) -> list[Action]:
    """Cast an airbended card for {2}: one action per castable face (a modal
    card offers each side that has a mana cost). Paying {2} replaces the face's
    normal cost; the chosen face then enters (permanent) or resolves
    (instant/sorcery)."""
    from ..cards.base import CardAction

    cost = ManaCost(generic=2)
    if not can_afford(state, cost):
        return []
    faces = _castable_faces(card)
    if not faces:
        return []
    multi = len(faces) > 1
    out: list[Action] = []

    def make(face_index: int, face_name: str):
        def fn(st: GameState):
            live = next((c for c in st.airbend_exile if c.name == card.name), None)
            if live is None:
                return None
            # Tag the on-stack face so the board viewer shows the side being cast
            # (a modal card's back face) rather than the default front. Set
            # BEFORE begin_cast, whose "cast … (on the stack)" frame reads it.
            if face_index >= 1 and len(live.faces) > 1:
                st.stack_face[id(live)] = face_index
            if not begin_cast(st, live, cost, zone=_AirbendZone(st, live),
                              tag="airbend, {2}"):
                st.stack_face.pop(id(live), None)
                return None
            # Enter as the chosen face for a permanent side; resolve otherwise.
            face = live.faces[face_index] if len(live.faces) > 1 else live
            tl = (getattr(face, "type_line", "") or live.type_line)
            is_perm_face = any(
                t in tl.split("—")[0].lower()
                for t in ("creature", "artifact", "enchantment",
                          "planeswalker", "battle", "land")
            )
            if is_perm_face:
                if live in st.stack:
                    st.stack.remove(live)
                st.stack_face.pop(id(live), None)  # off the stack now
                st.note_event("spell_resolved", live.name)
                st.resolving = ("spell", face_name)
                perm = st.put_on_battlefield(live, fire_etb=False)
                perm.transformed = face_index == 1
                st.emit(f"{face_name} resolves — enters the battlefield (airbended)")
                branches = perm.impl.enter_choices(st, perm)
                if branches is None:
                    st.queue_entry_triggers([perm])
                    return None
                for b in branches:
                    p2 = b.find_permanent(perm.uid)
                    if p2 is not None:
                        b.queue_entry_triggers([p2])
                return branches
            resolve_to_graveyard(st, live)
            st.stack_face.pop(id(live), None)  # off the stack now
            return _impl(live).on_resolve(st) or None
        return fn

    for face_index, face in faces:
        face_name = getattr(face, "name", None) or card.name
        suffix = f" ({face_name})" if multi else ""
        out.append(CardAction(
            f"cast {card.name}{suffix} from exile (airbend, {{2}})",
            make(face_index, face_name)))
    return out


# --------------------------------------------------------------------------
# Combat (goldfish-lite: attack a phantom opponent; no blockers)
# --------------------------------------------------------------------------
class DeclareAttackers(Action):
    """Attack with every creature able to attack. Subset attacks are not
    enumerated (all-or-nothing) to keep the search tractable."""

    label = "attack with all able creatures"

    def apply(self, state: GameState) -> None:
        # First DECLARE every attacker (tap them, mark them) so the replay shows a
        # single frame with ALL attackers — only THEN put the attack triggers on
        # the stack (otherwise the first attacker's trigger emits a frame before
        # the rest are declared, so attackers appear over two steps).
        declared: list[Permanent] = []
        for perm in state.battlefield:
            if not perm.is_creature_now or perm.tapped:
                continue
            if perm.summoning_sick and not state.has_keyword(perm, "Haste"):
                continue
            if state.has_keyword(perm, "Defender"):  # defenders can't attack
                continue
            state.attackers.append(perm.uid)
            perm.turn_flags["attacked"] = 1
            if not state.has_keyword(perm, "Vigilance"):
                perm.tapped = True
            declared.append(perm)
        if state.attackers:
            state.attacked_this_turn = True
            names = [p.name for p in state.battlefield if p.uid in state.attackers]
            state.emit(f"attack with {', '.join(names)}")
            # Now that all attackers are shown, put the per-attacker attack triggers
            # on the stack, then the player-level "whenever you attack" triggers
            # (Inti, Ellie), once each.
            for perm in declared:
                state.queue_attack_triggers(perm)
            you_attack: list = []
            for perm in list(state.battlefield):
                you_attack.extend(perm.impl.you_attack_stack_items(state, perm))
            state.push_triggered_abilities(you_attack)
        return state.settle()


def combat_actions(state: GameState) -> list[Action]:
    """The declare-attackers option: attack with all able creatures, if any can
    (passing/holding back is offered separately by the decision's PassPhase).
    Returns `[]` when no creature can attack."""
    if state.attackers:
        return []  # attackers already declared this combat (declared once)
    if any(p.impl.prevents_attacks for p in state.battlefield):
        return []  # Glacial Chasm: creatures you control can't attack
    able = [
        p for p in state.battlefield
        if p.is_creature_now and not p.tapped
        and (not p.summoning_sick or state.has_keyword(p, "Haste"))
        and not state.has_keyword(p, "Defender")  # defenders can't attack
    ]
    if not able:
        return []
    return [DeclareAttackers()]


def deal_combat_damage(state: GameState) -> None:
    """At the combat-damage step: attackers hit the phantom opponent. ALL
    damage is dealt and reported (life totals, lifelink) first; only then do
    the combat-damage triggers go on the stack and resolve."""
    total = 0
    hits: list[tuple[Permanent, int]] = []
    for uid in list(state.attackers):
        perm = state.find_permanent(uid)
        if perm is None:
            continue
        if state.prevent_all_combat_damage:  # Fog
            continue
        # Moonmist: this turn only Werewolves and Wolves deal combat damage
        # ("Werewolf" contains "wolf", so one subtype check covers both).
        if state.prevent_nonwolf_combat_damage and "wolf" not in perm.type_line.lower():
            continue
        dmg = max(0, state.effective_power(perm))
        # No blockers in a goldfish, so double strike is simply twice the damage
        # (first-strike + normal combat damage steps both connect).
        if state.has_keyword(perm, "Double strike"):
            dmg *= 2
        if dmg == 0:
            continue
        total += dmg
        state.opponent_life -= dmg
        if state.has_keyword(perm, "Lifelink"):
            state.life += dmg
        hits.append((perm, dmg))
    if total:
        state.emit(f"combat: {total} damage to opponent (opponent at {state.opponent_life})")
        state.check_life_totals()
    for perm, dmg in hits:
        state.queue_combat_damage_triggers(perm, dmg)
    # Do NOT settle here. The COMBAT_DAMAGE step in simulator._apply_step_entry
    # (this function's only caller) runs its final branch-capable state.settle(),
    # which resolves these queued triggers — so a combat-damage trigger MAY BRANCH
    # (Malcolm's discard choice / free cast) exactly like a phase-entry trigger.


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _impl(card):
    from ..cards import build_card

    return build_card(card)


def _find_in_zone(zone: list, name: str):
    for card in zone:
        if card.name == name:
            return card
    raise ValueError(f"{name!r} not found in zone")
