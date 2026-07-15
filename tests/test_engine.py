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
