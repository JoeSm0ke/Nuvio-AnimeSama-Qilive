#!/usr/bin/env python3
"""Refresh the classics snapshot without changing the catalog manifest.

Only already-verified search entries may be included. A shortened or changed
website response must not overwrite the last known-good classics list.
Use --dry-run to preview a regeneration without writing anything.
"""
import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SERIES = {
    "dragon-ball-z": "tt0121220",
    "dragon-ball": "tt0088509",
    "one-piece": "tt0388629",
    "naruto": "tt0409591",
    "naruto-shippuden": "tt0988824",
    "bleach": "tt0434665",
    "kingdom": "tt2404499",
    "yu-gi-oh": "tt0249327",
    "hunter-x-hunter": "tt2098220",
    "fullmetal-alchemist-brotherhood": "tt1355642",
    "fairy-tail": "tt1528406",
    "shingeki-no-kyojin": "tt2560140",
    "jujutsu-kaisen": "tt12343534",
    "demon-slayer": "tt9335498",
    "my-hero-academia": "tt5626028",
    "jojos-bizarre-adventure": "tt2359704",
    "sailor-moon": "tt0103369",
    "saint-seiya": "tt0161952",
    "ken-le-survivant": "tt0091211",
    "death-note": "tt0877057",
    "detective-conan": "tt0131179",
    "hajime-no-ippo": "tt0481256",
    "great-teacher-onizuka": "tt0315008",
    "evangelion": "tt0112159",
}


def main(dry_run: bool = False) -> None:
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    if sum(row.get("id") == "as_classics" for row in manifest["catalogs"]) != 1:
        raise RuntimeError("Expected exactly one existing classics row; preserving manifest")
    canonical_path = DOCS / "catalog/series/as_search.json"
    canonical = {
        item["id"]: item
        for item in json.loads(canonical_path.read_text(encoding="utf-8"))["metas"]
    }
    output = DOCS / "catalog/series/as_classics.json"
    previous = json.loads(output.read_text(encoding="utf-8"))["metas"]
    r = requests.get("https://anime-sama.to/", timeout=25,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    container = BeautifulSoup(r.text, "html.parser").select_one("#containerClassiques")
    if container is None:
        raise RuntimeError("Classics section missing; preserving previous snapshot")
    entries = []
    seen = set()
    for element in container.select(".as-carte-oeuvre[data-url]"):
        slug = element.get("data-url", "").strip("/").split("/")[-1]
        imdb_id = SERIES.get(slug)
        if not imdb_id or imdb_id in seen or imdb_id not in canonical:
            continue
        seen.add(imdb_id)
        # Use the canonical verified title + poster; site labels/covers can drift.
        entries.append(canonical[imdb_id])
    minimum = max(16, len(previous) - 4)
    if len(entries) < minimum:
        raise RuntimeError(f"Only {len(entries)} classics, expected >= {minimum}; preserving snapshot")
    print(f"Classics: {len(entries)} entries; catalog version preserved as {manifest['version']}")
    if dry_run:
        print("DRY RUN: no files changed")
        return
    with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp",
                            dir=output.parent, delete=False) as temp:
        json.dump({"metas": entries}, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
        tmp_path = Path(temp.name)
    tmp_path.replace(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
