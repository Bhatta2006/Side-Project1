// The game layer: evidence only. Every number here is computed from what the server already proved
// (skills learned by passing a check, skills mastered after a spaced review, minutes studied).
// No hearts, no gems, no leagues, nothing to buy, nothing that can be earned without the work.

/** Levels follow skills proven, never time spent. */
export const LEVELS = [
  { name: 'Novice', from: 0 },
  { name: 'Apprentice', from: 3 },
  { name: 'Seeker', from: 8 },
  { name: 'Thinker', from: 15 },
  { name: 'Scholar', from: 25 },
  { name: 'Sage', from: 40 },
] as const;

export interface LevelInfo {
  index: number;
  name: string;
  /** Skills proven so far. */
  proven: number;
  /** Proven skills the next level needs, or null at the top level. */
  next: number | null;
  nextName: string | null;
  /** 0 to 100 through the current level. */
  percent: number;
}

export function levelFor(proven: number): LevelInfo {
  const n = Math.max(0, Math.floor(proven));
  let index = 0;
  for (let i = 0; i < LEVELS.length; i++) if (n >= LEVELS[i].from) index = i;
  const here = LEVELS[index];
  const up = LEVELS[index + 1];
  const percent = up ? Math.round((100 * (n - here.from)) / (up.from - here.from)) : 100;
  return { index, name: here.name, proven: n, next: up ? up.from : null, nextName: up ? up.name : null, percent };
}

/**
 * Evidence points: 10 for each skill learned (passed its check), 15 more once it is mastered
 * (re-proven after time away), 1 for each minute studied today. Shown as XP; never spent.
 */
export function evidencePoints(o: { learned: number; mastered: number; minutesToday?: number }): number {
  return 10 * Math.max(0, o.learned) + 15 * Math.max(0, o.mastered) + Math.max(0, o.minutesToday ?? 0);
}

/** The daily-goal names the learner picks from, by minutes. */
export const DAILY_GOALS = [
  { minutes: 5, name: 'Taste' },
  { minutes: 10, name: 'Steady' },
  { minutes: 20, name: 'Serious' },
  { minutes: 30, name: 'Deep' },
] as const;

export const dailyGoalName = (minutes: number) =>
  [...DAILY_GOALS].reverse().find(g => minutes >= g.minutes)?.name ?? DAILY_GOALS[0].name;

/** Streak days worth a moment with Ember. */
export const STREAK_MILESTONES = [7, 30, 100] as const;

/** The milestone a streak of `days` has just reached, or null. */
export const streakMilestone = (days: number): number | null =>
  (STREAK_MILESTONES as readonly number[]).includes(days) ? days : null;

/** The next milestone above `days`, or null past the last one. */
export const nextStreakMilestone = (days: number): number | null => STREAK_MILESTONES.find(m => m > days) ?? null;

/**
 * Whether a level-up moment is due: the level for `proven` is above the last one the learner saw.
 * A first visit (nothing seen yet) records the level without a moment.
 */
export function levelUpDue(proven: number, seenIndex: number | null): boolean {
  return seenIndex !== null && levelFor(proven).index > seenIndex;
}
