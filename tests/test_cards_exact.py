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


def test_aang_swift_savior_flash_flying_and_etb_no_target():
    """Front face: 2/3 flash flyer; with no other creature its airbend ETB has
    no legal target and does nothing (no branch)."""
    from mtg_goldfish.engine.actions import _is_instant_speed

    data = card("Aang, Swift Savior // Aang and La, Ocean's Fury")
    assert _is_instant_speed(data)  # Flash
    state = _state([], hand_names=["Aang, Swift Savior // Aang and La, Ocean's Fury"])
    state.mana_pool.add("W", 1); state.mana_pool.add("U", 1); state.mana_pool.add("C", 1)
    cast = next(a for a in legal_actions(state) if a.label.startswith("cast Aang"))
    result = cast.apply(state)
    assert result is None  # no airbend target → no branching
    perm = state.permanents_named("Aang, Swift Savior // Aang and La, Ocean's Fury")[0]
    assert not perm.transformed
    assert state.effective_power(perm) == 2 and state.effective_toughness(perm) == 3
    assert not state.stack  # airbend ETB resolved with nothing to do


def test_aang_airbends_own_creature_and_recasts_for_two():
    """Airbend a creature you control: it is exiled and becomes castable for
    {2} while it stays exiled; recasting re-triggers its ETB."""
    state = _state([])
    aang = card("Aang, Swift Savior // Aang and La, Ocean's Fury")
    victim = card("Loyal Apprentice")  # cheap creature with an ETB
    apprentice = state.put_on_battlefield(victim, fire_etb=False)
    perm = state.put_on_battlefield(aang, fire_etb=False)
    branches = perm.impl.on_etb(state, perm)
    # airbend nothing + airbend the Loyal Apprentice
    assert branches is not None and len(branches) == 2
    airbended = next(b for b in branches
                     if not b.permanents_named("Loyal Apprentice"))
    assert any(c.name == "Loyal Apprentice" for c in airbended.airbend_exile)
    assert any(c.name == "Loyal Apprentice" for c in airbended.exile)
    # It can now be recast for {2} (any two mana).
    airbended.mana_pool.add("C", 2)
    recast = next(a for a in legal_actions(airbended)
                  if a.label.startswith("cast Loyal Apprentice")
                  and "airbend" in a.label)
    recast.apply(airbended)
    assert airbended.permanents_named("Loyal Apprentice")  # re-entered
    assert not airbended.airbend_exile  # consumed


def test_aang_airbend_modal_card_casts_any_face_for_two():
    """A modal (double-faced) card in airbend exile offers each face with a
    mana cost as a {2} cast — including the non-front face."""
    from mtg_goldfish.deck.models import CardData, CardFace

    modal = CardData(
        name="Front Bolt // Back Giant",
        type_line="Instant",
        mana_cost="{R}",
        faces=[
            CardFace(name="Front Bolt", type_line="Instant", mana_cost="{R}"),
            CardFace(name="Back Giant", type_line="Creature — Giant",
                     mana_cost="{6}{R}", power="7", toughness="7"),
        ],
    )
    state = _state([])
    state.exile.append(modal)
    state.airbend_exile.append(modal)
    state.mana_pool.add("C", 2)
    labels = [a.label for a in legal_actions(state) if "airbend" in a.label]
    # Both faces with a mana cost are castable for {2}.
    assert any("(Front Bolt)" in l for l in labels)
    assert any("(Back Giant)" in l for l in labels)
    # Cast the big back face for {2}: it enters as a 7/7 on its back face.
    giant = next(a for a in legal_actions(state)
                 if "airbend" in a.label and "(Back Giant)" in a.label)
    giant.apply(state)
    perms = state.permanents_named("Back Giant")
    assert perms and perms[0].transformed
    assert state.effective_power(perms[0]) == 7
    assert not state.airbend_exile
    # The viewer shows the BACK face on the stack while it is being cast.
    on_stack = [f for f in state.log
                if f.get("stack") and "(on the stack)" in f["desc"]]
    assert on_stack and on_stack[-1]["stack"][0]["name"] == "Back Giant"
    assert not state.stack_face  # cleared once off the stack


