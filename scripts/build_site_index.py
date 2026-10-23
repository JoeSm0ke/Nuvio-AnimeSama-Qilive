#!/usr/bin/env python3
"""Build a read-only Anime-Sama title index for native Nuvio search filtering.

This index only contains public catalogue labels and cover URLs; no videos, links
to episodes, or copyrighted media are stored. Fetch errors do not overwrite the
last known-good snapshot.
"""
from __future__ import annotations
import concurrent.futures
import json
import re
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE = "https://anime-sama.to/catalogue/"
OUT = Path(__file__).resolve().parents[1] / "docs/catalog/series/as_names.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Anime-Sama TV catalogue index; +https://github.com/JoeSm0ke/Nuvio-AnimeSama-Qilive)"}
KINDS = ("Anime", "Film")

def get_page(arg):
    kind, page = arg
    resp = requests.get(BASE, params={"tri":"titre","type[]":kind,"page":str(page)}, headers=HEADERS, timeout=22)
    resp.raise_for_status()
    parsed = BeautifulSoup(resp.text, "html.parser")
    result=[]
    for entry in parsed.select(".as-carte-oeuvre[data-url][data-nom]"):
        slug = entry.get("data-url", "").strip("/").split("/")[-1]
        name = entry.get("data-nom","").strip()
        if slug and name:
            result.append({"id":"as:"+slug,"type":"series","name":name,"poster":entry.get("data-img","")})
    return kind, page, result

def main():
    tasks=[(kind,p) for kind in KINDS for p in range(1,45)]
    results={}
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures=[pool.submit(get_page, args) for args in tasks]
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            try:
                kind,page,items=f.result()
                results[(kind,page)] = items
            except Exception as e:
                errors.append(str(e))
            if i%20==0:
                print(f"pages={i}/{len(tasks)}",flush=True)
    if errors:
        raise RuntimeError(f"{len(errors)} failed pages; keeping existing index. First: {errors[0]}")
    all_items={}
    counts={}
    for kind in KINDS:
        for page in range(1,45):
            for row in results[(kind,page)]:
                all_items.setdefault(row["id"],row)
        counts[kind] = sum(len(results[(kind,p)]) for p in range(1,45))
    previous_count = 0
    if OUT.exists():
        previous_count = len(json.loads(OUT.read_text(encoding="utf-8"))["metas"])
    minimum = max(400, int(previous_count * 0.85))
    if len(all_items) < minimum:
        raise RuntimeError(f"Unexpected index shrink {len(all_items)} < {minimum}; preserving snapshot")
    # Exact alternate series titles confirmed on the Anime-Sama detail page.
    # Do not add generic aliases such as "Bloom": they would admit unrelated
    # Cinemeta series with identical short names.
    alternate_titles = {
        "as:kaoru-hana-wa-rin-to-saku": ["The Fragrant Flower Blooms with Dignity"],
    }
    for source_id, titles in alternate_titles.items():
        original = all_items.get(source_id)
        if not original:
            continue
        for n, title in enumerate(titles):
            alias = dict(original)
            alias.update({"id":f"alias:{source_id}:{n}", "name":title})
            all_items[alias["id"]] = alias
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"metas":list(all_items.values())},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Index: {len(all_items)} titles, by type {counts}",flush=True)

if __name__=="__main__": main()
