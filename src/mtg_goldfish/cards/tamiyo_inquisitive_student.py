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

        def plus2(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("loyalty_used"):
                return None
            p.turn_flags["loyalty_used"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + 2
            st.emit(f"Tamiyo +2 (loyalty {p.counters['loyalty']}) — defensive, no combat effect")
            return None

        actions.append(CardAction("Tamiyo: +2", plus2))

        if perm.counters.get("loyalty", 0) >= 3:
            spells = sorted({
                c.name for c in state.graveyard
                if c.is_instant or c.is_sorcery
            })

            def make_minus3(name: str):
                def fn(st):
                    p = st.find_permanent(perm.uid)
                    c = next((x for x in st.graveyard if x.name == name), None)
                    if p is None or c is None or p.turn_flags.get("loyalty_used"):
                        return None
                    p.turn_flags["loyalty_used"] = 1
                    p.counters["loyalty"] -= 3
                    st.graveyard.remove(c)
                    st.hand.append(c)
                    st.emit(f"Tamiyo −3: return {name} to hand")
                    if "G" in c.colors:
                        st.mana_pool.add("G", 1)  # one mana of any colour
                        st.emit("Tamiyo −3: green card — add one mana")
                    return None
                return fn

            actions.extend(CardAction(f"Tamiyo: −3 return {n}", make_minus3(n)) for n in spells)

        if perm.counters.get("loyalty", 0) >= 7:
            def minus7(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.turn_flags.get("loyalty_used"):
                    return None
                p.turn_flags["loyalty_used"] = 1
                p.counters["loyalty"] -= 7
                n = (len(st.library) + 1) // 2
                st.emit(f"Tamiyo −7: draw {n}")
                st.draw(n)
                return None

            actions.append(CardAction("Tamiyo: −7 draw half the library", minus7))
        return actions
