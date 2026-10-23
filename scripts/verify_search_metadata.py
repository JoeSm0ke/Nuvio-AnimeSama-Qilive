#!/usr/bin/env python3
"""Validate ONLY new Anime-Sama index entries against Cinemeta full metadata.
Preserves the pre-existing catalog as a separate, already-working baseline.
Does not publish to GitHub. Failing/new entries are removed, never reassigned.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import re
import subprocess
import requests
ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "docs/catalog/series/as_search.json"
CACHE = ROOT / "scripts/search-id-verified-cache.json"

def verify(item):
    url = f"https://v3-cinemeta.strem.io/meta/series/{item['id']}.json"
    try:
        result = requests.get(url, timeout=(5, 12), headers={"User-Agent":"Anime-Sama-TV-Local-Index/1.0"})
        result.raise_for_status()
        meta = result.json().get("meta")
        if not meta or meta.get("id") != item["id"]:
            return item, False, "missing_meta"
        genres = [str(g).lower() for g in meta.get("genres") or []]
        if not ("animation" in genres or "anime" in genres):
            return item, False, "not_animation"
        # A series IMDb match needs actual episodes; otherwise it may be a placeholder.
        videos = meta.get("videos") or []
        if not isinstance(videos, list) or len(videos) == 0:
            return item, False, "no_episodes"
        return item, True, "valid"
    except (requests.RequestException, ValueError):
        return item, False, "unverifiable_now"

def main():
    all_items = json.loads(SEARCH.read_text(encoding="utf-8"))["metas"]
    original_raw = subprocess.check_output(
        ["git","show","HEAD:docs/catalog/series/as_search.json"], cwd=ROOT)
    previous = json.loads(original_raw.decode("utf-8"))["metas"]
    blocked_ids = {r["id"] for r in json.loads((ROOT / "scripts/quarantined-imdb-mappings.json").read_text(encoding="utf-8"))}
    old_ids = {r["id"] for r in previous if r["id"] not in blocked_ids}
    new = [r for r in all_items if r["id"] not in old_ids]
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    accepted = set()
    failure_count = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        jobs = [pool.submit(verify, it) for it in new]
        for n, future in enumerate(as_completed(jobs), 1):
            item, valid, reason = future.result()
            if valid: accepted.add(item["id"])
            else: failure_count[reason] = failure_count.get(reason,0)+1
            for c in cache.values():
                if isinstance(c,dict) and c.get("id")==item["id"]:
                    c["verified_animation"] = valid
                    c["verification_reason"] = reason
            if n%25==0 or n==len(new):
                print(f"Verified {n}/{len(new)} (accepted={len(accepted)})",flush=True)
    final = [r for r in all_items if r["id"] not in blocked_ids and
             (r["id"] in old_ids or r["id"] in accepted)]
    assert old_ids.issubset({r["id"] for r in final})
    assert len(final)==len({r["id"] for r in final})
    SEARCH.write_text(json.dumps({"metas":final},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"PASS accepted={len(accepted)} discarded={len(new)-len(accepted)} "
          f"baseline_preserved={len(old_ids)} final={len(final)} reasons={failure_count}",flush=True)

if __name__=="__main__":main()
