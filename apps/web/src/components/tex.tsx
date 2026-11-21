'use client';

import { useEffect, useState } from 'react';
import 'katex/dist/katex.min.css';

type Katex = typeof import('katex').default;

// KaTeX is about 70 KB gzipped: loaded on the first formula, not with every page that can show
// lesson text (it put 8 routes over the 410 KB first-load budget in CI).
let katex: Katex | null = null;
let loading: Promise<void> | null = null;
function load(): Promise<void> {
  loading ??= import('katex').then(m => { katex = m.default; });
  return loading;
}

/**
 * One formula, typeset by KaTeX. `trust: false` keeps \href, \url, \includegraphics and raw
 * HTML commands out, and KaTeX escapes everything else, so its HTML is safe to insert.
 * TeX that will not typeset is shown as its source, never as an error. Until KaTeX has loaded
 * (a moment, once per visit) the formula shows as its source.
 */
export function TeX({ tex, display = false }: { tex: string; display?: boolean }) {
  const [, setReady] = useState(katex !== null);
  useEffect(() => {
    if (!katex) load().then(() => setReady(true), () => undefined);
  }, []);
  const source = display ? `$$${tex}$$` : `$${tex}$`;
  if (!katex) return <span className={display ? 'math-display' : 'math-inline'} aria-label={tex}>{source}</span>;
  let html: string;
  try {
    html = katex.renderToString(tex, {
      displayMode: display, throwOnError: true, trust: false, strict: 'ignore', maxSize: 20, maxExpand: 500,
    });
  } catch {
    return <code className="math-source">{source}</code>;
  }
  // A span even for display maths (styled as a block): $$...$$ also appears inside paragraphs,
  // and a <div> inside a <p> is invalid HTML.
  return display
    ? <span className="math-display" role="math" aria-label={tex} dangerouslySetInnerHTML={{ __html: html }} />
    : <span className="math-inline" dangerouslySetInnerHTML={{ __html: html }} />;
}
