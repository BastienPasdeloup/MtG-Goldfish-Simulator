"""Exactness tests for card mechanics against real Scryfall data (cached)."""
from mtg_goldfish.cards import build_card, load_all_cards
from mtg_goldfish.deck.models import CardData, Deck, DeckBoard, DeckEntry
from mtg_goldfish.deck.scryfall import ScryfallClient
from mtg_goldfish.engine.actions import legal_actions
from mtg_goldfish.engine.game_state import StackAbility, new_game_from_deck
from mtg_goldfish.engine.phases import Phase

load_all_cards()
_SC = ScryfallClient()


def card(name: str) -> CardData:
    return _SC.get_named(name)  # served from the on-disk cache


def _state(library_names, hand_names=(), commander="Nick Fury, Agent of S.H.I.E.L.D."):
    entries = [DeckEntry(quantity=1, board=DeckBoard.COMMANDER, card=card(commander))]
    entries += [DeckEntry(quantity=1, board=DeckBoard.MAINBOARD, card=card(n))
                for n in library_names]
    state = new_game_from_deck(Deck(name="t", entries=entries))
    state.turn = 3
    state.phase = Phase.PRECOMBAT_MAIN
    for n in hand_names:
        state.hand.append(card(n))
    return state


def test_misty_rainforest_exact():
    """{T}, pay 1 life, sacrifice: search Forest or Island, put onto battlefield."""
    state = _state(["Tropical Island", "Plains", "Badlands"], hand_names=["Misty Rainforest"])
    # Play the fetch, then activate it.
    play = next(a for a in legal_actions(state) if a.label.startswith("play land Misty"))
    play.apply(state)
    fetches = [a for a in legal_actions(state) if "fetch" in a.label]
    # Only Tropical Island (Forest Island) qualifies — not Plains, not Badlands.
    assert len(fetches) == 1 and "Tropical Island" in fetches[0].label
    life_before = state.life
    fetches[0].apply(state)
    assert state.life == life_before - 1                      # paid 1 life
    assert "Misty Rainforest" in state.graveyard_names()      # sacrificed
    assert state.has_permanent_named("Tropical Island")       # fetched into play
    assert state.lands_played_this_turn == 1                  # fetch is not a land drop


def test_shockland_modes():
    state = _state([], hand_names=["Hallowed Fountain"])
    plays = [a for a in legal_actions(state) if a.label.startswith("play land Hallowed")]
    assert len(plays) == 2  # pay 2 life untapped / tapped
    untapped = next(a for a in plays if "pay 2 life" in a.label)
    untapped.apply(state)
    perm = state.permanents_named("Hallowed Fountain")[0]
    assert state.life == 18 and not perm.tapped


def test_city_of_brass_pays_life():
    from mtg_goldfish.engine.actions import pay_cost
    from mtg_goldfish.engine.mana import ManaCost

    state = _state([])
    perm = state.put_on_battlefield(card("City of Brass"))
    perm.summoning_sick = False
    assert pay_cost(state, ManaCost.parse("{R}"))
    assert state.life == 19


def test_counterspells_need_a_spell_on_the_stack():
    # A counterspell needs a valid target — a spell ON THE STACK. With the stack
    # empty (spells resolve atomically here) it is not castable; there is no
    # "counter your own spell" out of thin air.
    for name in ("Mana Tithe", "Daze", "Force of Negation", "Mana Leak"):
        state = _state([], hand_names=[name])
        for _ in range(4):
            state.put_on_battlefield(card("Island")).summoning_sick = False
        assert not any(name in a.label for a in legal_actions(state) if "cast" in a.label), name


def test_counterspell_counters_a_spell_on_the_stack():
    # With a spell actually on the stack (and mana), the counter is castable and
    # sends the countered spell to the graveyard.
    state = _state([], hand_names=["Mana Leak"])
    for _ in range(4):
        state.put_on_battlefield(card("Island")).summoning_sick = False
    state.stack.append(card("Brainstorm"))  # a spell to counter
    acts = [a for a in legal_actions(state) if a.label.startswith("cast Mana Leak countering")]
    assert acts, "Mana Leak should be able to counter the spell on the stack"
    acts[0].apply(state)
    assert "Mana Leak" in state.graveyard_names()
    assert "Brainstorm" in state.graveyard_names()


