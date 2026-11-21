import { Fragment, type ReactNode } from 'react';
import { CopyCodeBlock } from '@/components/socrat/copy-code-block';
import { TeX } from '@/components/tex';
import { displayMath, pieces } from '@/lib/math';
import './lesson-prose.css';

/**
 * Minimal Markdown renderer for lessons and assistant replies.
 * Produces React elements only (never raw HTML), so content cannot inject markup; the one
 * exception is KaTeX's own output for maths (components/tex.tsx), which escapes its input.
 * Code fences tagged with another programming language than `language` are hidden,
 * which lets one lesson carry Python, C++ and Java variants side by side.
 */

const CODE_LANGUAGES: Record<string, string> = {
  python: 'python', py: 'python', cpp: 'cpp', 'c++': 'cpp', c: 'cpp', java: 'java',
};

type Block =
  | { type: 'heading'; level: number; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'math'; tex: string }
  | { type: 'code'; lang: string; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'quote'; text: string }
  | { type: 'table'; head: string[]; rows: string[][] }
  | { type: 'reveal'; summary: string; text: string }
  | { type: 'rule' };

/** Text between the tags of a <details> block, as text only: no markup is ever rendered. */
function detailsBlock(raw: string): { summary: string; text: string } {
  const summary = raw.match(/<summary[^>]*>([\s\S]*?)<\/summary>/i)?.[1]?.trim() ?? '';
  const text = raw
    .replace(/<summary[^>]*>[\s\S]*?<\/summary>/i, ' ')
    .replace(/<\/?details[^>]*>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .trim();
  return { summary: summary.replace(/<[^>]+>/g, ''), text };
}

function cells(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
}

const DISPLAY_START = /^\s*(\$\$|\\\[)/;

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
    // Display maths, $$...$$ or \[...\], on one line or several.
    if (DISPLAY_START.test(line)) {
      const close = line.trim().startsWith('$$') ? '$$' : '\\]';
      let j = i;
      let body = line;
      while (j + 1 < lines.length && body.trim().indexOf(close, 2) < 0 && lines[j + 1].trim()) body += '\n' + lines[++j];
      const tex = displayMath(body);
      if (tex) { blocks.push({ type: 'math', tex }); i = j + 1; continue; }
    }
    // Generated lessons keep self-check answers in <details>; they become a reveal, not raw tags.
    if (/^\s*<details/i.test(line)) {
      const body: string[] = [];
      while (i < lines.length) {
        body.push(lines[i]);
        if (/<\/details>/i.test(lines[i++])) break;
      }
      blocks.push({ type: 'reveal', ...detailsBlock(body.join('\n')) });
      continue;
    }
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
      !bullet.test(lines[i]) && !/^\s*>/.test(lines[i]) && !lines[i].trim().startsWith('|') &&
      !(body.length && DISPLAY_START.test(lines[i]))
    ) body.push(lines[i++].trim());
    blocks.push({ type: 'paragraph', text: body.join(' ') });
  }
  return blocks;
}

/** Only `code` spans and maths: for question prompts, where * and _ are usually maths, not emphasis. */
export function codeSpans(text: string): ReactNode[] {
  return pieces(text).map((p, i) =>
    p.kind === 'math' ? <TeX key={i} tex={p.tex} display={p.display} /> : p.kind === 'code' ? <code key={i}>{p.text}</code> : p.text);
}

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*|_[^_\s][^_]*_)|(\[[^\]]+\]\([^)\s]+\))/g;

/**
 * Inline Markdown. Code spans and maths are cut out first, so emphasis never eats a subscript;
 * each leaves a placeholder in the line, so emphasis around it still pairs up
 * (`**Sample space ($S$)**` is bold with maths inside, not two stray `**`).
 */
export function inline(text: string): ReactNode[] {
  const slots: ReactNode[] = [];
  const masked = pieces(text).map((p, i) => {
    if (p.kind === 'text') return p.text.replace(/[\uE000\uE001]/g, '');
    slots.push(p.kind === 'math' ? <TeX key={`m${i}`} tex={p.tex} display={p.display} /> : <code key={`k${i}`}>{p.text}</code>);
    return `\uE000${slots.length - 1}\uE001`;
  }).join('');
  return markup(masked, 't', slots);
}

const SLOT = /\uE000(\d+)\uE001/g;

/** Text with its maths and code put back. */
function restore(text: string, slots: ReactNode[]): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(SLOT)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push(slots[Number(m[1])]);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function markup(text: string, prefix: string, slots: ReactNode[]): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let n = 0;
  const key = () => `${prefix}-${n++}`;
  for (const match of text.matchAll(INLINE)) {
    if (match.index > last) out.push(...restore(text.slice(last, match.index), slots));
    const token = match[0];
    if (match[1]) out.push(<code key={key()}>{token.slice(1, -1)}</code>);
    else if (match[2]) { const k = key(); out.push(<strong key={k}>{markup(token.slice(2, -2), k, slots)}</strong>); }
    else if (match[3]) { const k = key(); out.push(<em key={k}>{markup(token.slice(1, -1), k, slots)}</em>); }
    else {
      const [, label, href] = token.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/) ?? [];
      const k = key();
      if (href && /^https?:\/\//.test(href)) {
        out.push(<a key={k} href={href} target="_blank" rel="noopener noreferrer">{markup(label, k, slots)}</a>);
      } else if (href && href.startsWith('/')) {
        out.push(<a key={k} href={href}>{markup(label, k, slots)}</a>);
      } else out.push(...restore(label ?? token, slots));
    }
    last = match.index + token.length;
  }
  if (last < text.length) out.push(...restore(text.slice(last), slots));
  return out;
}