def test_aang_airbends_a_spell_being_cast_with_instant_speed():
    """With instant-speed play on, airbend can hit a spell you are casting: the
    hand spell is cast (its cost paid) then exiled before it resolves, and can
    be recast for {2}. Off by default (no spell target without instant_speed)."""
    from mtg_goldfish.deck.models import CardData, CardFace

    modal = CardData(
        name="Cheap Bolt // Huge Beast",
        type_line="Instant",
        mana_cost="{R}",
        faces=[
            CardFace(name="Cheap Bolt", type_line="Instant", mana_cost="{R}"),
            CardFace(name="Huge Beast", type_line="Creature — Beast",
                     mana_cost="{7}", power="8", toughness="8"),
        ],
    )
    # Default (instant_speed off): a spell in hand is NOT an airbend target.
    state = _state([])
    state.hand.append(modal)
    perm = state.put_on_battlefield(card("Aang, Swift Savior // Aang and La, Ocean's Fury"),
                                    fire_etb=False)
    assert perm.impl.on_etb(state, perm) is None  # no creature, no spell target

    # instant_speed on: airbend the spell you're casting.
    state = _state([])
    state.instant_speed = True
    state.hand.append(modal)
    state.mana_pool.add("R", 1)  # to cast the front (its {R} cost is paid)
    perm = state.put_on_battlefield(card("Aang, Swift Savior // Aang and La, Ocean's Fury"),
                                    fire_etb=False)
    branches = perm.impl.on_etb(state, perm)
    assert branches is not None and len(branches) == 2  # nothing + the spell
    airbended = next(b for b in branches if b.airbend_exile)
    assert any(c.name == modal.name for c in airbended.airbend_exile)
    assert modal not in airbended.hand and modal not in airbended.stack  # cast, off stack
    assert airbended.mana_pool.total() == 0  # the {R} cost was paid
    # Recast the big back face for {2}.
    airbended.mana_pool.add("C", 2)
    beast = next(a for a in legal_actions(airbended)
                 if "airbend" in a.label and "(Huge Beast)" in a.label)
    beast.apply(airbended)
    assert airbended.permanents_named("Huge Beast")


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


# --------------------------------------------------------------------------
# Event 87792 — 3rd place (Atraxa, Grand Unifier) card implementations
# --------------------------------------------------------------------------
def test_atraxa_reveal_puts_one_of_each_type_into_hand():
    state = _state([], commander="Atraxa, Grand Unifier")
    state.hand = []
    reps = {
        "creature": "Subtlety", "instant": "Lose Focus",
        "sorcery": "Wrath of the Skies", "artifact": "Arcane Signet",
        "enchantment": "World War Hulk", "planeswalker": "Teferi, Time Raveler",
        "land": "Swamp",
    }
    top = [card(n) for n in reps.values()] + [card("Swamp"), card("Swamp"), card("Swamp")]
    assert len(top) == 10
    state.library = list(top)
    atx = state.put_on_battlefield(card("Atraxa, Grand Unifier"), fire_etb=False)
    # Simulate the trigger's resolution context so effects are attributed to
    # Atraxa's triggered ability (the engine sets this in resolve_triggered_abilities).
    state.resolving = ("triggered", "Atraxa, Grand Unifier")
    branches = atx.impl.on_etb(state, atx)
    assert branches
    # Some branch takes one card of EACH of the seven present types.
    best = max(branches, key=lambda b: len(b.hand))
    assert len(best.hand) == 7
    heads = [c.type_line.split("—")[0].lower() for c in best.hand]
    for t in reps:
        assert any(t in h for h in heads), t
    # Nothing is lost: taken to hand + the rest bottomed == the original ten.
    assert len(best.hand) + len(best.library) == 10
    # The cards are PUT INTO HAND (not drawn): the put_in_hand tracking counts
    # exactly the 7 Atraxa's triggered ability added, and it is not a draw.
    assert len(best.cards_put_in_hand_by("Atraxa", via_kind="triggered")) == 7
    assert best.cards_put_in_hand_by("Atraxa", via_kind="triggered") >= 3
    assert best.cards_drawn_by("Atraxa") == 0


def test_dream_halls_casts_by_discarding_a_color_sharing_card():
    # Dream Halls lets Teferi (W/U) be cast by pitching a blue card (Lose Focus).
    state = _state([], hand_names=["Teferi, Time Raveler", "Lose Focus"],
                   commander="Atraxa, Grand Unifier")
    state.put_on_battlefield(card("Dream Halls"), fire_etb=False)
    acts = [a for a in legal_actions(state)
            if "Dream Halls" in a.label and "Teferi, Time Raveler" in a.label
            and "Lose Focus" in a.label]
    assert acts, [a.label for a in legal_actions(state) if "Dream Halls" in a.label]
    acts[0].apply(state)
    assert state.has_permanent_named("Teferi, Time Raveler")     # cast for free
    assert "Lose Focus" in state.graveyard_names()               # pitched as the cost


def test_world_war_hulk_chapter_one_grants_free_cast():
    state = _state([], commander="Teferi, Time Raveler")
    wwh = state.put_on_battlefield(card("World War Hulk"), fire_etb=False)
    state.queue_entry_triggers([wwh])
    state.settle()
    assert wwh.counters.get("lore") == 1
    assert any(g.get("creature") and set(g.get("colors", ())) == {"R", "G"}
               for g in state.free_casts)
    # A green creature in hand may now be cast without paying its mana cost.
    state.hand.append(card("Atraxa, Grand Unifier"))
    labels = [a.label for a in legal_actions(state)]
    assert any(l.startswith("cast Atraxa") and "without paying" in l for l in labels), labels


