"""The documented `state` API that compiled property code runs against.

This string is injected into the LLM prompt AND surfaced in the UI so users
understand what their English can reference. It must stay in sync with the
query helpers on `engine.game_state.GameState`.
"""

STATE_API_DOC = """\
You are given a variable `state` describing the current game. Available API:

Counts / booleans:
  state.commander_in_play() -> bool          # a commander is on the battlefield
  state.lands_in_play() -> int
  state.creatures_in_play() -> int
  state.permanents_in_play() -> int
  state.cards_in_hand() -> int
  state.cards_in_graveyard() -> int
  state.has_permanent_named(name: str) -> bool   # case-insensitive
  state.count_on_battlefield(pred) -> int         # pred: fn(card_data) -> bool

Creature stats (on the battlefield):
  state.total_power() -> int
  state.total_toughness() -> int
  state.max_power() -> int
  state.max_toughness() -> int
  state.creatures_with_power_at_least(n: int) -> int

Per-turn tallies (reset each turn):
  state.spells_cast_this_turn -> int
  state.creature_spells_cast_this_turn -> int
  state.noncreature_spells_cast_this_turn -> int
  state.lands_played_this_turn -> int
  state.cards_drawn_this_turn -> int
  state.storm_count -> int

Game-long:
  state.cards_drawn -> int          # total cards drawn this game
  state.life -> int
  state.turn -> int

Zones (lists of names):
  state.hand_names() -> list[str]
  state.battlefield_names() -> list[str]
  state.graveyard_names() -> list[str]

Past states / per-turn history (describe what happened on EARLIER turns):
  state.turns_played() -> int                       # current turn number
  state.graveyard_added_on(turn: int) -> list[str]  # cards put in GY that turn
  state.permanents_entered_on(turn: int) -> list[str]  # permanents that entered
  state.creatures_entered_on(turn: int) -> list[str]   # creatures that entered
  state.lands_entered_on(turn: int) -> list[str]       # lands that entered
  state.each_turn(pred) -> bool   # pred(turn)->bool holds for EVERY turn 1..now
  state.some_turn(pred) -> bool   # pred(turn)->bool holds for at least one turn

Each card exposed to count_on_battlefield's predicate has: .name, .cmc,
.type_line, .is_land, .is_creature, .colors (list like ["R"]).

History examples:
  # "a card was put in the graveyard on each turn since the beginning"
  def check(state):
      return state.each_turn(lambda t: len(state.graveyard_added_on(t)) >= 1)
  # "a creature has entered the battlefield on every turn"
  def check(state):
      return state.each_turn(lambda t: len(state.creatures_entered_on(t)) >= 1)
"""
