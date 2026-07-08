"""Card behaviour layer.

Public surface: the `Card` base class, `CardAction` for enumerated choices,
the `register` decorator for new card files, and the registry helpers used by
the engine.
"""
from .base import Card, CardAction, UnimplementedCard
from .registry import (
    build_card,
    get_impl,
    implemented_names,
    is_implemented,
    load_all_cards,
    register,
)

__all__ = [
    "Card",
    "CardAction",
    "UnimplementedCard",
    "build_card",
    "get_impl",
    "implemented_names",
    "is_implemented",
    "load_all_cards",
    "register",
]