def test_world_war_hulk_chapter_two_and_three():
    state = _state([], commander="Teferi, Time Raveler")
    wwh = state.put_on_battlefield(card("World War Hulk"), fire_etb=False)
    creat = state.put_on_battlefield(card("Subtlety"), fire_etb=False)
    p0, t0 = state.effective_power(creat), state.effective_toughness(creat)

    # Chapter II — three +1/+1 counters on a target creature.
    wwh.counters["lore"] = 1
    branches = wwh.impl._chapter(state, wwh, 2)
    b2 = branches[0]
    tp = next(p for p in b2.battlefield if p.name == "Subtlety")
    assert tp.counters.get("+1/+1") == 3

    # Chapter III — double P/T + trample, then sacrifice the Saga.
    wwh.counters["lore"] = 2
    branches = wwh.impl._chapter(state, wwh, 3)
    b3 = branches[0]
    tp = next(p for p in b3.battlefield if p.name == "Subtlety")
    assert b3.effective_power(tp) == 2 * p0
    assert b3.effective_toughness(tp) == 2 * t0
    assert b3.has_keyword(tp, "trample")
    assert not any(p.name == "World War Hulk" for p in b3.battlefield)  # sacrificed


def test_teferi_hero_plus_one_draws_and_untaps_lands_at_end_step():
    from mtg_goldfish.engine import simulator

    state = _state([], commander="Atraxa, Grand Unifier")
    state.library = [card("Swamp"), card("Island")]
    state.put_on_battlefield(card("Teferi, Hero of Dominaria"), fire_etb=False)
    l1 = state.put_on_battlefield(card("Swamp"), fire_etb=False)
    l2 = state.put_on_battlefield(card("Island"), fire_etb=False)
    l1.tapped = l2.tapped = True
    drawn0 = state.cards_drawn

    plus = next(a for a in legal_actions(state)
                if "Teferi, Hero" in a.label and "untap 2 lands" in a.label)
    plus.apply(state)
    tef = next(p for p in state.battlefield if p.name.startswith("Teferi, Hero"))
    assert state.cards_drawn == drawn0 + 1
    assert tef.counters["loyalty"] == 5
    assert state.untap_lands_end_step == 2

    state.phase = Phase.END_STEP
    simulator._apply_step_entry(state)
    assert not l1.tapped and not l2.tapped
    assert state.untap_lands_end_step == 0


def test_teferi_time_raveler_plus_one_gives_sorceries_flash():
    state = _state([], commander="Atraxa, Grand Unifier")
    state.put_on_battlefield(card("Teferi, Time Raveler"), fire_etb=False)
    plus = next(a for a in legal_actions(state)
                if "Teferi, Time Raveler" in a.label and "sorceries gain flash" in a.label)
    plus.apply(state)
    assert state.cast_sorcery_as_flash is True
    tef = next(p for p in state.battlefield if p.name.startswith("Teferi, Time"))
    assert tef.counters["loyalty"] == 5


def test_teferi_time_raveler_minus_three_bounces_and_draws():
    state = _state([], commander="Atraxa, Grand Unifier")
    state.library = [card("Swamp"), card("Island")]
    state.put_on_battlefield(card("Teferi, Time Raveler"), fire_etb=False)
    state.put_on_battlefield(card("Subtlety"), fire_etb=False)
    minus = next(a for a in legal_actions(state)
                 if "Teferi, Time Raveler" in a.label and "bounce up to one" in a.label)
    branches = minus.apply(state)
    assert isinstance(branches, list) and len(branches) >= 2
    assert any(any(c.name == "Subtlety" for c in b.hand) for b in branches)  # bounce branch
    for b in branches:
        assert b.cards_drawn >= 1  # every mode draws a card


# --------------------------------------------------------------------------
# Modal DFC "spell front // land back" cards (Waterlogged Teachings, ...)
# --------------------------------------------------------------------------
def test_mdfc_spell_front_land_back_plays_as_land_side():
    # "Instant // Land": the generic land drop must NOT be offered (it would
    # enter the FRONT Instant face). The back land is played via the card's own
    # action and enters showing the LAND side, in the lands part of the board.
    state = _state([], hand_names=["Waterlogged Teachings // Inundated Archive"])
    labels = [a.label for a in legal_actions(state)]
    assert "play land Waterlogged Teachings // Inundated Archive" not in labels
    play = next(a for a in legal_actions(state) if "play land Inundated Archive" in a.label)
    play.apply(state)
    perm = state.battlefield[-1]
    view = state._perm_view(perm)
    assert perm.transformed
    assert view["name"] == "Inundated Archive"                 # land side visible
    assert view["is_land"] and not view["is_creature"]         # placed with the lands
    assert "Inundated Archive" in state.lands_entered_on(3)     # attributed as the land


