// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { dailyGoalName, evidencePoints, levelFor } from '../src/lib/game.ts';

test('levels climb with proven skills only', () => {
  assert.deepEqual(levelFor(0), { index: 0, name: 'Novice', proven: 0, next: 3, nextName: 'Apprentice', percent: 0 });
  assert.equal(levelFor(2).percent, 67);
  assert.equal(levelFor(3).name, 'Apprentice');
  assert.equal(levelFor(3).next, 8);
  assert.equal(levelFor(40).name, 'Sage');
  assert.equal(levelFor(40).next, null);
  assert.equal(levelFor(40).percent, 100);
  assert.equal(levelFor(-4).name, 'Novice');
});

test('evidence points count learned, mastered and minutes, never below zero', () => {
  assert.equal(evidencePoints({ learned: 2, mastered: 1, minutesToday: 7 }), 42);
  assert.equal(evidencePoints({ learned: -1, mastered: 0 }), 0);
});

test('daily goals are named by minutes', () => {
  assert.equal(dailyGoalName(5), 'Taste');
  assert.equal(dailyGoalName(15), 'Steady');
  assert.equal(dailyGoalName(45), 'Deep');
  assert.equal(dailyGoalName(1), 'Taste');
});
