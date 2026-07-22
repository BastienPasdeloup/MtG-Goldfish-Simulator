"""Core engine + property behaviour."""
from mtg_goldfish.deck.models import CardData, Deck, DeckBoard, DeckEntry
from mtg_goldfish.engine import Phase, SimulationConfig, run_simulation
from mtg_goldfish.engine.mana import ManaCost, ManaPool
from mtg_goldfish.properties import PropertySpec, Timing, compile_all, compile_property


def _cd(name, mc="", tl="", ci=None, pt=None):
    return CardData(
        name=name, mana_cost=mc, type_line=tl, cmc=0, color_identity=ci or [],
        power=pt and pt[0], toughness=pt and pt[1],
    )


def _mono_red_deck():
    cmd = _cd("Test Commander", "{2}{R}", "Legendary Creature — Goblin", ci=["R"], pt=("2", "2"))
    entries = [DeckEntry(quantity=1, board=DeckBoard.COMMANDER, card=cmd)]
    entries.append(DeckEntry(quantity=40, board=DeckBoard.MAINBOARD, card=_cd("Mountain", "", "Basic Land — Mountain")))
    entries.append(DeckEntry(quantity=59, board=DeckBoard.MAINBOARD, card=_cd("Test Bolt", "{R}", "Instant")))
    return Deck(name="t", entries=entries)


class _Prop:
    def __init__(self, pid, timing, phase, turn, fn):
        self.id, self.timing, self.phase, self.turn = pid, timing, phase, turn
        self.description = pid
        self._fn = fn

    def evaluate(self, state):
        return self._fn(state)


def test_mana_cost_parse_and_pay():
    cost = ManaCost.parse("{2}{R}")
    assert cost.cmc == 3 and cost.pip_map == {"R": 1}
    pool = ManaPool()
    pool.add("R", 1)
    pool.add("C", 2)
    assert pool.can_pay(cost)
    assert pool.pay(cost)
    assert pool.total() == 0


def test_commander_castable_by_turn_four():
    deck = _mono_red_deck()
    prop = _Prop("cmd", "at", Phase.POSTCOMBAT_MAIN, 4, lambda s: s.commander_in_play())
    stats = run_simulation(deck, [prop], SimulationConfig(num_games=10, timeout_per_game_s=3))
    assert stats.games_run == 10
    assert stats.successes >= 8  # essentially always castable by T4 in mono-red


def test_property_stub_compiles_example():
    from mtg_goldfish.llm.stub_provider import StubProvider

    spec = PropertySpec(
        id="p1", timing=Timing.AT, phase="postcombat_main", turn=4,
        english="the commander is in play and 4 non-creature spells have been cast this turn",
    )
    # Force the offline stub explicitly, independent of the user's selected LLM.
    spec = compile_property(spec, provider=StubProvider())
    assert "commander_in_play" in spec.code
    assert "noncreature_spells_cast_this_turn >= 4" in spec.code
    compiled = compile_all([spec])
    assert compiled[0].turn == 4 and compiled[0].phase == Phase.POSTCOMBAT_MAIN


def test_validate_properties_blocks_run_on_missing_or_invalid_code():
    """The Run-time validity check: every enabled property must have valid,
    runnable code (Run does not recompile — it only checks)."""
    from mtg_goldfish.session import Session, new_id, now_iso
    from mtg_goldfish.web.app import store, validate_properties

    s = Session(id=new_id(), name="t", created_at=now_iso(), deck=Deck(name="t"))
    s.properties = [
        PropertySpec(id="ok", english="x",
                     code="def check(state):\n    return True\n", manual=True),
        PropertySpec(id="bad", english="y",
                     code="def check(state)\n    return True\n", manual=True),  # syntax error
        PropertySpec(id="none", english="z", code=None),
    ]
    store.save(s)
    try:
        out = validate_properties(s.id)
        assert out["ok"] is False
        assert out["results"]["ok"]["valid"] is True
        assert out["results"]["bad"]["valid"] is False
        assert out["results"]["none"] == {"valid": False, "problem": "no code"}
        assert len(out["warnings"]) == 2
        # All valid → run allowed.
        s.properties = [PropertySpec(id="ok", english="x",
                        code="def check(state):\n    return True\n", manual=True)]
        store.save(s)
        assert validate_properties(s.id)["ok"] is True
        # The manual flag survives a save/load round-trip.
        assert store.load(s.id).properties[0].manual is True
        # No enabled property → also blocked.
        s.properties = []
        store.save(s)
        assert validate_properties(s.id)["ok"] is False
    finally:
        store.delete(s.id)


