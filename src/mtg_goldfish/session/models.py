"""Session and simulation-result models (persisted to disk as JSON)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..deck.models import Deck
from ..properties.models import PropertySpec


class FixedBattlefieldCard(BaseModel):
    """A permanent placed on the battlefield in a Fixed-config run."""
    name: str
    tapped: bool = False
    # Counters to put on it, by kind (e.g. {"+1/+1": 2, "loyalty": 5}). These
    # OVERRIDE the permanent's natural enters-with counters for the kinds given.
    counters: dict[str, int] = Field(default_factory=dict)
    # Keywords granted until end of turn (lowercase, e.g. ["flying", "haste"]).
    granted: list[str] = Field(default_factory=list)


class FixedConfig(BaseModel):
    """A fully-specified starting game state for a Fixed-config run: the search
    begins from exactly this state (at `turn`/`phase`) instead of from an
    opening hand, and explores forward. The library is whatever deck cards are
    not placed in another zone (shuffled per game seed)."""
    battlefield: list[FixedBattlefieldCard] = Field(default_factory=list)
    hand: list[str] = Field(default_factory=list)
    graveyard: list[str] = Field(default_factory=list)
    exile: list[str] = Field(default_factory=list)
    life: int = 20
    opponent_life: int = 20
    # Mana currently in the pool, by colour symbol: W/U/B/R/G/C.
    mana_pool: dict[str, int] = Field(default_factory=dict)
    storm_count: int = 0
    turn: int = 1
    phase: str = "precombat_main"  # a Phase value (see engine.phases)


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
