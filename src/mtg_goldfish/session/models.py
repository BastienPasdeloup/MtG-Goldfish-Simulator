"""Session and simulation-result models (persisted to disk as JSON)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..deck.models import Deck
from ..properties.models import PropertySpec


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
    # Fixed-hand mode: force this exact opening hand (card names); None = normal.
    fixed_hand: list[str] | None = None
    # Fixed-hand mode: pad the hand with random cards up to this size (None = no padding).
    fixed_hand_pad_to: int | None = None


class SimResult(BaseModel):
    id: str
    created_at: str
    config: SimConfig
    # "running" while the simulation is in progress (the entry is created as
    # soon as the run starts and updated as games finish), then "done" or
    # "stopped" (cancelled). Old files default to "done".
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
