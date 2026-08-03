"""Ardyn, the Usurper — {5}{B}{B}{B} 4/4. Demons you control have menace,
lifelink, and haste. Starscourge — At the beginning of combat on your turn, exile
up to one target creature card from a graveyard; if you did, create a token that's
a copy of it, except it's a 5/5 black Demon.
The token is modelled as a vanilla 5/5 black Demon with haste (the copy's own
abilities are not adopted, matching Lazotep Quarry's 4/4 Zombie approximation)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class ArdynTheUsurper(Card):
    card_name = "Ardyn, the Usurper"

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.BEGIN_COMBAT:
            return []
        if not any(c.is_creature for c in state.graveyard):
            return []

        def resolve(st, uid=perm.uid):
            names, seen = [], set()
            for c in st.graveyard:
                if c.is_creature and c.name not in seen:
                    seen.add(c.name)
                    names.append(c.name)
            if not names:
                return None

            def fn(s, name):
                if name is None:
                    s.emit("Ardyn: Starscourge — exile nothing")
                    return None
                c = next((x for x in s.graveyard if x.name == name), None)
                if c is None:
                    return None
                s.graveyard.remove(c)
                s.exile.append(c)
                tok = s.make_token("Demon", 5, 5, "Token Creature — Demon", colors=["B"])
                tok.summoning_sick = False   # Ardyn grants Demons haste
                s.emit(f"Ardyn: Starscourge — exile {name}, create a 5/5 black Demon")
                return None

            return branch_over(st, [None] + names, fn)

        return [self.stack_ability(
            source_name=perm.name, label="Ardyn: Starscourge (begin combat)",
            resolve=resolve, trigger_text="At the beginning of combat on your turn",
            ability_text="Exile a creature card from a graveyard → a 5/5 black Demon token")]
