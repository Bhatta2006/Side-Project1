'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, ChevronDown } from '@/components/icons';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, PACE_LABEL, conceptHref, formatDate, hours } from '@/lib/routes';
import type { AssessmentStatus, ProgressView } from '@/lib/types';
import { ErrorNote, Loading, Page, Ring, StatCard } from '@/components/common';
import { SolvedBoard } from '@/components/socrat/solved-board';
import { EmptyState } from '@/components/socrat/states';
import { LearnerProfileCard } from '@/components/socrat/learner-profile';
import { PassportSettingsCard } from '@/components/socrat/passport-settings';
import { STATUS_LABEL, StatusIcon, StatusLabel, StatusLegend, statusFromBand } from '@/components/socrat/status';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Paper } from '@/components/ui/paper';
import { SocFigure } from '@/components/socrat/soc';

// Decorations from the large sticker and doodle catalogues load on their own, after the page.
const Stamp = dynamic(() => import('@/components/ui/stamp').then(m => m.Stamp), { ssr: false });

const KIND: Record<string, string> = { quiz: 'concept check', code: 'problem', checkpoint: 'checkpoint', review: 'review', placement: 'placement', external: 'practice', verified: 'Codeforces', guided: 'guided step', trace: 'trace', retrieval: 'recall', debug: 'debugging', explanation: 'explanation', explain: 'written answer (AI-graded)', project: 'project milestone (AI-graded)' };

function level(minutes: number) {
  if (!minutes) return 0;
  if (minutes < 15) return 1;
  if (minutes < 30) return 2;
  if (minutes < 60) return 3;
  return 4;
}

const TABS = ['skills', 'timeline', 'activity', 'share'] as const;
type TabId = (typeof TABS)[number];

