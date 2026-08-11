"""Scryfall API client with an on-disk cache.

Scryfall asks clients to set a User-Agent, throttle requests, and prefer the
bulk `/cards/collection` endpoint. We cache each resolved card by its exact
name so repeated deck imports (and hover-image lookups) hit the network once.
"""
from __future__ import annotations

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
    token_parts = [
        {"name": p.get("name", ""), "type_line": p.get("type_line", ""),
         "scryfall_id": p.get("id")}
        for p in raw.get("all_parts", []) or []
        if p.get("component") == "token"
    ]
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
        set=raw.get("set", "") or "",
        token_parts=token_parts,
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
    def get_by_id(self, scryfall_id: str) -> CardData | None:
        """Resolve a card (e.g. a token) by its Scryfall id, cached by id."""
        if not scryfall_id:
            return None
        key = "__id__" + scryfall_id
        cached = self._read_cache(key)
        if cached:
            return cached
        try:
            with httpx.Client(headers={"User-Agent": _USER_AGENT}, timeout=20) as client:
                resp = client.get(f"{SCRYFALL_API}/cards/{scryfall_id}")
                if resp.status_code != 200:
                    return None
                card = card_data_from_scryfall(resp.json())
                # Cache under the id key (token names collide across sets).
                self._mem[key] = card
                try:
                    self._cache_path(key).write_text(card.model_dump_json(indent=2))
                except Exception:
                    pass
                time.sleep(self.throttle_s)
                return card
        except Exception:
            return None

    def _get(self, client: "httpx.Client", path: str, params: dict, tries: int = 5):
        """GET with Scryfall rate-limit (429) handling: honour Retry-After (or
        exponential backoff) so a burst of fetches doesn't just fail."""
        resp = None
        for attempt in range(tries):
            resp = client.get(f"{SCRYFALL_API}{path}", params=params)
            if resp.status_code != 429:
                return resp
            wait = 0.0
            try:
                wait = float(resp.headers.get("Retry-After", "0"))
            except ValueError:
                pass
            time.sleep(min(max(wait, 0.4 * (2 ** attempt)), 12.0))
        return resp

    def _oldest_raw(self, client: "httpx.Client", name: str) -> dict | None:
        """The EARLIEST paper printing of `name` (so images use the first
        published art). Oracle text on Scryfall is the current wording for every
        printing, so only the art/set differs. Returns None if the exact-name
        prints search finds nothing (caller falls back to /cards/named).

        Alpha (`lea`) is EXCLUDED: Alpha scans have the distinctive rounded
        corners / off-centre art, so a card whose earliest printing is Alpha uses
        its BETA (`leb`) scan instead (the next printing). Cards not in Alpha are
        unaffected."""
        try:
            resp = self._get(client, "/cards/search", {
                "q": f'!"{name}" game:paper -set:lea', "unique": "prints",
                "order": "released", "dir": "asc"})
            if resp.status_code == 200:
                data = resp.json().get("data") or []
                if data:
                    return data[0]
        except Exception:  # noqa: BLE001 - best-effort; fall back below
            pass
        return None

    def _fetch_raw(self, client: "httpx.Client", name: str) -> dict | None:
        """Resolve `name` to a raw Scryfall card, preferring the earliest paper
        printing, then falling back to /cards/named (exact → fuzzy → front face)."""
        raw = self._oldest_raw(client, name)
        if raw is not None:
            return raw
        resp = self._get(client, "/cards/named", {"exact": name})
        if resp.status_code != 200:
            resp = self._get(client, "/cards/named", {"fuzzy": name})
        if resp.status_code != 200 and "//" in name:
            # Double-faced cards: exact/fuzzy on the full "Front // Back" name
            # often fails; the front face resolves.
            front = name.split("//")[0].strip()
            resp = self._get(client, "/cards/named", {"fuzzy": front})
        return resp.json() if resp.status_code == 200 else None

    def get_named(self, name: str, refresh: bool = False) -> CardData:
        """Resolve a single card by (fuzzy-tolerant) exact name. `refresh` skips
        the cache read (used to repopulate cards fetched before a schema change,
        e.g. to pick up `token_parts`)."""
        cached = None if refresh else self._read_cache(name)
        if cached:
            return cached
        with httpx.Client(headers={"User-Agent": _USER_AGENT}, timeout=20) as client:
            raw = self._fetch_raw(client, name)
            if raw is None:
                raise ScryfallError(f"Scryfall lookup failed for {name!r}")
            card = card_data_from_scryfall(raw)
            self._write_cache(card)
            time.sleep(self.throttle_s)
            return card

    def get_collection(self, names: list[str]) -> dict[str, CardData]:
        """Resolve many cards. Uncached names are fetched ONE AT A TIME so each
        can use its EARLIEST paper printing (first-published art — the batch
        /cards/collection endpoint can't order by release). Slower on the very
        first import of a deck; every load after is served from the on-disk cache.
        Names that fall through the per-card path are batch-resolved so a fetch
        failure never drops a card. Result is keyed by the *requested* name;
        unresolvable names are simply absent.
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
            still_missing: list[str] = []
            for name in missing:
                raw = self._fetch_raw(client, name)
                if raw is None:
                    still_missing.append(name)
                    continue
                card = card_data_from_scryfall(raw)
                self._write_cache(card)
                result[name] = card
                time.sleep(self.throttle_s)

            # Fallback: anything the per-card path couldn't resolve, batch-resolve
            # (default printing) so no card is silently dropped.
            for start in range(0, len(still_missing), _COLLECTION_BATCH):
                batch = still_missing[start : start + _COLLECTION_BATCH]
                payload = {"identifiers": [{"name": n} for n in batch]}
                resp = client.post(f"{SCRYFALL_API}/cards/collection", json=payload)
                if resp.status_code != 200:
                    continue
                requested = {n.lower(): n for n in batch}
                for raw in resp.json().get("data", []):
                    card = card_data_from_scryfall(raw)
                    self._write_cache(card)
                    key = requested.get(card.name.lower()) or next(
                        (orig for low, orig in requested.items() if low in card.name.lower()),
                        card.name)
                    result[key] = card
                time.sleep(self.throttle_s)
        return result
