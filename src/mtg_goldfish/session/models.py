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


class SimResult(BaseModel):
    id: str
    created_at: str
    config: SimConfig
    # Snapshot of the properties checked in this run (for later review).
    properties: list[PropertySpec] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
    # A handful of successful lines of play (each a list of board-snapshot
    # frames) for graphical review.
    sample_success_logs: list[list[dict]] = Field(default_factory=list)


class Session(BaseModel):
    id: str
    name: str
    format_id: str = "duel_commander"
    created_at: str
    deck: Deck
    properties: list[PropertySpec] = Field(default_factory=list)
    mulligans: int = 0
    results: list[SimResult] = Field(default_factory=list)
