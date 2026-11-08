'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { ApiError, api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { KIND_LABEL, NAME, QUIZ_KINDS, conceptHref, formatStamp, joinSegments } from '@/lib/routes';
import type { ActivityKind, Gate, QuizQuestion, QuizSession } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading } from '@/components/common';
import { Choice } from '@/components/choice';
import { StatusIcon } from '@/components/socrat/status';
import { AttentionIcon, LockedState } from '@/components/socrat/states';
import { AdaptiveCheck } from '@/components/socrat/adaptive-check';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { codeSpans } from '@/components/markdown';
import { UpgradeBanner } from '@/components/paywall';
import { SocFigure } from '@/components/socrat/soc';
import { useExamGuard } from '@/components/socrat/soc-moment';

function Options({ q, choice, onChoose, graded }: { q: QuizQuestion; choice: number | null; onChoose(i: number): void; graded: boolean }) {
  return (
    <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
      {q.options.map((option, index) => {
        let tone: 'idle' | 'correct' | 'wrong' = 'idle';
        if (graded && q.answered) {
          if (index === q.answer) tone = 'correct';
          else if (index === q.choice) tone = 'wrong';
        }
        const selected = q.answered ? q.choice === index : choice === index;
        const note = tone === 'correct' ? (q.choice === index ? 'Correct' : 'Correct answer') : tone === 'wrong' ? 'Incorrect' : selected && !q.answered ? 'Selected' : undefined;
        return (
          <Choice
            key={index}
            role="radio"
            aria-checked={selected}
            selected={selected && tone === 'idle'}
            tone={tone}
            note={note}
            marker={String.fromCharCode(65 + index)}
            disabled={q.answered}
            onClick={() => onChoose(index)}
          >
            <span className="choice-title whitespace-pre-wrap">{option}</span>
          </Choice>
        );
      })}
    </div>
  );
}

/** Focus header: back, title, question count and a thin bar. */
function QuizHeader({ title, topic, count, value }: { title: string; topic?: string; count?: string; value: number }) {
  return (
    <div className="mb-8">
      <div className="mb-4 flex items-center gap-3">
        <Link href="/today" transitionTypes={['nav-back']} aria-label={`Back to ${NAME.today}`} className="grid size-11 flex-none place-items-center rounded-full border border-border-strong transition-colors hover:bg-raised">
          <ArrowLeft className="size-5" strokeWidth={1.5} aria-hidden="true" />
        </Link>
        <p className="min-w-0 flex-1 truncate font-semibold">{title}{topic ? <span className="font-medium text-muted-foreground">, {topic}</span> : null}</p>
        {count ? <p className="flex-none text-sm font-semibold text-muted-foreground tabular-nums">{count}</p> : null}
      </div>
      <Progress value={value} aria-label="Progress" />
    </div>
  );
}

/** Misses are limited. Difficulty is never shown: every checkpoint question is a hard one. */
function GateMeter({ gate, asked }: { gate: Gate; asked: number }) {
  const left = gate.max_strikes - gate.strikes;
  return (
    <div className="mb-8 grid gap-4 paper rounded-card p-5 sm:grid-cols-[1fr_auto] sm:items-center lg:p-6">
      <div className="min-w-0">
        <p className="flex items-center gap-2 font-semibold"><StatusIcon status="locked" size={20} /> Checkpoint: {gate.module}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {gate.unlocks ? <>Pass to unlock <span className="font-semibold text-foreground">{gate.unlocks}</span>. </> : null}
          Every question here is a hard one. Results come at the end.
        </p>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div>
          <p className="text-[13px] text-muted-foreground">Question</p>
          <p className="font-bold tabular-nums">{asked} / up to {gate.max_items}</p>
        </div>
        <div role="img" aria-label={`${left} misses left`}>
          <p className="text-[13px] text-muted-foreground" aria-hidden="true">Misses left</p>
          <p className="mt-1 flex gap-1" aria-hidden="true">
            {Array.from({ length: gate.max_strikes }, (_, i) => (
              <span key={i} className={cn('size-3.5 rounded-full border-[1.5px]', i < left ? 'border-foreground bg-foreground' : 'border-dashed border-muted-foreground')} />
            ))}
          </p>
        </div>
      </div>
    </div>
  );
}

