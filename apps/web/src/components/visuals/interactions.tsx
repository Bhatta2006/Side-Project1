'use client';

import { useId, useMemo, useState, type ReactNode } from 'react';
import Markdown, { codeSpans } from '@/components/markdown';
import { Button } from '@/components/ui/button';
import { accepted, blanks, move, rightAt, shuffled } from '@/lib/interactions';
import { cn } from '@/lib/utils';

/**
 * The in-lesson interactions (engine/renderers.py INTERACTIONS): small things a learner does on
 * a lesson page. Params were validated on the server. Every control is a real button, input or
 * select, so each works with a keyboard and a screen reader; nothing is dragged. Results are
 * practice only: nothing here is stored or counted as mastery.
 */

type P = Record<string, any>;

const tile = 'rounded-lg border px-3 py-2 text-left text-sm transition-colors';
const good = 'border-db-correct bg-db-correct-tint';
const bad = 'border-db-wrong bg-db-wrong-tint';

function Result({ right, total, children }: { right: number; total: number; children?: ReactNode }) {
  const all = right === total;
  return (
    <div role="status" aria-live="polite" className="mt-3 grid gap-2 text-sm">
      <p className={cn('font-semibold', all ? 'text-db-correct-ink' : 'text-foreground')}>
        {all ? 'All right.' : `${right} of ${total} right.`}
      </p>
      {children}
    </div>
  );
}

function Explain({ text }: { text?: string }) {
  return text ? <Markdown source={text} className="text-sm" /> : null;
}

function Prompt({ text }: { text?: string }) {
  return text ? <p className="mb-3 text-[15px] font-medium">{codeSpans(text)}</p> : null;
}

/** Check / try again / show the answer, shared by the puzzles with an answer key. */
function Actions({ checked, solved, onCheck, onRetry, onReveal, ready = true }: {
  checked: boolean; solved: boolean; onCheck: () => void; onRetry: () => void; onReveal: () => void; ready?: boolean;
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {!checked ? <Button type="button" size="sm" onClick={onCheck} disabled={!ready}>Check</Button> : null}
      {checked && !solved ? (
        <>
          <Button type="button" size="sm" variant="outline" onClick={onRetry}>Try again</Button>
          <Button type="button" size="sm" variant="ghost" onClick={onReveal}>Show the answer</Button>
        </>
      ) : null}
    </div>
  );
}

export function PredictReveal({ params }: { params: P }) {
  const options: string[] = params.options ?? [];
  const [choice, setChoice] = useState<number | null>(null);
  const [shown, setShown] = useState(false);
  return (
    <div>
      <Prompt text={params.prompt} />
      <div role="group" aria-label="Your prediction" className="grid gap-2">
        {options.map((o, i) => (
          <button
            key={i}
            type="button"
            aria-pressed={choice === i}
            disabled={shown}
            onClick={() => setChoice(i)}
            className={cn(
              tile,
              shown && i === params.answer ? good : shown && i === choice ? bad : choice === i ? 'border-primary bg-primary/10' : 'hover:bg-muted',
            )}
          >
            {codeSpans(o)}
          </button>
        ))}
      </div>
      {!shown ? (
        <Button type="button" size="sm" className="mt-3" disabled={choice === null} onClick={() => setShown(true)}>
          Lock in and reveal
        </Button>
      ) : (
        <Result right={choice === params.answer ? 1 : 0} total={1}>
          <Explain text={params.explanation} />
        </Result>
      )}
    </div>
  );
}

