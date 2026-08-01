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
  # state filters: optional booleans. "flipped" / "transformed" / "on its back
  # side (or face)" all mean a double-faced permanent currently on its BACK
  # face -> transformed=True. Examples:
  #   "there is a flipped creature in play"
  #       state.count_permanents(type_contains="Creature", transformed=True) >= 1
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
      # .is_double_faced, .colors, ...). For a COUNT ("put at least one card"),
      # prefer permanents_put_by(...) >= N; cards_put_by(...) also compares by
      # length so cards_put_by(...) >= N works too.
  state.cards_drawn_by(source: str, turn=None) -> int
  state.cards_put_in_hand_by(source: str, via_kind=None, turn=None,
                             min_turn=None, max_turn=None) -> list[card]
      # the CARD OBJECTS a resolving spell/ability of `source` PUT INTO YOUR
      # HAND without drawing them — Atraxa's reveal-and-put-into-hand, a
      # tutor-to-hand, "return to hand", etc. NOT drawing, NOT the current hand
      # size. Compares by length, so cards_put_in_hand_by(...) >= N works.
      # "Atraxa's ETB put at least 3 cards into your hand" ->
      #   state.cards_put_in_hand_by(state.commander_name(), via_kind="triggered") >= 3
  state.ability_activated(source: str, turn=None) -> bool  # an activated ability
      # of a card whose name contains `source` was activated (optionally on `turn`)
  state.ability_succeeded(source: str, turn=None) -> bool  # ...and it achieved its
      # purpose (e.g. Nick Fury's power-up actually put a card onto the battlefield)
  state.ability_copied(source=None, by=None, target_kind=None, turn=None) -> int
      # how many times an ability was COPIED (e.g. Peter Parker's Camera copying
      # a trigger). `source` = the COPIED ability's source (the card whose
      # trigger/ability was copied, e.g. "Atraxa, Grand Unifier"); `by` = the
      # copier's name; `target_kind` = "triggered" | "activated". Compares by
      # count, so `>= 1` means "was copied at all". "Peter Parker's Camera is
      # activated and copies Atraxa's TRIGGERED ability" -> ability_copied(
      #   "Atraxa, Grand Unifier", by="Peter Parker's Camera", target_kind="triggered") >= 1

  ==== "played/cast" vs "entered the battlefield" — THESE ARE DIFFERENT ====
  Playing/casting is an ACTION the player takes. Entering the battlefield is
  what happens to a permanent — however it got there. They often coincide but
  NOT always: a land you FETCH enters the battlefield but was never "played";
  a creature you REANIMATE, or a TOKEN, enters but was never "cast"; a spell
  that is COUNTERED was cast but never enters. Choose the helper that matches
  the ENGLISH wording: "plays/casts X" -> played_on / cast_on; "X enters / comes
  into play / is put onto the battlefield" -> entered_battlefield.
  state.played_on(name, turn=None, min_turn=None, max_turn=None) -> bool
      # the player PLAYED or CAST a card named like `name` — cast a spell OR
      # played a land (a land drop). The act of playing, NOT entering play.
  state.cast_on(name, turn=None, min_turn=None, max_turn=None) -> bool
      # a SPELL named like `name` was CAST (put on the stack), even if later
      # countered. Lands are played, not cast — use played_on for lands.
  state.entered_battlefield(name, turn=None, min_turn=None, max_turn=None,
                            token=None, via_kind=None) -> bool
      # a permanent named like `name` ENTERED the battlefield, however it got
      # there. token= filters token/non-token; via_kind= narrows the cause
      # ("spell"|"land_drop"|"triggered"|"activated").
      # All three take an exact `turn` OR an INCLUSIVE min_turn/max_turn range
      # and read game-long history (usable at ANY later checkpoint — ALWAYS use
      # these for "X was played/entered on/before/between turn(s) ..." when the
      # property's trigger moment is LATER; has_permanent_named + state.turn
      # would never match there). Examples:
      #   "cast on turn 4"                     -> cast_on(name, 4)
      #   "played before turn 4"               -> played_on(name, max_turn=3)
      #   "entered play between turns 2 and 4" -> entered_battlefield(name, min_turn=2, max_turn=4)
  state.spell_resolved(name: str, turn=None) -> bool   # cast AND resolved (not countered)
  state.trigger_resolved(source: str, turn=None) -> bool  # a triggered ability resolved

  ==== the commander leaving play / the command zone ====
  In commander formats, when a commander LEAVES the battlefield (dies, is
  exiled, bounced...) its owner MAY return it to the command zone. The
  simulator explores BOTH: on one line it stays where it went, on another it is
  returned to the command zone (having briefly passed through the zone it left
  to, so leave/dies triggers still saw it there).
  state.commander_left_play(turn=None, min_turn=None, max_turn=None) -> bool
      # a commander left the battlefield (to ANY zone), on/within the turn(s)
  state.commander_returned_to_command_zone(turn=None, min_turn=None, max_turn=None) -> bool
      # a commander left play AND was returned to the command zone
  Examples:
    # "the commander leaves play and returns to the command zone"
    def check(state):
        return state.commander_returned_to_command_zone()
    # "the commander dies (or otherwise leaves the battlefield) by turn 5"
    def check(state):
        return state.commander_left_play(max_turn=5)
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
    # "Emperor of Bones uses its adapt ability, which puts a creature into play"
    # — ONE assertion binds BOTH halves: an ACTIVATED ability of that card (its
    # adapt) put a CREATURE onto the battlefield when it resolved. Do NOT split
    # it into ability_activated(...) AND a separate creatures_in_play() check —
    # that would pass even if some OTHER creature entered; the point is that THIS
    # ability is what put the creature into play. Use permanents_put_by with
    # via_kind="activated" (or cards_put_by, to test the creature's traits):
    def check(state):
        return state.permanents_put_by(
            "Emperor of Bones", via_kind="activated", creature=True) >= 1
    # "Deadpool, Trading Card is played on turn 4" — with the property's own
    # trigger moment set LATER (e.g. at end_step of turn 6), so it must query
    # the game history, not the current board:
    def check(state):
        return state.played_on("Deadpool, Trading Card", 4)
    # "a land entered the battlefield on turn 1 WITHOUT being played" (e.g. a
    # fetched land) — entered but not a land drop:
    def check(state):
        return state.entered_battlefield("", turn=1, via_kind="triggered")  # fetched
    # "you cast Lightning Bolt by turn 3" (cast — counts even if it fizzled):
    def check(state):
        return state.cast_on("Lightning Bolt", max_turn=3)

Generic event access (to test ANYTHING that happened during the game):
  state.count_events(kind=None, name=None, via=None, via_kind=None,
                     turn=None, pred=None) -> int
  state.events_matching(...same filters...) -> list[dict]
  state.events -> the raw list. Each event is a dict with at least
      {"turn", "kind", "name", "via", "via_kind"} where via/via_kind identify
      the resolving spell or ability that caused it. Kinds:
      "cast" (a spell was cast / put on the stack; + is_creature, is_land)
      "play_land" (a land was played as a land drop)
      "enter_battlefield" / "leave_battlefield"  (+ is_land, is_creature,
          is_token; leave also has "to": "graveyard"|"exile"|"hand"|"none")
      "draw" (name = the card drawn)
      "put_in_hand" (a card put into your hand WITHOUT drawing it — Atraxa's
          reveal, a tutor-to-hand, a bounce; + is_creature, is_land)
      "activated", "trigger_resolved", "spell_resolved", "ability_success"
      Remember: "cast"/"play_land" (the player's action) ≠ "enter_battlefield"
      (a permanent hitting the battlefield, however it got there); and
      "put_in_hand" (an effect moving a card into your hand) ≠ "draw"
      (drawing off the top of the library) ≠ the current hand SIZE.
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
