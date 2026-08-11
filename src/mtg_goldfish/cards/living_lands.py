"""Living Lands — {3}{G} Enchantment.
All Forests are 1/1 creatures that are still lands.

Continuous global animate: every Forest becomes a 1/1 creature (still a land,
still taps for {G}) while Living Lands is in play — so your Forests can attack and
can die to damage / board wipes."""
from ._common import global_land_animator

global_land_animator("Living Lands", "Forest", "G")