def test_mdfc_spell_front_is_castable():
    state = _state([], hand_names=["Waterlogged Teachings // Inundated Archive"])
    for _ in range(5):
        p = state.put_on_battlefield(card("Island"), fire_etb=False)
        p.tapped = False
        p.summoning_sick = False
    labels = [a.label for a in legal_actions(state)]
    assert any(l.startswith("cast Waterlogged Teachings") for l in labels)


def test_mdfc_creature_front_is_castable_no_front_land_drop():
    # "Creature // Land": the front creature is castable; no generic front land drop.
    state = _state([], hand_names=["Boggart Trawler // Boggart Bog"])
    for _ in range(3):
        p = state.put_on_battlefield(card("Swamp"), fire_etb=False)
        p.tapped = False
        p.summoning_sick = False
    labels = [a.label for a in legal_actions(state)]
    assert any(l.startswith("cast Boggart") for l in labels)
    assert "play land Boggart Trawler // Boggart Bog" not in labels


def test_weather_maker_removes_three_charge_for_three_damage():
    """{T}, remove three charge counters: 3 damage to any target."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    wm = g.put_on_battlefield(card("Weather Maker"))
    wm.counters["charge"] = 3
    opp = [a for a in wm.impl.battlefield_actions(g, wm) if "opponent" in a.label]
    assert opp, "no 3-damage-to-opponent action offered"
    before = g.opponent_life
    opp[0].apply(g)
    assert g.opponent_life == before - 3
    assert wm.counters["charge"] == 0 and wm.tapped
    # unavailable below three charges
    wm.counters["charge"] = 2
    wm.tapped = False
    assert not wm.impl.battlefield_actions(g, wm)


def test_lazotep_quarry_reanimates_as_4_4_zombie():
    """{X}{2},{T},Sac a Desert: exile a graveyard creature (MV X), make a 4/4 Zombie."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    lq = g.put_on_battlefield(card("Lazotep Quarry"))
    lq.tapped = False
    g.graveyard.append(CardData(name="Fallen Beast", type_line="Creature — Beast",
                                cmc=0, power="5", toughness="5"))
    g.mana_pool.add("R", 2)  # X=0 -> {2}
    acts = lq.impl.battlefield_actions(g, lq)
    assert len(acts) == 1
    acts[0].apply(g)
    zombie = next((p for p in g.battlefield if "Zombie" in p.type_line), None)
    assert zombie and zombie.base_power() == 4 and zombie.base_toughness() == 4
    assert any(c.name == "Fallen Beast" for c in g.exile)   # exiled from graveyard
    assert g.find_permanent(lq.uid) is None                 # sacrificed itself


def test_natures_rhythm_harmonize_from_graveyard():
    """Harmonize: cast from the graveyard (then exile) to tutor a creature into play."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    nr = card("Nature's Rhythm")
    g.graveyard.append(nr)
    g.library = [CardData(name="Elf Mystic", type_line="Creature — Elf", cmc=1,
                          power="1", toughness="1")]
    g.mana_pool.add("G", 5)  # X=1 -> {1}{G}{G}{G}{G}
    acts = build_card(nr).graveyard_actions(g)
    assert acts and any("harmonize" in a.label for a in acts)
    next(a for a in acts if "harmonize" in a.label).apply(g)
    assert g.has_permanent_named("Elf Mystic")
    assert any(c.name == "Nature's Rhythm" for c in g.exile)


def test_brainsurge_draws_four_puts_two_back_on_top():
    """Draw four, then put ANY two from the hand back on top (incl. cards already
    held), in a chosen order. Net +2, and the put-back card is drawn next."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    g.library = [CardData(name=f"Card{i}", type_line="Instant", cmc=0) for i in range(6)]
    g.hand = [CardData(name="Held", type_line="Instant", cmc=0)]  # a pre-existing hand card
    branches = build_card(card("Brainsurge")).on_resolve(g)
    # Draw 4 -> hand of 5 distinct names; ordered distinct pairs = 5*4 = 20.
    assert branches is not None and len(branches) == 20
    # Net +2 cards in hand (5 drawn-into-hand minus 2 put back), library -2.
    assert all(len(b.hand) == 3 and len(b.library) == 4 for b in branches)
    # A line that puts the pre-existing "Held" card back on top exists (proves
    # put-back is from the whole hand, not just the four drawn) and it's on top.
    held_top = [b for b in branches if b.library[0].name == "Held"]
    assert held_top


