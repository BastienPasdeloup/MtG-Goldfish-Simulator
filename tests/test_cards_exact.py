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


# --- Ellie, Vengeful Hunter deck: aristocrats / man-lands / evoke -----------
def _ellie(names, hand=()):
    return _state(names, hand_names=hand, commander="Ellie, Vengeful Hunter")


def test_mishras_factory_animates_and_reverts():
    from mtg_goldfish.engine.phases import Phase
    from mtg_goldfish.engine.simulator import _apply_step_entry
    state = _ellie([])
    for _ in range(2):
        state.put_on_battlefield(card("Mountain")).summoning_sick = False
    mf = state.put_on_battlefield(card("Mishra's Factory"))
    mf.summoning_sick = False
    mf.tapped = False
    act = next(a for a in legal_actions(state) if "become a 2/2" in a.label)
    act.apply(state)
    live = state.find_permanent(mf.uid)
    assert live.is_creature_now and state.effective_power(live) == 2
    assert live.is_land  # "It's still a land."
    state.phase = Phase.CLEANUP
    _apply_step_entry(state)
    assert not state.find_permanent(mf.uid).is_creature_now  # animation ended


def test_den_of_the_bugbear_attack_makes_goblin():
    from mtg_goldfish.engine.actions import DeclareAttackers
    from mtg_goldfish.engine.phases import Phase
    state = _ellie([])
    den = state.put_on_battlefield(card("Den of the Bugbear"))
    den.summoning_sick = False
    den.tapped = False
    for _ in range(4):
        state.put_on_battlefield(card("Mountain")).summoning_sick = False
    next(a for a in legal_actions(state) if "Den of the Bugbear: become" in a.label).apply(state)
    state.phase = Phase.DECLARE_ATTACKERS
    DeclareAttackers().apply(state)
    assert state.count_permanents(name_contains="Goblin") == 1
    assert len([u for u in state.attackers]) == 2  # Den + token


def test_aristocrats_sacrifice_drains_and_grows():
    state = _ellie([])
    cf = state.put_on_battlefield(card("Carrion Feeder"), fire_etb=False)
    cf.summoning_sick = False
    state.put_on_battlefield(card("Vraan, Executioner Thane"), fire_etb=False)
    state.put_on_battlefield(card("Marionette Apprentice"), fire_etb=False)
    fodder = state.put_on_battlefield(card("Gravecrawler"), fire_etb=False)
    sac = next(a for a in legal_actions(state)
               if "Carrion Feeder: sacrifice" in a.label and "Gravecrawler" in a.label)
    sac.apply(state)
    assert state.opponent_life == 17          # Vraan -2, Marionette -1
    assert state.life == 22                    # Vraan +2
    assert state.effective_power(state.find_permanent(cf.uid)) == 2  # +1/+1


def test_decayed_token_sacrificed_at_end_of_combat():
    from mtg_goldfish.engine.phases import Phase
    from mtg_goldfish.engine.simulator import _apply_step_entry
    state = _ellie([])
    jadar = state.put_on_battlefield(card("Jadar, Ghoulcaller of Nephalia"), fire_etb=False)
    jadar.summoning_sick = False
    state.phase = Phase.END_STEP
    _apply_step_entry(state)  # Jadar makes a decayed Zombie
    zombie = next(p for p in state.battlefield if p.counters.get("decayed"))
    state.attackers = [zombie.uid]
    state.phase = Phase.END_COMBAT
    _apply_step_entry(state)
    assert state.find_permanent(zombie.uid) is None  # sacrificed at end of combat


def test_commander_leaving_play_branches_stay_vs_command_zone():
    """When a commander leaves the battlefield, the search must explore BOTH
    leaving it in the destination zone AND returning it to the command zone."""
    state = _ellie([])
    cmd = state.put_on_battlefield(card("Ellie, Vengeful Hunter"),
                                   is_commander=True, fire_etb=False)
    state.leaves_battlefield(cmd, "graveyard", reason="dies")
    branches = state.settle()
    assert branches is not None and len(branches) == 2
    # both lines agree the commander left play...
    assert all(b.commander_left_play() for b in branches)
    # ...one returns it to the command zone, one leaves it in the graveyard.
    returned = [b for b in branches if b.commander_returned_to_command_zone()]
    stayed = [b for b in branches if not b.commander_returned_to_command_zone()]
    assert len(returned) == 1 and len(stayed) == 1
    assert any(c.name == "Ellie, Vengeful Hunter" for c in returned[0].command_zone)
    assert "Ellie, Vengeful Hunter" in stayed[0].graveyard_names()


