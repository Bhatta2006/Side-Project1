'use client';

import Link from 'next/link';
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
import { SocFigure } from '@/components/socrat/soc';
import { GoogleMark, PlanBuildingRun, WELCOME_KEY } from '@/components/socrat/plan-building';

/** A guest's plan is ready: signing in keeps it. Google returns to /start, which plays the build. */
function SavePlan() {
  const { features, profile, refresh } = useSession();
  const router = useRouter();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const remember = () => { try { sessionStorage.setItem(WELCOME_KEY, '1'); } catch { /* storage unavailable */ } };

  async function devSignIn() {
    setBusy(true);
    setError('');
    try {
      const name = profile?.display_name?.trim() || 'learner';
      const subject = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 64) || 'learner';
      await api.post('/auth/dev-login', { subject, display_name: name });
      remember();
      await refresh();
      router.replace('/start');
    } catch (e) {
      setError(explain(e));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid w-full max-w-md gap-8 px-4 pt-12 pb-32 sm:px-6 md:pt-20">
      <div className="grid justify-items-start gap-3">
        <SocFigure books mood="happy" idle size={130} />
        <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">nicely done</p>
        <h1 className="type-display-l">Save your <span className="hl hl-draw">plan</span></h1>
        <p className="text-base text-muted-foreground">Placement is done. Sign in so your plan and progress are kept, then we build it for you.</p>
      </div>
      <div className="grid gap-3">
        {features?.oidc_login ? (
          <Button asChild size="lg" className="w-full"><a href="/api/v1/auth/login" onClick={remember}><GoogleMark /> Continue with Google</a></Button>
        ) : null}
        {features?.email_login ? (
          <Button asChild variant="outline" size="lg" className="w-full"><Link href="/login?next=/start" onClick={remember}>Use email instead</Link></Button>
        ) : null}
        {features?.dev_login ? (
          <Button type="button" variant="outline" size="lg" className="w-full" disabled={busy} onClick={() => void devSignIn()}>Continue as a simulated learner (development)</Button>
        ) : null}
      </div>
      <p className="text-[13px] text-muted-foreground">
        By continuing you agree to the <a href="/terms" className="underline underline-offset-4">terms of service</a> and the <a href="/privacy" className="underline underline-offset-4">privacy policy</a>. You must be 13 or older.
      </p>
      {error ? <ErrorNote message={error} /> : null}
    </div>
  );
}

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
  const { profile, refresh } = useSession();
  const router = useRouter();
  const [state, setState] = useState<PlacementQuestion | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // After the last answer: guests save their plan first, signed-in learners watch it being built.
  const [phase, setPhase] = useState<'questions' | 'building' | 'save'>('questions');
  const guest = Boolean(profile?.guest);

  const finish = useCallback((justFinished: boolean) => {
    if (guest) setPhase('save');
    else if (justFinished) setPhase('building');
    else {
      // Just signed in from the save screen (the app shell remounts this page): /start plays the build.
      let welcome = false;
      try { welcome = sessionStorage.getItem(WELCOME_KEY) === '1'; } catch { /* storage unavailable */ }
      router.replace(welcome ? '/start' : '/today');
    }
  }, [guest, router]);
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

  if (phase === 'save') return <SavePlan />;
  // Refreshing the session last: it re-checks the guard, which would cut the sequence short.
  if (phase === 'building') return <PlanBuildingRun onDone={() => { void refresh().then(() => router.replace('/today')); }} />;

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