def test_venom_attack_sacrifices_for_cards():
    """Venom (back face) attacking: sacrifice a creature -> draw X (= its MV)."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    venom = g.put_on_battlefield(card("Eddie Brock // Venom, Lethal Protector"))
    venom.transformed = True
    fodder = g.put_on_battlefield(CardData(name="Spare Body", type_line="Creature — Human",
                                           cmc=2, power="2", toughness="2"))
    g.library = [CardData(name=f"D{i}", type_line="Instant", cmc=0) for i in range(3)]
    branches = venom.impl.on_attack(g, venom)
    assert branches is not None and len(branches) == 2  # no-sac + sac Spare Body
    sac = [b for b in branches if b.find_permanent(fodder.uid) is None]
    assert sac and len(sac[0].hand) == 2                # drew X=2
    # the front face (Eddie Brock) has no attack trigger
    venom.transformed = False
    assert venom.impl.on_attack(g, venom) is None


def test_smugglers_copter_crews_attacks_and_loots():
    """Crew 1 makes it a 3/3 flying artifact creature; attacking loots (draw/discard)."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    cop = g.put_on_battlefield(card("Smuggler's Copter"))
    cop.summoning_sick = False                    # controlled since last turn
    bird = g.put_on_battlefield(CardData(name="Bird", type_line="Creature — Bird",
                                         cmc=0, power="1", toughness="1"))
    bird.summoning_sick = True                    # can't attack, but can crew
    acts = cop.impl.battlefield_actions(g, cop)
    assert len(acts) == 1 and acts[0].label.startswith("crew")
    acts[0].apply(g)
    assert cop.is_creature_now and g.effective_power(cop) == 3
    assert g.find_permanent(bird.uid).tapped      # the bird crewed
    # Attack loot: don't loot, or draw one then discard it (one distinct card).
    g.library = [CardData(name="Dig", type_line="Instant", cmc=0)]
    branches = cop.impl.on_attack(g, cop)
    assert branches is not None and len(branches) == 2
    looted = [b for b in branches if "Dig" in b.graveyard_names()]
    assert looted, "the loot branch should draw then discard"


def test_shorikai_can_crew_eight():
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    sho = g.put_on_battlefield(card("Shorikai, Genesis Engine"))
    sho.summoning_sick = False
    # No creatures -> can't crew 8.
    assert not [a for a in sho.impl.battlefield_actions(g, sho) if a.label.startswith("crew")]
    big = g.put_on_battlefield(CardData(name="Giant", type_line="Creature — Giant",
                                        cmc=0, power="9", toughness="9"))
    big.summoning_sick = True
    crew = [a for a in sho.impl.battlefield_actions(g, sho) if a.label.startswith("crew")]
    assert len(crew) == 1
    crew[0].apply(g)
    assert sho.is_creature_now and g.effective_power(sho) == 8


