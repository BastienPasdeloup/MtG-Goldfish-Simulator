"""Reprieve — {1}{W} Instant. Return target spell to its owner's hand; draw a
card. It needs a spell on the stack, which never exists in a solitaire goldfish,
so it is not castable here (its cantrip only happens on a successful cast)."""
from ._common import uncastable_spell

uncastable_spell("Reprieve", "returns a target spell on the stack to hand")
