'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, explain } from '@/lib/api';
import { NAME, conceptHref } from '@/lib/routes';
import type { AdaptiveAnswer, AdaptiveSession, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading } from '@/components/common';
import { Choice } from '@/components/choice';
import { ConfidencePicker } from '@/components/confidence';
import { codeSpans } from '@/components/markdown';
import { AttentionIcon } from '@/components/socrat/states';
import { ReasonChip } from '@/components/socrat/reason-chip';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useSession } from '@/lib/session';
import { FeedbackSheet, KeyHint, RUN_GLOW, RunTally, StampButton, praise, runOf, useAnswerKeys, type PracticeItem } from '@/components/socrat/answer-flow';
import { PracticeRound } from '@/components/socrat/practice-round';
import { SessionEnd } from '@/components/socrat/session-end';

type Question = NonNullable<AdaptiveSession['current']>;

const BANDS = 5;
const key = (activityId: string) => `socrat:adaptive:${activityId}`;

/** Why the engine picked this difficulty, in the learner's words. */
const PACE: Record<string, string> = {
  testout_start: 'starting in the middle',
  jump_after_fast: 'quick and right, so two steps harder',
  ladder_up: 'harder after a right answer',
  confirm_after_slow: 'same level once more, you took your time',
  easier_after_miss: 'a step easier after a miss',
};

/** Difficulty you can see: bars rise as the questions get harder. */
export function DifficultyMeter({ band, reason, of = BANDS }: { band: number; reason?: string; of?: number }) {
  const level = Math.min(Math.max(band, 1), of);
  return (
    <div className="flex flex-wrap items-end gap-1.5" role="img" aria-label={`Difficulty level ${level} of ${of}`}>
      {Array.from({ length: of }, (_, i) => (
        <span key={i} className={cn('w-6 rounded-md', i < level ? 'bg-primary' : 'bg-raised')} style={{ height: `${10 + i * 7}px` }} />
      ))}
      <span className="ml-2 text-[13px] text-muted-foreground">Difficulty {level} of {of}{reason ? ` · ${reason}` : ''}</span>
    </div>
  );
}

/**
 * A concept check (or review) served by the adaptive engine: each answer picks the next
 * question's difficulty. Calls `onFallback` when the engine is off or can't serve this check.
 */
