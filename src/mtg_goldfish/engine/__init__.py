"""Simulation engine: game state, turn structure, actions, and the exhaustive
solitaire simulator."""
from .game_state import GameState, Permanent, new_game_from_deck
from .mana import ManaAbility, ManaCost, ManaPool
from .phases import MAIN_PHASES, TURN_ORDER, Phase, phase_labels
from .simulator import (
    CompiledProperty,
    GameOutcome,
    SimulationConfig,
    SimulationStats,
    run_simulation,
    simulate_game,
)

__all__ = [
    "GameState",
    "Permanent",
    "new_game_from_deck",
    "ManaAbility",
    "ManaCost",
    "ManaPool",
    "Phase",
    "TURN_ORDER",
    "MAIN_PHASES",
    "phase_labels",
    "CompiledProperty",
    "GameOutcome",
    "SimulationConfig",
    "SimulationStats",
    "run_simulation",
    "simulate_game",
]
