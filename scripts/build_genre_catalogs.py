#!/usr/bin/env python3
"""Build strictly metadata-backed themed Anime-Sama shelves, no publish.

Requires: verified IMDb series in as_search, a real animation-series Cinemeta
record with episodes, and its actual genre. Never guesses from title or slug.
Keeps cached successful genre verification, never persists transient failures.
"""
from __future__ import annotations
import concurrent.futures
import json
import re
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "docs/catalog/series"
SEARCH = SERIES / "as_search.json"
MANIFEST = ROOT / "docs/manifest.json"
CACHE = ROOT / "scripts/genre-metadata-cache.json"
GENRES = {
    "as_action": ("Action & aventure", {"action", "adventure", "action & adventure"}),
    "as_fantasy": ("Magie & fantasy", {"fantasy"}),
    "as_romance": ("Romance & émotions", {"romance"}),
    "as_comedy": ("Comédies", {"comedy"}),
    "as_scifi": ("Imaginaire & science-fiction", {"sci-fi", "sci-fi & fantasy", "science fiction"}),
}
# Avoid empty/sparsely populated rows or a home with too many thumbnails.
MAX_ROW = 36
MIN_ROW = 9
HEADERS = {"User-Agent": "Anime-Sama-TV-Metadata-Audit/1.0"}


def verify(item):
    key = item["id"]
    try:
        r = requests.get(f"https://v3-cinemeta.strem.io/meta/series/{key}.json",
                         headers=HEADERS, timeout=(4, 12))
        r.raise_for_status()
        meta = r.json().get("meta") or {}
        tags = [str(s).lower().strip() for s in (meta.get("genres") or [])]
        if meta.get("id") != key or not any(x in tags for x in ("animation", "anime")):
            return key, None, "not_anime"
        if not meta.get("videos") or not isinstance(meta["videos"], list):
            return key, None, "no_episodes"
        try:
            rating = float(meta.get("imdbRating") or 0)
        except (ValueError, TypeError):
            rating = 0.0
        return key, {"genres": tags, "imdb_rating": rating}, "verified"
    except (requests.RequestException, ValueError) as e:
        return key, None, type(e).__name__


def main():
    items = json.loads(SEARCH.read_text(encoding="utf-8"))["metas"]
    assert items and len({x["id"] for x in items}) == len(items)
    assert all(re.fullmatch(r"tt[0-9]{5,15}", x["id"]) for x in items)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    pending = [x for x in items if x["id"] not in cache]
    print(f"Search={len(items)} cached_genres={len(cache)} pending={len(pending)}", flush=True)
    errors = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(verify, x): x["id"] for x in pending}
        for n, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            key, info, status = fut.result()
            if info:
                cache[key] = info
            else:
                errors[status] = errors.get(status, 0) + 1
            if n % 40 == 0 or n == len(pending):
                print(f"Metadata checked {n}/{len(pending)} verified={len(cache)}", flush=True)
    # Never publish new genre data when the metadata service is unavailable.
    if len(cache) < max(70, len(items) // 3):
        raise RuntimeError(f"Only {len(cache)} verified entries, preserving last genre catalogs. Errors: {errors}")
    # Save metadata after validation. A future run can retry only the failed IDs.
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    records = {}
    for genre_id, (label, accepted) in GENRES.items():
        eligible = [
            x for x in items
            if x["id"] in cache and set(cache[x["id"]]["genres"]).intersection(accepted)
        ]
        eligible.sort(key=lambda x: (-cache[x["id"]]["imdb_rating"], x["name"].casefold()))
        eligible = eligible[:MAX_ROW]
        print(f"{genre_id}: {len(eligible)} eligible entries", flush=True)
        if len(eligible) >= MIN_ROW:
            records[genre_id] = (label, eligible)
    if len(records) < 3:
        raise RuntimeError("Not enough populated genres, preserving catalog")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Do not silently downgrade an already published manifest version.
    original = manifest.get("catalogs", [])
    manifest["catalogs"] = [x for x in original if x.get("id") not in GENRES]
    insert_after = next((n for n, x in enumerate(manifest["catalogs"])
                        if x.get("id") == "as_classics"), -1) + 1
    for name, (label, entries) in records.items():
        catalog = {"type": "series", "id": name, "name": label}
        manifest["catalogs"].insert(insert_after, catalog)
        insert_after += 1
    # Write after all validations; each row refers only to as_search metadata.
    for name, (label, entries) in records.items():
        (SERIES / f"{name}.json").write_text(
            json.dumps({"metas": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS added {len(records)} genre rows. Metadata failures={errors}", flush=True)


if __name__ == "__main__":
    main()
