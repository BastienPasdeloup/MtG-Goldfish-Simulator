"""Generate a card implementation file from oracle text via the LLM provider.

The model is asked to emit a `cards/<snake>.py` that subclasses `Card` and
registers itself. The output is validated (compiles, imports, and actually
registers the card) before it is written into the cards package and loaded.
Generation quality depends entirely on the selected model — small local
models will often fail validation; that failure is reported, not written.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..cards import registry
from ..deck.models import CardData
from . import get_provider

_CARDS_DIR = Path(registry.__file__).resolve().parent

_SYSTEM = '''\
You write ONE Python module implementing a Magic: the Gathering card's
behaviour for a solitaire (goldfish) simulator. Output ONLY Python code — no
prose, no markdown fences.

The module MUST:
- import: `from .base import Card, CardAction` and `from .registry import register`
  (import ManaAbility/ManaCost from `..engine.mana` only if used);
- define exactly one class decorated with `@register`, subclassing `Card`,
  with `card_name = "<EXACT card name>"`;
- override only the hooks it needs. Available hooks (all optional):
    cast_cost(state) -> ManaCost         is_castable(state) -> bool
    cast_actions(state) -> [CardAction]  hand_actions(state) -> [CardAction]
    etb_tapped(state) -> bool            etb_modes(state) -> [dict]
    mana_abilities(state) -> [ManaAbility]
    battlefield_actions(state, perm) -> [CardAction]
    on_etb(state, perm)  on_leave(state, perm)  on_resolve(state)
    on_phase(state, perm, phase)  on_attack(state, perm)
    on_other_etb(state, perm, entering)  extra_land_drops(state, perm) -> int
    dynamic_power(state, perm) -> int|None  dynamic_toughness(...) -> int|None

GameState methods you may call: state.draw(n), state.mill(n),
state.search_library(pred)->[CardData], state.take_from_library(card),
state.shuffle_library(), state.put_on_battlefield(card, tapped=bool),
state.make_token(name, power, toughness, type_line), state.emit(msg),
state.find_permanent(uid), state.life (int), state.mana_pool.add(color, n).
ManaAbility(amount=int, choices=(colors...)); colors are "W","U","B","R","G","C".

Rules:
- A land: override mana_abilities; set etb_tapped if it enters tapped.
- Opponent-only effects (counter target spell, "an opponent...", destroy an
  opponent's permanent) have no use in solitaire — make is_castable return
  False for such spells.
- NEVER make a choice inside apply(); enumerate one CardAction per choice.
- Output valid Python only.
'''


def _snake(name: str) -> str:
    front = name.split("//")[0].strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", front).strip("_")


def _strip_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


class CodegenError(RuntimeError):
    pass


def generate_card(card: CardData) -> str:
    """Generate, validate, and write a card module. Returns the module name.
    Raises CodegenError with a readable message on any failure."""
    provider = get_provider()
    if not getattr(provider, "is_real", False):
        raise CodegenError(
            "The offline stub can't write card code. Pick a local or API model "
            "in the model selector first."
        )

    module_name = _snake(card.name)
    if not module_name or module_name.startswith("_"):
        raise CodegenError(f"Can't derive a module name for {card.name!r}.")

    faces = ""
    for f in card.faces or []:
        faces += f"\n  FACE {f.name} [{f.type_line}] {f.mana_cost}: {f.oracle_text}"
    prompt = (
        f"Card name: {card.name}\n"
        f"Mana cost: {card.mana_cost or '-'}\n"
        f"Type: {card.type_line}\n"
        f"P/T: {card.power or '-'}/{card.toughness or '-'}\n"
        f"Oracle text: {card.oracle_text or '(none)'}{faces}\n\n"
        f'Write cards/{module_name}.py implementing "{card.name}".'
    )
    code = _strip_fences(provider.generate(_SYSTEM, prompt, max_tokens=2048))
    _validate_and_write(card, module_name, code)
    return module_name


def _validate_and_write(card: CardData, module_name: str, code: str) -> None:
    if "@register" not in code or "class" not in code:
        raise CodegenError("Model output did not define a registered Card subclass.")
    try:
        compile(code, f"<{module_name}>", "exec")
    except SyntaxError as exc:
        raise CodegenError(f"Generated code has a syntax error: {exc}") from exc

    path = _CARDS_DIR / f"{module_name}.py"
    backup = path.read_text() if path.exists() else None
    path.write_text(code)
    try:
        registry.load_module(module_name)
    except Exception as exc:  # import-time failure — roll back the file
        if backup is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(backup)
        raise CodegenError(f"Generated code failed to import: {exc}") from exc

    if not registry.is_implemented(card.name):
        if backup is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(backup)
        raise CodegenError(
            f"Generated module did not register {card.name!r} "
            f"(check its card_name matches exactly)."
        )
