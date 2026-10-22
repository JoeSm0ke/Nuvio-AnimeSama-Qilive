#!/usr/bin/env python3
"""Generate Stremio-compatible anime-only catalog snapshots sourced from anime-sama.to.

Discovery source: public catalogue entries. IMDB IDs: Cinemeta search, accepted only
on strong title similarity. No videos are downloaded or hosted. Unknown titles are
excluded instead of silently linking the wrong series.
"""
from __future__ import annotations
import concurrent.futures
import html
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlencode
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
CACHE = ROOT / "scripts" / "imdb-cache.json"
BASE = "https://anime-sama.to/catalogue/"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Anime-Sama-TV-Catalog/0.1)"})
STEMS = [
    ("as_latest", "Anime-Sama · Derniers ajouts", "ajout", 3),
    ("as_new", "Anime-Sama · Sorties récentes", "recent", 3),
]

def normal(s):
    s = unicodedata.normalize("NFKD", html.unescape(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def fetch_animes(sort, pages):
    output = []
    for page in range(1, pages+1):
        r = SESSION.get(BASE, params={"tri": sort, "type[]": "Anime", "page": page}, timeout=20)
        r.raise_for_status()
        doc = BeautifulSoup(r.text, "html.parser")
        count = 0
        for el in doc.select(".as-carte-oeuvre[data-url]"):
            badge = el.select_one(".as-badge-anime")
            if badge is None: continue
            slug = el.get("data-url", "").strip("/").split("/")[-1]
            name = html.unescape(el.get("data-nom", "")).strip()
            poster = el.get("data-img")
            if not slug or not name or not poster: continue
            output.append({"name": name, "slug": slug, "poster": poster})
            count += 1
        print(f"{sort} page={page}: {count} anime")
        if count == 0: break
        time.sleep(.25)
    unique = {}
    for item in output:
        unique.setdefault(item["slug"], item)
    return list(unique.values())

def resolve(item, cache):
    key = normal(item["name"])
    if key in cache:
        return cache[key]
    try:
        url = "https://v3-cinemeta.strem.io/catalog/series/top/search=" + quote(item["name"], safe="") + ".json"
        d = requests.get(url, timeout=15).json()
        candidates = []
        for m in d.get("metas", []):
            if m.get("type") != "series" or not re.fullmatch(r"tt[0-9]+", m.get("id", "")): continue
            score = max(fuzz.ratio(key, normal(m.get("name"))),
                        fuzz.token_sort_ratio(key, normal(m.get("name"))))
            candidates.append((score, m))
        candidates.sort(key=lambda a: a[0], reverse=True)
        if candidates and candidates[0][0] >= 89:
            result = {"id": candidates[0][1]["id"], "match": round(candidates[0][0], 1)}
        else:
            result = {"id": None, "match": round(candidates[0][0], 1) if candidates else 0}
    except Exception as e:
        print(f"lookup error {item['name']}: {str(e)[:60]}")
        result = {"id": None, "match": 0}
    return result

def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "catalog" / "series").mkdir(parents=True, exist_ok=True)
    CACHE.parent.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    data = {}
    all_items = {}
    for ident, label, sort, pages in STEMS:
        items = fetch_animes(sort, pages)
        data[ident] = (label, items)
        for item in items: all_items.setdefault(normal(item["name"]), item)
    unresolved = {k:v for k,v in all_items.items() if k not in cache}
    print(f"LOOKUPS={len(unresolved)}, CACHED={len(cache)}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {pool.submit(resolve, item, cache): key for key, item in unresolved.items()}
        for n, f in enumerate(concurrent.futures.as_completed(future_map), start=1):
            cache[future_map[f]] = f.result()
            if n % 25 == 0: print(f"Resolved {n}/{len(unresolved)}", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"id":"fr.joesm0ke.animesama.catalog", "version":"0.1.0",
                "name":"Anime-Sama TV · Catalogue", "description":"Anime uniquement, selection Anime-Sama, VF/VOSTFR via fournisseur Nuvio separe.",
                "resources":["catalog"], "types":["series"],
                "catalogs":[{"type":"series","id":ident,"name":label} for ident,label,_,_ in STEMS]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),encoding="utf-8")
    for ident,(label, items) in data.items():
        metas = []
        used = set()
        for item in items:
            imdb = cache.get(normal(item["name"]), {}).get("id")
            if not imdb or imdb in used: continue
            metas.append({"id":imdb, "type":"series", "name":item["name"], "poster":item["poster"],
                          "posterShape":"poster"})
            used.add(imdb)
        file = OUT / "catalog" / "series" / f"{ident}.json"
        file.write_text(json.dumps({"metas":metas},ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"{label}: {len(metas)}/{len(items)} verified matches -> {file}",flush=True)

if __name__ == "__main__":
    main()
