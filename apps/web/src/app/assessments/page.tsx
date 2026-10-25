'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, conceptHref, formatStamp } from '@/lib/routes';
import type { AssessmentStatus, AssessmentView } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { Choice } from '@/components/choice';
import { AttentionIcon, LockedState } from '@/components/socrat/states';
import { StatusIcon, StatusLabel, statusFromBand } from '@/components/socrat/status';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { SocFigure } from '@/components/socrat/soc';

interface Overview {
  current: AssessmentStatus;
  history: { id: string; week: string; score: number | null; finished_at: number }[];
}

/** Remaining time: tabular, no colour change; text changes in the last five minutes. */
function Countdown({ seconds, onExpire }: { seconds: number; onExpire: () => void }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    setLeft(seconds);
    const started = Date.now();
    const timer = setInterval(() => {
      const next = Math.max(0, seconds - Math.floor((Date.now() - started) / 1000));
      setLeft(next);
      if (next === 0) { clearInterval(timer); onExpire(); }
    }, 1000);
    return () => clearInterval(timer);
  }, [seconds, onExpire]);
  const minutes = Math.floor(left / 60);
  return (
    <span className="inline-flex h-10 items-center rounded-full border border-border-strong px-4 font-display text-base font-bold tabular-nums" aria-label={`About ${Math.max(1, Math.ceil(left / 60))} minutes left`}>
      {left <= 300 ? `${Math.max(1, Math.ceil(left / 60))} min left` : `${minutes}:${String(left % 60).padStart(2, '0')}`}
    </span>
  );
}

function Locked({ status }: { status: AssessmentStatus }) {
  const remaining = Math.max(0, status.needed - status.topics.length);
  return (
    <div className="grid gap-4">
      <LockedState title={`${NAME.assessment} unlocks as you study`} href="/today" action={`Continue ${NAME.today}`}>
        Study {remaining} more topic{remaining === 1 ? '' : 's'} this week and it opens. It is built only from what you studied.
      </LockedState>
      <div className="grid gap-2 px-1">
        <Progress value={(100 * status.topics.length) / Math.max(1, status.needed)} className="max-w-sm" aria-label={`${status.topics.length} of ${status.needed} topics studied this week`} />
        <p className="text-sm text-muted-foreground">{status.topics.length} of {status.needed} topics studied this week{status.topics.length ? `: ${status.topics.join(', ')}` : ''}.</p>
      </div>
    </div>
  );
}

function Available({ status, onStart, busy }: { status: AssessmentStatus; onStart: (timed: boolean) => void; busy: boolean }) {
  return (
    <section className="relative flex flex-col gap-5 overflow-hidden rounded-card bg-forest p-6 text-forest-foreground [--card-muted:color-mix(in_srgb,var(--forest-foreground),transparent_18%)] lg:p-8" data-tone="hero" aria-labelledby="available-heading">
      <div aria-hidden="true" className="pointer-events-none absolute right-8 -bottom-3 hidden w-[180px] lg:block"><SocFigure books mood="thinking" idle className="h-auto w-full" /></div>
      <div className="flex flex-wrap gap-2"><Badge>Available</Badge><Badge>Week {status.week.split('-W')[1]}</Badge></div>
      <h2 id="available-heading" className="type-display-l">{NAME.assessment}</h2>
      <p className="max-w-2xl text-base lg:pr-[200px]">
        {status.questions} questions from what you studied in the last seven days, weighted toward what is still shaky, plus a coding task. Answers are shown at the end. No tutor or learning help until you submit.
      </p>
      <ul className="flex flex-wrap gap-2">{status.topics.map(t => <li key={t}><Badge>{t}</Badge></li>)}</ul>
      <div className="flex flex-wrap gap-3">
        <Button variant="ink" size="lg" disabled={busy} aria-busy={busy} onClick={() => onStart(false)}>Start assessment<ArrowCircle loading={busy} /></Button>
        <Button variant="outline" size="lg" className="border-current text-current hover:bg-[color-mix(in_srgb,currentColor,transparent_88%)]" disabled={busy} onClick={() => onStart(true)}>
          Exam mode, {status.time_limit_minutes} min
        </Button>
      </div>
    </section>
  );
}