# --------------------------------------------------------------------------
# "played/cast" vs "entered the battlefield" — must be distinct events.
# --------------------------------------------------------------------------
def test_played_cast_vs_entered_battlefield():
    deck = _mono_red_deck()  # Test Bolt is a {R} Instant — cast, never enters play
    # By turn 3 in mono-red the bolt is essentially always castable.
    cast = _Prop("cast", "at", Phase.END_STEP, 3, lambda s: s.played_on("Test Bolt"))
    cast2 = _Prop("cast2", "at", Phase.END_STEP, 3, lambda s: s.cast_on("Test Bolt"))
    enter = _Prop("enter", "at", Phase.END_STEP, 3, lambda s: s.entered_battlefield("Test Bolt"))
    s = run_simulation(deck, [cast], SimulationConfig(num_games=6, timeout_per_game_s=3)).as_dict()
    s2 = run_simulation(deck, [cast2], SimulationConfig(num_games=6, timeout_per_game_s=3)).as_dict()
    s3 = run_simulation(deck, [enter], SimulationConfig(num_games=6, timeout_per_game_s=3)).as_dict()
    assert s["per_property"]["cast"] >= 5      # the instant WAS cast/played
    assert s2["per_property"]["cast2"] >= 5     # cast_on agrees
    assert s3["per_property"]["enter"] == 0     # an instant never ENTERS the battlefield


def test_played_on_excludes_fetched_permanents():
    # A land put onto the battlefield WITHOUT being played (a token/fetched land)
    # must not count as played_on, but does count as entered_battlefield.
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    g.turn = 2
    g.resolving = ("triggered", "Some Fetch")
    g.put_on_battlefield(_cd("Fetched Island", "", "Basic Land — Island"))
    g.resolving = None
    assert g.entered_battlefield("Fetched Island") is True
    assert g.played_on("Fetched Island") is False   # entered, but never "played"
    assert g.cast_on("Fetched Island") is False


def test_instant_speed_action_filter():
    from mtg_goldfish.engine.game_state import GameState, make_permanent
    from mtg_goldfish.engine.actions import legal_actions
    g = GameState(commander_color_identity=("R",))
    g.turn = 1
    land = _cd("Mountain", "", "Basic Land — Mountain")
    g.hand = [land, _cd("Test Bolt", "{R}", "Instant")]
    src = make_permanent(g, land)
    src.summoning_sick = False
    g.battlefield.append(src)
    sorcery = {a.label for a in legal_actions(g, sorcery_speed_ok=True)}
    instant = {a.label for a in legal_actions(g, sorcery_speed_ok=False)}
    assert "play land Mountain" in sorcery and "cast Test Bolt" in sorcery
    assert "cast Test Bolt" in instant           # instants are allowed at instant speed
    assert "play land Mountain" not in instant   # lands are sorcery-speed only


def test_search_bugs_are_recorded_not_swallowed():
    from mtg_goldfish.engine.actions import CastDefault
    deck = _mono_red_deck()
    prop = _Prop("cast", "at", Phase.POSTCOMBAT_MAIN, 3, lambda s: s.played_on("Test Bolt"))
    seen = []
    orig = CastDefault.apply
    CastDefault.apply = lambda self, state: (_ for _ in ()).throw(RuntimeError("synthetic"))
    try:
        run_simulation(deck, [prop], SimulationConfig(num_games=2, timeout_per_game_s=2),
                       on_game=lambda o, s: seen.append(o))
    finally:
        CastDefault.apply = orig
    assert len(seen) == 2                        # the run survived the crashing action
    assert any(o.bugs for o in seen)             # and the bug was recorded
    assert any("synthetic" in b["error"] for o in seen for b in o.bugs)


