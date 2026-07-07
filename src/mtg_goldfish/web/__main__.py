"""Entry point: `uv run mtg-goldfish` (or `python -m mtg_goldfish.web`)."""
from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("MTG_HOST", "127.0.0.1")
    port = int(os.environ.get("MTG_PORT", "8000"))
    print(f"MtG Goldfish Simulator → http://{host}:{port}")
    uvicorn.run("mtg_goldfish.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
