/**
 * Answer checking for the in-lesson interactions (engine/renderers.py INTERACTIONS). Pure, so
 * it is unit-tested without a browser. The server already checked each answer key is
 * consistent; these only compare what the learner did with it.
 */

/** Same answer whatever its case, spacing, closing punctuation or maths dollars. */
export function normalise(text: string): string {
  return text.toLowerCase().replace(/\$/g, '').replace(/\s+/g, ' ').trim().replace(/[.,;:!?]+$/, '').trim();
}

export type BlankPart = { text: string } | { blank: number; accept: string[] };

/** "A [[rule|rules]] from [[data]]" -> text and blanks, in order. */
export function blanks(text: string): BlankPart[] {
  const out: BlankPart[] = [];
  let last = 0;
  let n = 0;
  for (const m of text.matchAll(/\[\[([^[\]]+)\]\]/g)) {
    if (m.index > last) out.push({ text: text.slice(last, m.index) });
    out.push({ blank: n++, accept: m[1].split('|').map(a => a.trim()).filter(Boolean) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

export function accepted(given: string, accept: string[]): boolean {
  const g = normalise(given);
  return g !== '' && accept.some(a => normalise(a) === g);
}

function hash(seed: string): number {
  let h = 2166136261;
  for (const ch of seed) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return h >>> 0;
}

/**
 * A fixed shuffle for a seed (the same on server and client, so no hydration mismatch), never
 * the original order when there are two or more items: a puzzle must not start solved.
 */
export function shuffled<T>(items: T[], seed: string): T[] {
  const out = [...items];
  let h = hash(seed);
  for (let i = out.length - 1; i > 0; i--) {
    h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0;
    const j = h % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  if (out.length > 1 && out.every((x, i) => x === items[i])) out.push(out.shift()!);
  return out;
}

/** Positions (0-based) the learner has right, for ordered lists and per-item answers. */
export function rightAt<T>(given: T[], key: T[]): boolean[] {
  return key.map((k, i) => given[i] === k);
}

/** Move the item at `from` one place up (-1) or down (+1); out of range leaves it as it is. */
export function move<T>(items: T[], from: number, step: -1 | 1): T[] {
  const to = from + step;
  if (to < 0 || to >= items.length) return items;
  const out = [...items];
  [out[from], out[to]] = [out[to], out[from]];
  return out;
}