function GateResult({ gate }: { gate: Gate }) {
  const percent = Math.round((gate.score ?? 0) * 100);
  if (gate.passed) {
    return (
      <section data-tone="hero" className="relative mb-8 overflow-hidden rounded-card bg-forest p-6 text-forest-foreground animate-pop lg:p-8">
        <div aria-hidden="true" className="pointer-events-none absolute right-6 -bottom-3 hidden w-[170px] sm:block"><SocFigure books mood="proud" idle className="h-auto w-full" /></div>
        <p className="text-[15px] text-(--card-muted)">Checkpoint passed. Weighted score {percent}%.</p>
        <h1 className="type-display-l mt-2">{gate.unlocks ? `${gate.unlocks} unlocked` : 'Course checkpoint passed'}</h1>
        <p className="mt-3 text-base text-(--card-muted)">{gate.hard_correct} correct on the toughest questions. Your plan now opens the next module.</p>
        {gate.unlocks ? (
          <Link href="/plan" className="mt-5 flex min-h-14 items-center gap-3 rounded-[16px] bg-proof px-4 py-3 font-semibold text-proof-foreground transition-opacity hover:opacity-90">
            <StatusIcon status="not_seen" size={22} />
            <span className="flex-1">{gate.unlocks}</span>
            <span className="text-[13px] font-medium">Now open in {NAME.skills}</span>
          </Link>
        ) : null}
      </section>
    );
  }
  return (
    <section className="relative mb-8 overflow-hidden rounded-card border border-attention bg-card p-6 lg:p-8">
      <div aria-hidden="true" className="pointer-events-none absolute right-6 bottom-4 hidden w-[120px] sm:block"><SocFigure mood="worried" idle className="h-auto w-full" /></div>
      <p className="flex items-center gap-2 text-[15px] text-muted-foreground"><AttentionIcon /> Checkpoint: {gate.module}. Score {percent}%.</p>
      <h1 className="type-display-l mt-2">Not yet</h1>
      <p className="mt-3 max-w-xl text-base text-muted-foreground sm:pr-[130px]">
        Passing needs {Math.round(gate.pass_score * 100)}% and {gate.hard_needed} correct on the toughest questions ({gate.hard_correct} this time).
        Your plan added focused reviews on the weakest topics.
      </p>
      {gate.retry_at ? <p className="mt-4 inline-flex rounded-full border border-border-strong px-4 py-2 text-sm font-semibold">Next attempt opens {formatStamp(gate.retry_at)}</p> : null}
    </section>
  );
}