# --------------------------------------------------------------------------
# Property compiler: structured output (confidence + notes) and name context.
# --------------------------------------------------------------------------
class _FakeProvider:
    """Captures the prompt and returns a fixed completion."""
    is_real = True
    name = "fake"
    def __init__(self, out):
        self.out = out
        self.last_prompt = None
    def generate(self, system, prompt, *, max_tokens=4096):
        self.last_prompt = prompt
        return self.out


def test_compiler_parses_confidence_and_notes():
    from mtg_goldfish.properties.compiler import compile_condition_detailed
    out = ('Sure!\n```json\n{"code": "def check(state):\\n    return '
           'state.played_on(\\"Nick Fury, Agent of S.H.I.E.L.D.\\")\\n", '
           '"confidence": "high", "notes": "resolved Nick Fury -> full name"}\n```')
    r = compile_condition_detailed("Nick Fury is cast", provider=_FakeProvider(out))
    assert r["confidence"] == "high"
    assert "resolved Nick Fury" in r["notes"]
    assert "def check(state):" in r["code"]
    assert "Nick Fury, Agent of S.H.I.E.L.D." in r["code"]


def test_compiler_passes_card_names_to_prompt():
    from mtg_goldfish.properties.compiler import compile_condition_detailed
    prov = _FakeProvider('{"code": "def check(state):\\n    return True\\n", "confidence": "low", "notes": "n"}')
    compile_condition_detailed("Nick Fury is cast",
                               ["Nick Fury, Agent of S.H.I.E.L.D.", "Lightning Bolt"],
                               provider=prov)
    assert "Nick Fury, Agent of S.H.I.E.L.D." in prov.last_prompt   # deck names offered
    assert prov.last_prompt.rstrip().endswith("ENGLISH: Nick Fury is cast")  # english last


def test_compiler_non_json_falls_back_to_code():
    from mtg_goldfish.properties.compiler import compile_condition_detailed
    r = compile_condition_detailed("x", provider=_FakeProvider("def check(state):\n    return True\n"))
    assert r["confidence"] is None and r["code"].startswith("def check")


def test_stub_ignores_card_listing():
    # The card list must not pollute the offline stub's clause parsing.
    from mtg_goldfish.llm.stub_provider import StubProvider
    from mtg_goldfish.properties.compiler import compile_condition_detailed
    r = compile_condition_detailed(
        "the commander is in play",
        ["Some Random Card", "Another Card"],
        provider=StubProvider())
    assert "commander_in_play" in r["code"]


def test_only_one_commander_castable_per_game():
    """With a partner pair, once one commander is cast the other is no longer
    offered as a legal action for the rest of the game."""
    from mtg_goldfish.engine.actions import CastCommander, legal_actions
    from mtg_goldfish.engine.game_state import new_game_from_deck

    a = _cd("Partner A", "{R}", "Legendary Creature — Goblin", ci=["R"], pt=("1", "1"))
    b = _cd("Partner B", "{R}", "Legendary Creature — Goblin", ci=["R"], pt=("1", "1"))
    deck = Deck(name="t", entries=[
        DeckEntry(quantity=1, board=DeckBoard.COMMANDER, card=a),
        DeckEntry(quantity=1, board=DeckBoard.COMMANDER, card=b),
        DeckEntry(quantity=98, board=DeckBoard.MAINBOARD,
                  card=_cd("Mountain", "", "Basic Land — Mountain")),
    ])
    state = new_game_from_deck(deck)
    state.mana_pool.add("R", 5)  # enough to cast either

    def commander_casts(st):
        return {x.card_name for x in legal_actions(st) if isinstance(x, CastCommander)}

    assert commander_casts(state) == {"Partner A", "Partner B"}

    cast_a = next(x for x in legal_actions(state)
                  if isinstance(x, CastCommander) and x.card_name == "Partner A")
    cast_a.apply(state)
    assert state.commander_cast_this_game

    # Partner B may no longer be cast (it never was); the game is locked in.
    assert "Partner B" not in commander_casts(state)


