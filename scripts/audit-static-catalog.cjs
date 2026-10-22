#!/usr/bin/env node
'use strict';

// Deterministic offline audit for the public Anime-Sama TV catalog.
// No TV access, authentication, image downloads or output modification.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../docs/catalog/series');
const sets = [
  ['as_search', 'Search'],
  ['as_classics', 'Classics'],
  ['as_latest', 'Latest'],
  ['as_new', 'New']
];
const all = new Map();
let errors = 0;
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
    } else {
      const canonical = all.get(entry.id);
      if (!canonical) fail('missing from search catalog');
      else if (canonical.name !== entry.name ||
               canonical.poster !== entry.poster ||
               canonical.posterShape !== entry.posterShape) {
        fail('title, image or shape differs from search catalog');
      }
    }
  }
  console.log(label + ': ' + items.length + ' entries, ' + unique.size + ' unique IDs');
}
if (errors > 0) {
  console.error('Catalog audit FAILED: ' + errors + ' issue(s)');
  process.exitCode = 1;
} else {
  console.log('Catalog audit PASSED: consistent anime-only metadata and posters.');
}
