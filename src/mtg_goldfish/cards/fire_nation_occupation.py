"""Fire Nation Occupation — {2}{B} Enchantment. When it enters, create a 2/2 red
Soldier token with firebending 1. (Its "cast a spell during an opponent's turn"
trigger never fires in a goldfish, and firebending mana is not modelled.)"""
from .base import Card
from .registry import register


@register
class FireNationOccupation(Card):
    card_name = "Fire Nation Occupation"

    def on_etb(self, state, permanent):
        state.make_token(
            "Soldier", 2, 2, "Creature — Soldier",
            text="Firebending 1 (whenever it attacks, add {R} until end of combat).")
        state.emit("Fire Nation Occupation: create a 2/2 Soldier")
