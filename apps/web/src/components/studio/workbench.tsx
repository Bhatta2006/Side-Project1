'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Check, Lightbulb, Loader2 } from '@/components/icons';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { conceptHref } from '@/lib/routes';
import type { Today } from '@/lib/types';
import { Loading } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Graph } from './graph';
import type { StudioProps } from './registry';

interface Exercise { id: string; prompt: string; check: 'equivalent' | 'equation' | 'numeric' | 'steps'; unit: string; hints: string[]; plot: string[]; points: [number, number][]; difficulty: number }
interface Listing { concept: string; title: string; exercises: Exercise[] }
interface Verdict { verdict: 'correct' | 'incorrect' | 'unreadable'; reason: string; hint_text?: string; step?: number; evidence: boolean; explanation?: string; expected?: string }

const PLACEHOLDER: Record<Exercise['check'], string> = {
  equivalent: 'Type your answer, like (x+1)^2',
  equation: 'Type the solved equation, like x = 3',
  numeric: 'Type a number',
  steps: 'One line of working per line; the last line is your answer',
};

function Problem({ concept, exercise }: { concept: string; exercise: Exercise }) {
  const [given, setGiven] = useState('');
  const [shown, setShown] = useState(0);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [revealed, setRevealed] = useState<Verdict | null>(null);
  const [busy, setBusy] = useState(false);
  const [fit, setFit] = useState<{ slope: number; intercept: number } | null>(null);

  async function send(extra: object = {}) {
    setBusy(true);
    try {
      const body = exercise.check === 'steps' ? { lines: given.split('\n') } : { given: given + (exercise.check === 'numeric' && exercise.unit && !/[a-z]/i.test(given) ? ` ${exercise.unit}` : '') };
      return await api.post<Verdict>('/workbench/check', { concept, exercise: exercise.id, hints_used: shown, ...body, ...extra });
    } catch (e) { toast.error(explain(e)); return null; }
    finally { setBusy(false); }
  }

  const done = verdict?.verdict === 'correct' || revealed !== null;
  return (
    <section className="grid gap-3 rounded-card border p-5" aria-label={exercise.prompt}>
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium">{exercise.prompt}</p>
        <Badge variant="secondary">{'●'.repeat(exercise.difficulty)}</Badge>
      </div>
      <Graph expressions={exercise.plot} label={`Graph for: ${exercise.prompt}`} mine={exercise.check === 'equivalent' && !done ? given : undefined} points={exercise.points} onFit={(slope, intercept) => setFit({ slope, intercept })} />
      {exercise.points.length && fit ? <p role="status" className="text-sm">Drag the two red handles onto the teal points. Your line: slope <b>{fit.slope}</b>, intercept <b>{fit.intercept}</b>.</p> : null}
      {exercise.plot.length && exercise.check === 'equivalent' ? <p className="text-xs text-muted-foreground">Solid lines are the problem. Type your answer and its graph appears dashed in red: they should land on top of each other.</p> : null}
      {exercise.check === 'steps' ? (
        <Textarea value={given} onChange={e => setGiven(e.target.value)} rows={4} placeholder={PLACEHOLDER.steps} disabled={done} aria-label="Your working" />
      ) : (
        <div className="flex items-center gap-2">
          <Input value={given} onChange={e => setGiven(e.target.value)} placeholder={PLACEHOLDER[exercise.check]} disabled={done} aria-label="Your answer"
            onKeyDown={e => { if (e.key === 'Enter' && given.trim()) send().then(setVerdict); }} />
          {exercise.unit ? <span className="text-sm text-muted-foreground">{exercise.unit}</span> : null}
        </div>
      )}
      {shown > 0 ? <ul className="grid gap-1 text-sm text-muted-foreground">{exercise.hints.slice(0, shown).map(h => <li key={h}>Hint: {h}</li>)}</ul> : null}
      {verdict && !revealed ? (
        <p role="status" className={verdict.verdict === 'correct' ? 'text-sm font-medium text-success' : 'text-sm text-muted-foreground'}>
          {verdict.verdict === 'correct' ? 'Correct.' : verdict.reason}
          {verdict.verdict !== 'correct' && verdict.hint_text ? ` ${verdict.hint_text}` : ''}
        </p>
      ) : null}
      {(verdict?.verdict === 'correct' && verdict.explanation) || revealed ? (
        <div className="rounded-md bg-muted p-3 text-sm">
          {revealed ? <p className="mb-1 font-medium">Answer: {revealed.expected}</p> : null}
          <p>{revealed?.explanation ?? verdict?.explanation}</p>
        </div>
      ) : null}
      {!done ? (
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy || !given.trim()} onClick={() => send().then(setVerdict)}>
            {busy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Check data-icon="inline-start" />} Check
          </Button>
          {shown < exercise.hints.length ? (
            <Button variant="outline" onClick={() => setShown(n => n + 1)}><Lightbulb data-icon="inline-start" /> Hint</Button>
          ) : null}
          <Button variant="ghost" disabled={busy} onClick={() => send({ give_up: true }).then(r => r && setRevealed(r))}>Show me</Button>
        </div>
      ) : null}
    </section>
  );
}

/** The math studio: problems you answer, checked by a computer algebra system, with graphs. */
export function Workbench({ shape }: StudioProps) {
  void shape;
  const [state, setState] = useState<{ listing: Listing | null } | undefined>(undefined);
  useEffect(() => {
    api.get<Today>('/today')
      .then(today => {
        const concept = today.next?.concept;
        if (!concept) return null;
        return api.get<Listing>(`/workbench/${concept.replace(':', '/')}`);
      })
      .then(listing => setState({ listing }))
      .catch(() => setState({ listing: null }));
  }, []);

  if (state === undefined) return <Loading variant="article" label="Opening your problems" />;
  const listing = state.listing;
  if (!listing || !listing.exercises.length) {
    return (
      <EmptyState title="No problems for this topic yet">
        Read the lesson first; problems appear here once the topic has them.
      </EmptyState>
    );
  }
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        {listing.title} · <Link className="underline" href={conceptHref(listing.concept)}>read the lesson</Link>
      </p>
      {listing.exercises.map(e => <Problem key={e.id} concept={listing.concept} exercise={e} />)}
    </div>
  );
}
