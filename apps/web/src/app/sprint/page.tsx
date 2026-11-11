'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ExternalLink } from '@/components/icons';
import { ApiError, api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, formatStamp } from '@/lib/routes';
import type { SprintView } from '@/lib/types';
import { Difficulty, ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { ErrorState } from '@/components/socrat/states';
import { PracticeNav } from '@/components/socrat/practice-nav';
import { StatusIcon } from '@/components/socrat/status';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';

interface Overview {
  current: SprintView | null;
  history: { id: string; started_at: number; solved: number; total: number; minutes: number }[];
}

function clock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

function useCountdown(seconds: number | null, onExpire: () => void) {
  const [left, setLeft] = useState(seconds ?? 0);
  useEffect(() => {
    if (seconds === null) return;
    setLeft(seconds);
    const started = Date.now();
    const timer = setInterval(() => {
      const next = Math.max(0, seconds - Math.floor((Date.now() - started) / 1000));
      setLeft(next);
      if (next === 0) { clearInterval(timer); onExpire(); }
    }, 1000);
    return () => clearInterval(timer);
  }, [seconds, onExpire]);
  return left;
}

/** Announces 15, 5 and 1 minutes left, never every second. */
function useMilestones(left: number) {
  const [message, setMessage] = useState('');
  const said = useRef(new Set<number>());
  useEffect(() => {
    for (const minutes of [15, 5, 1]) {
      if (left <= minutes * 60 && left > minutes * 60 - 5 && !said.current.has(minutes)) {
        said.current.add(minutes);
        setMessage(`${minutes} minute${minutes > 1 ? 's' : ''} left in the sprint.`);
      }
    }
  }, [left]);
  return message;
}

function ProblemRow({ p, index, live }: { p: SprintView['problems'][number]; index: number; live: boolean }) {
  const solved = p.solved_after !== null;
  return (
    <li className="flex min-h-16 flex-wrap items-center gap-3 paper rounded-card px-4 py-3 lg:px-5">
      <StatusIcon status={solved ? 'practised' : 'not_seen'} size={24} title={solved ? 'Solved' : 'Not solved yet'} />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{index + 1}. {p.title}</p>
        <p className="text-[13px] text-muted-foreground">{p.concept}{solved ? `. Solved in ${clock(p.solved_after!)}` : ''}</p>
      </div>
      <Difficulty level={p.difficulty} />
      {live && !solved ? (
        <Button asChild size="sm" variant="outline">
          <a href={`/problems/${p.id}`} target="_blank" rel="noopener noreferrer">Solve<span className="sr-only"> {p.title}, opens in a new tab</span> <ExternalLink data-icon="inline-end" /></a>
        </Button>
      ) : !live ? <Link href={`/problems/${p.id}`} className="text-sm font-semibold underline underline-offset-4">Open<span className="sr-only"> {p.title}</span></Link> : null}
    </li>
  );
}

function Running({ sprint, refresh, finish, busy }: { sprint: SprintView; refresh: () => void; finish: () => void; busy: boolean }) {
  const left = useCountdown(sprint.seconds_left, refresh);
  const announcement = useMilestones(left);
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const onFocus = () => refresh();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [refresh]);
  const nearEnd = left <= 300;
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="inline-flex h-11 items-center rounded-full border border-border-strong px-4 font-display text-lg font-bold tabular-nums" aria-hidden={hidden}>
          {hidden ? 'Timer hidden' : nearEnd ? `${Math.max(1, Math.ceil(left / 60))} min left` : clock(left)}
        </span>
        <label className="flex min-h-11 items-center gap-3 text-[15px] font-medium">
          <Switch checked={hidden} onCheckedChange={setHidden} /> Hide timer
        </label>
        <span className="sr-only" role="status" aria-live="polite">{announcement}</span>
      </div>
      <p className="font-semibold tabular-nums">{sprint.solved} of {sprint.problems.length} solved</p>
      <ol className="grid gap-3">
        {sprint.problems.map((p, i) => <ProblemRow key={p.id} p={p} index={i} live />)}
      </ol>
      <p className="text-[13px] text-muted-foreground">Problems open in a new tab so the clock stays here. A solve counts when Submit solution is accepted.</p>
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={refresh}>Refresh</Button>
        <AlertDialog>
          <AlertDialogTrigger asChild><Button disabled={busy} aria-busy={busy}>Finish sprint</Button></AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Finish the sprint now</AlertDialogTitle>
              <AlertDialogDescription>The clock stops and unsolved problems stay unsolved for this sprint. They remain in your recommendations.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Keep going</AlertDialogCancel>
              <AlertDialogAction onClick={finish}>Finish sprint</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

function Result({ sprint }: { sprint: SprintView }) {
  return (
    <section className="grid gap-5" aria-labelledby="result-heading">
      <div>
        <h2 id="result-heading" className="type-display-l tabular-nums">{sprint.solved} of {sprint.problems.length} solved</h2>
        <p className="mt-3 text-base text-muted-foreground">Unsolved problems stay in your recommendations, so you can finish them without the clock.</p>
      </div>
      <ol className="grid gap-3">
        {sprint.problems.map((p, i) => <ProblemRow key={p.id} p={p} index={i} live={false} />)}
      </ol>
    </section>
  );
}

export default function Sprint() {
  const allowed = useGuard('active');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [view, setView] = useState<SprintView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notReady, setNotReady] = useState(false); // a normal precondition, not a failure

  const load = useCallback(() => {
    api.get<Overview>('/library/sprints').then(o => { setOverview(o); if (o.current) setView(o.current); }).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  const refresh = useCallback(() => {
    if (view) api.get<SprintView>(`/library/sprints/${view.id}`).then(setView).catch(() => undefined);
  }, [view]);

  async function start() {
    setBusy(true);
    setError('');
    setNotReady(false);
    try { setView(await api.post<SprintView>('/library/sprints')); } catch (e) { setError(explain(e)); setNotReady(e instanceof ApiError && e.code === 'sprint_unavailable'); } finally { setBusy(false); }
  }
  async function finish() {
    if (!view) return;
    setBusy(true);
    try { setView(await api.post<SprintView>(`/library/sprints/${view.id}/finish`)); load(); } catch (e) { setError(explain(e)); } finally { setBusy(false); }
  }

  if (!allowed || (!overview && !error)) return <Loading variant="list" label="Loading the sprint" />;
  return (
    <Page>
      <PracticeNav />
      <PageHeader eyebrow={NAME.practice} title={NAME.sprint} description="Judged problems just above where you are, from skills you have studied." />
      {view && !view.finished ? <Running sprint={view} refresh={refresh} finish={finish} busy={busy} /> : view?.finished ? (
        <div className="grid gap-6">
          <Result sprint={view} />
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => { setView(null); start(); }} disabled={busy} aria-busy={busy}>Start another sprint<ArrowCircle loading={busy} /></Button>
            <Button asChild variant="outline"><Link href="/library">{NAME.problems}</Link></Button>
            <Button asChild variant="outline"><Link href="/progress">{NAME.evidence}</Link></Button>
          </div>
        </div>
      ) : (
        <section className="flex flex-col gap-5 rounded-card bg-forest p-6 text-forest-foreground [--card-muted:color-mix(in_srgb,var(--forest-foreground),transparent_18%)] lg:p-8" data-tone="hero" aria-labelledby="sprint-heading">
          <p className="type-label">{NAME.sprint}</p>
          <h2 id="sprint-heading" className="type-display-l">3 problems, 45 minutes</h2>
          <p className="max-w-xl text-base">Problems come from skills you have studied, easiest first. Soc stays available, and the clock keeps running.</p>
          <div><Button variant="ink" size="lg" disabled={busy} aria-busy={busy} onClick={start}>Start sprint<ArrowCircle loading={busy} /></Button></div>
        </section>
      )}
      {error && notReady ? (
        <ErrorState title="Not ready for a sprint yet" message={error} actions={<Button asChild variant="outline"><Link href="/plan">Open Skills</Link></Button>} />
      ) : error ? <ErrorNote message={error} /> : null}
      {overview?.history.length ? (
        <section className="mt-10" aria-labelledby="history-heading">
          <h2 id="history-heading" className="mb-3 font-display text-xl font-semibold tracking-[-0.03em]">Past sprints</h2>
          <ul className="grid divide-y paper rounded-card px-5 text-[15px]">
            {overview.history.map(h => (
              <li key={h.id} className="flex min-h-12 items-center justify-between gap-3 py-2">
                <span>{formatStamp(h.started_at)}</span>
                <span className="font-semibold tabular-nums">{h.solved} of {h.total} solved, {h.minutes} min</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </Page>
  );
}
