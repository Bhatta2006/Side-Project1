/**
 * A lesson read one page at a time: each `## ` section is a page. Text before the first `## `
 * heading opens the first page. A lesson with fewer than two sections stays one page (it is
 * already short), so every lesson, old or new, can be shown this way without being rewritten.
 * How big each page is was decided for the learner when the lesson was written
 * (services/api/src/socrat/style/pages.py).
 */
export type Page = { title: string; body: string };

const CHECK = /^(check yourself|self-check|quick check|check your understanding)/i;

export function splitPages(source: string): Page[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const pages: Page[] = [];
  let lead: string[] = [];
  let current: { title: string; lines: string[] } | null = null;
  let fenced = false;
  for (const line of lines) {
    if (/^\s*```/.test(line)) fenced = !fenced;
    const heading = !fenced ? line.match(/^##\s+(.*)$/) : null;
    if (heading) {
      if (current) pages.push({ title: current.title, body: current.lines.join('\n').trim() });
      current = { title: heading[1].trim(), lines: current ? [] : lead };
      lead = [];
      continue;
    }
    (current ? current.lines : lead).push(line);
  }
  if (current) pages.push({ title: current.title, body: current.lines.join('\n').trim() });
  if (!pages.length) return [{ title: '', body: lead.join('\n').trim() }];
  return pages;
}

/** A closing page of questions, shown as the last check rather than more reading. */
export function isCheckPage(page: Page): boolean {
  return CHECK.test(page.title.replace(/[`*_]/g, ''));
}

/** Words of the page's teaching text (code and hidden answers excluded), for the reading time. */
export function words(page: Page): number {
  const text = page.body
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<details[\s\S]*?<\/details>/gi, ' ');
  return text.split(/\s+/).filter(Boolean).length;
}

/** Minutes to read, at a study pace; at least one. */
export function minutes(pages: Page[], rate = 130): number {
  return Math.max(1, Math.round(pages.reduce((n, p) => n + words(p), 0) / rate));
}