def test_fastland_condition():
    state = _state([], hand_names=["Seachrome Coast"])
    impl = build_card(card("Seachrome Coast"))
    assert impl.etb_tapped(state) is False  # 0 other lands
    for _ in range(3):
        state.put_on_battlefield(card("Plains"))
    assert impl.etb_tapped(state) is True   # 3 other lands


def test_fetch_shuffles_library():
    """Fetching must shuffle the remaining library (deterministically per seed)."""
    fillers = ["Badlands", "Bayou", "Plateau", "Savannah", "Scrubland", "Taiga",
               "Tundra", "Underground Sea", "Volcanic Island", "Plains",
               "Command Tower", "City of Brass", "Mana Confluence", "Starting Town",
               "Skullclamp", "Brainstorm", "Demonic Tutor", "Tithe", "Worldly Tutor"]
    state = _state(["Tropical Island"] + fillers, hand_names=["Misty Rainforest"])
    state.rng_seed = 99
    before = [c.name for c in state.library]
    next(a for a in legal_actions(state) if a.label.startswith("play land Misty")).apply(state)
    next(a for a in legal_actions(state) if "fetch Tropical Island" in a.label).apply(state)
    after = [c.name for c in state.library]
    no_shuffle = [n for n in before if n != "Tropical Island"]
    assert sorted(after) == sorted(no_shuffle)   # same cards...
    assert after != no_shuffle                   # ...new order: it shuffled


def test_skullclamp_draws_two():
    state = _state([c for c in ("Badlands", "Bayou", "Taiga")])
    state.put_on_battlefield(card("Plains")).summoning_sick = False
    clamp = state.put_on_battlefield(card("Skullclamp"))
    frog = state.put_on_battlefield(card("Psychic Frog"))  # 1/2
    malcolm = state.put_on_battlefield(card("Malcolm, Alluring Scoundrel"))  # 2/1
    equips = [a for a in legal_actions(state) if a.label.startswith("equip Skullclamp")]
    assert len(equips) == 2
    hand_before = state.cards_in_hand()
    target = next(a for a in equips if "Malcolm" in a.label)
    target.apply(state)  # 2/1 becomes 3/0 -> dies -> draw 2
    assert "Malcolm, Alluring Scoundrel" in state.graveyard_names()
    assert state.cards_in_hand() == hand_before + 2


def test_lotus_field_sacrifices_itself_when_two_or_fewer_lands_exist():
    state = _state([], hand_names=["Lotus Field"])
    state.put_on_battlefield(card("Forest"))
    play = next(a for a in legal_actions(state) if a.label == "play land Lotus Field")
    play.apply(state)
    assert not any("land" in p.type_line.lower() for p in state.battlefield)
    assert "Lotus Field" in state.graveyard_names()
    assert "Forest" in state.graveyard_names()


def test_green_suns_zenith_preserves_arboreal_grazer_etb_choices():
    state = _state(["Arboreal Grazer"], hand_names=["Green Sun's Zenith", "Plains"])
    for _ in range(2):
        state.put_on_battlefield(card("Forest")).summoning_sick = False
    action = next(
        a for a in legal_actions(state)
        if a.label == "cast Green Sun's Zenith (X=1) → Arboreal Grazer"
    )
    branches = action.apply(state.clone())
    assert branches is not None and len(branches) == 2
    assert all(branch.has_permanent_named("Arboreal Grazer") for branch in branches)
    assert any(branch.has_permanent_named("Plains") for branch in branches)
    assert any(not branch.has_permanent_named("Plains") for branch in branches)