def test_begin_combat_branching_trigger_fans_out():
    """A phase-entry triggered ability that BRANCHES (Emperor of Bones'
    begin-of-combat "exile up to one target from a graveyard", several choices)
    must fan out into search branches — not raise "Branching triggered abilities
    are unsupported during begin_combat triggers"."""
    import time
    from mtg_goldfish.engine.phases import Phase
    from mtg_goldfish.engine.simulator import _SearchContext, _advance
    from mtg_goldfish.properties.evaluator import CompiledProperty
    from mtg_goldfish.properties.models import PropertySpec

    state = _ellie([])
    emp = state.put_on_battlefield(card("Emperor of Bones"), fire_etb=False)
    emp.summoning_sick = False
    state.graveyard.append(card("Gravecrawler"))
    state.graveyard.append(card("Carrion Feeder"))
    state.phase = Phase.BEGIN_COMBAT

    prop = CompiledProperty(PropertySpec(
        id="p1", timing="at", phase="end_step", turn=9, english="never",
        code="def check(state):\n    return False", enabled=True))
    ctx = _SearchContext(properties=[prop], deadline=time.monotonic() + 60)

    status, satisfied, branches = _advance(state, ctx, frozenset())
    assert status == "branch"
    # "exile nothing" + one branch per distinct graveyard card.
    assert len(branches) == 3
    exiled = sorted(c.name for b in branches for c in b.exile)
    assert exiled == ["Carrion Feeder", "Gravecrawler"]
    # Each branch resumes advancing WITHOUT re-firing the trigger (no loop): it
    # moves on to declare-attackers and returns a normal status.
    for b in branches:
        assert b._skip_step_entry == (b.turn, b.phase)
        st, _sat, _br = _advance(b, ctx, satisfied)
        assert st in ("decision", "unviable", "dead", "success")
        assert b.phase != Phase.BEGIN_COMBAT  # advanced past the trigger step


def test_evoke_fury_sacrifices_itself():
    state = _ellie([], hand=["Fury", "Lightning Bolt"])  # Lightning Bolt = red fuel
    evoke = next(a for a in legal_actions(state) if a.label.startswith("cast Fury (evoke"))
    branches = evoke.apply(state)  # Fury's ETB branches (branch_over clones)
    state = branches[0] if branches else state
    # Fury entered and was sacrificed by evoke -> in the graveyard, not in play.
    assert not state.has_permanent_named("Fury")
    assert "Fury" in state.graveyard_names()
    assert "Lightning Bolt" in [c.name for c in state.exile]  # exiled as evoke cost


# --- Tasigur deck: land cycles + dig + delve --------------------------------
def test_check_land_drowned_catacomb():
    impl = build_card(card("Drowned Catacomb"))
    state = _state([])
    assert impl.etb_tapped(state) is True             # no Island/Swamp
    state.put_on_battlefield(card("Swamp"))
    assert impl.etb_tapped(state) is False            # a Swamp is present


def test_slow_fetch_bad_river():
    state = _state(["Snow-Covered Island", "Plains"], hand_names=["Bad River"])
    play = next(a for a in legal_actions(state) if a.label.startswith("play land Bad River"))
    play.apply(state)
    br = state.permanents_named("Bad River")[0]
    assert br.tapped                                  # enters tapped
    br.tapped = False                                 # (untap so we can activate)
    fetches = [a for a in legal_actions(state) if "Bad River: fetch" in a.label]
    # Only the Island qualifies (Island or Swamp); Plains does not.
    assert len(fetches) == 1 and "Snow-Covered Island" in fetches[0].label
    fetches[0].apply(state)
    assert state.has_permanent_named("Snow-Covered Island")
    assert "Bad River" in state.graveyard_names()     # sacrificed


def test_stock_up_digs_two():
    lib = ["Ponder", "Preordain", "Counterspell", "Cut Down", "Go for the Throat"]
    state = _state(lib, hand_names=["Stock Up"])
    for _ in range(3):
        state.put_on_battlefield(card("Island")).summoning_sick = False
    branches = next(a for a in legal_actions(state)
                    if a.label == "cast Stock Up").apply(state)
    # Every branch keeps exactly 2 of the top 5 in hand; the rest go to bottom.
    assert branches and all(b.cards_in_hand() == 2 for b in branches)
    assert all(len(b.library) == 3 for b in branches)  # 5 dug, 2 to hand, 3 to bottom


def test_tasigur_delve_reduces_cost():
    state = _state([])
    impl = build_card(card("Tasigur, the Golden Fang"))
    assert impl.cast_cost(state).cmc == 6             # {5}{B}, empty graveyard
    for n in ("Ponder", "Preordain", "Cremate"):
        state.graveyard.append(card(n))
    assert impl.cast_cost(state).cmc == 3             # delve 3 -> {2}{B}


def test_moonmist_transforms_humans_and_prevents_nonwolf_damage():
    """Transform all Humans (DFC-only); this turn only Wolves deal combat damage."""
    from mtg_goldfish.engine.actions import deal_combat_damage

    state = _state([], hand_names=["Moonmist"])
    bruce = state.put_on_battlefield(
        card("Bruce Banner // The Incredible Hulk"), fire_etb=False)
    wasp = state.put_on_battlefield(
        card("The Wasp, Winsome Avenger"), fire_etb=False)
    state.mana_pool.add("G", 1)
    state.mana_pool.add("C", 1)
    cast = next(a for a in legal_actions(state) if a.label.startswith("cast Moonmist"))
    cast.apply(state)
    # Bruce (a Human with a back face) flipped into the Hulk; the Wasp is a
    # Human but single-faced — untouched.
    assert bruce.transformed and bruce.name == "The Incredible Hulk"
    assert not wasp.transformed

    # Prevention: the (non-Wolf) Wasp attacks — no combat damage this turn...
    wasp.summoning_sick = False
    state.attackers = [wasp.uid]
    opp = state.opponent_life
    deal_combat_damage(state)
    assert state.opponent_life == opp
    # ...and the effect ends with the turn.
    state.reset_turn_counters()
    assert not state.prevent_nonwolf_combat_damage
    state.attackers = [wasp.uid]
    deal_combat_damage(state)
    assert state.opponent_life == opp - 2