export function StepThrough({ params }: { params: P }) {
  const steps: { title?: string; body: string }[] = params.steps ?? [];
  const [shown, setShown] = useState(1);
  return (
    <div>
      {params.intro ? <Markdown source={params.intro} className="mb-3 text-sm" /> : null}
      <ol className="grid gap-3">
        {steps.slice(0, shown).map((s, i) => (
          <li key={i} className="rounded-lg border bg-card px-3 py-2">
            <p className="text-[13px] font-medium text-muted-foreground">Step {i + 1}{s.title ? `: ${s.title}` : ''}</p>
            <Markdown source={s.body} className="text-sm" />
          </li>
        ))}
      </ol>
      <div className="mt-3 flex items-center gap-3" aria-live="polite">
        {shown < steps.length ? (
          <Button type="button" size="sm" onClick={() => setShown(n => n + 1)}>Next step</Button>
        ) : (
          <Button type="button" size="sm" variant="outline" onClick={() => setShown(1)}>Start over</Button>
        )}
        <span className="text-[13px] text-muted-foreground">{shown} of {steps.length}. Think about the next step before you open it.</span>
      </div>
    </div>
  );
}

export function OrderSteps({ params, seed }: { params: P; seed: string }) {
  const key: string[] = params.items ?? [];
  const start = useMemo(() => shuffled(key, seed), [key, seed]);
  const [items, setItems] = useState(start);
  const [checked, setChecked] = useState(false);
  const marks = rightAt(items, key);
  const right = marks.filter(Boolean).length;
  return (
    <div>
      <Prompt text={params.prompt} />
      <ol className="grid gap-2">
        {items.map((item, i) => (
          <li key={item} className={cn(tile, 'flex items-center gap-2', checked && (marks[i] ? good : bad))}>
            <span className="w-5 shrink-0 tabular-nums text-muted-foreground">{i + 1}.</span>
            <span className="flex-1">{codeSpans(item)}</span>
            <span className="flex shrink-0 gap-1">
              <Button type="button" size="sm" variant="ghost" aria-label={`Move "${item}" up`} disabled={checked || i === 0}
                onClick={() => setItems(x => move(x, i, -1))}>↑</Button>
              <Button type="button" size="sm" variant="ghost" aria-label={`Move "${item}" down`} disabled={checked || i === items.length - 1}
                onClick={() => setItems(x => move(x, i, 1))}>↓</Button>
            </span>
          </li>
        ))}
      </ol>
      {checked ? <Result right={right} total={key.length}>{right === key.length ? <Explain text={params.explanation} /> : null}</Result> : null}
      <Actions
        checked={checked}
        solved={right === key.length}
        onCheck={() => setChecked(true)}
        onRetry={() => setChecked(false)}
        onReveal={() => setItems(key)}
      />
    </div>
  );
}

export function SortBuckets({ params, seed }: { params: P; seed: string }) {
  const buckets: string[] = params.buckets ?? [];
  const items: { text: string; bucket: string }[] = useMemo(() => shuffled(params.items ?? [], seed), [params.items, seed]);
  const [placed, setPlaced] = useState<Record<string, string>>({});
  const [checked, setChecked] = useState(false);
  const right = items.filter(i => placed[i.text] === i.bucket).length;
  return (
    <div>
      <Prompt text={params.prompt} />
      <ul className="grid gap-2">
        {items.map(item => (
          <li key={item.text} className={cn(tile, 'grid gap-2', checked && (placed[item.text] === item.bucket ? good : bad))}>
            <span>{codeSpans(item.text)}</span>
            <span role="group" aria-label={`Category for ${item.text}`} className="flex flex-wrap gap-1">
              {buckets.map(b => (
                <button
                  key={b}
                  type="button"
                  aria-pressed={placed[item.text] === b}
                  disabled={checked}
                  onClick={() => setPlaced(p => ({ ...p, [item.text]: b }))}
                  className={cn('rounded-md border px-2 py-1 text-[13px]', placed[item.text] === b ? 'border-primary bg-primary/10 font-medium' : 'hover:bg-muted')}
                >
                  {b}
                </button>
              ))}
            </span>
          </li>
        ))}
      </ul>
      {checked ? <Result right={right} total={items.length}>{right === items.length ? <Explain text={params.explanation} /> : null}</Result> : null}
      <Actions
        checked={checked}
        solved={right === items.length}
        ready={Object.keys(placed).length === items.length}
        onCheck={() => setChecked(true)}
        onRetry={() => setChecked(false)}
        onReveal={() => setPlaced(Object.fromEntries(items.map(i => [i.text, i.bucket])))}
      />
    </div>
  );
}

