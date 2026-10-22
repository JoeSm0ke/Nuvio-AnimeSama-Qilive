#!/usr/bin/env python3
"""Build Anime-Sama TV's 'Les classiques' row from Anime-Sama's own homepage.

Series only: films/scan-only entries are deliberately excluded until a verified
movie-compatible metadata/player path is available. IDs have been manually
verified against Cinemeta as anime series, not similarly titled live-action.
"""
import html
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
# These IMDb IDs point to the original anime, not remakes/live-action adaptations.
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
r = requests.get("https://anime-sama.to/", timeout=25, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()
container = BeautifulSoup(r.text, "html.parser").select_one("#containerClassiques")
if container is None:
    raise RuntimeError("Anime-Sama changed the classics section; preserving previous snapshot")
result = []
for item in container.select(".as-carte-oeuvre[data-url][data-nom][data-img]"):
    slug = item["data-url"].strip("/").split("/")[-1]
    if slug not in SERIES:
        continue
    name = html.unescape(item["data-nom"]).strip()
    poster = item["data-img"]
    if not poster.startswith("https://"):
        continue
    result.append({"id": SERIES[slug], "type": "series", "name": name,
                   "poster": poster, "posterShape": "poster"})
if len(result) < 8:
    raise RuntimeError("Too few classics; keeping previous snapshot")
path = DOCS / "catalog" / "series" / "as_classics.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"metas":result}, ensure_ascii=False, indent=2), encoding="utf-8")
manifest_file = DOCS / "manifest.json"
manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
manifest["version"] = "0.3.0"
manifest["name"] = "Anime-Sama TV - Catalogue"
manifest["catalogs"] = [c for c in manifest["catalogs"] if c["id"] != "as_classics"]
manifest["catalogs"].insert(0, {
    "type":"series", "id":"as_classics", "name":"Les classiques - Anime-Sama"
})
for entry in manifest["catalogs"]:
    if entry["id"] == "as_latest": entry["name"] = "Anime-Sama - Derniers ajouts"
    if entry["id"] == "as_new": entry["name"] = "Anime-Sama - Sorties recentes"
manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Published {len(result)} classics; first: {[x['name'] for x in result[:8]]}")
