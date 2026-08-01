"""Base class for runtime card behaviour.

A `Card` binds a `CardData` (static facts) to *behaviour* the engine can invoke.
Card implementations live one-per-file in this package and register themselves
with `@register` (see `registry.py`). Instances are cheap and hold no per-game
mutable state — that lives on the engine's `Permanent` objects.

The engine drives cards through hooks:

Casting / playing
  cast_cost(state)          -> ManaCost   (dynamic costs, e.g. domain reduction)
  is_castable(state)        -> bool       (target availability etc.)
  cast_actions(state)       -> [Action]   (override for targets / X / choices)
  hand_actions(state)       -> [Action]   (cycling, channel, MDFC land face...)
  graveyard_actions(state)  -> [Action]   (escape, bestow from graveyard...)
  etb_modes(state)          -> [dict]     (shocklands: pay-2/tapped choices)
  etb_tapped(state)         -> bool       (fastlands & friends)

On the battlefield
  mana_abilities(state) / mana_abilities_perm(state, perm)
  on_tap_for_mana(state, perm, color)     (pain lands)
  battlefield_actions(state, perm) -> [Action]   (fetches, equip, draw engines)
  on_etb / on_leave / on_phase / on_attack / on_combat_damage
  on_draw_card(state, perm, nth)          ("when you draw your Nth card...")
  on_cast_other(state, perm, card)        (cast triggers, e.g. Basim)
  on_equipped_died(state, perm)           (Skullclamp)
  dynamic_power/toughness, equip_mod      (characteristic-defining, equipment)

Hooks that make choices should NOT choose inside `apply`; instead enumerate one
`CardAction` per choice so the exhaustive search explores them all.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, ClassVar

from ..deck.models import CardData
from ..engine.mana import ManaAbility, ManaCost

if TYPE_CHECKING:  # avoid import cycles; these are engine runtime types
    from ..engine.game_state import GameState, Permanent


class CardAction:
    """A concrete choice offered to the search. `fn(state)` mutates the state
    in place, or returns a list of branch states for further sub-choices."""

    def __init__(
        self,
        label: str,
        fn: Callable,
        *,
        sorcery_speed: bool = True,
        pre_fn: Callable | None = None,
        source_name: str | None = None,
        ability_text: str | None = None,
    ) -> None:
        self.label = label
        self._fn = fn
        self.sorcery_speed = sorcery_speed
        self._pre_fn = pre_fn
        self._source_name = source_name
        self._ability_text = ability_text

    @classmethod
    def activated(
        cls,
        label: str,
        pre_fn: Callable,
        resolve_fn: Callable,
        *,
        sorcery_speed: bool = False,  # activated abilities are instant-speed by default
        source_name: str | None = None,
        ability_text: str | None = None,
    ) -> "CardAction":
        return cls(
            label,
            resolve_fn,
            sorcery_speed=sorcery_speed,
            pre_fn=pre_fn,
            source_name=source_name,
            ability_text=ability_text,
        )

    def apply(self, state: "GameState"):
        if self.label.startswith(("cast ", "play ", "play land ", "cast commander ")):
            return state.settle(self._fn(state))

        from ..engine.game_state import StackAbility
        if self._pre_fn is not None and not self._pre_fn(state):
            return None
        source_name = self._source_name or _stack_source_from_label(self.label)
        # Property-visible event: this card's activated ability was activated.
        state.note_event("activated", source_name, detail=self.label)

        def resolve(st):
            return self._fn(st)

        state.push_triggered_abilities([StackAbility(
            self.label,
            resolve,
            source_name=source_name,
            kind="activated",
            ability_text=self._ability_text or self.label,
        )])
        return state.settle()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CardAction {self.label!r}>"


class Card:
    #: Exact Scryfall card name this implementation handles.
    card_name: ClassVar[str] = ""
    #: Whether this card's rules are actually modelled. `False` for the
    #: automatic fallback used when a card has no implementation yet.
    implemented: ClassVar[bool] = True
    #: DFCs played as their BACK face (e.g. MDFC land backs) set this so the
    #: permanent is on the right face from the moment it enters — before any
    #: board frame is emitted.
    enters_transformed: ClassVar[bool] = False
    #: Static: while on the battlefield, land cards may be played from the
    #: graveyard (Icetill Explorer).
    grants_gy_land_plays: ClassVar[bool] = False
    #: Static: creatures can't attack (Glacial Chasm).
    prevents_attacks: ClassVar[bool] = False
    #: If set, `on_phase` only fires at this phase (avoids the base
    #: "fires every phase" behaviour — see phase_stack_items). Cards that must
    #: react to several phases leave this None and gate inside on_phase.
    trigger_phase: ClassVar = None

    def __init__(self, data: CardData) -> None:
        self.data = data

    # ---- static facts (delegated to CardData) ------------------------------
    @property
    def name(self) -> str:
        return self.data.name

    @property
    def mana_cost(self) -> ManaCost:
        return ManaCost.parse(self.data.mana_cost)

    @property
    def is_land(self) -> bool:
        return self.data.is_land

    @property
    def is_permanent(self) -> bool:
        return self.data.is_permanent

    @property
    def is_creature(self) -> bool:
        return self.data.is_creature

    # ---- casting / playing ---------------------------------------------------
    def cast_cost(self, state: "GameState") -> ManaCost:
        return self.mana_cost

    def is_castable(self, state: "GameState") -> bool:
        """Whether this spell can legally be cast right now (beyond mana).

        Default: yes. Cards with real targeting constraints (e.g. counterspells,
        which target a spell — including one of your own — via `counterspell`)
        express those by overriding `cast_actions` to enumerate only legal
        casts, returning an empty list when none exist."""
        return True

    def cast_actions(self, state: "GameState") -> list["CardAction"] | None:
        """Return the cast choices for this card from hand. `None` means "use
        the engine's default single cast" (pay cost, resolve, permanents enter,
        others go to the graveyard). Override to enumerate targets/X/modes."""
        return None

    def hand_actions(self, state: "GameState") -> list["CardAction"]:
        """Extra non-cast plays from hand (cycling, channel, MDFC back face)."""
        return []

    def graveyard_actions(self, state: "GameState") -> list["CardAction"]:
        """Plays from the graveyard (escape, bestow from graveyard, ...)."""
        return []

    def etb_modes(self, state: "GameState") -> list[dict] | None:
        """Choice of how a land/permanent enters. Each mode is a dict:
        {"label": str, "tapped": bool, "life": int, "choice": any}.
        `None` = single default mode (etb_tapped decides tapped)."""
        return None

    def on_enter_choice(self, state: "GameState", perm: "Permanent") -> None:
        """Apply an "as it enters" replacement that depends on the entering
        mode/choice (`perm.chosen`), e.g. Vesuva entering as a copy of a land.

        Runs the instant the permanent enters — after the `etb_modes` choice is
        settled, before the entry frame and any ETB triggers — so it is NOT an
        ability on the stack. Each choice is already its own `etb_modes` branch,
        so this never needs to branch itself."""

    def enter_choices(self, state: "GameState", perm: "Permanent") -> list["GameState"] | None:
        """"As it enters" choices that FAN OUT into branches (e.g. Deadpool
        exchanging text boxes with up to one creature). Called the moment the
        permanent enters, BEFORE its ETB triggers are queued — the choice is
        part of entering, never an ability on the stack, and the queued ETBs
        reflect the applied choice. Return the branch states (each with the
        choice already applied), or None when there is nothing to choose."""
        return None

    def enters_with_counters(self, state: "GameState") -> dict[str, int]:
        """Counters this permanent enters the battlefield with ("enters with
        two depletion counters", loyalty, fading/vanishing...). This is a
        REPLACEMENT effect: the counters are on the permanent from the moment
        it enters — it never goes on the stack and no trigger fires."""
        return {}

    def etb_tapped(self, state: "GameState") -> bool:
        text = self.data.oracle_text.lower()
        # Look sentence by sentence: a card enters tapped only if IT is the
        # subject of an "enters ... tapped" clause. Triggered abilities such as
        # Amulet of Vigor's "whenever a permanent you control enters tapped,
        # untap it" mention the phrase but refer to OTHER permanents.
        # Split on newlines FIRST (then periods): a leading keyword line such as
        # "Trample" must not be glued to the next sentence — otherwise
        # "Trample\nWhenever ~ enters ... put them onto the battlefield tapped"
        # would read as this permanent entering tapped (Primeval Titan bug).
        sentences: list[str] = []
        for line in text.split("\n"):
            sentences.extend(line.split("."))
        for sentence in sentences:
            s = sentence.strip()
            if "enters" not in s or "tapped" not in s:
                continue
            if s.startswith(("when", "whenever")):  # triggered ability, not self
                continue
            head = s.split("enters", 1)[0]
            # A "when/whenever ... enters" trigger anywhere in this clause refers
            # to an EVENT; any "tapped" belongs to what the trigger does (e.g.
            # Primeval Titan puts fetched lands tapped), not to THIS permanent.
            if "when" in head:  # matches "when" and "whenever"
                continue
            # Another permanent is the subject ("a land you control enters...").
            if any(k in head for k in (
                "you control", "another", "each ", "a land", "a creature",
                "a permanent", "permanents", "they ", "one or more",
            )):
                continue
            # "unless"-style lands resolve their condition via etb_modes/overrides.
            if "unless" in s or "you may pay" in s:
                return False
            return True
        return False

    # ---- battlefield ----------------------------------------------------------
    def mana_abilities(self, state: "GameState") -> list[ManaAbility]:
        """Mana this card can produce while on the battlefield (untapped)."""
        return []

    def mana_abilities_perm(self, state: "GameState", perm: "Permanent") -> list[ManaAbility]:
        """Per-permanent variant (chosen-type lands etc.). Defaults to the
        permanent-agnostic list."""
        return self.mana_abilities(state)

    def on_tap_for_mana(self, state: "GameState", permanent: "Permanent", color: str) -> None:
        """Called when this permanent is tapped for mana (e.g. pain lands)."""

    def battlefield_actions(self, state: "GameState", perm: "Permanent") -> list["CardAction"]:
        """Non-mana activated abilities (fetch, equip, draw engines, ...)."""
        return []

    def stack_response_actions(self, state: "GameState", perm: "Permanent") -> list:
        """Instant-speed responses this permanent can make to the ability on top
        of the stack — copying it, countering it — BEFORE it resolves. Returns a
        list of `StackResponse` (see game_state). Offered only in the priority
        window opened while a triggered/activated ability waits to resolve, and
        only under instant-speed exploration. Default: no response."""
        return []

    def alt_cast_actions(self, state: "GameState", perm: "Permanent") -> list["CardAction"]:
        """Alternative ways to cast OTHER cards granted by this permanent while
        it is on the battlefield — a static that changes how spells may be cast
        (Dream Halls: discard a card that shares a color with a spell instead of
        paying its mana cost). Called once per battlefield permanent in
        `legal_actions`; each returned CardAction sets its own `sorcery_speed`."""
        return []

    # ---- triggers -------------------------------------------------------------
    def on_etb(self, state: "GameState", permanent: "Permanent") -> None:
        """Called when this card enters the battlefield."""

    def on_leave(self, state: "GameState", permanent: "Permanent") -> None:
        """Called when this permanent leaves the battlefield."""

    def on_resolve(self, state: "GameState") -> None:
        """Called when a non-permanent spell (instant/sorcery) resolves."""

    def on_phase(self, state: "GameState", perm: "Permanent", phase) -> None:
        """Called at the beginning of each phase while on the battlefield
        (upkeep triggers, fading, ...)."""

    def on_attack(self, state: "GameState", perm: "Permanent") -> None:
        """Called when this permanent is declared as an attacker."""

    def on_combat_damage(self, state: "GameState", perm: "Permanent", damage: int) -> None:
        """Called when this permanent deals combat damage to the opponent."""

    def on_you_attack(self, state: "GameState", perm: "Permanent") -> None:
        """Called ONCE (while on the battlefield) when you declare one or more
        attackers — the player-level "whenever you attack" triggers (Inti,
        Ellie Brick Master). Distinct from `on_attack`, which fires per
        attacking creature."""

    def on_draw_card(self, state: "GameState", perm: "Permanent", nth_this_turn: int) -> None:
        """Called (while on the battlefield) after the player draws a card."""

    def on_cast_other(self, state: "GameState", perm: "Permanent", card: CardData) -> None:
        """Called (while on the battlefield) when the player casts any spell."""

    def on_you_discard(self, state: "GameState", perm: "Permanent", count: int) -> None:
        """Called (while on the battlefield) when you discard one or more cards
        (Inti's impulse draw). Fired once per discard event via GameState.discard."""

    def on_other_etb_immediate(self, state: "GameState", perm: "Permanent", entering: "Permanent") -> None:
        """Immediate non-stack entry effects for static/replacement approximations."""

    def on_other_etb(self, state: "GameState", perm: "Permanent", entering: "Permanent") -> None:
        """Called (while on the battlefield) when ANOTHER permanent enters —
        landfall, 'whenever a permanent enters tapped' (Amulet of Vigor),
        artifact triggers (Tezzeret)... Fired after the entering permanent's
        tapped state is settled, before its own on_etb."""

    def on_other_leave(
        self, state: "GameState", perm: "Permanent", left: "Permanent",
        to: str, reason: str | None,
    ) -> None:
        """Called (while on the battlefield) when ANOTHER permanent leaves the
        battlefield — the death/sacrifice watchers of aristocrats effects
        (Vraan, Sephiroth, Marionette Apprentice, Juri...). `left` is a snapshot
        of the permanent that left (its final characteristics), `to` is the
        destination zone ("graveyard"/"exile"/"hand"/...) and `reason` is why it
        left ("dies"/"sacrifice"/"destroy"/None). "Dies" = put into a graveyard
        from the battlefield (to == "graveyard")."""

    def stack_ability(
        self,
        *,
        source_name: str,
        label: str,
        resolve: Callable,
        kind: str = "triggered",
        trigger_text: str | None = None,
        ability_text: str | None = None,
    ):
        from ..engine.game_state import StackAbility

        return StackAbility(
            label,
            resolve,
            source_name=source_name,
            kind=kind,
            trigger_text=trigger_text,
            ability_text=ability_text,
        )

    def etb_stack_items(self, state: "GameState", permanent: "Permanent") -> list:
        if type(self).on_etb is Card.on_etb:
            return []
        # Implemented DFC ETBs belong to the FRONT face: a permanent that is
        # already on its back face when it enters (Deadpool copying a flipped
        # card, an MDFC played as its land back) must not fire them. (A DFC
        # that enters front-faced and transforms during the same resolution —
        # Nick Fury's power-up — queues here BEFORE transforming, so its front
        # ETB still resolves.)
        if permanent.transformed and len(self.data.faces) > 1:
            return []

        def resolve(st, uid=permanent.uid):
            perm = st.find_permanent(uid)
            if perm is None:
                return None
            return perm.impl.on_etb(st, perm)

        return [self.stack_ability(
            source_name=permanent.name,
            label=f"{permanent.name}: ETB",
            resolve=resolve,
            trigger_text=f"{permanent.name} entered the battlefield",
            ability_text="Enter-the-battlefield ability",
        )]

    def leave_stack_items(self, state: "GameState", permanent: "Permanent") -> list:
        if type(self).on_leave is Card.on_leave:
            return []

        snapshot = permanent.clone()

        def resolve(st, snap=snapshot):
            return snap.impl.on_leave(st, snap)

        return [self.stack_ability(
            source_name=permanent.name,
            label=f"{permanent.name}: leaves the battlefield",
            resolve=resolve,
            trigger_text=f"{permanent.name} left the battlefield",
            ability_text="Leaves-the-battlefield ability",
        )]

    def phase_stack_items(self, state: "GameState", perm: "Permanent", phase) -> list:
        if type(self).on_phase is Card.on_phase:
            return []
        if self.trigger_phase is not None and phase != self.trigger_phase:
            return []

        def resolve(st, uid=perm.uid, phase_now=phase):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, phase_now)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: {phase.value} trigger",
            resolve=resolve,
            trigger_text=f"Beginning of {phase.value.replace('_', ' ')}",
            ability_text=f"{phase.value.replace('_', ' ')} triggered ability",
        )]

    def attack_stack_items(self, state: "GameState", perm: "Permanent") -> list:
        if type(self).on_attack is Card.on_attack:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_attack(st, live)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: attack trigger",
            resolve=resolve,
            trigger_text=f"{perm.name} attacked",
            ability_text="Attack-triggered ability",
        )]

    def you_attack_stack_items(self, state: "GameState", perm: "Permanent") -> list:
        if type(self).on_you_attack is Card.on_you_attack:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_you_attack(st, live)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: you attacked",
            resolve=resolve,
            trigger_text="You attacked with one or more creatures",
            ability_text="Attack-triggered ability",
        )]

    def combat_damage_stack_items(self, state: "GameState", perm: "Permanent", damage: int) -> list:
        if type(self).on_combat_damage is Card.on_combat_damage:
            return []

        def resolve(st, uid=perm.uid, dealt=damage):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_combat_damage(st, live, dealt)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: combat damage trigger",
            resolve=resolve,
            trigger_text=f"{perm.name} dealt combat damage",
            ability_text="Combat-damage triggered ability",
        )]

    def draw_stack_items(self, state: "GameState", perm: "Permanent", nth_this_turn: int) -> list:
        if type(self).on_draw_card is Card.on_draw_card:
            return []

        def resolve(st, uid=perm.uid, nth=nth_this_turn):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_draw_card(st, live, nth)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: draw trigger",
            resolve=resolve,
            trigger_text=f"A player drew card #{nth_this_turn} this turn",
            ability_text="Draw-triggered ability",
        )]

    def discard_stack_items(self, state: "GameState", perm: "Permanent", count: int) -> list:
        if type(self).on_you_discard is Card.on_you_discard:
            return []

        def resolve(st, uid=perm.uid, n=count):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_you_discard(st, live, n)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: you discarded",
            resolve=resolve,
            trigger_text="You discarded one or more cards",
            ability_text="Discard-triggered ability",
        )]

    def cast_other_stack_items(self, state: "GameState", perm: "Permanent", card: CardData) -> list:
        if type(self).on_cast_other is Card.on_cast_other:
            return []

        def resolve(st, uid=perm.uid, cast_card=card):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_cast_other(st, live, cast_card)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: cast trigger for {card.name}",
            resolve=resolve,
            trigger_text=f"{card.name} was cast",
            ability_text="Cast-triggered ability",
        )]

    def other_etb_stack_items(self, state: "GameState", perm: "Permanent", entering: "Permanent") -> list:
        if type(self).on_other_etb is Card.on_other_etb:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: {entering.name} trigger",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Triggered ability",
        )]

    def other_leave_stack_items(
        self, state: "GameState", perm: "Permanent", left: "Permanent",
        to: str, reason: str | None,
    ) -> list:
        if type(self).on_other_leave is Card.on_other_leave:
            return []

        # `left` is already off the battlefield — pass the snapshot straight
        # through (there is nothing to re-find).
        def resolve(st, uid=perm.uid, snap=left, dest=to, why=reason):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_other_leave(st, live, snap, dest, why)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: {left.name} left ({reason or to})",
            resolve=resolve,
            trigger_text=f"{left.name} left the battlefield",
            ability_text="Triggered ability",
        )]

    def extra_land_drops(self, state: "GameState", perm: "Permanent") -> int:
        """Additional land plays per turn granted while on the battlefield
        (Exploration, Icetill Explorer)."""
        return 0

    def attached_mana_amount_bonus(self, state: "GameState", perm: "Permanent",
                                   host: "Permanent") -> int:
        """For Auras attached to a land: extra mana added whenever the host is
        tapped for mana (Wild Growth, Utopia Sprawl). Planner-visible."""
        return 0

    def on_equipped_died(self, state: "GameState", perm: "Permanent") -> None:
        """Called when the creature this equipment was attached to dies."""

    def equipped_died_stack_items(self, state: "GameState", perm: "Permanent") -> list:
        if type(self).on_equipped_died is Card.on_equipped_died:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_equipped_died(st, live)

        return [self.stack_ability(
            source_name=perm.name,
            label=f"{perm.name}: equipped creature died",
            resolve=resolve,
            trigger_text="Equipped creature died",
            ability_text="Equipment death trigger",
        )]

    # ---- characteristics --------------------------------------------------------
    def dynamic_power(self, state: "GameState", perm: "Permanent") -> int | None:
        """Characteristic-defining power (Barrowgoyf); None = printed value."""
        return None

    def dynamic_toughness(self, state: "GameState", perm: "Permanent") -> int | None:
        return None

    def equip_mod(self, state: "GameState", perm: "Permanent") -> tuple[int, int]:
        """(power, toughness) bonus granted to the equipped creature."""
        return (0, 0)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__} {self.name!r}>"


class UnimplementedCard(Card):
    """Fallback for cards with no dedicated implementation.

    The UI renders it in red and offers to auto-implement it. For simulation it
    is treated as a **vanilla approximation** so the goldfish still does
    something useful: it can be cast/played, permanents enter the battlefield
    and count toward board state and spell tallies, but any special text is
    ignored. Unimplemented *lands* tap for one mana of any colour in the
    commander's colour identity (an optimistic default for Commander mana
    bases). Results involving unimplemented cards are therefore approximate.
    """

    implemented = False

    def mana_abilities(self, state: "GameState") -> list[ManaAbility]:
        if not self.is_land:
            return []
        identity = tuple(getattr(state, "commander_color_identity", ())) or (
            "W", "U", "B", "R", "G",
        )
        return [ManaAbility(amount=1, choices=identity)]


def _stack_source_from_label(label: str) -> str:
    if ":" in label:
        return label.split(":", 1)[0].strip()
    if label.startswith("equip "):
        return label[len("equip "):].split(" →", 1)[0].strip()
    if label.startswith("channel "):
        rest = label[len("channel "):]
        return rest.split(":", 1)[0].strip()
    return label
