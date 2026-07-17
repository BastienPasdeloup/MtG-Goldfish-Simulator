"""Stern Scolding — {U} Instant. Counter target creature spell with power or
toughness 2 or less. (Uncastable in a goldfish with no opponent spell on the
stack — see cards._common.counterspell.)"""
from ._common import counterspell


def _small_creature(card) -> bool:
    if not card.is_creature:
        return False

    def val(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return 0

    return val(card.power) <= 2 or val(card.toughness) <= 2


counterspell("Stern Scolding", target=_small_creature)
