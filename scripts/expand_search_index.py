#!/usr/bin/env python3
"""Safely expand playable Anime-Sama search with *verified* Cinemeta IDs.

Keeps all existing entries/IDs, skips ambiguous matches, and never publishes.
Usage:
  python scripts/expand_search_index.py --offline
  python scripts/expand_search_index.py --queries 250
  python scripts/expand_search_index.py --queries 0  # cached only
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
import json
import re
import unicodedata
from urllib.parse import quote
import requests

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "docs" / "catalog" / "series"
CACHE = ROOT / "scripts" / "search-id-verified-cache.json"
SEARCH = SERIES / "as_search.json"
INDEX = SERIES / "as_names.json"
OTHER = ["as_classics", "as_latest", "as_new"]
CINEMETA = "https://v3-cinemeta.strem.io/catalog/series/top/search="
IMDB = re.compile(r"tt[0-9]{4,15}$")

def normal(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).lower()
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", s))

def strength(a: str, b: str) -> float:
    a, b = normal(a), normal(b)
    if not a or not b: return 0.
    if a == b: return 100.
    if a.replace(" ", "") == b.replace(" ", "") and len(a) >= 5: return 99.
    if sorted(a.split()) == sorted(b.split()) and len(a.split()) > 1: return 97.
    return 100 * SequenceMatcher(None, a, b).ratio()

def load_metas(name):
    f = SERIES / f"{name}.json"
    return json.loads(f.read_text(encoding="utf-8"))["metas"]

def resolve(item):
    title = item["name"]
    # Don't trust suggestions without a strong title match.
    url = CINEMETA + quote(title, safe="") + ".json"
    try:
        res = requests.get(url, headers={"User-Agent": "Anime-Sama-TV-Local-Index/1.0"},
                           timeout=(4, 10))
        res.raise_for_status()
        metas = res.json().get("metas", [])
        scores = []
        for m in metas:
            cid = str(m.get("id", ""))
            if m.get("type") == "series" and IMDB.fullmatch(cid):
                scores.append((strength(title, m.get("name", "")), cid, m.get("name", "")))
        scores.sort(reverse=True)
        if not scores: return title, None
        best = scores[0]
        runner = scores[1][0] if len(scores) > 1 else 0
        # Exact names are safe; fuzzy matches need high confidence and margin.
        if best[0] < 96 or (best[0] < 99 and runner >= best[0] - 3):
            return title, None
        # A matching title can still be a live-action adaptation or a missing
        # Cinemeta record. Require actual animated-series metadata and episodes.
        metadata = requests.get(f"https://v3-cinemeta.strem.io/meta/series/{best[1]}.json",
                                timeout=(4, 10)).json().get("meta")
        genres = [str(g).lower() for g in (metadata or {}).get("genres") or []]
        if not metadata or metadata.get("id") != best[1]: return title, None
        if not ("animation" in genres or "anime" in genres): return title, None
        if not isinstance(metadata.get("videos"), list) or not metadata["videos"]:
            return title, None
        return title, {"id": best[1], "score": round(best[0], 1),
                       "matched_name": best[2], "verified_animation": True}
    except (requests.RequestException, ValueError):
        # A transient network failure must not permanently blacklist a title.
        return title, {"verification_reason": "unverifiable_now"}

def build(args):
    raw = load_metas("as_names")
    canonical = [i for i in raw if str(i.get("id", "")).startswith("as:") and i.get("poster")]
    slug_titles = {i["id"]: i for i in canonical}
    aliases = {}
    for item in raw:
        m = re.fullmatch(r"alias:(as:[^:]+):[0-9]+", str(item.get("id", "")))
        if m and m.group(1) in slug_titles:
            aliases.setdefault(m.group(1), []).append(item["name"])
    existing = load_metas("as_search")
    by_id = {i["id"]: dict(i) for i in existing if IMDB.fullmatch(str(i.get("id", "")))}
    old_ids = set(by_id)
    by_normal = {normal(i["name"]): i["id"] for i in by_id.values()}
    site_by_name = {normal(i["name"]): i for i in canonical}
    reused = 0
    # Known metadata from our already published rows. Do not override existing ids.
    for sheet in OTHER:
        for item in load_metas(sheet):
            key = normal(item.get("name", ""))
            source = site_by_name.get(key)
            imdb_id = str(item.get("id", ""))
            if key in by_normal or not source or imdb_id in by_id or not IMDB.fullmatch(imdb_id):
                continue
            by_id[imdb_id] = {"id": imdb_id, "type": "series", "name": source["name"],
                              "poster": source["poster"], "posterShape": "poster"}
            by_normal[key] = imdb_id
            reused += 1
    historic = json.loads((ROOT / "scripts" / "imdb-cache.json").read_text(encoding="utf-8"))
    for key, hit in historic.items():
        source = site_by_name.get(normal(key))
        imdb_id = str((hit or {}).get("id") or "")
        if (not source or not IMDB.fullmatch(imdb_id) or
            float((hit or {}).get("match", 0)) < 96 or
            normal(source["name"]) in by_normal or imdb_id in by_id):
            continue
        by_id[imdb_id] = {"id": imdb_id, "type": "series", "name": source["name"],
                          "poster": source["poster"], "posterShape": "poster"}
        by_normal[normal(source["name"])] = imdb_id
        reused += 1

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    from_live = 0
    def add_cached(item, hit):
        nonlocal from_live
        key = normal(item["name"])
        imdb_id = str((hit or {}).get("id") or "")
        if imdb_id in by_id or key in by_normal or not IMDB.fullmatch(imdb_id):
            return
        # Old title-only lookup caches are unsafe: names alone can resolve to
        # live-action adaptations with identical names. Require full meta proof.
        if (hit or {}).get("verified_animation") is not True:
            return
        # Never trust an old cache value if the canonical name stopped matching.
        if strength(item["name"], (hit or {}).get("matched_name", "")) < 96:
            return
        by_id[imdb_id] = {"id": imdb_id, "type": "series", "name": item["name"],
                          "poster": item["poster"], "posterShape": "poster"}
        by_normal[key] = imdb_id
        from_live += 1

    for item in canonical:
        add_cached(item, cache.get(normal(item["name"])))

    # Prioritize recognizable shows, then a deterministic balanced spread of titles.
    priorities = ["dandadan", "naruto", "kaoru hana wa rin to saku",
                  "attack on titan", "frieren", "demon slayer", "jujutsu kaisen",
                  "solo leveling", "one piece", "bleach", "death note", "spy x family",
                  "blue lock", "chainsaw man", "my hero academia"]
    indexed = {normal(i["name"]): i for i in canonical}
    ordered = [indexed[k] for k in priorities if k in indexed]
    # Stable stride over the complete alphabetical index instead of processing only A's.
    stride = 37
    ordered += [canonical[(i * stride) % len(canonical)] for i in range(len(canonical))]
    ordered += canonical
    to_query = []
    seen = set()
    for item in ordered:
        key = normal(item["name"])
        if key in seen or key in by_normal: continue
        hit = cache.get(key)
        if key in cache and not (isinstance(hit, dict) and hit.get("verification_reason") == "unverifiable_now"):
            continue
        seen.add(key)
        to_query.append(item)
    to_query = to_query[:args.queries]
    print(f"Site titles={len(canonical)} / aliases={sum(map(len, aliases.values()))} "
          f"existing={len(old_ids)}, verified_from_known={reused}, cached_additions={from_live}, "
          f"live_queries={len(to_query)}", flush=True)
    if to_query:
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(resolve, it) for it in to_query]
            for n, future in enumerate(as_completed(jobs), start=1):
                title, result = future.result()
                cache[normal(title)] = result
                if n % 30 == 0 or n == len(jobs):
                    print(f"Lookups completed {n}/{len(jobs)}", flush=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for item in canonical:
            add_cached(item, cache.get(normal(item["name"])))

    metas = list(by_id.values())
    metas.sort(key=lambda a: normal(a["name"]))
    assert all(IMDB.fullmatch(i["id"]) for i in metas)
    assert len(metas) == len({i["id"] for i in metas})
    assert old_ids.issubset({i["id"] for i in metas})
    if not args.dry_run:
        SEARCH.write_text(json.dumps({"metas": metas}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(f"RESULT playable_search={len(metas)} (+{len(metas)-len(old_ids)}), "
          f"preserved={len(old_ids)}, output={'dry-run' if args.dry_run else str(SEARCH)}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=int, default=0, help="Maximum new network Cinemeta title lookups")
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()
    if ns.queries < 0 or ns.queries > 1600: parser.error("queries should be 0..1600")
    build(ns)
