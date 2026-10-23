#!/usr/bin/env node
'use strict';

// Deterministic offline audit for the public Anime-Sama TV catalog.
// No TV access, authentication, image downloads or output modification.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../docs/catalog/series');
const manifest = JSON.parse(fs.readFileSync(path.resolve(root, '../../manifest.json'), 'utf8'));
const shelves = manifest.catalogs.filter(x => x.type === 'series' && x.id !== 'as_search');
const sets = [['as_search', 'Search'], ...shelves.map(x => [x.id, x.name])];
const genreCachePath = path.resolve(__dirname, 'genre-metadata-cache.json');
const genreCache = fs.existsSync(genreCachePath)
  ? JSON.parse(fs.readFileSync(genreCachePath, 'utf8')) : {};
const genreTags = {
  as_action: ['action', 'adventure', 'action & adventure'],
  as_fantasy: ['fantasy'],
  as_romance: ['romance'],
  as_comedy: ['comedy'],
  as_scifi: ['sci-fi', 'sci-fi & fantasy', 'science fiction']
};
// Pre-existing records whose Cinemeta genre is missing/non-animated. They are
// kept untouched to avoid silently deleting a previously published title,
// but must never be presented as independently verified or used in genre rows.
const legacyMetadataExceptions = new Set([
  'tt43140647', 'tt34570673', 'tt8985078', 'tt22008216',
  'tt11051342', 'tt37253585', 'tt48391033', 'tt40370555',
  'tt33086804', 'tt0108088', 'tt27531070'
]);
const all = new Map();
let errors = 0;
const metadataExceptionsFound = new Set();
for (const [file, label] of sets) {
  const input = JSON.parse(fs.readFileSync(path.join(root, file + '.json'), 'utf8'));
  assert.ok(Array.isArray(input.metas), file + ' must have a metas array');
  const unique = new Set();
  const items = input.metas;
  for (const [i, entry] of items.entries()) {
    const prefix = file + '[' + i + ']';
    const fail = message => {
      console.error('FAIL', prefix, message);
      errors++;
    };
    if (!/^tt\d{5,15}$/.test(entry.id ?? '')) fail('invalid IMDb ID');
    if (entry.type !== 'series') fail('not a series');
    if (typeof entry.name !== 'string' || !entry.name.trim()) fail('empty title');
    if (typeof entry.poster !== 'string' ||
        !/^https:\/\/raw\.githubusercontent\.com\/Anime-Sama\/IMG\/img\/contenu\/[^?#\s]+\.(jpe?g|png|webp)$/i.test(entry.poster)) {
      fail('invalid or unsupported poster URL');
    }
    if (entry.posterShape !== 'poster') fail('invalid poster shape');
    if (unique.has(entry.id)) fail('duplicate ID');
    unique.add(entry.id);
    if (file === 'as_search') {
      all.set(entry.id, entry);
      if (!genreCache[entry.id]) {
        if (legacyMetadataExceptions.has(entry.id)) {
          metadataExceptionsFound.add(entry.id);
        } else {
          fail('new IMDb mapping has no verified animation metadata');
        }
      }
    } else {
      const canonical = all.get(entry.id);
      if (!canonical) fail('missing from search catalog');
      else if (canonical.name !== entry.name ||
               canonical.poster !== entry.poster ||
               canonical.posterShape !== entry.posterShape) {
        fail('title, image or shape differs from search catalog');
      }
      if (genreTags[file]) {
        const verified = genreCache[entry.id];
        if (!verified || !Array.isArray(verified.genres) ||
            !verified.genres.some(tag => genreTags[file].includes(tag))) {
          fail('genre not supported by verified animated-series metadata');
        }
      }
    }
  }
  console.log(label + ': ' + items.length + ' entries, ' + unique.size + ' unique IDs');
}
if (metadataExceptionsFound.size) {
  console.warn('Legacy IMDb mappings awaiting independent genre verification: ' +
    metadataExceptionsFound.size + ' (excluded from thematic shelves)');
}
if (errors > 0) {
  console.error('Catalog audit FAILED: ' + errors + ' issue(s)');
  process.exitCode = 1;
} else {
  console.log('Catalog audit PASSED: consistent anime-only metadata and posters.');
}
