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

`engine/simulator.py` runs an exhaustive search of a single game:

- **Per game** = one random shuffle (seeded by game index).
- **Mulligans (Y):** all ways to bottom `Y` of the opening 7 are tried.
- **Lines of play:** at every priority window, every legal action (play a
  distinct land, cast a distinct affordable spell, activate an ability, declare
  attackers, or pass) is a branch. Main phases allow sorcery-speed plays; other
  steps (upkeep, combat sub-steps, end step) open an **instant-speed window**
  where only instants, flash and instant-speed abilities are offered — and are
  only stopped at when such a play is actually available. Mana is *not* a branch
  point — `actions.plan_payment` taps sources deterministically. Actions that
  raise mid-apply are recorded as **bugs** (surfaced per game in the runs table
  via a 🐛 icon), never silently dropped.
- A game **succeeds** if some single line satisfies *all* properties at their
  trigger moments; per-property "satisfied in any line" is tracked separately
  for statistics. Timing: "**at** X of turn N" is checked exactly there;
  "**before** X of turn N" is checked at *every* checkpoint strictly before
  that moment (any earlier phase or turn). Satisfaction is sticky along a
  line, and the search stops as soon as every property has been verified.
- **Viability pruning:** a branch is dropped the moment any unsatisfied
  property can no longer be verified on it (its "at" moment is past, or its
  "before" deadline reached) — no descendant could make the game a success.
  Per-property statistics therefore count satisfaction in *viable* lines.
- The **search strategy is selectable** (`SEARCH_MODES`): greedy best-first on
  a board-progress score (**default**), or BFS. Every mode visits the same
  states — only the order differs — so winning lines are found sooner and
  timeouts bite later.
- The search records a tree node for **every state created** (including
  passing priority), so the per-game graph shows all considered states; the
  winning line is marked bottom-up via parent links.
- Exhaustive with no node cap: a game's search runs until whichever comes
  first — the per-game wall-clock **timeout**, every property satisfied on some
  line, or no remaining branch able to satisfy the properties (the frontier
  drains).
- **Parallel tree exploration:** games run strictly in order, one at a time,
  but each game's tree is explored across CPU cores (`ProcessPoolExecutor`,
  spawn context, one worker per core minus one, pool reused for the whole
  run). Mid-game states are unpicklable (factory-built card classes), so no
  state crosses a process boundary: the master expands the tree level by
  level until enough subtrees hang at some depth (`_expand_to_split`), and
  each worker deterministically REBUILDS the same game from the seed, replays
  that exact expansion (same helper → same leaves in the same order), and
  explores only its share (`leaf j` goes to worker `j % num_parts`). Subtrees
  graft back into the master's tree — state-for-state identical to a
  sequential search. Workers recompile properties from their picklable
  `PropertySpec`s. The first success sets a manager Event that stops the
  other workers; user Stop is a second Event, both checked time-throttled in
  the search's hot path. Tiny games that drain during the shallow expansion
  never touch the workers.
- **Fake shuffling** (a UI toggle, on by default): `GameState.shuffle_library`
  never reorders the library — only the cards whose position the player knows
  (`mark_known_in_library`: Brainstorm put-backs, tutor tops, scry/mulligan
  bottoms) are reinserted at random spots. Keeps the library near-constant
  across lines so differently-shuffled lines don't over-evaluate "find X"
  probabilities.
- **Crash-safe & resumable runs:** the web runner persists the run's entry
  after every completed game (adaptive back-off when saving is slow); a run
  found dangling as "running" is marked **interrupted**, not dropped, and both
  stopped and interrupted runs can be **resumed** — `run_simulation` re-runs
  exactly the missing game indices with the stored stats as the starting
  counts (identical seeds ⇒ identical games).

## What is real vs. approximate

Engine mechanics (exercised by the sample cEDH deck, all 100 cards exact or
documented per-card):
- Moxfield import + Scryfall enrichment + role validation.
- Turn structure with phase-entry triggers (upkeep, fading, ...), land drops
  with **enter modes** (shocklands pay-2/tapped, Multiversal Passage type
  choice), casting from hand/command zone (commander tax), **activated
  abilities** (fetchlands, equip, draw engines, channel, planeswalker
  loyalty), **alternative costs** (evoke, escape, cycling, Phyrexian mana),
  dynamic costs (domain), library search with deterministic seeded shuffles,
  tokens, equipment with death triggers (Skullclamp), transform DFCs,
  MDFC land faces, draw/cast triggers, exile-play (impulse), and
  **goldfish combat** (attack a phantom opponent, damage/lifelink,
  attack & combat-damage triggers).
- Choices are **branches** of the exhaustive search: fetch targets, tutor
  targets, Brainstorm put-backs, surveil, discards, ETB targets, X values,
  payment variants. Mana payment itself stays deterministic.
- Exhaustive line-of-play + mulligan search with property checking, timeouts,
  live stats over WebSocket, session/result persistence.
- English→code property compilation (Anthropic when keyed; a regex stub
  offline): resolves approximate card names against the deck, reports a
  confidence + clarification note, and runs against a documented game-long
  event/state API that distinguishes *playing/casting* a card from a permanent
  *entering the battlefield* (`played_on`/`cast_on` vs `entered_battlefield`).

Documented approximations (each card file's docstring states its own):
- Opponent-facing text does nothing (no opponent): counterspells are never
  castable; "opponents can't..." statics are no-ops; targeted removal can only
  hit your own permanents (or the phantom opponent's face for damage).
- Combat is all-or-nothing (no attack subsets), no blockers, vehicles never
  crew/attack; combat-damage loot discards are deterministic (no branching
  inside triggers).
- A few deterministic choices where enumeration would explode: escape/evidence
  exile picks, March's white-card exiles, Nick Fury's bottom-order shuffle.
- **Unimplemented cards** (not in this deck) still play as vanilla
  approximations and are flagged red in the UI.
- The property sandbox restricts builtins but is not a security boundary
  (single-user local tool).

## Extending

- **New card:** add `cards/<snake_name>.py` with a `@register` `Card` subclass;
  override `mana_abilities` / `on_etb` / `on_resolve` as needed. Auto-discovered.
- **New action/rule:** add an `Action` in `engine/actions.py`; `legal_actions`
  enumerates generically.
- **New format:** subclass `Format`, register in `formats/__init__.py`.
- **Card auto-implementation** (the per-card 🔧 and the global 🔧 on the
  decklist header) asks the selected model to generate a `cards/*.py` from the
  card's oracle text. Output is validated (compiles, imports, and actually
  registers the card) before it is written and hot-loaded; failures are
  reported and the card keeps its vanilla approximation.
- **Model selection** (`llm/catalog.py`, the ⚙ Model dialog): the offline stub
  (default; property conditions only), a local open model via Ollama
  (`llm/ollama_provider.py` — private, downloaded with `ollama pull`), or the
  Anthropic API (needs a key). The choice persists to `data/llm_config.json`.
