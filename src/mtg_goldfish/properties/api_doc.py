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
  state.cards_in_hand() -> int
  state.has_permanent_named(name: str) -> bool   # case-insensitive
  state.count_on_battlefield(pred) -> int         # pred: fn(card_data) -> bool

Per-turn tallies (reset each turn):
  state.spells_cast_this_turn -> int
  state.creature_spells_cast_this_turn -> int
  state.noncreature_spells_cast_this_turn -> int
  state.lands_played_this_turn -> int
  state.storm_count -> int

Zones (lists of names):
  state.hand_names() -> list[str]
  state.battlefield_names() -> list[str]

Other:
  state.life -> int
  state.turn -> int

Each card exposed to count_on_battlefield's predicate has: .name, .cmc,
.type_line, .is_land, .is_creature, .colors (list like ["R"]).
"""
