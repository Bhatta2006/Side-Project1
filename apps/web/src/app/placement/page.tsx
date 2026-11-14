'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { useGuard, useSession } from '@/lib/session';
import type { PlacementQuestion } from '@/lib/types';
import { ErrorNote, Loading } from '@/components/common';
import { Choice } from '@/components/choice';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { codeSpans } from '@/components/markdown';
import { PlanBuildingRun } from '@/components/socrat/plan-building';

/** Placement questions are answered, not looked up: no copying, cutting, pasting or selecting. */
const noCopy = {
  onCopy: (e: React.ClipboardEvent) => e.preventDefault(),
  onCut: (e: React.ClipboardEvent) => e.preventDefault(),
  onPaste: (e: React.ClipboardEvent) => e.preventDefault(),
  onContextMenu: (e: React.MouseEvent) => e.preventDefault(),
  onDragStart: (e: React.DragEvent) => e.preventDefault(),
};

export default function Placement() {
  const allowed = useGuard('enrolled');
  const { refresh } = useSession();
  const router = useRouter();
  const [state, setState] = useState<PlacementQuestion | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // After the last answer the plan is built on screen, in place of a list of results.
  const [building, setBuilding] = useState(false);

  const finish = useCallback((justFinished: boolean) => {
    if (justFinished) setBuilding(true);
    else router.replace('/today');
  }, [router]);
  const loaded = useRef(false);

  useEffect(() => {
    if (!allowed || loaded.current) return;
    loaded.current = true;
    api
      .get<PlacementQuestion>('/placement')
      .then(q => {
        setState(q);
        if (q.done) finish(false);
      })
      .catch(e => setError(explain(e)));
  }, [allowed, finish]);

  async function submit(answer: number | null) {
    if (!state?.question) return;
    setBusy(true);
    setError('');
    try {
      const next = await api.post<PlacementQuestion>('/placement/answer', { item: state.question.id, choice: answer });
      setState(next);
      setChoice(null);
      if (next.done) finish(true);
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  // Refreshing the session last: it re-checks the guard, which would cut the sequence short.
  if (building) return <PlanBuildingRun onDone={() => { void refresh().then(() => router.replace('/today')); }} />;

  if (!allowed || (!state && !error)) return <Loading variant="quiz" label="Loading the placement check" />;

  const q = state?.question;
  return (
    <div className="mx-auto w-full max-w-2xl px-4 pt-8 pb-32 sm:px-6 md:pt-12">
      <div className="mb-10 grid gap-3">
        <div className="flex items-center justify-between gap-4">
          <p className="font-semibold">Placement check</p>
          {state?.max_questions ? <p className="text-sm font-semibold text-muted-foreground tabular-nums">Question {state.asked + 1} of at most {state.max_questions}</p> : <p className="text-sm font-semibold text-muted-foreground tabular-nums">Question {(state?.asked ?? 0) + 1}</p>}
        </div>
        {state?.max_questions ? <Progress value={(100 * state.asked) / state.max_questions} aria-label="Placement progress" /> : null}
      </div>
      {q ? (
        <div key={q.id} className="grid gap-5 select-none animate-in fade-in duration-200 [-webkit-touch-callout:none]" {...noCopy}>
          <Badge className="w-fit">{q.topic}</Badge>
          <h1 className="type-title min-h-[2.4em] text-balance">{codeSpans(q.prompt)}</h1>
          {q.code ? <pre className="code-block">{q.code}</pre> : null}
          <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
            {q.options.map((option, index) => (
              <Choice key={option} role="radio" aria-checked={choice === index} selected={choice === index} note={choice === index ? 'Selected' : undefined} marker={String.fromCharCode(65 + index)} onClick={() => setChoice(index)}>
                <span className="choice-title whitespace-pre-wrap">{option}</span>
              </Choice>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:flex">
            <Button size="lg" disabled={busy || choice === null} aria-busy={busy} onClick={() => submit(choice)}>Submit answer</Button>
            <Button size="lg" variant="outline" disabled={busy} onClick={() => submit(null)}>Not sure yet</Button>
          </div>
          <p className="text-sm text-muted-foreground">These questions are hard on purpose: edge cases, traces and bugs. Not sure yet is fine; that topic stays on your plan instead of being skipped.</p>
        </div>
      ) : null}
      {error ? <ErrorNote message={error} /> : null}
    </div>
  );
}
