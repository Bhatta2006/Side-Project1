'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ApiError, api, explain } from '@/lib/api';
import type { VisualArtifact } from '@/lib/explainer';
import { NAME } from '@/lib/routes';
import { ErrorNote } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';

const VisualExplainer = dynamic(() => import('@/components/visual-explainer'), { ssr: false, loading: () => <Skeleton className="h-[560px] w-full rounded-card" /> });

type Shared =
  | { state: 'none' | 'failed'; error?: string | null }
  | { state: 'generating'; progress: { phase?: string }; mine: boolean }
  | { state: 'ready'; artifact: VisualArtifact };

const PHASE: Record<string, string> = { generating: 'Building the visual', checking: 'Checking that it runs', reviewing: 'Reviewing it' };
const POLL_MS = 2000;
// A request nobody has started building after this long is stuck (no generator is running).
const QUEUED_LIMIT_MS = 60_000;
// Generation itself is bounded server-side; past this the page stops waiting.
const TOTAL_LIMIT_MS = 6 * 60_000;

/**
 * The concept's visual, in the page where the learner is. It is the same one for every learner,
 * so a click usually shows it at once; only the first request ever waits for it to be made.
 * `problem` makes the server refuse it while that problem is an unaided transfer check.
 */
export function ConceptVisual({ concept, title, problem }: { concept: string; title: string; problem?: string }) {
  const [shared, setShared] = useState<Shared | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState('');
  const [thanks, setThanks] = useState(false);
  const [since, setSince] = useState<number | null>(null);
  const [stalled, setStalled] = useState(false);
  const where = { concept, ...(problem ? { problem } : {}) };

  const start = useCallback(() => {
    setBusy(true); setError(''); setThanks(false); setStalled(false); setSince(Date.now());
    api.post<Shared>('/playground/shared', where)
      .then(setShared)
      .catch(e => setError(e instanceof ApiError && e.code === 'independent_work_in_progress' ? 'Visuals are off while you do this unaided.' : explain(e)))
      .finally(() => setBusy(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [concept, problem]);

  // While it is being made (by this learner or another), look again until it is ready.
  useEffect(() => {
    if (shared?.state !== 'generating') return;
    const waited = Date.now() - (since ?? Date.now());
    if (waited > TOTAL_LIMIT_MS || (waited > QUEUED_LIMIT_MS && !shared.progress?.phase)) {
      setStalled(true);
      return;
    }
    const timer = setTimeout(() => {
      api.get<Shared>(`/playground/shared?${new URLSearchParams(where)}`).then(setShared).catch(e => setError(explain(e)));
    }, POLL_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shared, concept, problem, since]);

  const report = () => {
    if (shared?.state !== 'ready') return;
    api.post(`/playground/artifacts/${shared.artifact.id}/report`, { reason: reason.trim() })
      .then(() => { setShared(null); setReporting(false); setReason(''); setThanks(true); })
      .catch(e => setError(explain(e)));
  };

  if (shared?.state === 'ready') {
    return (
      <div className="grid gap-3">
        <VisualExplainer artifact={shared.artifact} onReport={() => setReporting(true)} />
        {reporting ? (
          <div className="paper grid gap-3 rounded-card p-4">
            <label htmlFor="visual-report" className="text-[15px] font-semibold">What is wrong with this visual?</label>
            <Textarea id="visual-report" value={reason} onChange={e => setReason(e.target.value)} rows={3} maxLength={1000} />
            <div className="flex gap-2">
              <Button size="sm" disabled={reason.trim().length < 5} onClick={report}>Send report</Button>
              <Button size="sm" variant="outline" onClick={() => setReporting(false)}>Cancel</Button>
            </div>
          </div>
        ) : null}
        {error ? <ErrorNote message={error} /> : null}
        <p className="text-[13px] text-muted-foreground">Want something specific? <Link href={`/playground?concept=${encodeURIComponent(concept)}`} className="underline underline-offset-4">Ask in the {NAME.playground}</Link>.</p>
      </div>
    );
  }

  const failed = shared?.state === 'failed' || stalled;
  return (
    <div className="grid gap-3">
      {shared?.state === 'generating' && !stalled ? (
        <div className="paper rounded-card p-5" role="status">
          <p className="font-semibold">{PHASE[shared.progress.phase ?? ''] ?? 'Getting it ready'}</p>
          <p className="mt-1 text-[15px] text-muted-foreground">
            {shared.mine ? 'You are the first to ask for this one, so it is being made now. Next time it opens at once.' : 'Another learner just asked for this one. It will appear here when it is ready.'}
          </p>
        </div>
      ) : (
        <div className="paper flex flex-wrap items-center justify-between gap-4 rounded-card p-5 lg:p-6">
          <div className="min-w-0 flex-1 basis-64">
            <p className="type-label">{NAME.playground}</p>
            <p className="mt-1 font-display text-lg font-semibold tracking-[-0.02em]">
              {thanks ? 'Thanks for flagging it' : failed ? 'That one did not come out' : `Watch ${title} work, step by step`}
            </p>
            <p className="mt-1 text-[15px] text-muted-foreground">
              {thanks
                ? 'If enough learners flag it, it is replaced.'
                : stalled
                  ? 'The visual maker did not pick this up in time. Try again in a moment.'
                  : failed
                    ? 'Try once more.'
                    : 'An interactive picture of the idea. Change the inputs and see what happens.'}
            </p>
          </div>
          <Button disabled={busy} onClick={start}>{failed ? 'Try again' : thanks ? 'Watch it again' : 'Watch it work'}</Button>
        </div>
      )}
      {error ? <ErrorNote message={error} retry={start} /> : null}
    </div>
  );
}
