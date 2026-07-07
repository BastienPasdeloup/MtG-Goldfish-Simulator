"""Scryfall API client with an on-disk cache.

Scryfall asks clients to set a User-Agent, throttle requests, and prefer the
bulk `/cards/collection` endpoint. We cache each resolved card by its exact
name so repeated deck imports (and hover-image lookups) hit the network once.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from ..config import CONFIG
from .models import CardData, CardFace

SCRYFALL_API = "https://api.scryfall.com"
_USER_AGENT = "MtGGoldfishSimulator/0.1 (personal deck-testing tool)"
_COLLECTION_BATCH = 75


class ScryfallError(RuntimeError):
    pass


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()) + ".json"


def _parse_face(raw: dict) -> CardFace:
    img = (raw.get("image_uris") or {}).get("normal")
    return CardFace(
        name=raw.get("name", ""),
        mana_cost=raw.get("mana_cost", "") or "",
        type_line=raw.get("type_line", "") or "",
        oracle_text=raw.get("oracle_text", "") or "",
        power=raw.get("power"),
        toughness=raw.get("toughness"),
        loyalty=raw.get("loyalty"),
        image_normal=img,
    )


def card_data_from_scryfall(raw: dict) -> CardData:
    """Convert a raw Scryfall card object into our `CardData` model."""
    faces = [_parse_face(f) for f in raw.get("card_faces", [])]
    image = (raw.get("image_uris") or {}).get("normal")
    if image is None and faces:
        image = faces[0].image_normal
    # For multi-faced cards Scryfall may omit top-level oracle_text/type_line.
    type_line = raw.get("type_line", "") or (faces[0].type_line if faces else "")
    oracle = raw.get("oracle_text", "")
    if not oracle and faces:
        oracle = "\n//\n".join(f.oracle_text for f in faces)
    return CardData(
        name=raw.get("name", ""),
        mana_cost=raw.get("mana_cost", "") or (faces[0].mana_cost if faces else ""),
        cmc=float(raw.get("cmc", 0.0) or 0.0),
        type_line=type_line,
        oracle_text=oracle,
        colors=raw.get("colors", []) or [],
        color_identity=raw.get("color_identity", []) or [],
        keywords=raw.get("keywords", []) or [],
        power=raw.get("power"),
        toughness=raw.get("toughness"),
        loyalty=raw.get("loyalty"),
        layout=raw.get("layout", "normal"),
        image_normal=image,
        faces=faces,
        scryfall_id=raw.get("id"),
    )


class ScryfallClient:
    def __init__(self, cache_dir: Path | None = None, throttle_s: float = 0.1) -> None:
        self.cache_dir = cache_dir or CONFIG.scryfall_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.throttle_s = throttle_s
        self._mem: dict[str, CardData] = {}

    # ---- cache helpers -----------------------------------------------------
    def _cache_path(self, name: str) -> Path:
        return self.cache_dir / _safe_filename(name)

    def _read_cache(self, name: str) -> CardData | None:
        if name in self._mem:
            return self._mem[name]
        path = self._cache_path(name)
        if path.exists():
            try:
                data = CardData.model_validate_json(path.read_text())
                self._mem[name] = data
                return data
            except Exception:
                return None
        return None

    def _write_cache(self, card: CardData) -> None:
        self._mem[card.name] = card
        try:
            self._cache_path(card.name).write_text(card.model_dump_json(indent=2))
        except Exception:
            pass  # cache is best-effort

    # ---- public API --------------------------------------------------------
    def get_named(self, name: str) -> CardData:
        """Resolve a single card by (fuzzy-tolerant) exact name."""
        cached = self._read_cache(name)
        if cached:
            return cached
        with httpx.Client(headers={"User-Agent": _USER_AGENT}, timeout=20) as client:
            resp = client.get(f"{SCRYFALL_API}/cards/named", params={"exact": name})
            if resp.status_code == 404:
                resp = client.get(f"{SCRYFALL_API}/cards/named", params={"fuzzy": name})
            if resp.status_code != 200:
                raise ScryfallError(f"Scryfall lookup failed for {name!r}: {resp.status_code}")
            card = card_data_from_scryfall(resp.json())
            self._write_cache(card)
            time.sleep(self.throttle_s)
            return card

    def get_collection(self, names: list[str]) -> dict[str, CardData]:
        """Resolve many cards, batching uncached names through /cards/collection.

        Returns a mapping keyed by the *requested* name. Names Scryfall cannot
        resolve are simply absent from the result.
        """
        result: dict[str, CardData] = {}
        missing: list[str] = []
        for name in names:
            cached = self._read_cache(name)
            if cached:
                result[name] = cached
            else:
                missing.append(name)

        if not missing:
            return result

        with httpx.Client(headers={"User-Agent": _USER_AGENT}, timeout=30) as client:
            for start in range(0, len(missing), _COLLECTION_BATCH):
                batch = missing[start : start + _COLLECTION_BATCH]
                payload = {"identifiers": [{"name": n} for n in batch]}
                resp = client.post(f"{SCRYFALL_API}/cards/collection", json=payload)
                if resp.status_code != 200:
                    raise ScryfallError(
                        f"Scryfall collection request failed: {resp.status_code}"
                    )
                body = resp.json()
                # Match returned cards back to requested names (case-insensitive).
                requested = {n.lower(): n for n in batch}
                for raw in body.get("data", []):
                    card = card_data_from_scryfall(raw)
                    self._write_cache(card)
                    key = requested.get(card.name.lower())
                    if key is None:
                        # Fuzzy/alias: fall back to matching any requested substring.
                        key = next(
                            (orig for low, orig in requested.items() if low in card.name.lower()),
                            card.name,
                        )
                    result[key] = card
                time.sleep(self.throttle_s)
        return result
