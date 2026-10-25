import { Fragment, type ReactNode } from 'react';
import { CopyCodeBlock } from '@/components/socrat/copy-code-block';

/**
 * Minimal, dependency-free Markdown renderer for lessons and assistant replies.
 * Produces React elements only (never raw HTML), so content cannot inject markup.
 * Code fences tagged with another programming language than `language` are hidden,
 * which lets one lesson carry Python, C++ and Java variants side by side.
 */

const CODE_LANGUAGES: Record<string, string> = {
  python: 'python', py: 'python', cpp: 'cpp', 'c++': 'cpp', c: 'cpp', java: 'java',
};

type Block =
  | { type: 'heading'; level: number; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'code'; lang: string; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'quote'; text: string }
  | { type: 'table'; head: string[]; rows: string[][] }
  | { type: 'rule' };

function cells(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
}

export function parse(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const fence = line.match(/^\s*```\s*([\w+#-]*)/);
    if (fence) {
      const body: string[] = [];
      i++;
      while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) body.push(lines[i++]);
      i++;
      blocks.push({ type: 'code', lang: fence[1].toLowerCase(), text: body.join('\n') });
      continue;
    }
    if (!line.trim()) { i++; continue; }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) { blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] }); i++; continue; }
    if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) { blocks.push({ type: 'rule' }); i++; continue; }
    if (line.trim().startsWith('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const head = cells(line);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(cells(lines[i++]));
      blocks.push({ type: 'table', head, rows });
      continue;
    }
    if (/^\s*>/.test(line)) {
      const body: string[] = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) body.push(lines[i++].replace(/^\s*>\s?/, ''));
      blocks.push({ type: 'quote', text: body.join(' ') });
      continue;
    }
    const bullet = /^\s*([-*+]|\d+[.)])\s+/;
    if (bullet.test(line)) {
      const ordered = /^\s*\d/.test(line);
      const items: string[] = [];
      while (i < lines.length && (bullet.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && items.length))) {
        if (bullet.test(lines[i])) items.push(lines[i].replace(bullet, ''));
        else items[items.length - 1] += ' ' + lines[i].trim();
        i++;
      }
      blocks.push({ type: 'list', ordered, items });
      continue;
    }
    const body: string[] = [];
    while (
      i < lines.length && lines[i].trim() && !/^\s*```/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i]) &&
      !bullet.test(lines[i]) && !/^\s*>/.test(lines[i]) && !lines[i].trim().startsWith('|')
    ) body.push(lines[i++].trim());
    blocks.push({ type: 'paragraph', text: body.join(' ') });
  }
  return blocks;
}

/** Only `code` spans: for question prompts, where * and _ are usually maths, not emphasis. */
export function codeSpans(text: string): ReactNode[] {
  return text.split(/(`[^`]+`)/).map((part, i) => (i % 2 ? <code key={i}>{part.slice(1, -1)}</code> : part));
}

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*|_[^_\s][^_]*_)|(\[[^\]]+\]\([^)\s]+\))/g;

export function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const match of text.matchAll(INLINE)) {
    if (match.index > last) out.push(text.slice(last, match.index));
    const token = match[0];
    if (match[1]) out.push(<code key={key++}>{token.slice(1, -1)}</code>);
    else if (match[2]) out.push(<strong key={key++}>{inline(token.slice(2, -2))}</strong>);
    else if (match[3]) out.push(<em key={key++}>{inline(token.slice(1, -1))}</em>);
    else {
      const [, label, href] = token.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/) ?? [];
      if (href && /^https?:\/\//.test(href)) {
        out.push(<a key={key++} href={href} target="_blank" rel="noopener noreferrer">{inline(label)}</a>);
      } else if (href && href.startsWith('/')) {
        out.push(<a key={key++} href={href}>{inline(label)}</a>);
      } else out.push(label ?? token);
    }
    last = match.index + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const HEADINGS = ['h2', 'h2', 'h3', 'h4', 'h4', 'h4'] as const;

/** Stable anchor for a heading, shared with the lesson's "On this page" links. */
export function slug(text: string): string {
  return 'section-' + text.toLowerCase().replace(/[`*_[\]()]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/** Second-level headings of a lesson, for on-page navigation. */
export function outline(source: string): { id: string; text: string }[] {
  return parse(source).filter(b => b.type === 'heading' && b.level <= 2).map(b => {
    const text = (b as { text: string }).text.replace(/[`*_]/g, '');
    return { id: slug(text), text };
  });
}

export default function Markdown({ source, language, className = '' }: { source: string; language?: string; className?: string }) {
  const blocks = parse(source).filter(b => {
    if (b.type !== 'code' || !language) return true;
    const owner = CODE_LANGUAGES[b.lang];
    return !owner || owner === language;
  });
  return (
    <div className={`prose-socrat ${className}`}>
      {blocks.map((b, index) => {
        switch (b.type) {
          case 'heading': {
            const Tag = HEADINGS[b.level - 1];
            return <Tag key={index} id={b.level <= 2 ? slug(b.text.replace(/[`*_]/g, '')) : undefined}>{inline(b.text)}</Tag>;
          }
          case 'paragraph':
            return <p key={index}>{inline(b.text)}</p>;
          case 'code':
            return <CopyCodeBlock key={index} code={b.text} lang={b.lang || undefined} />;
          case 'list': {
            const Tag = b.ordered ? 'ol' : 'ul';
            return <Tag key={index}>{b.items.map((item, n) => <li key={n}>{inline(item)}</li>)}</Tag>;
          }
          case 'quote': {
            // A quote right after "try it before reading the reasoning" is an answer: hidden until asked for.
            const before = blocks[index - 1];
            const answer = before?.type === 'paragraph' && /before reading|reasoning below|try it|think first/i.test(before.text);
            return answer ? (
              <details key={index} className="answer-reveal">
                <summary>Show the reasoning</summary>
                <blockquote>{inline(b.text)}</blockquote>
              </details>
            ) : <blockquote key={index}>{inline(b.text)}</blockquote>;
          }
          case 'table':
            return (
              <div key={index} className="table-scroll" tabIndex={0} role="region" aria-label="Table">
                <table>
                  <thead><tr>{b.head.map((h, n) => <th key={n}>{inline(h)}</th>)}</tr></thead>
                  <tbody>{b.rows.map((row, r) => <tr key={r}>{row.map((c, n) => <td key={n}>{inline(c)}</td>)}</tr>)}</tbody>
                </table>
              </div>
            );
          case 'rule':
            return <hr key={index} />;
          default:
            return <Fragment key={index} />;
        }
      })}
    </div>
  );
}
