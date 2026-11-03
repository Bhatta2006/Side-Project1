/**
 * The order a learner meets a concept's activities (master prompt 4 and 14: arbitrary ordered
 * combinations of activity types). The API sends `sequence` as ids such as "lesson", "quiz",
 * "visual:0", "task:reflect" or "problem:two-sum". Blocks the page renders in place (the lesson
 * text, visuals, tasks) follow that order; blocks the sequence does not name keep their default
 * order after the named ones, so a concept without a sequence looks exactly as before.
 */

export type InPage = { key: string; kind: 'lesson' | 'visual' | 'task'; index: number };

export type Step = { id: string; kind: string; ref: string; inPage: boolean };

const IN_PAGE = new Set(['lesson', 'visual', 'task']);

/** Default page order: lesson, then visuals, then tasks. */
export function defaultBlocks(visuals: number, taskIds: string[]): InPage[] {
  return [
    { key: 'lesson', kind: 'lesson', index: 0 },
    ...Array.from({ length: visuals }, (_, i) => ({ key: `visual:${i}`, kind: 'visual' as const, index: i })),
    ...taskIds.map((id, i) => ({ key: `task:${id}`, kind: 'task' as const, index: i })),
  ];
}

/** The page's own blocks, ordered by `sequence`; unnamed blocks keep their place after. */
export function orderBlocks(sequence: string[] | undefined, blocks: InPage[]): InPage[] {
  if (!sequence?.length) return blocks;
  const byKey = new Map(blocks.map(b => [b.key, b]));
  const named = sequence.map(s => byKey.get(s)).filter((b): b is InPage => Boolean(b));
  const seen = new Set(named.map(b => b.key));
  return [...named, ...blocks.filter(b => !seen.has(b.key))];
}

/** The full planned path, for the "your path through this lesson" list. */
export function steps(sequence: string[] | undefined): Step[] {
  return (sequence ?? []).map(id => {
    const [kind, ...rest] = id.split(':');
    return { id, kind, ref: rest.join(':'), inPage: IN_PAGE.has(kind) };
  });
}
