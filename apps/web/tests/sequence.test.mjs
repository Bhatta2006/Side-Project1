// Run: node --experimental-strip-types --test apps/web/tests/sequence.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defaultBlocks, orderBlocks, steps } from '../src/lib/sequence.ts';

const blocks = defaultBlocks(2, ['reflect', 'perform']);
const keys = list => list.map(b => b.key);

test('no sequence keeps the default order', () => {
  assert.deepEqual(keys(orderBlocks(undefined, blocks)), ['lesson', 'visual:0', 'visual:1', 'task:reflect', 'task:perform']);
  assert.deepEqual(keys(orderBlocks([], blocks)), keys(blocks));
});

test('named blocks follow the sequence, the rest keep their place after', () => {
  const order = orderBlocks(['visual:1', 'lesson', 'quiz', 'task:perform'], blocks);
  assert.deepEqual(keys(order), ['visual:1', 'lesson', 'task:perform', 'visual:0', 'task:reflect']);
});

test('ids the page does not render are ignored for ordering', () => {
  assert.deepEqual(keys(orderBlocks(['problem:two-sum', 'visual:9'], blocks)), keys(blocks));
});

test('steps split kind and reference and mark in-page ones', () => {
  assert.deepEqual(steps(['lesson', 'quiz', 'problem:a:b', 'task:reflect']), [
    { id: 'lesson', kind: 'lesson', ref: '', inPage: true },
    { id: 'quiz', kind: 'quiz', ref: '', inPage: false },
    { id: 'problem:a:b', kind: 'problem', ref: 'a:b', inPage: false },
    { id: 'task:reflect', kind: 'task', ref: 'reflect', inPage: true },
  ]);
});
