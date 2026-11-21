import katex from 'katex';
import 'katex/dist/katex.min.css';

/**
 * One formula, typeset by KaTeX. `trust: false` keeps \href, \url, \includegraphics and raw
 * HTML commands out, and KaTeX escapes everything else, so its HTML is safe to insert.
 * TeX that will not typeset is shown as its source, never as an error.
 */
export function TeX({ tex, display = false }: { tex: string; display?: boolean }) {
  let html: string;
  try {
    html = katex.renderToString(tex, {
      displayMode: display, throwOnError: true, trust: false, strict: 'ignore', maxSize: 20, maxExpand: 500,
    });
  } catch {
    return <code className="math-source">{display ? `$$${tex}$$` : `$${tex}$`}</code>;
  }
  return display
    ? <div className="math-display" role="math" aria-label={tex} dangerouslySetInnerHTML={{ __html: html }} />
    : <span className="math-inline" dangerouslySetInnerHTML={{ __html: html }} />;
}
