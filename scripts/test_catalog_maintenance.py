"""Offline regression tests: no accidental manifest downgrade or partial overwrite."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_catalog
import build_classics
import build_genre_catalogs


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def meta(imdb_id, name):
    return {
        "id": imdb_id, "type": "series", "name": name,
        "poster": "https://raw.githubusercontent.com/Anime-Sama/IMG/img/contenu/" + name + ".jpg",
        "posterShape": "poster"
    }


def manifest(version="9.8.7"):
    return {
        "id": "test.catalog", "version": version,
        "catalogs": [
            {"id": x, "name": x, "type": "series"}
            for x in ("as_classics", "as_action", "as_fantasy", "as_romance",
                      "as_comedy", "as_scifi", "as_latest", "as_new", "as_search")
        ]
    }


class CatalogMaintenanceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.docs = Path(self.temp.name) / "docs"
        self.rows = self.docs / "catalog/series"
        self.rows.mkdir(parents=True)
        write(self.docs / "manifest.json", manifest())
        self.reference = [meta(imdb, slug) for slug, imdb in build_classics.SERIES.items()]
        write(self.rows / "as_search.json", {"metas": self.reference})
        write(self.rows / "as_classics.json", {"metas": self.reference})
        self._manifest_before = (self.docs / "manifest.json").read_bytes()

    def test_classics_keeps_manifest_and_verified_posters(self):
        html = '<div id="containerClassiques">' + "".join(
            f'<div class="as-carte-oeuvre" data-url="/catalogue/{slug}"'
            f' data-nom="UNTRUSTED" data-img="https://untrusted.test/cover.jpg"></div>'
            for slug in build_classics.SERIES
        ) + '</div>'
        class Response:
            text = html
            def raise_for_status(self):
                return None
        with patch.object(build_classics, "DOCS", self.docs), patch.object(
            build_classics.requests, "get", return_value=Response()
        ):
            build_classics.main(dry_run=False)
        self.assertEqual(self._manifest_before, (self.docs / "manifest.json").read_bytes())
        self.assertEqual(self.reference, json.loads(
            (self.rows / "as_classics.json").read_text(encoding="utf-8")
        )["metas"])

    def test_short_classics_response_cannot_replace_good_snapshot(self):
        html = '<div id="containerClassiques">' + "".join(
            f'<div class="as-carte-oeuvre" data-url="/catalogue/{slug}"></div>'
            for slug in list(build_classics.SERIES)[:8]
        ) + '</div>'
        class Response:
            text = html
            def raise_for_status(self):
                return None
        old = (self.rows / "as_classics.json").read_bytes()
        with patch.object(build_classics, "DOCS", self.docs), patch.object(
            build_classics.requests, "get", return_value=Response()
        ):
            with self.assertRaisesRegex(RuntimeError, "preserving snapshot"):
                build_classics.main()
        self.assertEqual(old, (self.rows / "as_classics.json").read_bytes())
        self.assertEqual(self._manifest_before, (self.docs / "manifest.json").read_bytes())

    def test_recents_use_only_verified_matches_without_manifest_mutation(self):
        catalog_items = [meta(f"tt{i:07}", f"Anime-{i}") for i in range(1, 30)]
        write(self.rows / "as_search.json", {"metas": catalog_items})
        for name in ("as_latest", "as_new"):
            write(self.rows / f"{name}.json", {"metas": catalog_items[:16]})
        def fetch(session, sort, pages):
            return [(x["name"], x["poster"]) for x in catalog_items[:20]]
        with patch.object(build_catalog, "DOCS", self.docs), patch.object(
            build_catalog, "SERIES", self.rows
        ), patch.object(build_catalog, "fetch_animes", side_effect=fetch):
            build_catalog.main(dry_run=False)
        self.assertEqual(self._manifest_before, (self.docs / "manifest.json").read_bytes())
        for name in ("as_latest", "as_new"):
            self.assertEqual(catalog_items[:20], json.loads(
                (self.rows / f"{name}.json").read_text(encoding="utf-8")
            )["metas"])

    def test_short_recents_response_cannot_replace_either_snapshot(self):
        catalog_items = [meta(f"tt{i:07}", f"Anime-{i}") for i in range(1, 30)]
        write(self.rows / "as_search.json", {"metas": catalog_items})
        for name in ("as_latest", "as_new"):
            write(self.rows / f"{name}.json", {"metas": catalog_items[:16]})
        old = {n: (self.rows / f"{n}.json").read_bytes() for n in ("as_latest", "as_new")}
        def fetch(session, sort, pages):
            count = 20 if sort == "ajout" else 3
            return [(x["name"], x["poster"]) for x in catalog_items[:count]]
        with patch.object(build_catalog, "DOCS", self.docs), patch.object(
            build_catalog, "SERIES", self.rows
        ), patch.object(build_catalog, "fetch_animes", side_effect=fetch):
            with self.assertRaisesRegex(RuntimeError, "preserving ALL"):
                build_catalog.main()
        for name in ("as_latest", "as_new"):
            self.assertEqual(old[name], (self.rows / f"{name}.json").read_bytes())
        self.assertEqual(self._manifest_before, (self.docs / "manifest.json").read_bytes())

    def test_genre_refresh_never_downgrades_manifest_version(self):
        items = [meta(f"tt{i:07}", f"Anime-{i}") for i in range(1, 81)]
        write(self.rows / "as_search.json", {"metas": items})
        cache_file = Path(self.temp.name) / "genre-cache.json"
        tags = ["animation", "fantasy", "action", "romance", "comedy", "sci-fi"]
        write(cache_file, {x["id"]: {"genres": tags, "imdb_rating": 8.0} for x in items})
        with patch.object(build_genre_catalogs, "SEARCH", self.rows / "as_search.json"), patch.object(
            build_genre_catalogs, "SERIES", self.rows
        ), patch.object(build_genre_catalogs, "MANIFEST", self.docs / "manifest.json"), patch.object(
            build_genre_catalogs, "CACHE", cache_file
        ):
            build_genre_catalogs.main()
        updated = json.loads((self.docs / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("9.8.7", updated["version"])
        self.assertEqual(9, len(updated["catalogs"]))
        self.assertEqual(36, len(json.loads(
            (self.rows / "as_fantasy.json").read_text(encoding="utf-8")
        )["metas"]))


if __name__ == "__main__":
    unittest.main()