export function FillBlank({ params }: { params: P }) {
  const id = useId();
  const parts = useMemo(() => blanks(String(params.text ?? '')), [params.text]);
  const keys = parts.flatMap(p => ('blank' in p ? [p.accept] : []));
  const [given, setGiven] = useState<string[]>(() => keys.map(() => ''));
  const [checked, setChecked] = useState(false);
  const marks = keys.map((accept, i) => accepted(given[i] ?? '', accept));
  const right = marks.filter(Boolean).length;
  return (
    <div>
      <p className="text-[15px] leading-9">
        {parts.map((p, n) => 'blank' in p ? (
          <input
            key={n}
            id={`${id}-${p.blank}`}
            aria-label={`Blank ${p.blank + 1}`}
            value={given[p.blank] ?? ''}
            readOnly={checked}
            onChange={e => setGiven(g => g.map((v, i) => (i === p.blank ? e.target.value : v)))}
            onKeyDown={e => { if (e.key === 'Enter') setChecked(true); }}
            size={Math.max(6, ...p.accept.map(a => a.length + 2))}
            className={cn('mx-1 rounded-md border bg-background px-2 py-0.5 text-sm', checked && (marks[p.blank] ? good : bad))}
          />
        ) : <span key={n}>{codeSpans(p.text)}</span>)}
      </p>
      {checked ? <Result right={right} total={keys.length}>{right === keys.length ? <Explain text={params.explanation} /> : null}</Result> : null}
      <Actions
        checked={checked}
        solved={right === keys.length}
        ready={given.some(Boolean)}
        onCheck={() => setChecked(true)}
        onRetry={() => setChecked(false)}
        onReveal={() => setGiven(keys.map(k => k[0]))}
      />
    </div>
  );
}

export function MatchPairs({ params, seed }: { params: P; seed: string }) {
  const id = useId();
  const pairs: { left: string; right: string }[] = params.pairs ?? [];
  const rights = useMemo(() => shuffled(pairs.map(p => p.right), seed), [pairs, seed]);
  const [chosen, setChosen] = useState<string[]>(() => pairs.map(() => ''));
  const [checked, setChecked] = useState(false);
  const marks = rightAt(chosen, pairs.map(p => p.right));
  const right = marks.filter(Boolean).length;
  return (
    <div>
      <Prompt text={params.prompt} />
      <ul className="grid gap-2">
        {pairs.map((p, i) => (
          <li key={p.left} className={cn(tile, 'grid gap-2 sm:grid-cols-2 sm:items-center', checked && (marks[i] ? good : bad))}>
            <label htmlFor={`${id}-${i}`}>{codeSpans(p.left)}</label>
            <select
              id={`${id}-${i}`}
              value={chosen[i]}
              disabled={checked}
              onChange={e => setChosen(c => c.map((v, n) => (n === i ? e.target.value : v)))}
              className="min-h-9 w-full rounded-md border bg-background px-2 text-sm"
            >
              <option value="">Choose…</option>
              {rights.map(r => <option key={r} value={r}>{r.replace(/\$/g, '')}</option>)}
            </select>
          </li>
        ))}
      </ul>
      {checked ? <Result right={right} total={pairs.length} /> : null}
      <Actions
        checked={checked}
        solved={right === pairs.length}
        ready={chosen.every(Boolean)}
        onCheck={() => setChecked(true)}
        onRetry={() => setChecked(false)}
        onReveal={() => setChosen(pairs.map(p => p.right))}
      />
    </div>
  );
}
