"""Card implementation registry and loader.

Every module in this package that defines a `Card` subclass decorates it with
`@register`. `load_all_cards()` imports all sibling modules so those decorators
run, populating `_REGISTRY`. Lookups are by normalized card name.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from ..deck.models import CardData
from .base import Card, UnimplementedCard

if TYPE_CHECKING:
    from types import ModuleType

_REGISTRY: dict[str, type[Card]] = {}
_LOADED = False


def normalize(name: str) -> str:
    # Match on the front face of split/DFC names too.
    front = name.split("//")[0]
    return front.strip().lower()


def register(cls: type[Card]) -> type[Card]:
    """Class decorator: register a card implementation by its `card_name`."""
    if not cls.card_name:
        raise ValueError(f"{cls.__name__} must set `card_name` to register.")
    _REGISTRY[normalize(cls.card_name)] = cls
    return cls


def load_all_cards() -> None:
    """Import every card module so registrations take effect (idempotent)."""
    global _LOADED
    if _LOADED:
        return
    package = importlib.import_module(__package__)
    for mod in pkgutil.iter_modules(package.__path__):
        if mod.name in {"base", "registry", "__init__"}:
            continue
        importlib.import_module(f"{__package__}.{mod.name}")
    _LOADED = True


def is_implemented(name: str) -> bool:
    load_all_cards()
    return normalize(name) in _REGISTRY


def get_impl(name: str) -> type[Card] | None:
    load_all_cards()
    return _REGISTRY.get(normalize(name))


def build_card(data: CardData) -> Card:
    """Instantiate the best available behaviour for a card's data."""
    impl = get_impl(data.name)
    if impl is not None:
        return impl(data)
    return UnimplementedCard(data)


def implemented_names() -> set[str]:
    load_all_cards()
    return set(_REGISTRY.keys())
