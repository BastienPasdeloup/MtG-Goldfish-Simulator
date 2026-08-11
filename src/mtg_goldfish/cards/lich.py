"""Lich — {B}{B}{B}{B} Enchantment.
As this enchantment enters, you lose life equal to your life total.
You don't lose the game for having 0 or less life.
If you would gain life, draw that many cards instead.
Whenever you're dealt damage, sacrifice that many nontoken permanents. If you
can't, you lose the game.
When this enchantment is put into a graveyard from the battlefield, you lose the
game.

Modelled: ETB drops your life to 0; while it is in play any life you WOULD gain is
drawn as cards instead (GameState.gain_life checks `replaces_lifegain_with_draw`);
each point of damage you take sacrifices a nontoken permanent (via on_owner_damaged
— the classic Lich + Zuran Orb draw engine). The two "you lose the game" clauses
are noted but not enforced (a solitaire goldfish has no player-loss subsystem)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Lich(Card):
    card_name = "Lich"

    def on_etb(self, state, permanent):
        state.emit(f"Lich: lose {state.life} life (life becomes 0)")
        state.life = 0

    def replaces_lifegain_with_draw(self, state, perm):
        return True

    def on_owner_damaged(self, state, perm, amount):
        # Sacrifice `amount` nontoken permanents (least valuable first: lands, then
        # others), preferring not to sacrifice Lich itself.
        for _ in range(amount):
            victims = [p for p in state.battlefield
                       if not p.is_token and p.uid != perm.uid]
            if not victims:
                state.emit("Lich: no permanent to sacrifice — you would lose the game")
                return None
            victims.sort(key=lambda p: (0 if p.is_land else 1, state.effective_power(p)))
            v = victims[0]
            state.emit(f"Lich: sacrifice {v.name} (damage taken)")
            state.leaves_battlefield(v, "graveyard", reason="sacrifice")
        return None

    def on_leave(self, state, permanent):
        state.emit("Lich: put into graveyard — you would lose the game (not enforced)")