/** Big-O and Theta in running text, e.g. O(n log n), so costs stand out as small chips. */
const COST = /(\b[OΘΩ]\([^()]*(?:\([^()]*\)[^()]*)*\))/g;

/** Rich inline: everything `inline` does, plus cost chips in plain text. Lessons only. */
function richInline(text: string): ReactNode[] {
  return inline(text).flatMap((node, n): ReactNode[] => {
    if (typeof node !== 'string') return [node];
    return node.split(COST).map((part, i) => (i % 2 ? <span key={`c${n}-${i}`} className="cost">{part}</span> : part));
  });
}

/** Lesson sections that read better as a margin note than as more body text. */
type Callout = 'mistake' | 'insight' | 'cue' | 'example' | 'recipe' | 'check' | 'compare';
const CALLOUTS: [RegExp, Callout, string][] = [
  [/common mistakes|things to watch|pitfall|gotcha|watch out|boundary cases/i, 'mistake', 'watch out'],
  [/why this works|big idea|key idea|intuition|in short|takeaway|remember/i, 'insight', 'the idea'],
  [/recognition cues|when to use|spot it/i, 'cue', 'spot it'],
  [/anchor|worked example|example/i, 'example', 'try this one'],
  [/template|recipe|state, transition|steps/i, 'recipe', 'the recipe'],
  [/check your understanding|self-check|quick check/i, 'check', 'check yourself'],
  [/contrast|variants|compare/i, 'compare', 'compare'],
];

function calloutFor(text: string): [Callout, string] | null {
  const hit = CALLOUTS.find(([rx]) => rx.test(text));
  return hit ? [hit[1], hit[2]] : null;
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

export default function Markdown({ source, language, className = '', rich = false }: {
  source: string;
  language?: string;
  className?: string;
  /** Lessons: margin-note callouts, highlighted key terms, formula cards and cost chips. */
  rich?: boolean;
}) {
  const blocks = parse(source).filter(b => {
    if (b.type !== 'code' || !language) return true;
    const owner = CODE_LANGUAGES[b.lang];
    return !owner || owner === language;
  });
  const text = rich ? richInline : inline;
  let lead = rich;

  function render(b: Block, index: number): ReactNode {
    switch (b.type) {
      case 'heading': {
        const Tag = HEADINGS[b.level - 1];
        return <Tag key={index} id={b.level <= 2 ? slug(b.text.replace(/[`*_]/g, '')) : undefined}>{text(b.text)}</Tag>;
      }
      case 'paragraph': {
        // A paragraph that is one code span on its own is a formula: give it room.
        if (rich && /^`[^`]+`\.?$/.test(b.text.trim())) {
          return <p key={index} className="formula"><code>{b.text.trim().replace(/\.$/, '').slice(1, -1)}</code></p>;
        }
        const first = lead;
        lead = false;
        return <p key={index} className={first ? 'lead' : undefined}>{text(b.text)}</p>;
      }
      case 'math':
        return <TeX key={index} tex={b.tex} display />;
      case 'code':
        return <CopyCodeBlock key={index} code={b.text} lang={b.lang || undefined} />;
      case 'list': {
        const Tag = b.ordered ? 'ol' : 'ul';
        return <Tag key={index}>{b.items.map((item, n) => <li key={n}>{text(item)}</li>)}</Tag>;
      }
      case 'quote': {
        // A quote right after "try it before reading the reasoning" is an answer: hidden until asked for.
        const before = blocks[index - 1];
        const answer = before?.type === 'paragraph' && /before reading|reasoning below|try it|think first/i.test(before.text);
        return answer ? (
          <details key={index} className="answer-reveal">
            <summary>Show the reasoning</summary>
            <blockquote>{text(b.text)}</blockquote>
          </details>
        ) : <blockquote key={index}>{text(b.text)}</blockquote>;
      }
      case 'table':
        return (
          <div key={index} className="table-scroll" tabIndex={0} role="region" aria-label="Table">
            <table>
              <thead><tr>{b.head.map((h, n) => <th key={n}>{text(h)}</th>)}</tr></thead>
              <tbody>{b.rows.map((row, r) => <tr key={r}>{row.map((c, n) => <td key={n}>{text(c)}</td>)}</tr>)}</tbody>
            </table>
          </div>
        );
      case 'reveal':
        return (
          <details key={index} className="answer-reveal">
            <summary>{b.summary ? text(b.summary) : 'Show the answer'}</summary>
            <div className="mt-2 grid gap-2">
              {b.text.split(/\n\s*\n/).map((para, n) => <p key={n}>{text(para.replace(/\s+/g, ' '))}</p>)}
            </div>
          </details>
        );
      case 'rule':
        return <hr key={index} />;
      default:
        return <Fragment key={index} />;
    }
  }

  const out: ReactNode[] = [];
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];
    const kind = rich && b.type === 'heading' && b.level >= 3 ? calloutFor(b.text) : null;
    if (b.type === 'heading' && kind) {
      // A small section (### Common mistakes, ### Why this works, ...) becomes one margin-note card,
      // running until the next heading.
      const body: ReactNode[] = [];
      let j = i + 1;
      while (j < blocks.length && blocks[j].type !== 'heading') body.push(render(blocks[j], j++));
      out.push(
        <section key={i} className={`callout callout-${kind[0]}`} aria-label={b.text.replace(/[`*_]/g, '')}>
          <p className="callout-note" aria-hidden="true">{kind[1]}</p>
          {render(b, i)}
          {body}
        </section>,
      );
      i = j - 1;
      continue;
    }
    if (rich && b.type === 'heading' && b.level <= 2 && /big idea/i.test(b.text)) lead = true;
    out.push(render(b, i));
  }
  return <div className={`prose-socrat ${rich ? 'prose-lesson' : ''} ${className}`}>{out}</div>;
}