def test_the_wasp_is_flash_flying_vanilla():
    """2/1 flash flyer; its goldfish-irrelevant triggers add no stack items."""
    from mtg_goldfish.engine.actions import _is_instant_speed

    data = card("The Wasp, Winsome Avenger")
    assert _is_instant_speed(data)  # Flash
    state = _state([], hand_names=["The Wasp, Winsome Avenger"])
    state.mana_pool.add("U", 1)
    state.mana_pool.add("C", 1)
    cast = next(a for a in legal_actions(state) if a.label.startswith("cast The Wasp"))
    cast.apply(state)
    perm = state.permanents_named("The Wasp, Winsome Avenger")[0]
    assert state.effective_power(perm) == 2
    assert not state.stack  # ETB modelled as a no-op: nothing queued


def test_aang_swift_savior_flash_flying_and_etb_noop():
    """Front face: 2/3 flash flyer whose airbend ETB is a goldfish no-op."""
    from mtg_goldfish.engine.actions import _is_instant_speed

    data = card("Aang, Swift Savior // Aang and La, Ocean's Fury")
    assert _is_instant_speed(data)  # Flash
    state = _state([], hand_names=["Aang, Swift Savior // Aang and La, Ocean's Fury"])
    state.mana_pool.add("W", 1); state.mana_pool.add("U", 1); state.mana_pool.add("C", 1)
    cast = next(a for a in legal_actions(state) if a.label.startswith("cast Aang"))
    cast.apply(state)
    perm = state.permanents_named("Aang, Swift Savior // Aang and La, Ocean's Fury")[0]
    assert not perm.transformed
    assert state.effective_power(perm) == 2 and state.effective_toughness(perm) == 3
    assert not state.stack  # airbend ETB modelled as a no-op — nothing queued


def test_aang_waterbend_transforms_to_5_5():
    """Waterbend {8}: Transform → Aang and La, Ocean's Fury (5/5)."""
    state = _state([])
    perm = state.put_on_battlefield(
        card("Aang, Swift Savior // Aang and La, Ocean's Fury"), fire_etb=False)
    perm.summoning_sick = False
    # Not enough mana → no transform option; with {8} it appears.
    assert not any("transform" in a.label.lower() for a in perm.impl.battlefield_actions(state, perm))
    state.mana_pool.add("C", 8)
    act = next(a for a in perm.impl.battlefield_actions(state, perm) if "transform" in a.label.lower())
    act.apply(state)
    assert perm.transformed
    assert perm.name == "Aang and La, Ocean's Fury"
    assert state.effective_power(perm) == 5 and state.effective_toughness(perm) == 5
    # Transformed: the waterbend option is gone.
    assert not perm.impl.battlefield_actions(state, perm)


def test_aang_and_la_attack_counters_tapped_creatures():
    """Back face attacks: +1/+1 on each tapped creature you control (attackers
    are tapped first, so both Aang and La and an already-tapped creature get one;
    the front face has no such trigger)."""
    from mtg_goldfish.engine.actions import DeclareAttackers
    from mtg_goldfish.engine.phases import Phase

    state = _state([])
    state.phase = Phase.DECLARE_ATTACKERS
    aang = state.put_on_battlefield(
        card("Aang, Swift Savior // Aang and La, Ocean's Fury"), fire_etb=False)
    aang.transformed = True  # Aang and La, Ocean's Fury
    aang.summoning_sick = False
    # A second creature, already tapped (e.g. from a prior activation).
    other = state.put_on_battlefield(card("Loyal Apprentice"), fire_etb=False)
    other.tapped = True
    DeclareAttackers().apply(state)
    assert aang.counters.get("+1/+1") == 1   # attacker tapped itself, then counted
    assert other.counters.get("+1/+1") == 1  # already-tapped creature counted


def test_aang_front_face_attack_has_no_trigger():
    from mtg_goldfish.engine.actions import DeclareAttackers
    from mtg_goldfish.engine.phases import Phase

    state = _state([])
    state.phase = Phase.DECLARE_ATTACKERS
    aang = state.put_on_battlefield(
        card("Aang, Swift Savior // Aang and La, Ocean's Fury"), fire_etb=False)
    aang.summoning_sick = False  # front face, not transformed
    DeclareAttackers().apply(state)
    assert not aang.counters.get("+1/+1")  # front face: no attack trigger
    assert not state.stack
