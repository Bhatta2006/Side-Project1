// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { speakableChunks } from '../src/lib/speech.ts';

test('lesson text is spoken in sentence-sized chunks, in order, nothing lost', () => {
  const text = 'A fraction names equal parts.  Half of 8 is 4!   Is a third bigger than a quarter? Yes.';
  const chunks = speakableChunks(text, 40);
  assert.ok(chunks.every(c => c.length <= 40 && c.length > 0));
  assert.equal(chunks.join(' ').replace(/\s+/g, ' '), text.replace(/\s+/g, ' '));
});

test('a very long sentence is split at commas or spaces, never mid-word when it can help it', () => {
  const long = Array.from({ length: 60 }, (_, i) => `word${i}`).join(', ') + '.';
  const chunks = speakableChunks(long, 100);
  assert.ok(chunks.length > 3 && chunks.every(c => c.length <= 100));
  assert.ok(chunks.every(c => !/^\d|ord\d+$/.test(c.split(' ')[0])));
  assert.equal(chunks.join(' ').replace(/\s+/g, ' '), long);
});

test('empty or blank text has nothing to say', () => {
  assert.deepEqual(speakableChunks(''), []);
  assert.deepEqual(speakableChunks('   \n '), []);
});