def test_crop_rotation_preserves_fetched_land_etb_choices():
    state = _state(["Guildless Commons"], hand_names=["Crop Rotation"])
    state.put_on_battlefield(card("Forest")).summoning_sick = False
    state.put_on_battlefield(card("Plains")).summoning_sick = False
    action = next(a for a in legal_actions(state) if a.label == "cast Crop Rotation → Guildless Commons")
    branches = action.apply(state.clone())
    assert branches is not None and len(branches) == 2
    assert any(branch.has_permanent_named("Guildless Commons") for branch in branches)
    assert any("Guildless Commons" in [c.name for c in branch.hand] for branch in branches)
    assert any("Plains" in [c.name for c in branch.hand] for branch in branches)


def test_city_of_traitors_triggers_when_a_land_is_played():
    state = _state([], hand_names=["Plains"])
    state.put_on_battlefield(card("City of Traitors"))
    play = next(a for a in legal_actions(state) if a.label == "play land Plains")
    play.apply(state)
    assert "City of Traitors" in state.graveyard_names()
    assert state.has_permanent_named("Plains")


def test_city_of_traitors_does_not_trigger_on_fetched_land():
    state = _state(["Tropical Island"])
    state.put_on_battlefield(card("Misty Rainforest"))
    state.put_on_battlefield(card("City of Traitors"))
    fetch = next(a for a in legal_actions(state) if a.label == "Misty Rainforest: fetch Tropical Island")
    fetch.apply(state)
    assert state.has_permanent_named("City of Traitors")
    assert state.has_permanent_named("Tropical Island")


def test_lumra_puts_all_returned_lands_in_before_etbs_stack():
    state = _state([])
    lumra = state.put_on_battlefield(card("Lumra, Bellow of the Woods"), fire_etb=False)
    state.graveyard.extend([card("Guildless Commons"), card("Forest")])
    state.push_triggered_abilities(lumra.impl.etb_stack_items(state, lumra))
    branches = state.resolve_triggered_abilities()
    assert branches is not None and len(branches) == 2
    returned = {tuple(sorted(branch.hand_names())) for branch in branches}
    assert returned == {("Forest",), ("Guildless Commons",)}
    assert any(frame["desc"] == "Guildless Commons: ETB (on the stack)"
               for frame in branches[0].log + branches[1].log)


def test_gingerbread_cabin_only_triggers_if_it_enters_untapped():
    state = _state([], hand_names=["Gingerbread Cabin"])
    state.put_on_battlefield(card("Amulet of Vigor"))
    for _ in range(2):
        state.put_on_battlefield(card("Forest"))
    play = next(a for a in legal_actions(state) if a.label == "play land Gingerbread Cabin")
    play.apply(state)
    cabin = state.permanents_named("Gingerbread Cabin")[0]
    assert not cabin.tapped
    assert not state.has_permanent_named("Food")
    assert any(frame["desc"] == "Amulet of Vigor: untap Gingerbread Cabin (on the stack)"
               for frame in state.log)
    assert not any(frame["desc"] == "Gingerbread Cabin entered untapped — Food token"
                   for frame in state.log)


def test_creature_entry_does_not_queue_landfall_stack_items():
    state = _state([])
    state.put_on_battlefield(card("Lotus Cobra"))
    frog = state.put_on_battlefield(card("Psychic Frog"), fire_etb=False)
    state.queue_entry_triggers([frog])
    assert state.stack == []


def test_stack_snapshot_carries_source_and_trigger_metadata():
    state = _state([])
    state.put_on_battlefield(card("Amulet of Vigor"))
    for _ in range(2):
        state.put_on_battlefield(card("Forest"))
    cabin = state.put_on_battlefield(card("Gingerbread Cabin"), fire_etb=False)
    state.queue_entry_triggers([cabin])
    assert state.stack and isinstance(state.stack[-1], StackAbility)
    frame = state.snapshot()["stack"][-1]
    assert frame["source_name"] == "Amulet of Vigor"
    assert frame["trigger"] == "Gingerbread Cabin entered the battlefield tapped"
    assert frame["ability"] == "Untap Gingerbread Cabin"
