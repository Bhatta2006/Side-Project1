// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { answerToPicks, matchReady, move, picksToAnswer } from '../src/lib/arrange.ts';

test('moving an item shifts it by one place and never leaves the list', () => {
  assert.deepEqual(move([0, 1, 2], 0, 1), [1, 0, 2]);
  assert.deepEqual(move([0, 1, 2], 2, -1), [0, 2, 1]);
  assert.deepEqual(move([0, 1, 2], 0, -1), [0, 1, 2]);
  assert.deepEqual(move([0, 1, 2], 2, 1), [0, 1, 2]);
  assert.deepEqual(move([0, 1, 2], 5, 1), [0, 1, 2]);
  const original = [0, 1, 2];
  move(original, 0, 1);
  assert.deepEqual(original, [0, 1, 2]);
});

test('answers round-trip through the text the API expects', () => {
  assert.equal(picksToAnswer([2, 0, 1]), '2,0,1');
  assert.deepEqual(answerToPicks('2,0,1'), [2, 0, 1]);
  assert.equal(answerToPicks('2,x,1'), null);
  assert.equal(answerToPicks(''), null);
  assert.equal(answerToPicks(undefined), null);
  assert.equal(answerToPicks('1,-1'), null);
});

test('a match is ready only when every left has a different choice', () => {
  assert.equal(matchReady([0, 1, 2]), true);
  assert.equal(matchReady([0, null, 2]), false);
  assert.equal(matchReady([0, 0, 2]), false);
  assert.equal(matchReady([]), false);
});
