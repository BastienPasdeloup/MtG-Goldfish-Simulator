"""Tamiyo, Inquisitive Student // Tamiyo, Seasoned Scholar — {U} 0/3 flying.
Attacks: investigate (Clue token). Third draw in a turn: transform into the
planeswalker (loyalty 2). Back: +2 (defensive, no-op vs no attackers);
−3: return an instant/sorcery from graveyard to hand (+ any-colour mana if
it's green); −7: draw half your library. One loyalty ability per turn."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class TamiyoInquisitiveStudent(Card):
    card_name = "Tamiyo, Inquisitive Student // Tamiyo, Seasoned Scholar"

    def attack_stack_items(self, state, perm):
        if perm.transformed:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_attack(st, live)

        return [self.stack_ability(
            source_name=perm.name,
            label="Tamiyo: attack trigger",
            resolve=resolve,
            trigger_text=f"{perm.name} attacked",
            ability_text="Investigate",
        )]

    def draw_stack_items(self, state, perm, nth_this_turn):
        if perm.transformed or nth_this_turn != 3:
            return []

        def resolve(st, uid=perm.uid, nth=nth_this_turn):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_draw_card(st, live, nth)

        return [self.stack_ability(
            source_name=perm.name,
            label="Tamiyo: third-draw trigger",
            resolve=resolve,
            trigger_text="You drew your third card this turn",
            ability_text="Transform Tamiyo into Tamiyo, Seasoned Scholar",
        )]

    def on_attack(self, state, perm):
        if not perm.transformed:
            state.emit("Tamiyo attacks: investigate")
            state.make_token("Clue", 0, 0, "Token Artifact — Clue")

    def on_draw_card(self, state, perm, nth_this_turn):
        if not perm.transformed and nth_this_turn == 3:
            perm.transformed = True
            perm.summoning_sick = True
            perm.counters["loyalty"] = 2
            state.emit("Tamiyo: third draw this turn — transforms (loyalty 2)")

    def battlefield_actions(self, state, perm):
        if not perm.transformed or perm.turn_flags.get("loyalty_used"):
            return []
        actions = []

        def pay_plus2(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("loyalty_used"):
                return False
            p.turn_flags["loyalty_used"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + 2
            return True

        def resolve_plus2(st):
            p = st.find_permanent(perm.uid)
            if p is None:
                return None
            st.emit(f"Tamiyo +2 (loyalty {p.counters['loyalty']}) — defensive, no combat effect")
            return None

        actions.append(CardAction.activated(
            "Tamiyo: +2",
            pay_plus2,
            resolve_plus2,
            source_name="Tamiyo, Seasoned Scholar",
            ability_text="Add 2 loyalty",
        ))

        if perm.counters.get("loyalty", 0) >= 3:
            spells = sorted({
                c.name for c in state.graveyard
                if c.is_instant or c.is_sorcery
            })

            def make_minus3(name: str):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.turn_flags.get("loyalty_used"):
                        return False
                    p.turn_flags["loyalty_used"] = 1
                    p.counters["loyalty"] -= 3
                    return True

                def resolve(st):
                    c = next((x for x in st.graveyard if x.name == name), None)
                    if c is None:
                        return None
                    st.graveyard.remove(c)
                    st.hand.append(c)
                    st.emit(f"Tamiyo −3: return {name} to hand")
                    if "G" in c.colors:
                        st.mana_pool.add("G", 1)  # one mana of any colour
                        st.emit("Tamiyo −3: green card — add one mana")
                    return None
                return CardAction.activated(
                    f"Tamiyo: −3 return {name}",
                    pay,
                    resolve,
                    source_name="Tamiyo, Seasoned Scholar",
                    ability_text=f"Return {name} to hand",
                )

            actions.extend(make_minus3(n) for n in spells)

        if perm.counters.get("loyalty", 0) >= 7:
            def pay_minus7(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.turn_flags.get("loyalty_used"):
                    return False
                p.turn_flags["loyalty_used"] = 1
                p.counters["loyalty"] -= 7
                return True

            def resolve_minus7(st):
                n = (len(st.library) + 1) // 2
                st.emit(f"Tamiyo −7: draw {n}")
                st.draw(n)
                return None

            actions.append(CardAction.activated(
                "Tamiyo: −7 draw half the library",
                pay_minus7,
                resolve_minus7,
                source_name="Tamiyo, Seasoned Scholar",
                ability_text="Draw half your library",
            ))
        return actions
