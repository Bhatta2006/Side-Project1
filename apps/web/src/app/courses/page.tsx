'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import type { Course } from '@/lib/types';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

/** A course card from GET /courses; ``community`` marks one a learner made (with AI). */
type Listed = Course & { community?: { by: string | null; mine: boolean; shared: boolean; ai_generated: boolean } };
interface Started { id: string; course: string; title: string; active: boolean; status: string }

const TEAM = new Set(['zero', 'dsa', 'cp']);
const MINUTES = [15, 20, 30, 45, 60, 90, 120];

/**
 * Every course in one place: the ones the learner started or made, and the library of
 * Socrat's courses and the ones other learners shared.
 */
export default function Courses() {
  const allowed = useGuard('signed-in');
  const router = useRouter();
  const { profile, refresh } = useSession();
  const [courses, setCourses] = useState<Listed[] | null>(null);
  const [started, setStarted] = useState<Started[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (!allowed) return;
    api.get<{ items: Listed[] }>('/courses').then(r => setCourses(r.items)).catch(e => setError(explain(e)));
    api.get<{ items: Started[] }>('/enrollments').then(r => setStarted(r.items)).catch(() => undefined);
  }, [allowed]);

  const byCourse = useMemo(() => new Map(started.map(s => [s.course, s])), [started]);
  if (!allowed || (!courses && !error)) return <Loading label="Loading courses" />;
  if (!courses) return <Page><ErrorNote message={error} /></Page>;

  const go = (id: string, work: () => Promise<unknown>) => {
    setBusy(id);
    setError('');
    work()
      .then(() => refresh())
      .then(() => router.push('/today'))
      .catch(e => { setError(explain(e)); setBusy(''); });
  };
  const resume = (s: Started) => go(s.course, () => api.post('/enrollments/switch', { enrollment: s.id }));
  // A learner-made course can be started any time: the current course pauses with its progress.
  const begin = (c: Listed) => {
    const now = profile?.enrollment;
    go(c.id, () => api.post('/enrollments', {
      course: c.id,
      language: c.languages[0] ?? 'python',
      level: c.levels[0]?.id ?? 'beginner',
      minutes_per_day: now && MINUTES.includes(now.minutes_per_day) ? now.minutes_per_day : 30,
      weekdays: now?.weekdays.length ? now.weekdays : [0, 1, 2, 3, 4],
    }));
  };

  const mine = courses.filter(c => byCourse.has(c.id) || c.community?.mine);
  const q = query.trim().toLowerCase();
  const library = courses.filter(c => !mine.includes(c) && (!q || `${c.title} ${c.tagline} ${c.description}`.toLowerCase().includes(q)));

  const action = (c: Listed) => {
    const s = byCourse.get(c.id);
    if (s?.active) return <Button asChild size="sm"><Link href="/today">Continue</Link></Button>;
    if (s) return <Button size="sm" variant="outline" disabled={!!busy} onClick={() => resume(s)}>{busy === c.id ? 'Opening…' : 'Switch to this course'}</Button>;
    if (c.community) return <Button size="sm" variant="outline" disabled={!!busy} onClick={() => begin(c)}>{busy === c.id ? 'Starting…' : 'Start this course'}</Button>;
    // Socrat's own courses run in order: one opens when the one before it is finished.
    if (TEAM.has(c.id) && profile?.enrollment) return <span className="text-[13px] text-muted-foreground">Opens after your current Socrat course</span>;
    return <Button asChild size="sm" variant="outline"><Link href={`/start?course=${c.id}`}>Start this course</Link></Button>;
  };

  const card = (c: Listed) => (
    <li key={c.id}>
      <Card tone="raised" size="sm" className="h-full">
        <div className="flex h-full flex-col gap-3 px-(--card-spacing)">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="font-display text-lg leading-tight font-semibold tracking-[-0.02em]">{c.title}</h3>
            {byCourse.get(c.id)?.active ? <Badge>Current</Badge> : null}
          </div>
          {c.tagline ? <p className="text-sm text-muted-foreground">{c.tagline}</p> : null}
          <p className="text-[13px] text-muted-foreground">
            {c.modules.length} module{c.modules.length === 1 ? '' : 's'} · {c.concept_count} lessons
            {c.community ? (c.community.mine ? ' · Made by you' : c.community.by ? ` · Shared by ${c.community.by}` : ' · Shared by a learner') : ' · By Socrat'}
            {c.community?.ai_generated ? ' · Written with AI' : ''}
          </p>
          <div className="mt-auto">{action(c)}</div>
        </div>
      </Card>
    </li>
  );

  return (
    <Page>
      <PageHeader
        title="Courses"
        description="The courses you started or made, and a library of courses from Socrat and other learners."
        actions={<Button asChild><Link href="/new">Make a new course</Link></Button>}
      />
      {error ? <ErrorNote message={error} /> : null}

      <section aria-labelledby="mine-heading" className="mb-10">
        <h2 id="mine-heading" className="mb-4 font-display text-xl font-semibold tracking-[-0.03em]">Your courses</h2>
        {mine.length ? (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{mine.map(card)}</ul>
        ) : (
          <p className="text-muted-foreground">Nothing yet. Start one from the library below, or <Link href="/new" className="underline underline-offset-4">make your own</Link>.</p>
        )}
      </section>

      <section aria-labelledby="library-heading">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <h2 id="library-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Course library</h2>
          <label className="w-full max-w-xs">
            <span className="sr-only">Search the library</span>
            <Input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search courses" />
          </label>
        </div>
        {library.length ? (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{library.map(card)}</ul>
        ) : (
          <p className="text-muted-foreground">{q ? 'No course matches that yet.' : 'No other courses yet. Courses learners share appear here.'}</p>
        )}
      </section>
    </Page>
  );
}
