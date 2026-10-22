#!/usr/bin/env node
// Live metadata/stream-resolution smoke tests (PC only; never contacts an Android TV).
// No video files are downloaded. Tests only the stream descriptors returned by the provider.
const assert = require('node:assert/strict');
const provider = require('../providers/anime-sama.js');
const cases = [
  { title: 'Dan Da Dan S1E1', id: 'tt30217403', season: 1, episode: 1 },
  { title: 'Naruto S1E1', id: 'tt0409591', season: 1, episode: 1 },
  { title: 'The Fragrant Flower Blooms with Dignity S1E1', id: 'tt36592690', season: 1, episode: 1 },
];
// Redact host links and signed tokens even in error logs.
const originalLog = console.log.bind(console);
const originalWarn = console.warn.bind(console);
const originalError = console.error.bind(console);
const scrub = args => args.map(String).join(' ')
  .replace(/https?:\/\/[^\s\]'"<>]+/g, '[URL]')
  .replace(/[A-Za-z0-9_-]{70,}/g, '[TOKEN]');
console.log = (...args) => { if (process.env.VERBOSE_TESTS) originalLog(scrub(args)); };
console.warn = (...args) => { if (process.env.VERBOSE_TESTS) originalWarn(scrub(args)); };
console.error = (...args) => originalError(scrub(args));
(async () => {
  for (const item of cases) {
    const started = Date.now();
    const streams = await provider.getStreams(item.id, 'tv', item.season, item.episode);
    const count = Array.isArray(streams) ? streams.length : 0;
    originalLog(item.title + ': ' + count + ' resolved entries in ' + (Date.now()-started) + 'ms');
    assert.ok(count > 0, item.title + ': no playable descriptors');
    assert.ok(streams.every(s => typeof s.url === 'string' && /^https?:\/\//.test(s.url)), item.title + ': invalid URL');
  }
  originalLog('PASS: 3/3 Anime-Sama stream resolution smoke tests on PC.');
})().catch(err => { originalError('FAIL:', err.message); process.exitCode = 1; });
