# Architecture

## Overview

The app is a solitaire MtG simulator. The data flows in one direction:

```
Moxfield URL ──▶ deck/ (import + Scryfall) ──▶ Session (session/)
                                                  │
   properties/ (English ──LLM──▶ code) ◀──────────┤
                                                  ▼
                          engine/ (exhaustive search) ──▶ stats + winning lines
                                                  ▲
                       cards/ (per-card behaviour registry)
```

The **web/** layer is a thin FastAPI shell over these packages; the engine and
domain logic have no web dependency and can be driven from a script or tests.

## Packages

| Package | Responsibility |
|---|---|
| `config` | Env/paths (`ANTHROPIC_API_KEY`, `MTG_DATA_DIR`, model). |
| `deck` | `CardData`/`Deck` models, Scryfall client (cached), Moxfield importer. Commander/companion roles come from Moxfield's boards and are cross-checked against Scryfall facts. |
| `formats` | `Format` rules (`DuelCommander`): starting life/hand, deck validation. |
| `cards` | Runtime card **behaviour**. One file per card + a registry. `build_card` returns the registered `Card` or an `UnimplementedCard` vanilla approximation. |
| `engine` | `GameState` (cloneable), turn `phases`, `mana`, `actions` (+ mana-payment planner), and the exhaustive `simulator`. |
| `properties` | `PropertySpec` model, LLM `compiler` (English→`check(state)`), and a sandboxed `evaluator`. |
| `llm` | Provider interface + Anthropic implementation + deterministic offline `StubProvider`. |
| `session` | `Session`/`SimResult` models + JSON-file `SessionStore`. |
| `web` | FastAPI routes, WebSocket `Hub`, threaded `SimulationRunner`, static frontend. |

## The search

`engine/simulator.py` does a depth-first search of a single game:

- **Per game** = one random shuffle (seeded by game index).
- **Mulligans (Y):** all ways to bottom `Y` of the opening 7 are tried.
- **Lines of play:** in each main phase, every legal action (play a distinct
  land, cast a distinct affordable spell, or pass) is a branch. Mana is *not* a
  branch point — `actions.plan_payment` taps sources deterministically.
- A game **succeeds** if some single line satisfies *all* properties at their
  trigger moments; per-property "satisfied in any line" is tracked separately
  for statistics.
- Bounded by a per-game wall-clock **timeout** and a node cap; the search stops
  as soon as all properties are met.

## What is real vs. approximate (v0.1)

Implemented and exercised:
- Moxfield import + Scryfall enrichment + role validation.
- Turn structure, land drops, casting from hand + command zone (with commander
  tax), mana solving across colours/identity sources, summoning sickness for
  mana dorks.
- Exhaustive line-of-play + mulligan search with property checking, timeouts,
  live stats over WebSocket, session/result persistence.
- English→code property compilation (Anthropic when keyed; a regex stub offline).
- Example cards: 5 basics, Sol Ring, Arcane Signet, Command Tower, Llanowar
  Elves, Lightning Bolt.

Deliberately approximate / not yet modelled (extension points, not blockers):
- **Unimplemented cards play as vanilla**: permanents enter and count toward
  board/spell tallies but their text does nothing; unimplemented lands tap for
  one mana of any commander-identity colour. Results involving them are
  approximate — the UI flags them red.
- No combat/opponent, no triggered/activated abilities beyond mana, no ETB
  effects, no stack interaction, no cleanup discard, no companion mechanic,
  no `{X}`/hybrid nuance in payment.
- The property sandbox restricts builtins but is not a security boundary
  (single-user local tool).

## Extending

- **New card:** add `cards/<snake_name>.py` with a `@register` `Card` subclass;
  override `mana_abilities` / `on_etb` / `on_resolve` as needed. Auto-discovered.
- **New action/rule:** add an `Action` in `engine/actions.py`; `legal_actions`
  enumerates generically.
- **New format:** subclass `Format`, register in `formats/__init__.py`.
- **Card auto-implementation** (the 🔧 icon) is wired in the UI and returns 501
  server-side — the intended hook is to have the LLM generate a `cards/*.py`
  file from the card's oracle text.
