// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { strongSoFar } from '../src/lib/strong-so-far.ts';

test('a strong band with evidence short of demonstrated is "strong so far"', () => {
  for (const stage of ['unknown', 'emerging', 'developing', 'proficient']) {
    assert.equal(strongSoFar({ band: 'strong', evidence: { stage } }), true, stage);
  }
});

test('demonstrated evidence earns the Mastered label', () => {
  assert.equal(strongSoFar({ band: 'strong', evidence: { stage: 'demonstrated' } }), false);
});

test('other bands and missing evidence are unchanged', () => {
  assert.equal(strongSoFar({ band: 'developing', evidence: { stage: 'emerging' } }), false);
  assert.equal(strongSoFar({ band: 'strong' }), false);
  assert.equal(strongSoFar({ band: 'strong', evidence: null }), false);
});