def test_six_retrace_casts_permanents_from_graveyard():
    """Retrace: cast a nonland permanent from the graveyard by discarding a land."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    six = g.put_on_battlefield(card("Six"))
    g.graveyard.append(CardData(name="Grizzly Bears", type_line="Creature — Bear",
                                cmc=2, mana_cost="{1}{G}", power="2", toughness="2"))
    g.hand.append(CardData(name="Forest", type_line="Basic Land — Forest", cmc=0))
    g.mana_pool.add("G", 2)
    acts = six.impl.alt_cast_actions(g, six)
    assert len(acts) == 1 and "retrace" in acts[0].label
    acts[0].apply(g)
    assert g.has_permanent_named("Grizzly Bears")            # retraced into play
    assert "Forest" in g.graveyard_names()                   # discarded land
    assert not any(c.name == "Grizzly Bears" for c in g.graveyard)
    # Needs a land in hand to discard.
    g.hand.clear()
    g.graveyard.append(CardData(name="Grizzly Bears", type_line="Creature — Bear",
                                cmc=2, mana_cost="{1}{G}", power="2", toughness="2"))
    assert not six.impl.alt_cast_actions(g, six)


def test_torture_pit_amplifies_noncombat_damage():
    """Torture Pit: your noncombat damage to an opponent deals +2 (via
    GameState.damage_opponent); combat damage is unaffected."""
    from mtg_goldfish.engine.game_state import GameState
    g = GameState()
    assert g.damage_opponent(3) == 3                    # no amplifier yet
    tp = g.put_on_battlefield(card("Spiked Corridor // Torture Pit"))
    tp.counters["torture"] = 1
    opp = g.opponent_life
    assert g.damage_opponent(3) == 5                    # +2
    assert g.opponent_life == opp - 5
    # The 'any target' burn helper (used by Lightning Bolt, Devils, ...) routes
    # opponent damage through damage_opponent, so it's amplified.
    from mtg_goldfish.cards._common import damage_any_target_options
    opp_apply = dict(damage_any_target_options(g))["opponent"]
    opp2 = g.opponent_life
    opp_apply(g, 3)                                     # 3 -> 5 with Torture Pit
    assert g.opponent_life == opp2 - 5
    # Two Torture Pits stack (+2 each); the Spiked (Devil) door alone does NOT.
    g2 = GameState()
    for _ in range(2):
        p = g2.put_on_battlefield(card("Spiked Corridor // Torture Pit"))
        p.counters["torture"] = 1
    assert g2.damage_opponent(1) == 5                   # 1 + 2 + 2
    g3 = GameState()
    g3.put_on_battlefield(card("Spiked Corridor // Torture Pit")).counters["spiked"] = 1
    assert g3.damage_opponent(4) == 4


def test_ba_sing_se_earthbend_animates_a_land_permanently():
    """{2}{G}, {T}: Earthbend 2 — target land you control becomes a permanent
    2/2 land creature with haste (survives cleanup, attacks next turn too)."""
    from mtg_goldfish.engine.simulator import _apply_step_entry
    state = _state([])
    state.phase = Phase.PRECOMBAT_MAIN
    bs = state.put_on_battlefield(card("Ba Sing Se"))
    bs.summoning_sick = False
    bs.tapped = False
    for _ in range(4):
        f = state.put_on_battlefield(card("Forest"))
        f.summoning_sick = False
    target = next(p for p in state.battlefield if p.name == "Forest")
    act = next(a for a in build_card(bs.card).battlefield_actions(state, bs)
               if a.label.endswith("Forest"))
    act.apply(state)
    live = state.find_permanent(target.uid)
    assert live.is_creature_now and live.is_land          # still a land, now a creature
    assert state.effective_power(live) == 2 and state.effective_toughness(live) == 2
    assert state.has_keyword(live, "Haste") and not live.summoning_sick
    assert state.find_permanent(bs.uid).tapped             # paid its own {T}
    # A normal man-land loses its animation at cleanup; earthbend is permanent.
    state.phase = Phase.CLEANUP
    _apply_step_entry(state)
    assert state.find_permanent(target.uid).is_creature_now


def test_malcolm_combat_damage_branches_and_free_casts_at_four_chorus():
    """Malcolm's combat-damage trigger now BRANCHES: chorus++ then draw, one
    line per distinct discardable card, and — at 4+ chorus for a castable
    nonland discard — an extra line that free-casts it from the graveyard.
    Combat damage is dealt in every branch."""
    from mtg_goldfish.engine.phases import Phase
    from mtg_goldfish.engine.simulator import _apply_step_entry

    # Under 4 chorus: only the discard choice branches (no free cast).
    state = _state([])
    m = state.put_on_battlefield(card("Malcolm, Alluring Scoundrel"))
    m.counters["chorus"] = 1
    state.library = [card("Forest")]           # drawn card (a land)
    state.hand = [card("Psychic Frog")]        # a castable nonland
    low = build_card(m.card).on_combat_damage(state, m, 2)
    assert len(low) == 2                        # discard Forest / discard Frog
    assert not any(b.has_permanent_named("Psychic Frog") for b in low)

    # At 4 chorus, through the real COMBAT_DAMAGE pipeline: the step BRANCHES.
    state = _state([])
    state.turn, state.phase = 5, Phase.COMBAT_DAMAGE
    m = state.put_on_battlefield(card("Malcolm, Alluring Scoundrel"))
    m.summoning_sick = False
    m.counters["chorus"] = 3                     # this hit makes it 4
    state.library = [card("Forest")]
    state.hand = [card("Psychic Frog")]
    state.attackers = [m.uid]
    branches = _apply_step_entry(state)
    assert branches is not None and len(branches) == 3
    # chorus counter reached 4 everywhere; combat damage (2) dealt in every line.
    assert all(b.find_permanent(m.uid).counters.get("chorus") == 4 for b in branches)
    assert all(b.opponent_life == 18 for b in branches)
    # Exactly one line free-cast the discarded Frog onto the battlefield.
    assert sum(1 for b in branches if b.has_permanent_named("Psychic Frog")) == 1


def test_mirrorpool_copies_target_creature_with_its_abilities():
    """Mirrorpool: {4}{C}, {T}, Sacrifice: create a token that's a copy of target
    creature you control — a full copy (P/T + abilities), sacrificing Mirrorpool."""
    state = _state([])
    state.phase = Phase.PRECOMBAT_MAIN
    mp = state.put_on_battlefield(card("Mirrorpool"))
    mp.tapped = False
    for _ in range(5):                       # colorless sources for {4}{C}
        s = state.put_on_battlefield(card("Mirrorpool"))
        s.tapped = False
        s.summoning_sick = False
    frog = state.put_on_battlefield(card("Psychic Frog"))
    frog.summoning_sick = False
    act = next(a for a in build_card(mp.card).battlefield_actions(state, mp)
               if "Psychic Frog" in a.label)
    act.apply(state)
    frogs = state.permanents_named("Psychic Frog")
    assert len(frogs) == 2                    # original + token copy
    token = next(p for p in frogs if p.is_token)
    assert state.effective_power(token) == 1 and state.effective_toughness(token) == 2
    assert not state.has_permanent_named("Mirrorpool") or \
        any(not p.is_token for p in state.permanents_named("Mirrorpool"))  # activated one gone
    assert "Mirrorpool" in state.graveyard_names()   # sacrificed as a cost

    # The copy adopts the original's (branching) ETB: copying Arboreal Grazer
    # branches on its "put a land from hand" ETB.
    state = _state([])
    state.phase = Phase.PRECOMBAT_MAIN
    mp = state.put_on_battlefield(card("Mirrorpool"))
    mp.tapped = False
    for _ in range(5):
        s = state.put_on_battlefield(card("Mirrorpool"))
        s.tapped = False
        s.summoning_sick = False
    grazer = state.put_on_battlefield(card("Arboreal Grazer"))
    grazer.summoning_sick = False
    state.hand = [card("Forest")]
    act = next(a for a in build_card(mp.card).battlefield_actions(state, mp)
               if "Arboreal Grazer" in a.label)
    branches = act.apply(state)
    assert branches is not None and len(branches) == 2
    assert all(sum(1 for p in b.battlefield if p.name == "Arboreal Grazer" and p.is_token) == 1
               for b in branches)
    assert any(b.has_permanent_named("Forest") for b in branches)
    assert any(not b.has_permanent_named("Forest") for b in branches)


def test_springheart_nantuko_landfall_copies_the_enchanted_creature():
    """Landfall while bestowed on a creature BRANCHES: pay {1}{G} for a token
    copy of that creature, or make the 1/1 Insect. Unattached → just the Insect.
    A land entering during an atomic (non-branching) resolution must not crash."""
    from mtg_goldfish.engine.actions import PlayLand

    def setup(attached):
        state = _state([])
        state.phase = Phase.PRECOMBAT_MAIN
        host = state.put_on_battlefield(card("Psychic Frog"))
        host.summoning_sick = False
        for _ in range(3):                       # mana lands down BEFORE attaching
            f = state.put_on_battlefield(card("Forest"))
            f.summoning_sick = False
        sh = state.put_on_battlefield(card("Springheart Nantuko"))
        sh.summoning_sick = False
        if attached:
            sh.attached_to = host.uid
            sh.counters["bestowed"] = 1
        state.hand = [card("Forest")]
        state.lands_played_this_turn = 0
        return state, host

    # Attached: playing a land branches into copy-the-Frog vs 1/1 Insect.
    state, host = setup(True)
    branches = PlayLand("Forest").apply(state)
    assert branches is not None and len(branches) == 2
    assert any(sum(1 for p in b.battlefield if p.name == "Psychic Frog" and p.is_token) == 1
               for b in branches)
    assert any(b.permanents_named("Insect") for b in branches)

    # Unattached: no landfall branch, just the 1/1 Insect.
    state, host = setup(False)
    branches = PlayLand("Forest").apply(state)
    end = branches[0] if branches else state
    assert len(end.permanents_named("Insect")) == 1
    assert not any(p.is_token for p in end.permanents_named("Psychic Frog"))

    # A land entering during a non-branching resolution must not raise.
    state, host = setup(True)
    state.put_on_battlefield(card("Forest"))     # fire_etb=True → settle_nonbranching
    assert len(state.permanents_named("Insect")) == 1


def test_shifting_woodland_delirium_becomes_a_graveyard_permanent_copy():
    """Delirium — {2}{G}{G}: becomes a copy of target permanent card in your
    graveyard until end of turn (full copy: name/types/P/T/abilities), reverting
    to a land at cleanup. Gated on 4+ card types; only permanents are targetable."""
    from mtg_goldfish.engine.simulator import _apply_step_entry

    state = _state([])
    state.phase = Phase.PRECOMBAT_MAIN
    state.turn = 6
    sw = state.put_on_battlefield(card("Shifting Woodland"))
    sw.tapped = False
    sw.summoning_sick = False
    for _ in range(4):                       # {2}{G}{G} from other sources
        f = state.put_on_battlefield(card("Forest"))
        f.tapped = False
        f.summoning_sick = False
    # 4 card types in graveyard -> delirium on; a creature + a noncreature permanent
    # + two nonpermanents (which must NOT be offered as copy targets).
    for n in ["Psychic Frog", "Skullclamp", "Lightning Bolt", "Tropical Island"]:
        state.graveyard.append(card(n))

    acts = build_card(sw.card).battlefield_actions(state, sw)
    labels = [a.label for a in acts]
    assert any("Psychic Frog" in l for l in labels)          # creature permanent
    assert any("Skullclamp" in l for l in labels)            # artifact permanent
    assert not any("Lightning Bolt" in l for l in labels)    # instant — not a permanent

    next(a for a in acts if "Psychic Frog" in a.label).apply(state)
    live = state.find_permanent(sw.uid)
    assert live.name == "Psychic Frog" and live.is_creature_now and not live.is_land
    assert state.effective_power(live) == 1 and state.effective_toughness(live) == 2
    assert not live.tapped and not live.summoning_sick        # untapped: can attack
    assert build_card(live.card).mana_abilities(state) == []  # lost the land's {G}

    # Cleanup reverts it to the land (name, type, and mana ability restored).
    state.phase = Phase.CLEANUP
    _apply_step_entry(state)
    live = state.find_permanent(sw.uid)
    assert live.name == "Shifting Woodland" and live.is_land and not live.is_creature_now
    assert build_card(live.card).mana_abilities(state)        # {G} back


def test_fear_of_missing_out_delirium_extra_combat_phase():
    """Delirium — when FOMO attacks (first time), untap target creature AND take
    an additional combat phase. The turn loops END_COMBAT → BEGIN_COMBAT once
    (GameState.extra_combats), letting the untapped creature swing again."""
    from mtg_goldfish.engine.actions import DeclareAttackers, combat_actions
    from mtg_goldfish.engine.simulator import _apply_step_entry, _goto_next_phase

    def run(delirium):
        state = _state([])
        state.turn = 6
        state.phase = Phase.DECLARE_ATTACKERS
        fomo = state.put_on_battlefield(card("Fear of Missing Out"))
        fomo.summoning_sick = False
        frog = state.put_on_battlefield(card("Psychic Frog"))   # 1/2
        frog.summoning_sick = False
        if delirium:                          # 4 card types in the graveyard
            for n in ["Psychic Frog", "Lightning Bolt", "Skullclamp", "Tropical Island"]:
                state.graveyard.append(card(n))
        combats, start, guard = 0, state.opponent_life, 0
        while state.phase != Phase.POSTCOMBAT_MAIN and guard < 40:
            guard += 1
            if state.phase == Phase.DECLARE_ATTACKERS and combat_actions(state):
                DeclareAttackers().apply(state)
                combats += 1
                continue
            branches = _apply_step_entry(state)
            state = branches[0] if branches else state
            _goto_next_phase(state)
        return combats, start - state.opponent_life, state.extra_combats

    combats, dmg, left = run(True)
    assert combats == 2 and left == 0        # one extra combat, consumed
    assert dmg == 4                          # FOMO(2)+Frog(1), then untapped Frog(1)

    combats, dmg, left = run(False)
    assert combats == 1 and dmg == 3         # no delirium: single combat, no untap


class _DmgProp:
    def __init__(self, pid, timing, phase, turn, fn):
        self.id, self.timing, self.phase, self.turn = pid, timing, phase, turn
        self.description = pid
        self._fn = fn

    def evaluate(self, state):
        return self._fn(state)


def test_fear_of_missing_out_extra_combat_reachable_by_the_search():
    """End-to-end: through the real search, a damage threshold that a single
    combat cannot reach IS reached when FOMO's delirium grants an extra combat
    phase (the untapped attacker swings twice). Without delirium it is not."""
    from mtg_goldfish.deck.models import Deck, DeckBoard, DeckEntry
    from mtg_goldfish.engine import SimulationConfig, run_simulation

    gy = ["Psychic Frog", "Lightning Bolt", "Skullclamp", "Tropical Island"]  # 4 types
    entries = [DeckEntry(quantity=1, board=DeckBoard.COMMANDER,
                         card=card("Nick Fury, Agent of S.H.I.E.L.D."))]
    for n in ["Fear of Missing Out"] + gy:
        entries.append(DeckEntry(quantity=1, board=DeckBoard.MAINBOARD, card=card(n)))
    for _ in range(30):
        entries.append(DeckEntry(quantity=1, board=DeckBoard.MAINBOARD, card=card("Forest")))
    deck = Deck(name="t", entries=entries)

    # FOMO (2 power) + a 2/2 Bear token in play. One combat deals at most 4;
    # with the extra combat the untapped Bear swings again for 6 total.
    def fixed(with_delirium):
        return {"turn": 5, "phase": "precombat_main",
                "battlefield": ["Fear of Missing Out",
                                {"name": "Bear", "token": True, "power": 2, "toughness": 2,
                                 "type_line": "Token Creature — Bear"}],
                "graveyard": gy if with_delirium else []}

    prop = _DmgProp("dmg", "at", Phase.POSTCOMBAT_MAIN, 5, lambda s: s.opponent_life <= 15)

    hit = run_simulation(deck, [prop], SimulationConfig(
        num_games=1, timeout_per_game_s=8, fixed_config=fixed(True), parallel_workers=1))
    assert hit.successes == 1                 # extra combat gets to 6 damage (opp 14)

    miss = run_simulation(deck, [prop], SimulationConfig(
        num_games=1, timeout_per_game_s=8, fixed_config=fixed(False), parallel_workers=1))
    assert miss.successes == 0                # no delirium: single combat, opp 16 > 15
