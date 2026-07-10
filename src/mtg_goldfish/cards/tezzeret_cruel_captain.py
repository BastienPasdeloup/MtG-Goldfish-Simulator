"""Tezzeret, Cruel Captain — {3} Legendary Planeswalker — Tezzeret.
Has no printed starting loyalty; instead it gains a loyalty counter whenever
an artifact you control enters. One loyalty ability per turn (sorcery speed):
 0: untap target artifact or creature (branch; +1/+1 counter if it's an
    artifact creature);
 −3: search your library for an artifact with mana value 1 or less, put it
    into your hand, then shuffle (branch per target).
The −7 emblem is out of scope."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class TezzeretCruelCaptain(Card):
    card_name = "Tezzeret, Cruel Captain"

    def on_etb(self, state, permanent):
        permanent.counters["loyalty"] = 0

    def other_etb_stack_items(self, state, perm, entering):
        if "artifact" not in entering.type_line.lower():
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Tezzeret: artifact trigger",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield as an artifact",
            ability_text="Put a loyalty counter on Tezzeret",
        )]

    def on_other_etb(self, state, perm, entering):
        if "artifact" in entering.type_line.lower():
            perm.counters["loyalty"] = perm.counters.get("loyalty", 0) + 1
            state.emit(f"Tezzeret: artifact entered — loyalty {perm.counters['loyalty']}")

    def battlefield_actions(self, state, perm):
        if perm.turn_flags.get("loyalty_used"):
            return []
        acts = []

        # 0: untap target artifact or creature.
        targets = {}
        for p in state.battlefield:
            if (p.tapped and (p.is_creature_now or "artifact" in p.type_line.lower())
                    and p.name not in targets):
                targets[p.name] = p.uid

        def make_zero(uid):
            def pay(st):
                p = st.find_permanent(perm.uid)
                t = st.find_permanent(uid)
                if p is None or t is None or p.turn_flags.get("loyalty_used"):
                    return False
                p.turn_flags["loyalty_used"] = 1
                return True

            def resolve(st):
                p = st.find_permanent(perm.uid)
                t = st.find_permanent(uid)
                if p is None or t is None:
                    return None
                t.tapped = False
                if t.is_creature_now and "artifact" in t.type_line.lower():
                    t.counters["+1/+1"] = t.counters.get("+1/+1", 0) + 1
                st.emit(f"Tezzeret 0: untap {t.name}")
                return None
            return CardAction.activated(
                f"Tezzeret: 0 untap {state.find_permanent(uid).name if state.find_permanent(uid) else uid}",
                pay,
                resolve,
                source_name="Tezzeret, Cruel Captain",
                ability_text="Untap target artifact or creature",
            )

        for name, uid in targets.items():
            acts.append(make_zero(uid))

        # −3: search for an artifact with mv <= 1 to hand.
        if perm.counters.get("loyalty", 0) >= 3:
            for target in state.search_library(
                lambda c: "artifact" in c.type_line.lower() and not c.is_land and c.cmc <= 1
            ):
                def make_minus3(name):
                    def pay(st):
                        p = st.find_permanent(perm.uid)
                        if p is None or p.turn_flags.get("loyalty_used"):
                            return False
                        p.turn_flags["loyalty_used"] = 1
                        p.counters["loyalty"] -= 3
                        return True

                    def resolve(st):
                        p = st.find_permanent(perm.uid)
                        if p is None:
                            return None
                        card = next((c for c in st.library if c.name == name), None)
                        if card is None:
                            return None
                        st.take_from_library(card)
                        st.shuffle_library()
                        st.hand.append(card)
                        st.emit(f"Tezzeret −3: search {name} to hand — shuffle")
                        return None
                    return CardAction.activated(
                        f"Tezzeret: −3 search {name}",
                        pay,
                        resolve,
                        source_name="Tezzeret, Cruel Captain",
                        ability_text=f"Search {name} to hand",
                    )
                acts.append(make_minus3(target.name))

        return acts