export default function ProgressPage() {
  const allowed = useGuard('active');
  const [data, setData] = useState<ProgressView | null>(null);
  const [assessment, setAssessment] = useState<AssessmentStatus | null>(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<TabId>('skills');

  const load = useCallback(() => {
    setError('');
    api.get<ProgressView>('/progress').then(setData).catch(e => setError(explain(e)));
    api.get<{ current: AssessmentStatus }>('/assessments').then(r => setAssessment(r.current)).catch(() => undefined);
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  // The open section lives in the URL hash, so a link or a refresh lands where the learner was.
  useEffect(() => {
    const wanted = window.location.hash.slice(1) as TabId;
    if (TABS.includes(wanted)) setTab(wanted);
  }, []);
  const pick = (value: string) => {
    setTab(value as TabId);
    window.history.replaceState(null, '', `#${value}`);
  };

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
        <p className="font-hand mb-2 origin-left -rotate-2 text-[22px] text-pen">{NAME.evidence}</p>
        <h1 className="type-display-l">What you have <span className="hl hl-draw">shown</span></h1>
      </header>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:gap-6">
        {assessmentOpen ? (
          <Link href="/assessments" className="group flex min-h-16 flex-wrap items-center justify-between gap-3 paper rounded-card px-5 py-4 transition-transform duration-200 hover:-translate-y-0.5" aria-label={`${NAME.assessment}: ${assessment.state === 'in_progress' ? 'continue' : 'open'}`}>
            <span className="flex flex-wrap items-center gap-3">
              <Badge>{assessment.state === 'in_progress' ? 'In progress' : 'Available'}</Badge>
              <span className="font-display text-lg font-semibold tracking-[-0.02em]">{NAME.assessment}</span>
              <span className="text-sm text-muted-foreground">A proof event built from what you studied this week.</span>
            </span>
            <ArrowRight className="size-5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </Link>
        ) : null}

        {/* Hero: course completion. */}
        <Paper as="section" stock="sticky-yellow" tape="both" tilt={-0.3} seed="evidence-hero" className="flex flex-wrap items-center gap-6 p-6 text-ink lg:gap-8 lg:p-8" data-tone="hero" data-tour="evidence-course" aria-labelledby="course-heading">
          <div aria-hidden="true" className="pointer-events-none absolute right-8 -bottom-3 hidden w-[150px] xl:block"><SocFigure books mood="proud" idle className="h-auto w-full" /></div>
          <Ring value={data.progress.percent} size={104} stroke={6} label={<span className="font-display text-3xl">{data.progress.percent}%</span>} ariaLabel={`Course ${data.progress.percent} percent complete`} />
          <div className="min-w-0 flex-1 xl:pr-[180px]">
            <p className="font-script origin-left -rotate-2 text-[24px] text-red">look how far you&apos;ve come</p>
            <h2 id="course-heading" className="type-display-m mt-2 tabular-nums">{data.progress.finished} of {data.progress.total} skills</h2>
            <p className="mt-2 text-base" data-visual-mask="">Projected finish {formatDate(data.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })}. {PACE_LABEL[data.pace]} pace.</p>
            <p className="mt-1 max-w-xl text-sm">Counts skills you have practised or mastered{data.progress.assumed ? `. ${data.progress.assumed} more are assumed from placement until a short review confirms them` : ''}.</p>
          </div>
          {mastered > 0 ? (
            <Stamp text="PROVEN" sub={`${mastered} mastered`} shape="round" ink="green" size={96} tilt={-8} seed="evidence-proven" className="absolute top-4 right-[200px] hidden xl:block" />
          ) : null}
        </Paper>

        <SolvedBoard />

        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:gap-6">
          <StatCard value={mastered} icon={<StatusIcon status="mastered" size={28} />} label="Skills mastered" hint="Evidence from checks, judged code and reviews passed the mastery threshold." />
          <StatCard value={due} icon={<StatusIcon status="review" size={28} />} label="Reviews due" hint="Spaced reviews that are due now." />
          <StatCard value={weak} icon={<StatusIcon status="needs_practice" size={28} />} label="Need practice" hint="Recent results show these are not holding yet." />
          <StatCard value={data.solves.independent_solves} label="Problems solved without help" hint={`Accepted with no hints. ${data.solves.assisted_solves} more solved with help.`} />
        </div>

        <Tabs value={tab} onValueChange={pick} className="gap-5">
          <TabsList className="w-full justify-start sm:w-fit" aria-label="Sections of your evidence">
            <TabsTrigger value="skills" className="flex-none px-4 sm:px-5">Skills <span className="text-[13px] font-semibold text-muted-foreground tabular-nums">{mastered}/{concepts.length}</span></TabsTrigger>
            <TabsTrigger value="timeline" className="flex-none px-4 sm:px-5">Timeline {data.recent.length ? <span className="text-[13px] font-semibold text-muted-foreground tabular-nums">{data.recent.length}</span> : null}</TabsTrigger>
            <TabsTrigger value="activity" className="flex-none px-4 sm:px-5">Activity <span className="text-[13px] font-semibold text-muted-foreground tabular-nums">{data.streak.current}d</span></TabsTrigger>
            <TabsTrigger value="share" className="flex-none px-4 sm:px-5">Profile and sharing</TabsTrigger>
          </TabsList>

          {/* Skills: mastery by module, one module open at a time. */}
          <TabsContent value="skills">
            <section aria-labelledby="mastery-heading" className="grid min-w-0 content-start gap-4">
              <h2 id="mastery-heading" className="font-display text-2xl font-semibold tracking-[-0.03em]">Mastery by module</h2>
              {data.modules.map((m, mi) => {
                const moduleWeak = m.concepts.filter(c => c.band === 'needs_practice').length;
                const moduleMastered = m.concepts.filter(c => c.band === 'strong').length;
                return (
                  <details key={m.id} className="group paper rounded-card" open={mi === 0 || moduleWeak > 0}>
                    <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-5 py-4 lg:px-6 [&::-webkit-details-marker]:hidden">
                      <span className="font-display text-lg font-semibold tracking-[-0.02em]">{m.title}</span>
                      <span className="flex items-center gap-3 text-sm font-semibold text-muted-foreground tabular-nums">
                        {moduleMastered} mastered{moduleWeak ? `, ${moduleWeak} need practice` : ''}
                        <ChevronDown className="size-5 text-foreground transition-transform group-open:rotate-180" aria-hidden="true" />
                      </span>
                    </summary>
                    <ul className="grid gap-2 px-5 pb-5 lg:px-6">
                      {m.concepts.map(c => {
                        const due = c.next_review !== null && c.next_review <= now;
                        const status = due && c.band !== 'not_started' ? 'review' : c.status === 'practiced' ? 'learned' : c.status === 'assumed' ? 'assumed' : statusFromBand(c.band, due);
                        const helped = (c.assisted ?? 0) > (c.independent ?? 0);
                        return (
                          <li key={c.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-[4px] bg-raised px-4 py-3">
                            <Link href={conceptHref(c.id)} transitionTypes={['nav-forward']} className="min-w-0 flex-1 basis-40 font-semibold underline-offset-4 hover:underline">{c.title}</Link>
                            <StatusLabel status={status} className="text-[13px]" />
                            {helped ? <span className="text-[13px] text-muted-foreground">mostly with help</span> : null}
                            {status === 'needs_practice' ? (
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
              <details className="group rounded-card border">
                <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-5 py-3 text-[15px] font-semibold [&::-webkit-details-marker]:hidden">
                  What the icons mean
                  <ChevronDown className="size-5 transition-transform group-open:rotate-180" aria-hidden="true" />
                </summary>
                <div className="px-5 pb-5"><StatusLegend only={['not_seen', 'assumed', 'practised', 'learned', 'mastered', 'review', 'needs_practice']} /></div>
              </details>
            </section>
          </TabsContent>

          {/* Timeline: the latest results, newest first. */}
          <TabsContent value="timeline">
            <section className="paper max-w-3xl rounded-card p-5 lg:p-6" aria-labelledby="timeline-heading">
              <h2 id="timeline-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Evidence timeline</h2>
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
          </TabsContent>

          {/* Activity: time spent, never a measure of mastery. */}
          <TabsContent value="activity">
            <section className="paper max-w-3xl rounded-card p-5 lg:p-6" aria-labelledby="activity-heading">
              <h2 id="activity-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Study activity</h2>
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
          </TabsContent>

          {/* Profile and sharing: what Socrat knows about you and what others can see. */}
          <TabsContent value="share" className="grid gap-4 lg:grid-cols-2 lg:gap-6">
            <PassportSettingsCard />
            <LearnerProfileCard />
          </TabsContent>
        </Tabs>
      </div>
      <p className="sr-only">Status labels: {Object.values(STATUS_LABEL).join(', ')}.</p>
    </Page>
  );
}