# --------------------------------------------------------------------------
# Fake shuffling: shuffles never reorder the library — only the cards whose
# position the player knows are reinserted at random spots.
# --------------------------------------------------------------------------
def test_fake_shuffle_keeps_unknown_cards_in_order():
    from mtg_goldfish.engine.game_state import GameState

    cards = [_cd(f"C{i}", "", "Instant") for i in range(10)]
    st = GameState(library=list(cards), rng_seed=7)
    st.fake_shuffle = True
    st.mark_known_in_library(cards[0], cards[5])
    st.shuffle_library()
    # The 8 unknown cards keep their relative order; the 2 known ones moved
    # somewhere random; knownness is consumed by the shuffle.
    rest = [c.name for c in st.library if c.name not in ("C0", "C5")]
    assert rest == [f"C{i}" for i in range(10) if i not in (0, 5)]
    assert sorted(c.name for c in st.library) == sorted(c.name for c in cards)
    assert not st.known_library_ids

    # With nothing known, a fake shuffle is a strict no-op.
    order = [c.name for c in st.library]
    st.shuffle_library()
    assert [c.name for c in st.library] == order

    # A REAL shuffle does reorder (sanity check of the toggle).
    st2 = GameState(library=list(cards), rng_seed=7)
    st2.shuffle_library()
    assert [c.name for c in st2.library] != [c.name for c in cards]


def test_fake_shuffle_flag_survives_clone():
    from mtg_goldfish.engine.game_state import GameState

    cards = [_cd(f"C{i}", "", "Instant") for i in range(4)]
    st = GameState(library=list(cards), rng_seed=1)
    st.fake_shuffle = True
    st.mark_known_in_library(cards[2])
    cl = st.clone()
    assert cl.fake_shuffle
    assert cl.known_library_ids == st.known_library_ids
    cl.known_library_ids.clear()
    assert st.known_library_ids  # sets are independent


# --------------------------------------------------------------------------
# Parallel simulation: games run strictly IN ORDER; each game's tree is
# explored across worker processes, with results identical to sequential.
# --------------------------------------------------------------------------
def test_parallel_run_matches_sequential_and_stays_in_order():
    deck = _mono_red_deck()
    spec = PropertySpec(
        id="p1", timing=Timing.AT, phase="postcombat_main", turn=3,
        english="the commander is in play",
        code="def check(state):\n    return state.commander_in_play()\n",
    )
    props = compile_all([spec])
    order: list[int] = []
    seq = run_simulation(deck, props, SimulationConfig(
        num_games=6, timeout_per_game_s=3, base_seed=42, parallel_workers=1)).as_dict()
    par = run_simulation(deck, props, SimulationConfig(
        num_games=6, timeout_per_game_s=3, base_seed=42, parallel_workers=2),
        on_game=lambda o, s: order.append(o.game_index)).as_dict()
    # Games are reported strictly in game order (the table fills 1, 2, 3...).
    assert order == list(range(6))
    assert par["games_run"] == 6
    assert par["successes"] == seq["successes"]
    assert par["per_property"] == seq["per_property"]


# --------------------------------------------------------------------------
# Resume: running the missing game indices with the stored stats continues
# exactly where the run left off (per-game seeds depend only on the index).
# --------------------------------------------------------------------------
def test_run_simulation_resumes_from_partial_stats():
    deck = _mono_red_deck()
    prop = _Prop("cmd", "at", Phase.POSTCOMBAT_MAIN, 4, lambda s: s.commander_in_play())
    cfg = SimulationConfig(num_games=6, timeout_per_game_s=3, base_seed=99,
                           parallel_workers=1)
    full = run_simulation(deck, [prop], cfg).as_dict()
    first = run_simulation(deck, [prop], cfg, game_indices=[0, 1, 2]).as_dict()
    assert first["games_run"] == 3
    resumed = run_simulation(deck, [prop], cfg, game_indices=[3, 4, 5],
                             initial_stats=first).as_dict()
    assert resumed["games_run"] == 6
    assert resumed["successes"] == full["successes"]
    assert resumed["per_property"] == full["per_property"]


