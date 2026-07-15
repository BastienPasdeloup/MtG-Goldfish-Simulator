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

Permanent types and states (matched on the ACTIVE face, so a transformed /
flipped double-faced card matches its back face's name and types):
  state.count_permanents(type_contains=None, name_contains=None, tapped=None,
                         transformed=None, token=None, commander=None) -> int
  # string filters: case-insensitive substrings of the type line / name;
  # state filters: optional booleans. Examples:
  #   "a flipped Hero creature is in play"
  #       state.count_permanents(type_contains="Hero", transformed=True) >= 1
  #   "at least two untapped artifact tokens"
  #       state.count_permanents(type_contains="Artifact", token=True, tapped=False) >= 2

Ability / spell outcomes (game-long event history — every effect is recorded
with the spell or ability that CAUSED it, so properties can test what a
resolution actually did):
  state.commander_name() -> str            # the deck's commander (stable name)
  state.permanents_put_by(source: str, via_kind=None, land=None, creature=None,
                          token=None, turn=None) -> int
      # permanents put onto the battlefield by a resolving spell/ability of
      # `source` (name substring). via_kind narrows the cause:
      # "triggered" | "activated" | "spell" | "land_drop".
  state.cards_put_by(source: str, via_kind=None, turn=None) -> list[card]
      # the CARD OBJECTS put onto the battlefield by `source`'s resolving
      # spell/ability — test any characteristic (.type_line, .cmc, .faces,
      # .is_double_faced, .colors, ...)
  state.cards_drawn_by(source: str, turn=None) -> int
  state.ability_activated(source: str, turn=None) -> bool  # an activated ability
      # of a card whose name contains `source` was activated (optionally on `turn`)
  state.ability_succeeded(source: str, turn=None) -> bool  # ...and it achieved its
      # purpose (e.g. Nick Fury's power-up actually put a card onto the battlefield)
  state.played_on(name: str, turn=None) -> bool
      # a card named like `name` was played/cast during `turn` (None = any
      # turn): it entered the battlefield (tokens excluded) or its spell
      # resolved. Game-long history — usable at ANY later checkpoint. ALWAYS
      # use this for "X is/was played on turn N" when the property's trigger
      # moment is LATER than turn N (has_permanent_named + state.turn would
      # never match there).
  state.spell_resolved(name: str, turn=None) -> bool   # the spell resolved (not countered)
  state.trigger_resolved(source: str, turn=None) -> bool  # a triggered ability resolved
  Examples:
    # "the commander is in play, and its triggered ability has put at least
    #  2 lands into play"
    def check(state):
        return state.commander_in_play() and state.permanents_put_by(
            state.commander_name(), via_kind="triggered", land=True) >= 2
    # "Cultivate resolved and put 2 lands into play"
    def check(state):
        return state.permanents_put_by("Cultivate", via_kind="spell", land=True) >= 2
    # "the commander's activated ability is activated and finds a card to put
    #  into play" — ANY card counts; add characteristic filters ONLY when the
    # property explicitly asks for them
    def check(state):
        return len(state.cards_put_by(state.commander_name(), via_kind="activated")) >= 1
    # Same property PLUS "...and this card is double sided" (the is_double_faced
    # filter is used ONLY because the property explicitly requires it):
    def check(state):
        return any(c.is_double_faced for c in
                   state.cards_put_by(state.commander_name(), via_kind="activated"))
    # "Deadpool, Trading Card is played on turn 4" — with the property's own
    # trigger moment set LATER (e.g. at end_step of turn 6), so it must query
    # the game history, not the current board:
    def check(state):
        return state.played_on("Deadpool, Trading Card", 4)

Generic event access (to test ANYTHING that happened during the game):
  state.count_events(kind=None, name=None, via=None, via_kind=None,
                     turn=None, pred=None) -> int
  state.events_matching(...same filters...) -> list[dict]
  state.events -> the raw list. Each event is a dict with at least
      {"turn", "kind", "name", "via", "via_kind"} where via/via_kind identify
      the resolving spell or ability that caused it. Kinds:
      "enter_battlefield" / "leave_battlefield"  (+ is_land, is_creature,
          is_token; leave also has "to": "graveyard"|"exile"|"hand"|"none")
      "draw" (name = the card drawn)
      "activated", "trigger_resolved", "spell_resolved", "ability_success"
  Examples:
    # "at least two creatures died this game"
    def check(state):
        return state.count_events(kind="leave_battlefield",
            pred=lambda e: e.get("to") == "graveyard" and e.get("is_creature")) >= 2
    # "a fetch land found something on turn 1"
    def check(state):
        return state.count_events(kind="enter_battlefield", via_kind="triggered",
                                  turn=1, pred=lambda e: e.get("is_land")) >= 1

Raw objects (full flexibility — inspect any state detail directly):
  state.battlefield -> list of permanents: .name, .type_line (active face),
      .tapped, .transformed, .summoning_sick, .is_token, .is_commander,
      .is_land, .is_creature_now, .counters (dict, e.g. {"+1/+1": 2, "lore": 1}),
      .attached_to (host uid or None), .uid
  state.hand / state.graveyard / state.exile / state.library -> lists of cards
      (each with .name, .cmc, .type_line, .is_land, .is_creature, .colors,
       .is_double_faced, .faces, .oracle_text)

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
  state.energy -> int               # energy counters currently in the pool

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
