"""Spell Pierce — {U} Instant. Counter target noncreature spell unless its
controller pays {2}. (Soft counter; uncastable in a goldfish with no opponent
spell on the stack — see cards._common.counterspell.)"""
from ._common import counterspell

counterspell("Spell Pierce", target=lambda c: not c.is_creature)
