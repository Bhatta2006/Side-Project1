'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { activityHref, conceptHref } from '@/lib/routes';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/** One scheduled review (GET /reviews), master prompt 9.6. */
interface ReviewItem {
  concept: string;
  title: string;
  course?: string;
  course_title?: string;
  courses?: string[];
  current_course?: boolean;
  builds_on?: boolean;
  due_at: number;
  due: boolean;
  snoozed_until: number | null;
  reason: string;
}

interface Queue { items: ReviewItem[]; scope: 'course' | 'all'; max_snooze_days: number; daily_limit: number; due_now: number }

const SNOOZE = [1, 3, 7];

function when(seconds: number): string {
  return new Date(seconds * 1000).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
}

function Row({ item, onChange }: { item: ReviewItem; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  async function act(days: number | null) {
    setBusy(true);
    try {
      if (days === null) await api.del(`/reviews/${item.concept}/snooze`);
      else await api.post(`/reviews/${item.concept}/snooze`, { days });
      toast.success(days === null ? 'Back on your plan.' : `Snoozed for ${days} day${days > 1 ? 's' : ''}.`);
      onChange();
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy(false);
    }
  }
  const held = item.snoozed_until !== null;
  return (
    <li className="grid gap-2 py-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <Link href={conceptHref(item.concept)} className="text-[17px] font-semibold underline-offset-4 hover:underline">{item.title}</Link>
        {item.course_title && item.current_course === false ? <Badge variant="outline">{item.course_title}</Badge> : null}
        {item.builds_on ? <Badge variant="secondary">Needed for this course</Badge> : null}
        <span className="text-sm text-muted-foreground">
          {held ? `Snoozed until ${when(item.snoozed_until!)}` : item.due ? 'Due now' : `Due ${when(item.due_at)}`}
        </span>
      </div>
      <p className="max-w-[68ch] text-[15px] text-muted-foreground">{item.reason}</p>
      <div className="flex flex-wrap gap-2">
        {item.due && !held ? (
          <Button asChild size="sm"><Link href={activityHref(`review:${item.concept}`)}>Review now</Link></Button>
        ) : null}
        {held ? (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => act(null)}>Bring back</Button>
        ) : (
          SNOOZE.map(d => (
            <Button key={d} size="sm" variant="ghost" disabled={busy} onClick={() => act(d)}>
              Snooze {d} day{d > 1 ? 's' : ''}
            </Button>
          ))
        )}
      </div>
    </li>
  );
}

export default function ReviewsPage() {
  const allowed = useGuard('active');
  const [scope, setScope] = useState<'course' | 'all'>('course');
  const [queue, setQueue] = useState<Queue | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<Queue>(`/reviews?scope=${scope}`).then(setQueue).catch(e => setError(explain(e)));
  }, [scope]);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!queue && !error)) return <Loading label="Loading your reviews" />;
  if (!queue) return <Page><ErrorNote message={error} retry={load} /></Page>;

  return (
    <Page narrow>
      <PageHeader
        title="Reviews"
        description={`Short recall checks, spaced further apart each time you get them right. Your plan fits in up to ${queue.daily_limit} a day.`}
      />
      <div className="mb-6 inline-flex rounded-full bg-raised p-1" role="group" aria-label="Which reviews">
        {(['course', 'all'] as const).map(s => (
          <button
            key={s}
            type="button"
            aria-pressed={scope === s}
            onClick={() => setScope(s)}
            className={`min-h-10 rounded-full px-4 text-sm font-semibold ${scope === s ? 'bg-card shadow-sm' : 'text-muted-foreground'}`}
          >
            {s === 'course' ? 'This course' : 'All my courses'}
          </button>
        ))}
      </div>
      {queue.items.length ? (
        <Card className="p-5 lg:p-6">
          <p className="text-sm font-medium">{queue.due_now ? `${queue.due_now} due now.` : 'Nothing due right now.'}</p>
          <ul className="mt-1 divide-y">{queue.items.map(i => <Row key={i.concept} item={i} onChange={load} />)}</ul>
        </Card>
      ) : (
        <EmptyState title="No reviews scheduled yet">
          <p className="text-[15px] text-muted-foreground">Reviews appear after you finish a lesson and its concept check.</p>
        </EmptyState>
      )}
    </Page>
  );
}
