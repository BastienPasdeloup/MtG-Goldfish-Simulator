# MtG Goldfish Simulator

A solitaire ("goldfish") **Magic: the Gathering** simulator with a web
interface. You give it a deck and a set of properties written in plain English
("the commander is in play and 4 non-creature spells have been cast this
turn"), and it **exhaustively explores every line of play** up to a chosen
moment in the game to measure how often those properties can be satisfied.

Think of it as a search engine over the decision tree of a solo game: it does
not try to play *well*, it tries every legal sequence of decisions and counts
the ones that reach your target board state.

## Status

Early scaffold + a runnable vertical slice. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and the roadmap of
what is stubbed vs. implemented.

## Requirements

- Python ≥ 3.11 (3.13 recommended)
- [uv](https://docs.astral.sh/uv/)
- Optional: an `ANTHROPIC_API_KEY` in `.env` (copy from `.env.example`) to enable
  the LLM-backed features (turning English properties into code, auto-coding
  cards). Without a key the app falls back to a deterministic stub.

## Quick start

```bash
uv sync
uv run mtg-goldfish        # starts the web UI on http://127.0.0.1:8000
```

Then in the browser:

1. Choose a format (Duel Commander).
2. Paste a Moxfield deck URL and a name; validate. Commanders and companions
   are detected automatically.
3. In the session, define properties (trigger + English condition) and how many
   mulligans to take.
4. Review the generated property code, then run a simulation (X games, timeout
   per game) and watch the statistics update live.

## Layout

```
src/mtg_goldfish/
  config.py         environment / paths
  deck/             Moxfield import, Scryfall data, deck models
  formats/          format rules (Duel Commander)
  cards/            one file per implemented card + the registry
  engine/           game state, zones, phases, mana, actions, simulator
  properties/       property model, English->code compiler, evaluator
  llm/              provider interface + Anthropic + stub
  session/          session + result models and on-disk store
  web/              FastAPI app, WebSocket, static frontend
```

## Extending

- **New card:** drop a file in `src/mtg_goldfish/cards/` defining a `Card`
  subclass and decorate it with `@register`. It is picked up automatically.
- **New format:** add a module under `formats/` implementing the `Format`
  protocol and register it.
- **New rule / action:** implement an `Action` in `engine/actions.py`; the
  simulator enumerates all legal actions generically.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.
