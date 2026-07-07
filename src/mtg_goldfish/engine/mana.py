"""Mana primitives shared by the card layer and the engine.

Kept deliberately small: five colours plus colourless, generic cost paid by any
mana. Hybrid / Phyrexian / {X} are parsed leniently (treated as generic or a
fixed choice) so that unusual costs never crash the importer; refine per-card in
the card implementation when it matters.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

COLORS = ("W", "U", "B", "R", "G")
COLORLESS = "C"
ALL_PIPS = COLORS + (COLORLESS,)

_SYMBOL_RE = re.compile(r"\{([^}]+)\}")


@dataclass(frozen=True)
class ManaCost:
    """A mana cost: some generic amount plus per-colour pip requirements."""

    generic: int = 0
    pips: tuple[tuple[str, int], ...] = ()  # e.g. (("W", 1), ("U", 1))

    @property
    def pip_map(self) -> dict[str, int]:
        return dict(self.pips)

    @property
    def cmc(self) -> int:
        return self.generic + sum(n for _, n in self.pips)

    def is_free(self) -> bool:
        return self.cmc == 0

    @classmethod
    def parse(cls, cost_str: str) -> "ManaCost":
        generic = 0
        counts: Counter[str] = Counter()
        for sym in _SYMBOL_RE.findall(cost_str or ""):
            sym = sym.strip().upper()
            if sym.isdigit():
                generic += int(sym)
            elif sym == "X":
                continue  # {X} contributes 0 unless a card sets it
            elif sym in ALL_PIPS:
                counts[sym] += 1
            elif "/" in sym:
                # Hybrid / Phyrexian: pick the first colour pip if any, else generic.
                parts = [p for p in sym.split("/") if p in COLORS]
                if parts:
                    counts[parts[0]] += 1
                else:
                    generic += 1
            else:
                generic += 1
        pips = tuple((c, counts[c]) for c in ALL_PIPS if counts[c])
        return cls(generic=generic, pips=pips)

    def __str__(self) -> str:
        out = f"{{{self.generic}}}" if self.generic or not self.pips else ""
        for c, n in self.pips:
            out += f"{{{c}}}" * n
        return out or "{0}"


@dataclass(frozen=True)
class ManaAbility:
    """A mana-producing ability: add `amount` mana, all of one colour chosen
    from `choices`. Covers basics (choices=('W',)), rocks (Sol Ring:
    amount=2, choices=('C',)), duals, and identity-flexible sources
    (Command Tower: choices=commander colour identity).
    """

    amount: int = 1
    choices: tuple[str, ...] = (COLORLESS,)

    @property
    def is_fixed(self) -> bool:
        return len(self.choices) == 1


@dataclass
class ManaPool:
    """Available mana, by colour. Colourless is stored under 'C'."""

    amounts: dict[str, int] = field(default_factory=lambda: {p: 0 for p in ALL_PIPS})

    def copy(self) -> "ManaPool":
        return ManaPool(amounts=dict(self.amounts))

    def add(self, color: str, n: int = 1) -> None:
        color = color.upper()
        self.amounts[color] = self.amounts.get(color, 0) + n

    def total(self) -> int:
        return sum(self.amounts.values())

    def clear(self) -> None:
        for k in list(self.amounts):
            self.amounts[k] = 0

    def can_pay(self, cost: ManaCost) -> bool:
        return self._pay(cost, commit=False)

    def pay(self, cost: ManaCost) -> bool:
        """Spend the cost if possible; returns True on success."""
        return self._pay(cost, commit=True)

    def _pay(self, cost: ManaCost, *, commit: bool) -> bool:
        avail = dict(self.amounts)
        # 1) Satisfy coloured pips from their exact colour.
        for color, need in cost.pips:
            if avail.get(color, 0) < need:
                return False
            avail[color] -= need
        # 2) Satisfy generic from any remaining mana (spend colourless first).
        remaining_generic = cost.generic
        for color in (COLORLESS, *COLORS):
            if remaining_generic <= 0:
                break
            take = min(avail.get(color, 0), remaining_generic)
            avail[color] -= take
            remaining_generic -= take
        if remaining_generic > 0:
            return False
        if commit:
            self.amounts = avail
        return True
