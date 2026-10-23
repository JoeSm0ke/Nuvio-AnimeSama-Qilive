#!/usr/bin/env python3
"""Safely refresh 'Derniers ajouts' and 'Sorties récentes' from Anime-Sama.

Matches against the *already verified* as_search IMDb ID, name and poster.
Does not re-run fuzzy IMDb searches, modify the manifest, or change its
version. A partial site response or weak match preserves previous snapshots.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import unicodedata
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SERIES = DOCS / "catalog/series"
BASE = "https://anime-sama.to/catalogue/"
STEMS = [
    ("as_latest", "Derniers ajouts", "ajout", 3),
    ("as_new", "Sorties récentes", "recent", 3),
]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", html.unescape(value or ""))
    value = "".join(x for x in value if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def fetch_animes(session: requests.Session, sort: str, pages: int) -> list[dict]:
    rows = []
    for page in range(1, pages + 1):
        response = session.get(BASE, params={"tri": sort, "type[]": "Anime", "page": page},
                               timeout=20)
        response.raise_for_status()
        root = BeautifulSoup(response.text, "html.parser")
        batch = []
        for entry in root.select(".as-carte-oeuvre[data-url]"):
            if not entry.select_one(".as-badge-anime"):
                continue
            name = html.unescape(entry.get("data-nom", "")).strip()
            poster = entry.get("data-img", "")
            if name and poster.startswith("https://"):
                batch.append((name, poster))
        if len(batch) < 5:
            raise RuntimeError(f"Unexpectedly short page {page} of {sort}: {len(batch)}")
        rows.extend(batch)
        time.sleep(0.15)
    return rows


def main(dry_run: bool = False) -> None:
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    row_ids = {c.get("id") for c in manifest.get("catalogs", [])}
    if any(ident not in row_ids for ident, _, _, _ in STEMS):
        raise RuntimeError("A required catalog row is absent: preserving all snapshots")
    verified = json.loads((SERIES / "as_search.json").read_text(encoding="utf-8"))["metas"]
    by_identity = {}
    for item in verified:
        by_identity.setdefault((normalize(item["name"]), item["poster"]), []).append(item)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Anime-Sama TV catalog maintenance)"
    output = {}
    for ident, name, sort, pages in STEMS:
        candidates = fetch_animes(session, sort, pages)
        entries, seen = [], set()
        for title, poster in candidates:
            matched = by_identity.get((normalize(title), poster), [])
            if len(matched) != 1:
                continue  # no fuzzy association to the wrong work or season
            entry = matched[0]
            if entry["id"] not in seen:
                entries.append(entry)
                seen.add(entry["id"])
        target = SERIES / f"{ident}.json"
        previous = json.loads(target.read_text(encoding="utf-8"))["metas"]
        minimum = max(12, int(len(previous) * 0.7))
        print(f"{name}: {len(entries)} verified from {len(candidates)} site entries; minimum={minimum}")
        if len(entries) < minimum:
            raise RuntimeError(f"Too few trusted rows in {ident}; preserving ALL catalog snapshots")
        output[target] = entries
    print(f"Catalog version preserved: {manifest['version']}")
    if dry_run:
        print("DRY RUN: no files changed")
        return
    # Validate every row before writing any file.
    for target, entries in output.items():
        with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp",
                                dir=target.parent, delete=False) as temp:
            json.dump({"metas": entries}, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp_path = Path(temp.name)
        temp_path.replace(target)
    print("Both catalog snapshots refreshed; manifest untouched.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
