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

# Restricted mana: mana that may be spent only for certain purposes. A restriction
# is a single-letter code (shown as a badge on the mana symbol) mapped to the set
# of payment "purposes" it is allowed for and a human tooltip.
#   "A" = artifact-only (Mishra's Workshop, Powerstone): cast artifact spells.
RESTRICTION_LABELS = {
    "A": "Can be spent only to cast artifact spells",
}
# Which payment purposes each restriction allows. `pay(..., allow=<purposes>)` is
# called with the current purpose; a restricted chunk is usable iff its code's
# allowed-purpose set intersects `allow`.
RESTRICTION_PURPOSES = {
    "A": frozenset({"artifact_spell"}),
}


def usable_restrictions(allow: frozenset) -> frozenset:
    """The restriction CODES whose allowed purposes intersect `allow`."""
    return frozenset(code for code, ps in RESTRICTION_PURPOSES.items() if ps & allow)

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

    `life_cost` models activation costs like Starting Town's
    "{T}, Pay 1 life: Add one mana of any color". A permanent may expose
    several abilities; the payment planner uses at most one per permanent.
    """

    amount: int = 1
    choices: tuple[str, ...] = (COLORLESS,)
    life_cost: int = 0
    #: Restriction code on the mana this ability produces ("" = unrestricted;
    #: "A" = artifact-only, e.g. Mishra's Workshop / a Powerstone token).
    restriction: str = ""

    @property
    def is_fixed(self) -> bool:
        return len(self.choices) == 1


@dataclass
class ManaPool:
    """Available mana, by colour (colourless under 'C'). `restricted` holds mana
    that may be spent only for certain purposes, keyed by restriction code then
    colour: e.g. {"A": {"C": 3}} = 3 artifact-only colourless. Restricted mana is
    always spent BEFORE unrestricted (use-it-or-lose-it), and only when the payment
    allows its restriction."""

    amounts: dict[str, int] = field(default_factory=lambda: {p: 0 for p in ALL_PIPS})
    restricted: dict[str, dict[str, int]] = field(default_factory=dict)

    def copy(self) -> "ManaPool":
        return ManaPool(amounts=dict(self.amounts),
                        restricted={k: dict(v) for k, v in self.restricted.items()})

    def add(self, color: str, n: int = 1) -> None:
        color = color.upper()
        self.amounts[color] = self.amounts.get(color, 0) + n

    def add_restricted(self, color: str, n: int, restriction: str) -> None:
        if not restriction:
            self.add(color, n)
            return
        cols = self.restricted.setdefault(restriction, {})
        cols[color.upper()] = cols.get(color.upper(), 0) + n

    def restricted_total(self) -> int:
        return sum(n for cols in self.restricted.values() for n in cols.values())

    def available(self, color: str, *, allow: frozenset = frozenset()) -> int:
        """Mana of `color` spendable for a payment with these purposes: unrestricted
        plus restricted mana whose restriction permits one of `allow`."""
        codes = usable_restrictions(allow)
        return self.amounts.get(color, 0) + sum(
            cols.get(color, 0) for code, cols in self.restricted.items() if code in codes)

    def total(self) -> int:
        return sum(self.amounts.values()) + self.restricted_total()

    def clear(self) -> None:
        for k in list(self.amounts):
            self.amounts[k] = 0
        self.restricted.clear()

    def can_pay(self, cost: ManaCost, *, allow: frozenset = frozenset()) -> bool:
        return self._pay(cost, commit=False, allow=allow)

    def pay(self, cost: ManaCost, *, allow: frozenset = frozenset()) -> bool:
        """Spend the cost if possible; returns True on success. `allow` is the set
        of payment purposes this spend is for (e.g. {"artifact_spell"}); restricted
        mana whose restriction permits one of those purposes may be used."""
        return self._pay(cost, commit=True, allow=allow)

    def _pay(self, cost: ManaCost, *, commit: bool, allow: frozenset = frozenset()) -> bool:
        codes = usable_restrictions(allow)
        unrestricted = dict(self.amounts)
        # Working copies of the restricted chunks we may draw from this payment.
        usable = {code: dict(cols) for code, cols in self.restricted.items() if code in codes}

        def avail(color: str) -> int:
            return unrestricted.get(color, 0) + sum(c.get(color, 0) for c in usable.values())

        def take(color: str, n: int) -> None:
            # Spend restricted (allowed) mana of this colour first, then unrestricted.
            for cols in usable.values():
                if n <= 0:
                    break
                t = min(cols.get(color, 0), n)
                if t:
                    cols[color] -= t
                    n -= t
            if n > 0:
                unrestricted[color] = unrestricted.get(color, 0) - n

        for color, need in cost.pips:
            if avail(color) < need:
                return False
            take(color, need)
        remaining_generic = cost.generic
        for color in (COLORLESS, *COLORS):
            if remaining_generic <= 0:
                break
            t = min(avail(color), remaining_generic)
            take(color, t)
            remaining_generic -= t
        if remaining_generic > 0:
            return False
        if commit:
            self.amounts = unrestricted
            for code in codes:
                if code in self.restricted:
                    self.restricted[code] = {c: n for c, n in usable[code].items() if n}
                    if not self.restricted[code]:
                        del self.restricted[code]
        return True
