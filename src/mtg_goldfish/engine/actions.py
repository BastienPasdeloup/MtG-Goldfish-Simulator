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
        for ability in perm.impl.mana_abilities_perm(state, perm):
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
) -> list[tuple[int, str]] | None:
    """Decide which sources to tap (and for which colour) to pay `cost`.

    Returns a list of (source_index, colour) or None if unaffordable. Greedy:
    cover coloured pips with the least-flexible, lowest-life-cost sources
    first, then top up generic. At most one ability per permanent."""
    pool = base_pool.copy()
    used_perms: set[int] = set()
    plan: list[tuple[int, str]] = []

    def candidates(pred) -> list[int]:
        return [
            i for i, (perm, ab) in enumerate(sources)
            if perm.uid not in used_perms and pred(ab)
        ]

    for color, need in cost.pip_map.items():
        while pool.amounts.get(color, 0) < need:
            cands = candidates(lambda ab: color in ab.choices)
            if not cands:
                return None
            cands.sort(key=lambda i: (sources[i][1].life_cost, len(sources[i][1].choices)))
            i = cands[0]
            used_perms.add(sources[i][0].uid)
            pool.add(color, sources[i][1].amount)
            plan.append((i, color))

    while not pool.can_pay(cost):
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
        pool.add(color, ability.amount)
        plan.append((i, color))

    return plan


def _pool_str(pool: ManaPool) -> str:
    parts = [f"{n}{c}" for c, n in pool.amounts.items() if n]
    return "{" + " ".join(parts) + "}" if parts else "{empty}"


def pay_cost(state: GameState, cost: ManaCost, extra_life: int = 0,
             exclude_uids: set[int] | None = None) -> bool:
    """Tap sources and spend `cost` (plus optional life). False if unaffordable.
    `exclude_uids` omits permanents from the payment (see available_mana_sources)."""
    if extra_life and state.life <= extra_life:
        return False
    sources = available_mana_sources(state, exclude_uids)
    plan = plan_payment(cost, sources, state.mana_pool)
    if plan is None:
        return False
    taps: list[str] = []
    for idx, color in plan:
        perm, ability = sources[idx]
        perm.tapped = True
        state.mana_pool.add(color, ability.amount)
        if ability.life_cost:
            state.life -= ability.life_cost
        perm.impl.on_tap_for_mana(state, perm, color)  # e.g. pain-land damage
        taps.append(f"{perm.name}→{color}")
    if taps:
        state.emit(f"tap for mana: {', '.join(taps)}  pool={_pool_str(state.mana_pool)}")
    ok = state.mana_pool.pay(cost)
    if extra_life:
        state.life -= extra_life
    return ok


def can_afford(state: GameState, cost: ManaCost, extra_life: int = 0,
               exclude_uids: set[int] | None = None) -> bool:
    if extra_life and state.life <= extra_life:
        return False
    return plan_payment(
        cost, available_mana_sources(state, exclude_uids), state.mana_pool
    ) is not None


# --------------------------------------------------------------------------
# Casting helpers (used by generic actions AND by card implementations)
# --------------------------------------------------------------------------
def begin_cast(
    state: GameState, card, cost: ManaCost, *,
    zone: list | None = None, extra_life: int = 0, tag: str = "",
) -> bool:
    """Pay the cost, move the card from `zone` (default: hand) to the stack,
    bump the cast counters, and fire cast triggers. Returns False if unpaid."""
    zone = state.hand if zone is None else zone
    if not pay_cost(state, cost, extra_life=extra_life):
        return False
    zone.remove(card)
    state.stack.append(card)
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
    state.note_event("cast", card.name, card=card,
                     is_creature=card.is_creature, is_land=card.is_land)
    state.emit(f"cast {card.name}{f' ({tag})' if tag else ''} (on the stack)")
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
    state.note_event("spell_resolved", card.name)
    # The spell's `on_resolve` effects run right after this; attribute them to
    # the spell ("Cultivate put 2 lands into play") until settle() clears it.
    state.resolving = ("spell", card.name)
    state.to_graveyard(card)
    state.emit(f"{card.name} resolves")


# --------------------------------------------------------------------------
# Generic actions
# --------------------------------------------------------------------------
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

    def __init__(self, card_name: str) -> None:
        self.card_name = card_name
        self.label = f"cast {card_name}"

    def apply(self, state: GameState):
        card = _find_in_zone(state.hand, self.card_name)
        impl = _impl(card)
        if not begin_cast(state, card, impl.cast_cost(state)):
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

        if impl.is_land and land_drop_ok:
            modes = impl.etb_modes(state)
            if modes:
                actions.extend(PlayLand(card.name, mode=m) for m in modes)
            else:
                actions.append(PlayLand(card.name))
        elif not impl.is_land:
            inst = _is_instant_speed(card)
            custom = impl.cast_actions(state)
            if custom is not None:
                actions.extend(_mark(list(custom), inst))
            elif impl.is_castable(state) and can_afford(state, impl.cast_cost(state)):
                actions.append(_mark([CastDefault(card.name)], inst)[0])
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
        if state.find_permanent(source_uid) is None:
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

    if not sorcery_speed_ok:
        actions = [a for a in actions if not a.sorcery_speed]
    actions.append(PassPhase())
    return actions


def _has_instant_actions(state: GameState) -> bool:
    """Whether any instant-speed play (beyond passing) is available now — used
    to decide if a non-main step is worth stopping at as a decision point."""
    return len(legal_actions(state, sorcery_speed_ok=False)) > 1


def _exile_play_actions(state: GameState, source_uid: int, card) -> list[Action]:
    from ..cards.base import CardAction

    impl = _impl(card)
    out: list[Action] = []

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
            if not begin_cast(st, c, _impl(c).cast_cost(st), zone=_ExileZone(st, entry), tag="from exile"):
                return None
            if c.is_permanent:
                return resolve_to_battlefield(st, c) or None
            resolve_to_graveyard(st, c)
            return _impl(c).on_resolve(st) or None
        return fn

    if impl.is_land:
        if state.lands_played_this_turn < 1:
            out.append(CardAction(f"play {card.name} from exile", make_play(card)))
    elif impl.is_castable(state) and can_afford(state, impl.cast_cost(state)):
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
        for perm in state.battlefield:
            if not perm.is_creature_now or perm.tapped:
                continue
            if perm.summoning_sick and not state.has_keyword(perm, "Haste"):
                continue
            state.attackers.append(perm.uid)
            perm.turn_flags["attacked"] = 1
            if not state.has_keyword(perm, "Vigilance"):
                perm.tapped = True
            state.queue_attack_triggers(perm)
        if state.attackers:
            state.attacked_this_turn = True
            names = [p.name for p in state.battlefield if p.uid in state.attackers]
            state.emit(f"attack with {', '.join(names)}")
            # Player-level "whenever you attack" triggers (Inti, Ellie), once each.
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
    for perm, dmg in hits:
        state.queue_combat_damage_triggers(perm, dmg)
    state.settle_nonbranching("combat damage triggers")


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