function Attempt({ view, setView }: { view: AssessmentView; setView: (v: AssessmentView) => void }) {
  const firstOpen = view.questions.findIndex(q => !q.answered);
  const [index, setIndex] = useState(firstOpen < 0 ? 0 : firstOpen);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const answered = view.questions.filter(q => q.answered).length;
  const total = view.questions.length;
  const q = view.questions[Math.min(index, total - 1)];

  const finish = useCallback(async () => {
    setBusy(true);
    try {
      setView(await api.post<AssessmentView>(`/assessments/${view.id}/finish`));
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }, [view.id, setView]);
  const expire = useCallback(() => { api.get<AssessmentView>(`/assessments/${view.id}`).then(setView).catch(() => undefined); }, [view.id, setView]);

  async function submit() {
    if (choice === null) return;
    setBusy(true);
    setError('');
    try {
      const next = await api.post<AssessmentView>(`/assessments/${view.id}/answer`, { item: q.id, choice });
      setChoice(null);
      setView(next);
      setSavedAt(new Date());
      const following = next.questions.findIndex((x, i) => i > index && !x.answered);
      const anyOpen = next.questions.findIndex(x => !x.answered);
      setIndex(following >= 0 ? following : anyOpen >= 0 ? anyOpen : index);
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <div className="mb-4 grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-semibold text-muted-foreground tabular-nums">Question {Math.min(index + 1, total)} of {total}. {answered} answered</p>
            {view.timed && view.seconds_left !== null ? <Countdown seconds={view.seconds_left} onExpire={expire} /> : null}
          </div>
          <Progress value={total ? (100 * answered) / total : 0} aria-label={`${answered} of ${total} answered`} />
          <p className="text-sm font-semibold">No tutor or learning help during this assessment.</p>
        </div>
        <div className="mb-6 flex flex-wrap gap-1.5" role="group" aria-label="Go to question">
          {view.questions.map((x, i) => (
            <button
              key={x.id}
              type="button"
              aria-label={`Question ${i + 1}${x.answered ? ', answered' : ''}`}
              aria-current={i === index ? 'step' : undefined}
              onClick={() => { setIndex(i); setChoice(null); }}
              className={cn('grid size-9 place-items-center rounded-full border text-[13px] font-bold tabular-nums transition-colors', x.answered ? 'border-foreground bg-foreground text-background' : 'border-border-strong border-dashed', i === index && 'ring-2 ring-primary ring-offset-2 ring-offset-background')}
            >
              {i + 1}
            </button>
          ))}
        </div>
        {q ? (
          <div key={q.id} className="grid gap-5 animate-in fade-in duration-200">
            <Badge className="w-fit">{q.concept_title}</Badge>
            <h2 className="type-title text-balance">{q.prompt}</h2>
            {q.code ? <pre className="code-block">{q.code}</pre> : null}
            <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
              {q.options.map((option, i) => {
                const selected = q.answered ? q.choice === i : choice === i;
                return (
                  <Choice key={i} role="radio" aria-checked={selected} selected={selected} note={selected ? (q.answered ? 'Saved' : 'Selected') : undefined} marker={String.fromCharCode(65 + i)} disabled={q.answered} onClick={() => setChoice(i)}>
                    <span className="choice-title whitespace-pre-wrap">{option}</span>
                  </Choice>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {!q.answered ? (
                <Button size="lg" disabled={busy || choice === null} aria-busy={busy} onClick={submit}>Save answer</Button>
              ) : null}
              <p className="text-sm text-muted-foreground" role="status">
                {q.answered && savedAt ? `Saved ${savedAt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}` : q.answered ? 'Answer saved' : choice === null ? 'Choose an answer to save it.' : ''}
              </p>
            </div>
          </div>
        ) : null}
        {error ? <ErrorNote message={error} /> : null}
      </div>

      <aside className="grid content-start gap-4 lg:sticky lg:top-24 lg:self-start" aria-label="Assessment">
        {view.coding.length ? (
          <section className="paper rounded-card p-5" aria-labelledby="coding-heading">
            <h2 id="coding-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">Coding tasks</h2>
            <p className="mt-1 text-sm text-muted-foreground">Submit them in the editor. They count if accepted before you finish.</p>
            <ul className="mt-3 grid gap-2">
              {view.coding.map(c => (
                <li key={c.id} className="flex min-h-11 items-center gap-3">
                  <StatusIcon status={c.solved ? 'practised' : 'not_seen'} size={22} title={c.solved ? 'Solved' : 'Not solved yet'} />
                  <Link href={`/problems/${c.id}`} className="flex-1 font-semibold underline-offset-4 hover:underline">{c.title}</Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <section className="grid gap-3 paper rounded-card p-5" aria-label="Submit">
          <p className="text-[15px] text-muted-foreground">{answered === total ? 'All questions answered.' : `${total - answered} question${total - answered === 1 ? '' : 's'} left.`} You can submit at any time.</p>
          <AlertDialog>
            <AlertDialogTrigger asChild><Button disabled={busy}>Submit assessment</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Submit your assessment</AlertDialogTitle>
                <AlertDialogDescription>
                  {answered < total ? `${total - answered} unanswered question${total - answered === 1 ? '' : 's'} will count as incorrect. ` : ''}
                  You see every answer and a report straight away.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep going</AlertDialogCancel>
                <AlertDialogAction onClick={finish}>Submit</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </section>
      </aside>
    </div>
  );
}

function Report({ view }: { view: AssessmentView }) {
  const report = view.report!;
  const percent = Math.round((view.score ?? 0) * 100);
  const delta = report.previous_score !== null ? percent - Math.round(report.previous_score * 100) : null;
  return (
    <div className="grid gap-6">
      <section>
        <p className="text-[15px] text-muted-foreground">Week {view.week.split('-W')[1]}. {report.minutes} min.</p>
        <h2 className="type-display-l mt-2 tabular-nums">{report.correct} of {report.questions} correct</h2>
        <p className="mt-3 text-base text-muted-foreground">
          Score {percent}%{report.coding_total ? `. ${report.coding_solved} of ${report.coding_total} coding tasks solved` : ''}{delta !== null ? `. ${delta >= 0 ? '+' : ''}${delta} points compared with last week` : ''}.
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-2 lg:gap-6">
        <section className="paper rounded-card p-5 lg:p-6" aria-labelledby="topics-heading">
          <h2 id="topics-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">By topic</h2>
          <p className="mt-1 text-sm text-muted-foreground">Status after this assessment, with the mastery estimate before and after.</p>
          <ul className="mt-4 grid gap-3">
            {report.topics.map(t => (
              <li key={t.id} className="grid gap-2 rounded-[16px] bg-raised p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link href={conceptHref(t.id)} className="font-semibold underline-offset-4 hover:underline">{t.title}</Link>
                  <span className="text-sm font-semibold tabular-nums">{t.correct} of {t.total}</span>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 text-[13px]">
                  <StatusLabel status={statusFromBand(t.band)} size={18} className="text-[13px]" />
                  <span className="text-muted-foreground tabular-nums">Estimate {Math.round(t.before * 100)}% to {Math.round(t.after * 100)}%</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <div className="grid content-start gap-4 lg:gap-6">
          <section className="paper rounded-card p-5 lg:p-6" aria-labelledby="focus-heading">
            <h2 id="focus-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Topics to focus on</h2>
            {report.focus.length ? (
              <ul className="mt-3 grid gap-3">
                {report.focus.map(f => (
                  <li key={f.id} className="grid gap-2 rounded-[16px] bg-raised p-4">
                    <p className="flex items-center gap-2 font-semibold"><AttentionIcon size={20} /> {f.title}</p>
                    <div className="flex flex-wrap gap-2">
                      <Button asChild size="sm"><Link href={conceptHref(f.id)}>Practice this</Link></Button>
                      <Button asChild size="sm" variant="outline"><Link href={`/playground?concept=${encodeURIComponent(f.id)}`}>Explore in {NAME.playground}</Link></Button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : <p className="mt-2 text-[15px] text-muted-foreground">Nothing urgent. Your plan keeps stretching you.</p>}
          </section>
          {report.strengths.length ? (
            <section className="paper rounded-card p-5 lg:p-6" aria-labelledby="strengths-heading">
              <h2 id="strengths-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Strengths</h2>
              <ul className="mt-3 flex flex-wrap gap-2">{report.strengths.map(s => <li key={s}><Badge>{s}</Badge></li>)}</ul>
            </section>
          ) : null}
        </div>
      </div>

      <details className="group paper rounded-card">
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 font-semibold [&::-webkit-details-marker]:hidden">
          Review every question
          <ChevronDown className="size-5 transition-transform group-open:rotate-180" aria-hidden="true" />
        </summary>
        <ul className="grid gap-4 border-t p-5">
          {view.questions.map(q => (
            <li key={q.id} className="grid gap-2">
              <p className="flex items-start gap-2 font-semibold">
                {q.correct
                  ? <span className="mt-0.5 grid size-6 flex-none place-items-center rounded-full bg-cream text-cream-foreground" aria-label="Correct"><svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg></span>
                  : <span className="mt-0.5 flex-none" aria-label="Incorrect"><AttentionIcon size={22} /></span>}
                {q.prompt}
              </p>
              {q.code ? <pre className="code-block">{q.code}</pre> : null}
              <p className="text-[15px]"><span className="font-bold">Correct answer:</span> {q.answer !== undefined ? q.options[q.answer] : ''}</p>
              {q.explanation ? <p className="text-sm text-muted-foreground">{q.explanation}</p> : null}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

export default function Assessments() {
  const allowed = useGuard('active');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [view, setView] = useState<AssessmentView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<Overview>('/assessments')
      .then(async o => {
        setOverview(o);
        if (o.current.id) setView(await api.get<AssessmentView>(`/assessments/${o.current.id}`));
      })
      .catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  async function start(timed: boolean) {
    setBusy(true);
    setError('');
    try {
      setView(await api.post<AssessmentView>('/assessments/start', { timed }));
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  const history = useMemo(() => (overview?.history ?? []).slice().reverse(), [overview]);
  if (!allowed || (!overview && !error)) return <Loading label="Loading the weekly assessment" />;
  if (!overview) return <Page><ErrorNote message={error} retry={load} /></Page>;
  const inProgress = view && !view.finished;

  return (
    <Page>
      {inProgress ? (
        <h1 className="mb-6 font-display text-3xl font-semibold tracking-[-0.03em]">{NAME.assessment}</h1>
      ) : (
        <PageHeader eyebrow={NAME.evidence} title={NAME.assessment} description="A short check each week, built from what you studied. It is a proof event: no help while you take it." />
      )}
      {inProgress ? <Attempt view={view} setView={setView} /> : view?.finished ? <Report view={view} /> : overview.current.state === 'available' ? (
        <Available status={overview.current} onStart={start} busy={busy} />
      ) : <Locked status={overview.current} />}
      {error ? <ErrorNote message={error} /> : null}

      {history.length && !inProgress ? (
        <section className="mt-10 paper rounded-card p-5 lg:p-6" aria-labelledby="history-heading">
          <div className="mb-4 flex items-baseline justify-between gap-3">
            <h2 id="history-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Past weeks</h2>
            <span className="text-sm font-semibold text-muted-foreground">{history.length} completed</span>
          </div>
          <ol className="flex h-36 items-end gap-2" aria-label="Weekly assessment scores">
            {history.map(h => {
              const pct = Math.round((h.score ?? 0) * 100);
              return (
                <li key={h.id} className="flex flex-1 flex-col items-center gap-1" title={`Week ${h.week.split('-W')[1]}: ${pct}%, ${formatStamp(h.finished_at)}`}>
                  <span className="text-xs font-semibold tabular-nums">{pct}%</span>
                  <span className="w-full max-w-10 rounded-t-lg bg-primary" style={{ height: `${Math.max(6, pct * 0.9)}px` }} aria-hidden="true" />
                  <span className="text-xs text-muted-foreground"><span className="sr-only">Week </span>W{h.week.split('-W')[1]}</span>
                </li>
              );
            })}
          </ol>
        </section>
      ) : null}
    </Page>
  );
}
