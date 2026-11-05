/** Helpers for the "put in order" and "match" practice questions. Pure, so they are testable. */

/** `order` with the item at `from` moved by `delta` places (clamped); the input is not changed. */
export function move(order: number[], from: number, delta: number): number[] {
  const to = from + delta;
  if (from < 0 || from >= order.length || to < 0 || to >= order.length || delta === 0) return order;
  const next = [...order];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

/** The answer text the API expects: option indexes, comma-separated ("2,0,1"). */
export function picksToAnswer(picks: number[]): string {
  return picks.join(',');
}

/** The picks an answer text stands for, or null when it is not a list of whole numbers. */
export function answerToPicks(answer: string | undefined): number[] | null {
  if (!answer) return null;
  const parts = answer.split(',');
  const picks = parts.map(p => (/^\d+$/.test(p) ? Number(p) : NaN));
  return picks.some(Number.isNaN) ? null : picks;
}

/** A match is complete when every left item has a different right item chosen. */
export function matchReady(picks: (number | null)[]): picks is number[] {
  return picks.length > 0 && picks.every(p => p !== null) && new Set(picks).size === picks.length;
}
