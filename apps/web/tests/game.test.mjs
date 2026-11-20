// Run: npm run test:web-unit
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { dailyGoalName, evidencePoints, levelFor, levelUpDue, nextStreakMilestone, streakMilestone } from '../src/lib/game.ts';

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

test('streak milestones are 7, 30 and 100 days', () => {
  assert.equal(streakMilestone(7), 7);
  assert.equal(streakMilestone(8), null);
  assert.equal(streakMilestone(100), 100);
  assert.equal(nextStreakMilestone(0), 7);
  assert.equal(nextStreakMilestone(7), 30);
  assert.equal(nextStreakMilestone(100), null);
});

test('a level-up is due only past a level already seen', () => {
  assert.equal(levelUpDue(3, null), false, 'first visit records, no moment');
  assert.equal(levelUpDue(3, 0), true);
  assert.equal(levelUpDue(3, 1), false);
  assert.equal(levelUpDue(2, 0), false);
});
