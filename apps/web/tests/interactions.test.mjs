// Run: node --experimental-strip-types --test apps/web/tests/interactions.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { accepted, blanks, move, normalise, rightAt, shuffled } from '../src/lib/interactions.ts';

test('blanks split text and keep every accepted form', () => {
  assert.deepEqual(blanks('A [[rule|rules]] from [[data]].'), [
    { text: 'A ' }, { blank: 0, accept: ['rule', 'rules'] }, { text: ' from ' }, { blank: 1, accept: ['data'] }, { text: '.' },
  ]);
});

test('answers match whatever their case, spaces, closing full stop or dollars', () => {
  assert.equal(normalise('  The  Rule. '), 'the rule');
  assert.ok(accepted('RULES', ['rule', 'rules']));
  assert.ok(accepted('$x^2$', ['x^2']));
  assert.ok(!accepted('', ['rule']));
  assert.ok(!accepted('rul', ['rule']));
});

test('a shuffle is fixed for its seed and never starts solved', () => {
  const items = ['a', 'b', 'c', 'd'];
  assert.deepEqual(shuffled(items, 'x'), shuffled(items, 'x'));
  for (const seed of ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']) {
    const out = shuffled(items, seed);
    assert.deepEqual([...out].sort(), items);
    assert.notDeepEqual(out, items);
  }
  assert.notDeepEqual(shuffled(['a', 'b'], 'z'), ['a', 'b']);
  assert.deepEqual(items, ['a', 'b', 'c', 'd']); // the input is not changed
});

test('moving and checking an order', () => {
  assert.deepEqual(move(['a', 'b', 'c'], 0, 1), ['b', 'a', 'c']);
  assert.deepEqual(move(['a', 'b', 'c'], 0, -1), ['a', 'b', 'c']);
  assert.deepEqual(rightAt(['b', 'a', 'c'], ['a', 'b', 'c']), [false, false, true]);
});
