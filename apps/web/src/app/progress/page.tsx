'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, PACE_LABEL, conceptHref, formatDate, hours } from '@/lib/routes';
import type { AssessmentStatus, ProgressView } from '@/lib/types';
import { ErrorNote, Loading, Page, Ring, StatCard } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { LearnerProfileCard } from '@/components/socrat/learner-profile';
import { PassportSettingsCard } from '@/components/socrat/passport-settings';
import { STATUS_LABEL, StatusIcon, StatusLabel, StatusLegend, statusFromBand } from '@/components/socrat/status';
import { Badge } from '@/components/ui/badge';
import { ArrowCircle, Button } from '@/components/ui/button';

const KIND: Record<string, string> = { quiz: 'concept check', code: 'problem', checkpoint: 'checkpoint', review: 'review', placement: 'placement', external: 'practice', verified: 'Codeforces', guided: 'guided step', trace: 'trace', retrieval: 'recall', debug: 'debugging', explanation: 'explanation', explain: 'written answer (AI-graded)', project: 'project milestone (AI-graded)' };

function level(minutes: number) {
  if (!minutes) return 0;
  if (minutes < 15) return 1;
  if (minutes < 30) return 2;
  if (minutes < 60) return 3;
  return 4;
}

export default function ProgressPage() {
  const allowed = useGuard('active');
  const [data, setData] = useState<ProgressView | null>(null);
  const [assessment, setAssessment] = useState<AssessmentStatus | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<ProgressView>('/progress').then(setData).catch(e => setError(explain(e)));
    api.get<{ current: AssessmentStatus }>('/assessments').then(r => setAssessment(r.current)).catch(() => undefined);
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!data && !error)) return <Loading label="Loading your evidence" />;
  if (!data) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const now = Date.now() / 1000;
  const concepts = data.modules.flatMap(m => m.concepts);
  const mastered = concepts.filter(c => c.band === 'strong').length;
  const due = concepts.filter(c => c.next_review !== null && c.next_review <= now && c.band !== 'not_started').length;
  const weak = concepts.filter(c => c.band === 'needs_practice').length;
  const leading = (7 + new Date(`${data.heatmap[0]?.day}T00:00:00`).getDay() - 1) % 7;
  const activeDays = data.heatmap.filter(d => d.minutes > 0).length;
  const assessmentOpen = assessment && (assessment.state === 'available' || assessment.state === 'in_progress');

  return (
    <Page wide>
      <header className="mb-8">
        <p className="type-label mb-3 text-muted-foreground">{NAME.evidence}</p>
        <h1 className="type-display-l">What you have shown</h1>
      </header>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:gap-6">
        {assessmentOpen ? (
          <section className="flex flex-wrap items-center justify-between gap-4 rounded-card border bg-card p-5 lg:p-6" aria-labelledby="assessment-heading">
            <div>
              <div className="mb-2"><Badge>{assessment.state === 'in_progress' ? 'In progress' : 'Available'}</Badge></div>
              <h2 id="assessment-heading" className="font-display text-xl font-bold tracking-[-0.03em]">{NAME.assessment}</h2>
              <p className="text-sm text-muted-foreground">A proof event built from what you studied this week.</p>
            </div>
            <Button asChild><Link href="/assessments">{assessment.state === 'in_progress' ? 'Continue assessment' : 'Open assessment'}<ArrowCircle /></Link></Button>
          </section>
        ) : null}

        {/* Hero: course completion. */}
        <section className="flex flex-wrap items-center gap-6 rounded-card bg-forest p-6 text-forest-foreground [--card-muted:color-mix(in_srgb,var(--forest-foreground),transparent_18%)] lg:gap-10 lg:p-8" data-tone="hero" aria-labelledby="course-heading">
          <Ring value={data.progress.percent} size={128} stroke={6} label={<span className="font-display text-3xl">{data.progress.percent}%</span>} ariaLabel={`Course ${data.progress.percent} percent complete`} />
          <div className="min-w-0 flex-1">
            <p className="type-label">Course completion</p>
            <h2 id="course-heading" className="type-display-m mt-2 tabular-nums">{data.progress.finished} of {data.progress.total} skills</h2>
            <p className="mt-2 text-base" data-visual-mask="">Projected finish {formatDate(data.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })}. {PACE_LABEL[data.pace]} pace.</p>
            <p className="mt-1 text-sm">Counts skills you have practised or mastered{data.progress.assumed ? `. ${data.progress.assumed} more are assumed from placement until a short review confirms them` : ''}.</p>
          </div>
        </section>

        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:gap-6">
          <StatCard value={mastered} icon={<StatusIcon status="mastered" size={28} />} label="Skills mastered" hint="Evidence from checks, judged code and reviews passed the mastery threshold." />
          <StatCard value={due} icon={<StatusIcon status="review" size={28} />} label="Reviews due" hint="Spaced reviews that are due now." />
          <StatCard value={weak} icon={<StatusIcon status="needs_practice" size={28} />} label="Need practice" hint="Recent results show these are not holding yet." />
          <StatCard value={data.solves.independent_solves} label="Problems solved without help" hint={`Accepted with no hints. ${data.solves.assisted_solves} more solved with help.`} />
        </div>

        <PassportSettingsCard />

        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-12 lg:gap-6">
          {/* Mastery comes before activity on every width. */}
          <section aria-labelledby="mastery-heading" className="grid min-w-0 content-start gap-4 lg:col-span-8">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h2 id="mastery-heading" className="font-display text-2xl font-bold tracking-[-0.03em]">Mastery by module</h2>
            </div>
            {data.modules.map((m, mi) => {
              const moduleWeak = m.concepts.filter(c => c.band === 'needs_practice').length;
              const moduleMastered = m.concepts.filter(c => c.band === 'strong').length;
              return (
                <details key={m.id} className="group rounded-card border bg-card" open={mi === 0 || moduleWeak > 0}>
                  <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-5 py-4 lg:px-6 [&::-webkit-details-marker]:hidden">
                    <span className="font-display text-lg font-bold tracking-[-0.02em]">{m.title}</span>
                    <span className="flex items-center gap-3 text-sm font-semibold text-muted-foreground tabular-nums">
                      {moduleMastered} mastered{moduleWeak ? `, ${moduleWeak} need practice` : ''}
                      <ChevronDown className="size-5 text-foreground transition-transform group-open:rotate-180" aria-hidden="true" />
                    </span>
                  </summary>
                  <ul className="grid gap-2 px-5 pb-5 lg:px-6">
                    {m.concepts.map(c => {
                      const status = statusFromBand(c.band, c.next_review !== null && c.next_review <= now);
                      return (
                        <li key={c.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-[16px] bg-raised px-4 py-3">
                          <Link href={conceptHref(c.id)} transitionTypes={['nav-forward']} className="min-w-0 flex-1 basis-40 font-semibold underline-offset-4 hover:underline">{c.title}</Link>
                          <StatusLabel status={status} className="text-[13px]" />
                          {c.band === 'needs_practice' ? (
                            <span className="flex basis-full flex-wrap gap-2 sm:basis-auto">
                              <Button asChild size="sm"><Link href={conceptHref(c.id)}>Practice this</Link></Button>
                              <Button asChild size="sm" variant="outline"><Link href={`/playground?concept=${encodeURIComponent(c.id)}`}>Explore in {NAME.playground}</Link></Button>
                            </span>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                </details>
              );
            })}
            <div className="rounded-card border p-5"><StatusLegend only={['not_seen', 'assumed', 'practised', 'mastered', 'review', 'needs_practice']} /></div>
          </section>

          <aside className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-4 lg:col-span-4 lg:gap-6" aria-label="Activity and results">
            <section className="rounded-card border bg-card p-5 lg:p-6" aria-labelledby="timeline-heading">
              <h2 id="timeline-heading" className="font-display text-xl font-bold tracking-[-0.03em]">Evidence timeline</h2>
              {data.recent.length ? (
                <ol className="mt-4 grid gap-0">
                  {data.recent.map((r, i) => {
                    const pct = Math.round(r.score * 100);
                    const ok = r.score >= 0.7;
                    return (
                      <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
                        {i < data.recent.length - 1 ? <span aria-hidden="true" className="absolute top-6 bottom-0 left-[10px] w-px bg-border-strong" /> : null}
                        <StatusIcon status={ok ? 'practised' : 'needs_practice'} size={22} className="relative bg-card" />
                        <div className="min-w-0">
                          <p className="text-[15px] font-semibold">
                            {new Date(r.at * 1000).toLocaleDateString(undefined, { weekday: 'short' })}, {r.concept}, {r.assisted ? 'with help' : 'independent'}
                          </p>
                          <p className="text-[13px] text-muted-foreground tabular-nums">{KIND[r.kind] ?? r.kind}, {pct}%. {new Date(r.at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</p>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <EmptyState as="h3" illustration={false} title="No results yet" className="mt-4 py-6">Finish a concept check or a problem to see results here.</EmptyState>
              )}
            </section>

            <LearnerProfileCard />

            <section className="rounded-card border bg-card p-5 lg:p-6" aria-labelledby="activity-heading">
              <h2 id="activity-heading" className="font-display text-xl font-bold tracking-[-0.03em]">Study activity</h2>
              <p className="mt-1 text-sm font-semibold">Activity shows time spent. It does not measure mastery.</p>
              <p className="mt-1 text-sm text-muted-foreground">{hours(data.total_minutes)} over {activeDays} days in the last 6 months. This week: {data.week.minutes} of {data.week.goal} min.</p>
              <div className="mt-4 overflow-x-auto rounded-lg pb-1" tabIndex={0} role="region" aria-label="Study activity, scrolls sideways">
                <div className="heatmap w-max overflow-visible!" role="img" aria-label={`Study minutes per day over the last ${data.heatmap.length} days: ${activeDays} days with activity, ${hours(data.total_minutes)} in total`}>
                  {Array.from({ length: leading }, (_, i) => <span key={`pad-${i}`} style={{ visibility: 'hidden' }} />)}
                  {data.heatmap.map(d => (
                    <span key={d.day} data-level={level(d.minutes)} title={`${formatDate(d.day)}: ${d.minutes} min, ${d.activities} activities`} />
                  ))}
                </div>
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-[13px] text-muted-foreground">
                Less <span className="heatmap grid-rows-[12px]! overflow-visible! p-0!" aria-hidden="true">{[0, 1, 2, 3, 4].map(l => <span key={l} data-level={l} />)}</span> More
                <span className="sr-only">Levels: none, under 15 minutes, under 30, under 60, an hour or more.</span>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{data.streak.current}-day streak. Longest {data.streak.longest} days.</p>
            </section>
          </aside>
        </div>
      </div>
      <p className="sr-only">Status labels: {Object.values(STATUS_LABEL).join(', ')}.</p>
    </Page>
  );
}
