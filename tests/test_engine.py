"""Core engine + property behaviour."""
from mtg_goldfish.deck.models import CardData, Deck, DeckBoard, DeckEntry
from mtg_goldfish.engine import Phase, SimulationConfig, run_simulation
from mtg_goldfish.engine.mana import ManaCost, ManaPool
from mtg_goldfish.properties import PropertySpec, Timing, compile_all, compile_property


def _cd(name, mc="", tl="", ci=None):
    return CardData(name=name, mana_cost=mc, type_line=tl, cmc=0, color_identity=ci or [])


def _mono_red_deck():
    cmd = _cd("Test Commander", "{2}{R}", "Legendary Creature — Goblin", ci=["R"])
    entries = [DeckEntry(quantity=1, board=DeckBoard.COMMANDER, card=cmd)]
    entries.append(DeckEntry(quantity=40, board=DeckBoard.MAINBOARD, card=_cd("Mountain", "", "Basic Land — Mountain")))
    entries += [
        DeckEntry(quantity=1, board=DeckBoard.MAINBOARD, card=_cd(f"Bolt{i}", "{R}", "Instant"))
        for i in range(59)
    ]
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
    spec = PropertySpec(
        id="p1", timing=Timing.AT, phase="postcombat_main", turn=4,
        english="the commander is in play and 4 non-creature spells have been cast this turn",
    )
    spec = compile_property(spec)  # offline stub
    assert "commander_in_play" in spec.code
    assert "noncreature_spells_cast_this_turn >= 4" in spec.code
    compiled = compile_all([spec])
    assert compiled[0].turn == 4 and compiled[0].phase == Phase.POSTCOMBAT_MAIN
