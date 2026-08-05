"""Session and simulation-result models (persisted to disk as JSON)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..deck.models import Deck
from ..properties.models import PropertySpec


class FixedBattlefieldCard(BaseModel):
    """A permanent placed on the battlefield in a Fixed-config run."""
    name: str
    tapped: bool = False
    # Arrived this turn — summoning-sick (can't attack/tap for abilities yet).
    sick: bool = False
    # Counters to put on it, by kind (e.g. {"+1/+1": 2, "loyalty": 5}). These
    # OVERRIDE the permanent's natural enters-with counters for the kinds given.
    counters: dict[str, int] = Field(default_factory=dict)
    # Keywords granted permanently (lowercase, e.g. ["flying", "haste"]).
    granted: list[str] = Field(default_factory=list)
    # Keywords granted only until end of turn (lowercase).
    granted_eot: list[str] = Field(default_factory=list)
    # Keywords REMOVED from the card (editor unchecks a printed keyword):
    # permanently, or only until end of turn.
    removed_keywords: list[str] = Field(default_factory=list)
    removed_keywords_eot: list[str] = Field(default_factory=list)
    # For a double-faced card: True = on its back face.
    transformed: bool = False
    # A token (not a deck card): created via make_token with these characteristics.
    token: bool = False
    power: int | None = None
    toughness: int | None = None
    type_line: str = ""
    text: str = ""
    colors: list[str] = Field(default_factory=list)  # token colour (W/U/B/R/G)
    # Attacking this turn (honoured only in a combat phase).
    attacking: bool = False
    # Index (within `battlefield`) of the permanent this one is attached to
    # (auras enchanting / equipment equipping it); None = unattached.
    attached_to: int | None = None
    # A COPY token: the name of the card it copies. The remaining fields carry
    # that card's data so the engine rebuilds a faithful token copy (picking up
    # the card's implementation by name).
    copy_of: str | None = None
    # An ARBITRARY card added into play (not from the deck; may be a nonpermanent
    # placed for sandbox testing). Its data is carried in the fields below.
    added: bool = False
    oracle_text: str = ""
    mana_cost: str = ""
    cmc: float = 0
    keywords: list[str] = Field(default_factory=list)
    # An explicit P/T override, and/or turning a noncreature permanent into a
    # creature (editor: "Make a creature" / "Set power/toughness").
    set_power: int | None = None
    set_toughness: int | None = None
    make_creature: bool = False
    # A colour override (editor "Set color"): W/U/B/R/G list, [] = colourless,
    # None = the card's printed colours. (For tokens / added cards the colour
    # lives in `colors` instead — those are built from the spec.)
    set_colors: list[str] | None = None
    # A creature-TYPE (subtype) override (editor "Alter card > Set creature
    # types"): the words RIGHT of the "—" (e.g. ["Zombie", "Wizard"]).
    set_creature_types: list[str] | None = None
    # Face-down: how it was turned face down (manifest / morph / disguise / cloak
    # / a plain 2/2), which sets its characteristics. Empty = not face down.
    face_down: str = ""
    # Per-entry "until end of turn" flags for the Alter-card changes.
    set_power_eot: bool = False
    set_toughness_eot: bool = False
    make_creature_eot: bool = False
    set_creature_types_eot: bool = False
    set_colors_eot: bool = False


class FixedExileCard(BaseModel):
    """An exiled card that was exiled WITH a battlefield permanent (by name), so
    the engine sets it up in that permanent's mechanism (playable from exile /
    recorded in its exiled_with). If `added` (the card is not in the deck — e.g.
    a creature copied by Superior Spider-Man that came from an opponent's
    graveyard), its data is carried in the fields below."""
    name: str
    exiled_with: str | None = None
    added: bool = False
    type_line: str = ""
    power: int | None = None
    toughness: int | None = None
    colors: list[str] = Field(default_factory=list)
    oracle_text: str = ""
    mana_cost: str = ""
    cmc: float = 0
    keywords: list[str] = Field(default_factory=list)


class FixedConfig(BaseModel):
    """A fully-specified starting game state for a Fixed-config run: the search
    begins from exactly this state (at `turn`/`phase`) instead of from an
    opening hand, and explores forward. The library is whatever deck cards are
    not placed in another zone (shuffled per game seed)."""
    battlefield: list[FixedBattlefieldCard] = Field(default_factory=list)
    hand: list[str] = Field(default_factory=list)
    graveyard: list[str] = Field(default_factory=list)
    # Each exile entry is either a bare card name or {name, exiled_with}.
    exile: list[str | FixedExileCard] = Field(default_factory=list)
    # Explicit top of the library (in order, top first). The remaining deck
    # cards are shuffled in below.
    library: list[str] = Field(default_factory=list)
    life: int = 20
    opponent_life: int = 20
    # Mana currently in the pool, by colour symbol: W/U/B/R/G/C.
    mana_pool: dict[str, int] = Field(default_factory=dict)
    storm_count: int = 0
    energy: int = 0
    turn: int = 1
    phase: str = "precombat_main"  # a Phase value (see engine.phases)
    # Commander tax: times each commander has already been cast this game
    # ({name: count}); the recast tax is {2}×count.
    commander_cast: dict[str, int] = Field(default_factory=dict)
    # Commanders removed from every zone (shuffled into the library at game start).
    commander_removed: list[str] = Field(default_factory=list)


class SimConfig(BaseModel):
    num_games: int = 100
    timeout_per_game_s: float = 5.0
    mulligans: int = 0
    on_the_play: bool = True
    base_seed: int = 12345
    search_mode: str = "best_first"  # see engine.simulator.SEARCH_MODES
    # Explore instant-speed plays (instants/flash/abilities in non-main steps,
    # and countering your own spells). Off by default — much larger search.
    instant_speed: bool = False
    # Fake shuffling: "shuffles" never really reorder the library — only the
    # cards whose position the player knows are reinserted at random spots, so
    # the library stays near-constant across all lines of play.
    fake_shuffle: bool = False
    # Spread each game's tree search across CPU cores. On by default; turn off to
    # run single-threaded (parallel_workers=1) — easier to profile / reproduce.
    parallel: bool = True
    # Record the explored-states tree (for the tree viz). Off = smaller saved
    # sessions + a little faster; replays are unaffected.
    save_tree: bool = True
    # Fixed-hand mode: force this exact opening hand (card names); None = normal.
    fixed_hand: list[str] | None = None
    # Fixed-hand mode: pad the hand with random cards up to this size (None = no padding).
    fixed_hand_pad_to: int | None = None
    # Fixed-config mode: a fully-specified starting state; None = normal.
    fixed_config: FixedConfig | None = None


class SimResult(BaseModel):
    id: str
    created_at: str
    config: SimConfig
    # "running" while the simulation is in progress (the entry is created as
    # soon as the run starts and updated as games finish), then "done" or
    # "stopped" (cancelled), or "interrupted" (the app died mid-run; the games
    # persisted so far are kept, and the run can be resumed). Old files
    # default to "done".
    status: str = "done"
    # Snapshot of the properties checked in this run (for later review).
    properties: list[PropertySpec] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
    # A handful of successful lines of play (each a list of board-snapshot
    # frames) for graphical review. Retained for backward compatibility; new
    # runs populate `sample_runs`, which carries the same frames plus the
    # opening hand, search-shape counts and the explored-states tree.
    sample_success_logs: list[list[dict]] = Field(default_factory=list)
    # One entry per game: {game_index, success, timed_out, hand,
    # branches_explored, branches_considered, tree_gz (gzip+base64 search tree
    # with per-node board snapshots), tree_truncated, log(frames, successes
    # only)}.
    sample_runs: list[dict] = Field(default_factory=list)


class Session(BaseModel):
    id: str
    name: str
    format_id: str = "duel_commander"
    created_at: str
    deck: Deck
    properties: list[PropertySpec] = Field(default_factory=list)
    mulligans: int = 0
    results: list[SimResult] = Field(default_factory=list)