export default function Quiz() {
  const allowed = useGuard('active');
  const params = useParams<{ activity: string[] }>();
  const path = joinSegments(params.activity);
  // /quiz/<course>/<skill> is a concept check; the older /quiz/quiz/... form still works.
  const activityId = path.startsWith('quiz:') || QUIZ_KINDS.includes(path.split(':')[0]) ? path : `quiz:${path}`;
  const kind = activityId.split(':')[0] as ActivityKind;
  const { features } = useSession();
  // Concept checks and reviews adapt question by question; everything else is a fixed set.
  const [fixed, setFixed] = useState(false);
  const adaptive = (kind === 'quiz' || kind === 'review' || kind === 'testout') && features?.adaptive_quiz === true && !fixed;
  const [locked, setLocked] = useState(false);
  const [upgrade, setUpgrade] = useState(false);
  const fallBack = useCallback(() => setFixed(true), []);
  const lock = useCallback(() => setLocked(true), []);
  const [session, setSession] = useState<QuizSession | null>(null);
  const [index, setIndex] = useState(0);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const finishedFixed = Boolean(session?.completed && (session.feedback === 'at_end' || index === (session?.questions.length ?? 0)));
  // Checks and tests are your own work: no copy, paste or screenshots while one is open.
  const guard = useExamGuard(allowed && kind !== 'review' && !finishedFixed && !locked && !upgrade);

  const load = useCallback(() => {
    setError('');
    api
      .get<QuizSession>(`/quiz/${activityId}`)
      .then(s => {
        setSession(s);
        const first = s.questions.findIndex(q => !q.answered);
        setIndex(first < 0 ? 0 : first);
      })
      .catch(e => {
        if (e instanceof ApiError && e.code === 'concept_locked') setLocked(true);
        else if (e instanceof ApiError && e.code === 'upgrade_required') setUpgrade(true);
        else setError(explain(e));
      });
  }, [activityId]);
  useEffect(() => { if (allowed && features && !adaptive) load(); }, [allowed, features, adaptive, load]);

  async function answer() {
    if (!session || choice === null) return;
    const q = session.questions[index];
    setBusy(true);
    setError('');
    try {
      const next = await api.post<QuizSession>(`/quiz/${activityId}/answer`, { item: q.id, choice });
      setSession(next);
      setChoice(null);
      if (next.feedback === 'at_end' && !next.completed) setIndex(i => Math.min(i + 1, next.questions.length - 1));
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  const total = session?.questions.length ?? 0;
  const showResults = Boolean(session?.completed && (session.feedback === 'at_end' || index === total));
  const percent = Math.round((session?.score ?? 0) * 100);

  if (upgrade) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <UpgradeBanner title="This check is for Founding Members">
          Free covers the first 2 modules. Unlock every topic, checkpoint and practice problem to keep going.
        </UpgradeBanner>
      </div>
    );
  }
  if (locked) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <LockedState title="This check is locked for now" href="/plan" action="See checkpoints">
          It opens when you pass the checkpoint before it. Your plan shows which one.
        </LockedState>
      </div>
    );
  }
  if (allowed && adaptive) {
    const concept = activityId.split(':').slice(1).join(':');
    const label = KIND_LABEL[kind] ?? 'Quiz';
    return (
      <div className="mx-auto w-full max-w-3xl px-4 pt-6 pb-32 sm:px-6 md:pt-8">
        <QuizHeader title={label} topic={concept.split(':')[1]?.replaceAll('-', ' ')} value={0} />
        <AdaptiveCheck activityId={activityId} mode={kind === 'review' ? 'review' : kind === 'testout' ? 'testout' : 'concept_check'} concept={concept} title={label} onFallback={fallBack} onLocked={lock} />
        {guard}
      </div>
    );
  }
  if (!allowed || (!session && !error)) return <Loading variant="quiz" label="Loading the questions" />;
  if (!session) return <div className="mx-auto max-w-3xl p-6"><ErrorNote message={error} retry={load} /></div>;

  const title = KIND_LABEL[kind] ?? 'Quiz';
  const topic = kind === 'checkpoint' ? 'mixed questions from this module' : session.questions[0]?.concept_title;

  if (showResults) {
    const wrong = session.questions.filter(q => q.correct === false);
    const right = session.questions.filter(q => q.correct).length;
    const topics = [...new Map(wrong.map(q => [q.concept, q.concept_title])).entries()];
    return (
      <div className="mx-auto w-full max-w-3xl px-4 pt-6 pb-32 sm:px-6 md:pt-8">
        <QuizHeader title={title} topic={topic} value={100} />
        {session.gate ? <GateResult gate={session.gate} /> : (
          <section data-tone={percent >= 80 ? 'hero' : undefined} className={cn('mb-8', percent >= 80 && 'rounded-card bg-forest p-6 text-forest-foreground lg:p-8 animate-pop')}>
            {percent >= 80 ? <span className="mb-4 grid size-12 place-items-center rounded-full bg-proof text-proof-foreground" aria-hidden="true"><svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg></span> : null}
            <p className={cn('text-[15px]', percent >= 80 ? 'text-(--card-muted)' : 'text-muted-foreground')}>{title} complete</p>
            <h1 className="type-display-l mt-2">{right} of {total} correct</h1>
            <p className={cn('mt-3 text-base', percent >= 80 ? 'text-(--card-muted)' : 'text-muted-foreground')}>
              {session.testout
                ? session.testout.passed
                  ? 'Test-out passed: you skip straight past this on your plan.'
                  : 'Not this time, and nothing is lost. Your plan carries on as normal.'
                : kind === 'probe'
                  ? 'Socrat uses this to find the real gap and may suggest a refresher. You decide.'
                  : percent >= 80
                    ? 'Your plan moves you forward.'
                    : 'Not counted yet. Socrat added a different explanation and a fresh check to your plan.'}
            </p>
          </section>
        )}
        {topics.length ? (
          <section className="mb-8" aria-labelledby="revisit-heading">
            <h2 id="revisit-heading" className="mb-3 font-display text-xl font-semibold tracking-[-0.03em]">Topics worth revisiting</h2>
            <ul className="grid gap-2">
              {topics.map(([id, name]) => (
                <li key={id} className="flex min-h-14 items-center gap-3 rounded-[16px] bg-raised px-4 py-2">
                  <StatusIcon status="review" size={22} />
                  <span className="flex-1 font-semibold">{name}</span>
                  <Link href={conceptHref(id)} className="text-[15px] font-semibold underline underline-offset-4">Review<span className="sr-only"> {name}</span></Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {wrong.length ? (
          <section className="mb-8" aria-labelledby="answers-heading">
            <h2 id="answers-heading" className="mb-3 font-display text-xl font-semibold tracking-[-0.03em]">Answers to review</h2>
            <div className="grid gap-3">
              {wrong.map(q => (
                <div key={q.id} className="grid gap-3 paper rounded-card p-5">
                  <Badge className="w-fit">{q.concept_title}</Badge>
                  <p className="font-semibold">{codeSpans(q.prompt)}</p>
                  {q.code ? <pre className="code-block">{q.code}</pre> : null}
                  <p className="text-[15px]"><span className="font-bold">Correct answer:</span> {q.answer !== undefined ? q.options[q.answer] : ''}</p>
                  {q.explanation ? <p className="text-sm text-muted-foreground">{q.explanation}</p> : null}
                </div>
              ))}
            </div>
          </section>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href={session.gate?.passed ? '/plan' : '/today'}>{session.gate?.passed ? 'See what is unlocked' : 'Continue'}<ArrowCircle /></Link>
          </Button>
          <Button asChild size="lg" variant="outline"><Link href="/plan">{NAME.skills}</Link></Button>
          <Button asChild size="lg" variant="outline"><Link href="/progress">{NAME.evidence}</Link></Button>
        </div>
      </div>
    );
  }

  const q = session.questions[Math.min(index, total - 1)];
  const graded = session.feedback === 'immediate';
  const isLast = index >= total - 1;
  const answered = session.questions.filter(item => item.answered).length;
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pt-6 pb-32 sm:px-6 md:pt-8">
      {guard}
      <QuizHeader title={title} topic={topic} count={session.gate ? undefined : `Question ${Math.min(index + 1, total)} of ${total}`} value={total ? (100 * answered) / total : 0} />
      {session.gate ? <GateMeter gate={session.gate} asked={Math.min(index + 1, total)} /> : null}

      <div key={q.id} className="grid gap-5 animate-in fade-in duration-200">
        {kind === 'checkpoint' || kind === 'review' ? <Badge className="w-fit">{kind === 'review' ? `Review: ${q.concept_title}` : q.concept_title}</Badge> : null}
        <h1 className="type-title text-balance">{codeSpans(q.prompt)}</h1>
        {q.code ? <pre className="code-block">{q.code}</pre> : null}
        <Options q={q} choice={choice} onChoose={setChoice} graded={graded} />

        {graded && q.answered ? (
          <div role="status" className={cn('flex items-start gap-3 rounded-[20px] border bg-card p-4 animate-in fade-in slide-in-from-bottom-2 duration-200', q.correct ? 'border-foreground' : 'border-attention')}>
            {q.correct ? (
              <span className="grid size-7 flex-none place-items-center rounded-full bg-proof text-proof-foreground animate-pop" aria-hidden="true">
                <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
              </span>
            ) : <AttentionIcon size={28} />}
            <div>
              <p className="font-bold">{q.correct ? 'Correct' : 'Incorrect'}</p>
              {q.explanation ? <p className="mt-1 text-[15px] text-muted-foreground">{q.explanation}</p> : null}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          {!q.answered ? (
            <Button size="lg" disabled={busy || choice === null} aria-busy={busy} onClick={answer}>Check answer</Button>
          ) : graded ? (
            <Button size="lg" onClick={() => setIndex(isLast ? total : index + 1)}>
              {isLast ? 'See results' : 'Next question'}<ArrowCircle />
            </Button>
          ) : null}
          {choice === null && !q.answered ? <p className="text-sm text-muted-foreground">Choose an answer to check it.</p> : null}
        </div>
        {error ? <ErrorNote message={error} /> : null}
      </div>
    </div>
  );
}
