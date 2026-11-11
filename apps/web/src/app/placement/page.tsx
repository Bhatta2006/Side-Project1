'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import type { PlacementQuestion, PlacementSummary } from '@/lib/types';
import { ErrorNote, Loading } from '@/components/common';
import { Choice } from '@/components/choice';
import { StatusLabel } from '@/components/socrat/status';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { codeSpans } from '@/components/markdown';
import { SocFigure } from '@/components/socrat/soc';

export default function Placement() {
  const allowed = useGuard('enrolled');
  const { refresh } = useSession();
  const [state, setState] = useState<PlacementQuestion | null>(null);
  const [summary, setSummary] = useState<PlacementSummary | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const finish = useCallback(async () => {
    setSummary(await api.get<PlacementSummary>('/placement/summary'));
    await refresh();
  }, [refresh]);

  useEffect(() => {
    if (!allowed) return;
    api
      .get<PlacementQuestion>('/placement')
      .then(async q => {
        setState(q);
        if (q.done) await finish();
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
      if (next.done) await finish();
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  if (!allowed || (!state && !error)) return <Loading variant="quiz" label="Loading the placement check" />;

  if (summary) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 pt-10 pb-32 sm:px-6 md:pt-16">
        <SocFigure books mood="happy" idle size={170} className="mb-4" />
        <p className="text-[15px] text-muted-foreground">Placement complete. {summary.correct} of {summary.asked} answered correctly.</p>
        <h1 className="type-display-l mt-2">Your plan is <span className="hl hl-draw">ready</span></h1>
        <p className="mt-3 text-base text-muted-foreground">
          {summary.starting_concept ? <>You start with <strong className="text-foreground">{summary.starting_concept}</strong>, at the edge of what you know.</> : 'You answered everything we asked. Short confirmation checks prove it before anything counts as learned.'}
        </p>
        {summary.weak_concepts?.length ? (
          <p className="mt-2 text-[15px] text-muted-foreground">Placement caught gaps in {summary.weak_concepts.join(', ')}. Your plan picks up there.</p>
        ) : null}
        {summary.known_concepts.length ? (
          <section className="mt-8 paper rounded-card p-5 lg:p-6" aria-labelledby="skip-heading">
            <h2 id="skip-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Lessons you can skip, once confirmed</h2>
            <p className="mt-1 text-[15px] text-muted-foreground">Placement suggests you know these. They are not counted as learned yet: each gets a short, harder confirmation check on your plan. Pass it and the skill counts; miss it and you learn it properly, no harm done.</p>
            <ul className="mt-4 grid gap-2">
              {summary.known_concepts.map(c => (
                <li key={c} className="flex min-h-12 flex-wrap items-center justify-between gap-2 rounded-[4px] bg-raised px-4 py-2.5">
                  <span className="font-semibold">{c}</span>
                  <StatusLabel status="assumed" muted className="text-[13px]" />
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <Button asChild size="lg" className="mt-8">
          <Link href="/today">See your plan<ArrowCircle /></Link>
        </Button>
      </div>
    );
  }

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
        <div key={q.id} className="grid gap-5 animate-in fade-in duration-200">
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