export function AdaptiveCheck({ activityId, mode, concept, title, onFallback, onLocked }: {
  activityId: string;
  mode: 'concept_check' | 'review' | 'testout';
  concept: string;
  title: string;
  onFallback(): void;
  onLocked(): void;
}) {
  const [session, setSession] = useState<AdaptiveSession | null>(null);
  const [feedback, setFeedback] = useState<AdaptiveAnswer | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [sure, setSure] = useState<number | null>(null); // optional, for calibration
  const [history, setHistory] = useState<{ band: number; correct: boolean }[]>([]);
  const [next, setNext] = useState<Today['next'] | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const shownAt = useRef(Date.now());
  const testout = mode === 'testout';
  const top = testout ? 7 : BANDS;
  // Lesson feel (features.lesson_feel): the answered question stays on screen under a sheet,
  // and misses come back once, as practice, before the results. Test-outs keep results to the end.
  const { features } = useSession();
  const feel = features?.lesson_feel === true && !testout;
  const [asked, setAsked] = useState<{ question: Question; choice: number | null } | null>(null);
  const [missed, setMissed] = useState<PracticeItem[]>([]);
  const [practised, setPractised] = useState(false);
  const [ended, setEnded] = useState(false); // server-arranged end screens (features.session_end)

  const starting = useRef('');
  const start = useCallback(async (retry = false) => {
    // One session per check, even when React runs the effect twice.
    if (starting.current === activityId && !retry) return;
    starting.current = activityId;
    setError('');
    try {
      let saved = '';
      try { saved = sessionStorage.getItem(key(activityId)) ?? ''; } catch { /* per-tab nicety */ }
      if (saved) {
        const resumed = await api.get<AdaptiveSession>(`/adaptive-quiz/sessions/${saved}/next`).catch(() => null);
        if (resumed && !resumed.finished) { setSession(resumed); return; }
      }
      const s = await api.post<AdaptiveSession | { engine: 'legacy' }>('/adaptive-quiz/sessions', { mode, concepts: [concept] });
      if (s.engine !== 'adaptive') return onFallback();
      try { sessionStorage.setItem(key(activityId), s.id); } catch { /* ignore */ }
      setSession(s);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'concept_locked') onLocked();
      else if (e instanceof ApiError && e.status === 404 && e.code !== 'not_in_course') onFallback();
      else setError(explain(e));
    }
  }, [activityId, concept, mode, onFallback, onLocked]);
  useEffect(() => { void start(); }, [start]);
  useEffect(() => { shownAt.current = Date.now(); }, [session?.current?.item]);
  useEffect(() => {
    // After the check, show what the plan does next and why: the adaptation, not a guess.
    if (session?.finished && next === undefined) api.get<Today>('/today').then(t => setNext(t.next)).catch(() => setNext(null));
  }, [session?.finished, next]);

  async function answer(picked: number | null) {
    if (!session?.current) return;
    setBusy(true);
    setError('');
    try {
      const band = session.current.band;
      const result = await api.post<AdaptiveAnswer>(`/adaptive-quiz/sessions/${session.id}/answer`, {
        item: session.current.item,
        choice: picked,
        time_s: Math.round((Date.now() - shownAt.current) / 1000),
        ...(picked !== null && sure !== null ? { confidence: sure } : {}),
      });
      setSure(null);
      if (testout) {
        // Graded at the end: no right/wrong between questions, straight on to the next.
        setHistory(h => [...h, { band, correct: false }]);
        setSession(result.session);
        setChoice(null);
        if (result.session.finished) try { sessionStorage.removeItem(key(activityId)); } catch { /* ignore */ }
        return;
      }
      if (result.outcome !== 'skipped') setHistory(h => [...h, { band, correct: result.outcome === 'correct' }]);
      const question = session.current;
      setAsked({ question, choice: picked });
      if (result.outcome === 'wrong' && result.answer !== null) {
        setMissed(m => [...m, { key: `${question.item}:${m.length}`, prompt: codeSpans(question.prompt), code: question.code, options: question.options, answer: result.answer!, explanation: result.explanation }]);
      }
      setFeedback(result);
      if (result.session.finished) try { sessionStorage.removeItem(key(activityId)); } catch { /* ignore */ }
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  function proceed() {
    if (feedback) setSession(feedback.session);
    setFeedback(null);
    setAsked(null);
    setChoice(null);
  }

  const live = feedback ? null : session?.current ?? null;
  const run = runOf(history.map(h => h.correct));
  useAnswerKeys({
    enabled: feel && Boolean(live || feedback) && !busy,
    count: live?.options.length ?? 0,
    onPick: i => setChoice(i),
    onSubmit: () => {
      if (feedback) proceed();
      else if (choice !== null) void answer(choice);
    },
  });

  if (!session) return error ? <ErrorNote message={error} retry={() => start(true)} /> : <Loading variant="quiz" label="Loading the questions" />;

  if (feel && session.finished && !feedback && missed.length && !practised) {
    return <PracticeRound items={missed} onDone={() => setPractised(true)} />;
  }

  if (session.finished && !feedback && features?.session_end && !ended) {
    return <SessionEnd activityId={activityId} right={history.filter(h => h.correct).length} total={history.length || undefined} onDone={() => setEnded(true)} />;
  }

  if (session.finished && !feedback) {
    const trail = session.results ?? history;
    const right = trail.filter(h => h.correct).length;
    const passed = session.passed ?? (trail.length > 0 && right / trail.length >= 0.8);
    const peak = Math.max(0, ...trail.map(h => h.band));
    const early = session.stop_reason === 'needs_lesson';
    if (testout) {
      const transfer = `/transfer/${concept.split(':').join('/')}`;
      return (
        <div className="grid gap-6">
          <section data-tone={passed ? 'hero' : undefined} className={cn(passed ? 'rounded-card bg-forest p-6 text-forest-foreground lg:p-8 animate-pop' : 'rounded-card border border-attention bg-card p-6 lg:p-8')}>
            <p className={cn('text-[15px]', passed ? 'text-(--card-muted)' : 'text-muted-foreground')}>Test-out complete</p>
            <h1 className="type-display-l mt-2">{right} of {trail.length} correct</h1>
            <p className={cn('mt-3 text-base', passed ? 'text-(--card-muted)' : 'text-muted-foreground')}>
              {passed
                ? `Proven. ${session.hard_correct ?? 0} right at difficulty ${session.hard_band ?? peak}, the hardest Socrat has on this. You skip it on your plan.`
                : session.needs_transfer
                  ? 'Strong answers, but Socrat only has a few questions on this skill. Solve one unseen problem on your own to prove it.'
                  : session.stop_reason === 'strikes'
                    ? 'Three misses, so Socrat stopped. Nothing is lost: your plan teaches this one normally.'
                    : `Not proven yet: passing needs 75% and ${session.hard_needed ?? 2} right at the hardest level. Your plan teaches this one normally.`}
            </p>
            {peak ? <div className="mt-4"><DifficultyMeter band={peak} of={top} reason="highest reached" /></div> : null}
          </section>
          {trail.length ? (
            <section aria-labelledby="trail-heading" className="paper rounded-card p-5">
              <h2 id="trail-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">How it climbed</h2>
              <ol className="mt-4 flex items-end gap-1.5" aria-label="Difficulty and result of each question">
                {trail.map((h, i) => (
                  <li key={i} className="flex flex-col items-center gap-1">
                    <span className={cn('w-5 rounded-md', h.correct ? 'bg-primary' : 'border border-dashed border-attention bg-transparent')} style={{ height: `${8 + h.band * 7}px` }} />
                    <span className="sr-only">Question {i + 1}: difficulty {h.band}, {h.correct ? 'right' : 'missed'}</span>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}
          <div className="flex flex-wrap gap-3">
            {session.needs_transfer ? <Button asChild size="lg"><Link href={transfer}>Solve the proof problem<ArrowCircle /></Link></Button> : null}
            <Button asChild size="lg" variant={session.needs_transfer ? 'outline' : 'default'}><Link href="/today">Continue{session.needs_transfer ? null : <ArrowCircle />}</Link></Button>
            {!passed && !session.needs_transfer ? <Button asChild size="lg" variant="outline"><Link href={conceptHref(concept)}>Read the lesson</Link></Button> : null}
          </div>
        </div>
      );
    }
    return (
      <div className="grid gap-6">
        <section data-tone={passed ? 'hero' : undefined} className={cn(passed ? 'rounded-card bg-forest p-6 text-forest-foreground lg:p-8 animate-pop' : 'rounded-card border border-attention bg-card p-6 lg:p-8')}>
          <p className={cn('text-[15px]', passed ? 'text-(--card-muted)' : 'text-muted-foreground')}>{title} complete</p>
          <h1 className="type-display-l mt-2">{history.length ? `${right} of ${history.length} correct` : 'Check finished'}</h1>
          <p className={cn('mt-3 text-base', passed ? 'text-(--card-muted)' : 'text-muted-foreground')}>
            {mode === 'review'
              ? passed ? 'It stuck. The next review comes later than this one.' : 'It slipped a little, so the next review comes sooner.'
              : passed
                ? `Learned. You reached difficulty ${peak} of ${BANDS}; a review in a few days turns this into mastery.`
                : early
                  ? 'Socrat stopped early so you can learn the idea first instead of guessing at harder questions.'
                  : 'Not counted yet. Socrat added a different explanation and a fresh check to your plan.'}
          </p>
          {peak ? <div className="mt-4"><DifficultyMeter band={peak} reason="highest reached" /></div> : null}
        </section>
        {next ? (
          <section aria-labelledby="changed-heading" className="paper rounded-card p-5">
            <h2 id="changed-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">What Socrat does next</h2>
            <p className="mt-2 font-semibold">{next.title}</p>
            {next.reason ? <p className="mt-1 text-[15px] text-muted-foreground">{next.reason}</p> : null}
            {next.code ? <ReasonChip code={next.code} className="mt-3" /> : null}
          </section>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg"><Link href="/today">Continue<ArrowCircle /></Link></Button>
          {!passed ? <Button asChild size="lg" variant="outline"><Link href={conceptHref(concept)}>Read the lesson again</Link></Button> : null}
          <Button asChild size="lg" variant="outline"><Link href="/progress">{NAME.evidence}</Link></Button>
        </div>
      </div>
    );
  }

  if (feel) {
    const question = feedback ? asked?.question ?? null : session.current;
    const count = history.length + (feedback ? 0 : 1);
    return (
      <div className="grid gap-5">
        <div className="grid gap-2">
          <Progress value={(100 * history.length) / session.max_items} aria-label={`${history.length} answered, up to ${session.max_items}`} tone={run >= RUN_GLOW ? 'hi' : undefined} />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground tabular-nums">Question {count} · up to {session.max_items} · stops early once Socrat is sure</p>
            <RunTally run={run} />
          </div>
        </div>
        {question ? (
          <div key={question.item} className="grid gap-5 animate-in fade-in duration-200">
            <DifficultyMeter band={question.band} of={top} reason={history.length > (feedback ? 1 : 0) ? (history[history.length - (feedback ? 2 : 1)].correct ? 'harder after a right answer' : 'easier after a miss') : 'starting just below your level'} />
            {question.micro_lesson && !feedback ? (
              <p className="rounded-[4px] bg-raised px-4 py-3 text-[15px]">
                A few misses in a row. Quick refresher before the next one: <Link href={conceptHref(question.concept)} className="font-semibold underline underline-offset-4">reread the key idea</Link>.
              </p>
            ) : null}
            <h1 className="type-title text-balance">{codeSpans(question.prompt)}</h1>
            {question.code ? <pre className="code-block">{question.code}</pre> : null}
            <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
              {question.options.map((option, i) => {
                const tone = feedback && feedback.answer === i ? 'correct' : feedback && asked?.choice === i ? 'wrong' : 'idle';
                return (
                  <Choice key={i} role="radio" aria-checked={(feedback ? asked?.choice : choice) === i} selected={!feedback && choice === i} tone={tone} marker={String.fromCharCode(65 + i)} disabled={Boolean(feedback)} onClick={() => setChoice(i)}>
                    <span className="choice-title whitespace-pre-wrap">{option}</span>
                  </Choice>
                );
              })}
            </div>
            {!feedback ? (
              <>
                {choice !== null ? <ConfidencePicker value={sure} onChange={setSure} /> : null}
                <div className="flex flex-wrap items-center gap-3">
                  <StampButton disabled={busy || choice === null} aria-busy={busy} onClick={() => answer(choice)}>Check</StampButton>
                  <Button size="lg" variant="ghost" disabled={busy} onClick={() => answer(null)}>I haven&apos;t learned this yet</Button>
                </div>
                <KeyHint count={question.options.length} />
              </>
            ) : (
              <FeedbackSheet
                key={`${question.item}:sheet`}
                tone={feedback.outcome === 'correct' ? 'correct' : feedback.outcome === 'wrong' ? 'wrong' : 'neutral'}
                title={feedback.outcome === 'correct' ? praise(run, history.length) : feedback.outcome === 'skipped' ? 'Noted: not learned yet' : 'Not quite'}
                action={feedback.session.finished ? (missed.length ? 'Practise the misses' : 'See results') : 'Continue'}
                onContinue={proceed}
              >
                {feedback.outcome === 'wrong' && feedback.answer !== null ? <p>Answer: <span className="font-semibold">{question.options[feedback.answer]}</span>. It comes back once at the end, for practice.</p> : null}
                {feedback.explanation ? <p className="text-muted-foreground">{feedback.explanation}</p> : null}
                {feedback.misconception ? <p>Socrat noted a common mix-up here and will target it next.</p> : null}
              </FeedbackSheet>
            )}
          </div>
        ) : null}
        {error ? <ErrorNote message={error} /> : null}
      </div>
    );
  }

  const current = feedback ? null : session.current;
  const shown = current ?? null;
  const answered = history.length;
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <Progress value={(100 * answered) / session.max_items} aria-label={`${answered} answered, up to ${session.max_items}`} />
        <p className="text-sm text-muted-foreground tabular-nums">
          Question {answered + (feedback ? 0 : 1)} · up to {session.max_items} · {testout ? 'quick right answers climb faster, three misses end it, results at the end' : 'stops early once Socrat is sure'}
        </p>
      </div>
      {shown ? (
        <div key={shown.item} className="grid gap-5 animate-in fade-in duration-200">
          <DifficultyMeter band={shown.band} of={top} reason={testout ? PACE[shown.reason ?? ''] : history.length ? (history[history.length - 1].correct ? 'harder after a right answer' : 'easier after a miss') : 'starting just below your level'} />
          {shown.micro_lesson ? (
            <p className="rounded-[4px] bg-raised px-4 py-3 text-[15px]">
              A few misses in a row. Quick refresher before the next one: <Link href={conceptHref(shown.concept)} className="font-semibold underline underline-offset-4">reread the key idea</Link>.
            </p>
          ) : null}
          <h1 className="type-title text-balance">{codeSpans(shown.prompt)}</h1>
          {shown.code ? <pre className="code-block">{shown.code}</pre> : null}
          <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
            {shown.options.map((option, i) => (
              <Choice key={i} role="radio" aria-checked={choice === i} selected={choice === i} marker={String.fromCharCode(65 + i)} onClick={() => setChoice(i)}>
                <span className="choice-title whitespace-pre-wrap">{option}</span>
              </Choice>
            ))}
          </div>
          {choice !== null ? <ConfidencePicker value={sure} onChange={setSure} /> : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" disabled={busy || choice === null} aria-busy={busy} onClick={() => answer(choice)}>Check answer</Button>
            {testout ? null : <Button size="lg" variant="ghost" disabled={busy} onClick={() => answer(null)}>I haven&apos;t learned this yet</Button>}
          </div>
        </div>
      ) : feedback ? (
        <div role="status" className={cn('flex items-start gap-3 rounded-[4px] border bg-card p-4', feedback.outcome === 'correct' ? 'border-foreground' : 'border-attention')}>
          {feedback.outcome === 'correct' ? null : <AttentionIcon size={28} />}
          <div className="grid gap-2">
            <p className="font-bold">{feedback.outcome === 'correct' ? 'Correct' : feedback.outcome === 'skipped' ? 'Noted: you have not learned this yet' : 'Incorrect'}</p>
            {feedback.explanation ? <p className="text-[15px] text-muted-foreground">{feedback.explanation}</p> : null}
            {feedback.misconception ? <p className="text-[15px]">Socrat noted a common mix-up here and will target it next.</p> : null}
            <Button size="lg" className="mt-1 w-fit" onClick={proceed}>{feedback.session.finished ? 'See results' : 'Next question'}<ArrowCircle /></Button>
          </div>
        </div>
      ) : null}
      {error ? <ErrorNote message={error} /> : null}
    </div>
  );
}