# --------------------------------------------------------------------------
# A worker wedged in card code (never returns, never rechecks its deadline)
# must NOT hang the run: past a grace it is killed, the pool rebuilt, and the
# remaining games proceed. Injected via the MTG_TEST_HANG_GAME env var, which
# spawned workers inherit (see _tree_worker).
# --------------------------------------------------------------------------
def test_wedged_worker_is_contained_and_run_continues(monkeypatch):
    import time as _time

    import mtg_goldfish.engine.simulator as sim

    deck = _mono_red_deck()
    spec = PropertySpec(
        id="p1", timing=Timing.AT, phase="postcombat_main", turn=6,
        english="x", code="def check(state):\n    return len(state.battlefield) >= 40\n",
    )
    props = compile_all([spec])
    monkeypatch.setattr(sim, "_WORKER_GRACE_S", 1.0)  # keep the test quick
    monkeypatch.setenv("MTG_TEST_HANG_GAME", "2")  # game 2's workers hang forever

    order: list[int] = []
    t0 = _time.monotonic()
    stats = run_simulation(
        deck, props,
        SimulationConfig(num_games=4, timeout_per_game_s=1.0, base_seed=7,
                         parallel_workers=2),
        on_game=lambda o, s: order.append(o.game_index),
    ).as_dict()
    elapsed = _time.monotonic() - t0

    # It returned (no hang) with every game accounted for, in order...
    assert order == [0, 1, 2, 3]
    assert stats["games_run"] == 4
    # ...the wedged game was reported as a timeout, not lost...
    assert stats["timeouts"] >= 1
    # ...and it didn't take anywhere near the 3600 s the wedged worker sleeps.
    assert elapsed < 60


# --------------------------------------------------------------------------
# Property API robustness: a card-list result compares numerically by length
# (so `cards_put_by(...) >= 1` works, not just `any(... for c in ...)`), and a
# property whose code RAISES is surfaced as a bug rather than silently making
# every game search to timeout.
# --------------------------------------------------------------------------
def test_cardlist_compares_by_length():
    from mtg_goldfish.engine.game_state import CardList
    two = CardList(["a", "b"])
    assert (two >= 1) and (two >= 2) and not (two >= 3)
    assert (two > 1) and not (two > 2)
    assert (two <= 2) and (two < 3) and (two == 2) and (two != 1)
    assert CardList() >= 0 and not (CardList() >= 1)
    # Still a real list: iterable, truthy-by-emptiness, list-equality intact.
    assert list(two) == ["a", "b"] and bool(two) and not bool(CardList())
    assert CardList(["a"]) == ["a"]


def test_cards_put_by_supports_numeric_comparison():
    from mtg_goldfish.engine.game_state import GameState
    g = GameState(commander_names=("Fetcher",))
    g.turn = 2
    g.resolving = ("activated", "Fetcher")
    g.put_on_battlefield(_cd("Made Token", "", "Creature — Elemental"))
    g.resolving = None
    # The exact shape a compiler might emit for "put at least one card".
    assert g.cards_put_by("Fetcher", via_kind="activated") >= 1
    assert not (g.cards_put_by("Fetcher", via_kind="activated") >= 2)


def test_raising_property_is_recorded_not_silently_false():
    deck = _mono_red_deck()
    # A property whose code raises at evaluation time (here: comparing a list to
    # an int, the classic compiler slip) must surface as a bug.
    bad = _Prop("bad", "before", Phase.END_STEP, 3,
                lambda s: (["x"] >= 1))  # raises TypeError every call
    seen = []
    run_simulation(deck, [bad], SimulationConfig(num_games=1, timeout_per_game_s=2,
                                                 parallel_workers=1),
                   on_game=lambda o, st: seen.append(o))
    assert seen and seen[0].bugs
    assert any("property" in b["context"] for b in seen[0].bugs)
