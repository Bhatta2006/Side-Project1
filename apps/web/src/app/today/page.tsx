'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, ChevronRight, Flame } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { KIND_LABEL, NAME, PACE_LABEL, activityHref, conceptHref, formatDate } from '@/lib/routes';
import type { Activity, AssessmentStatus, PlanView, Recommendations, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, Reveal, Ring } from '@/components/common';
import { Level, PlatformTag, ProblemName } from '@/components/practice';
import Assistant from '@/components/assistant';
import Markdown from '@/components/markdown';
import { ProposalList } from '@/components/socrat/proposals';
import { Illustration, Soc } from '@/components/socrat/illustration';
import { SocFigure } from '@/components/socrat/soc';
import { StatusIcon, statusFromBand, statusFromRoadmap } from '@/components/socrat/status';
import { SkillGrid } from '@/components/socrat/skill-grid';
import { WeekStrip } from '@/components/socrat/week-strip';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { CommunityCard } from '@/components/community-link';

const VERB: Record<string, string> = {
  lesson: 'Start lesson',
  problem: 'Open problem',
  quiz: 'Take concept check',
  checkpoint: 'Start checkpoint',
  review: 'Start review',
  remedial: 'Start refresher',
  probe: 'Take the check',
  testout: 'Start test-out',
  moduletest: 'Start test-out',
  example: 'See the example',
  explain: 'Read it another way',
  checkin: 'Talk it through',
  stretch: 'Try the stretch',
};
const CHIP: Record<string, string> = {
  lesson: 'lesson',
  problem: 'practice',
  quiz: 'check',
  checkpoint: 'check',
  review: 'review',
  remedial: 'review',
  probe: 'check',
  testout: 'test-out',
  moduletest: 'test-out',
  example: 'lesson',
  explain: 'lesson',
  checkin: 'tutor',
  stretch: 'practice',
};

function greeting(name: string) {
  const hour = new Date().getHours();
  return `${hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'}, ${name}`;
}

/** The current module from the plan: the next milestone, with real counts only. */
function milestone(plan: PlanView | null) {
  if (!plan) return null;
  const module = plan.modules.find(m => m.concepts.some(c => c.concept === plan.current_concept)) ?? plan.modules.find(m => !m.locked_by);
  if (!module) return null;
  const finished = module.concepts.filter(c => ['mastered', 'practiced'].includes(c.status)).length;
  return { title: module.title, finished, total: module.concepts.length, concepts: module.concepts, current: plan.current_concept };
}

/** Progress with a violet-to-lilac fill that grows in once on load. */
function GradientBar({ value, label }: { value: number; label: string }) {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(frame);
  }, []);
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value)} className="h-2.5 flex-1 overflow-hidden rounded-full bg-raised">
      <div className="h-full rounded-full bg-gradient-to-r from-primary to-[#A98BFF] transition-[width] duration-700 ease-[var(--ease-soft)]" style={{ width: drawn ? `${Math.max(2, Math.min(100, value))}%` : '0%' }} />
    </div>
  );
}

function SessionRow({ activity, done }: { activity: Activity; done: boolean }) {
  return (
    <li>
      <Link href={activityHref(activity.id)} className="group flex min-h-14 items-center gap-3 rounded-[16px] px-3 py-2 transition-colors hover:bg-raised">
        <StatusIcon status={done ? 'practised' : 'not_seen'} size={22} />
        <span className="min-w-0 flex-1">
          <span className={cn('block font-semibold', done && 'text-muted-foreground')}>{activity.title}</span>
          <span className="text-[13px] text-muted-foreground">{KIND_LABEL[activity.kind]}{activity.minutes ? `, ${activity.minutes} min` : ''}{done ? ', done' : ''}</span>
        </span>
        {!done ? <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" /> : null}
      </Link>
    </li>
  );
}

export default function TodayPage() {
  const allowed = useGuard('active');
  const { profile } = useSession();
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState('');
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [assessment, setAssessment] = useState<AssessmentStatus | null>(null);
  const [askSoc, setAskSoc] = useState(0);

  const load = useCallback(() => {
    setError('');
    api.get<Today>('/today').then(setToday).catch(e => setError(explain(e)));
    api.get<Recommendations>('/library/recommendations?limit=4').then(setRecs).catch(() => undefined);
    api.get<PlanView>('/plan').then(setPlan).catch(() => undefined);
    api.get<{ current: AssessmentStatus }>('/assessments').then(r => setAssessment(r.current)).catch(() => undefined);
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!today && !error)) return <Loading label="Loading today" />;
  if (!today) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const name = profile?.display_name || today.greeting.split(', ').slice(1).join(', ') || 'there';
  const minutePercent = today.minutes.goal ? (100 * today.minutes.done) / today.minutes.goal : 0;
  const next = today.next;
  const review = today.queue.find(a => a.kind === 'review');
  const weak = recs?.topics.find(t => t.band === 'needs_practice');
  const goal = milestone(plan);
  const goalPercent = goal && goal.total ? (100 * goal.finished) / goal.total : 0;
  const mastered = plan ? plan.modules.reduce((n, mod) => n + mod.concepts.filter(c => c.status === 'mastered').length, 0) : today.progress.finished;
  const assessmentOpen = assessment && (assessment.state === 'available' || assessment.state === 'in_progress');
  const queue = next ? [...today.queue].sort((x, y) => Number(y.id === next.id) - Number(x.id === next.id)) : today.queue;
  const session = [...today.done.map(a => ({ a, done: true })), ...queue.map(a => ({ a, done: false }))];
  // A learner who has not started sees a plan, not a column of zeros.
  const fresh = today.streak.current === 0 && today.done.length === 0 && today.progress.finished === 0 && today.streak.week_minutes === 0;

  return (
    <Page wide>
      {/* 1. Header: phone shows "Hi, name" and today's minutes; desktop shows the greeting. */}
      <Reveal>
        <header className="mb-6 flex items-center justify-between gap-4 lg:mb-8">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid size-11 flex-none place-items-center rounded-full border-2 border-[var(--soc-outline)] bg-[var(--highlight)] text-[15px] font-semibold text-[#15161E] lg:hidden" aria-hidden="true">{name.slice(0, 2).toUpperCase()}</span>
            <div className="min-w-0">
              <p className="font-hand hidden origin-left -rotate-2 text-[22px] text-pen lg:block" data-visual-mask="">{formatDate(today.date, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
              <h1 className="truncate font-display text-2xl font-semibold tracking-[-0.03em] lg:type-display-l lg:whitespace-normal">
                <span className="lg:hidden">Hi, {name}</span>
                <span className="hidden lg:inline">{greeting(name)}</span>
              </h1>
              <p className="text-sm text-muted-foreground lg:mt-2 lg:text-lg" data-visual-mask="">
                <span className="lg:hidden">{formatDate(today.date, { weekday: 'long', month: 'long', day: 'numeric' })}. {today.course.title}</span>
                <span className="hidden lg:inline">Here&apos;s your <span className="hl text-foreground">learning plan</span> for today.</span>
              </p>
            </div>
          </div>
          <p className="flex-none text-right lg:hidden">
            <span className="sr-only">Today: </span>
            <span className="type-display-m tabular-nums">{today.minutes.goal}</span>
            <span className="ml-1 text-sm font-semibold text-muted-foreground">min today</span>
          </p>
        </header>
      </Reveal>

      {/* 2. Return after absence. */}
      {today.days_away >= 3 ? (
        <Reveal>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-card border px-5 py-4" role="status">
            <p className="font-semibold">Welcome back. Your plan moved forward while you were away.</p>
            <Link href="/plan#why-heading" className="text-[15px] font-semibold underline underline-offset-4">See what changed</Link>
          </div>
        </Reveal>
      ) : null}

      {/* Soc opens the day: yesterday's work, today's first step, and anything to decide. */}
      {today.checkin || today.proposals.length || today.nudges.some(n => n.kind !== 'proposals' && n.kind !== 'away') ? (
        <Reveal>
          <Card className="mb-6" aria-labelledby="checkin-heading">
            <div className="grid gap-4 px-(--card-spacing)">
              <div className="flex items-start gap-3">
                <button type="button" onClick={() => setAskSoc(n => n + 1)} aria-haspopup="dialog" aria-label="Ask Soc about this check-in" className="flex-none rounded-full">
                  <Soc size={40} />
                </button>
                <div className="min-w-0">
                  <h2 id="checkin-heading" className="sr-only">Check-in from Soc</h2>
                  {today.checkin ? <Markdown source={today.checkin.message} className="prose-compact text-[15px]" /> : null}
                  {today.milestone ? (
                    <p className="mt-1 text-[14px] text-muted-foreground">
                      This week&apos;s milestone: {today.milestone.concepts.map(c => c.title).join(', ')}.
                    </p>
                  ) : null}
                </div>
              </div>
              {today.nudges.filter(n => n.kind !== 'proposals' && n.kind !== 'away').length ? (
                <ul className="grid gap-2" aria-label="Things to look at">
                  {today.nudges.filter(n => n.kind !== 'proposals' && n.kind !== 'away').map(n => (
                    <li key={n.kind + n.title}>
                      <Link href={n.href} className={cn('block rounded-[16px] border px-4 py-3 transition-colors hover:bg-raised', n.severity === 'high' && 'border-attention')}>
                        <span className="font-semibold">{n.title}</span>
                        <span className="block text-[14px] text-muted-foreground">{n.body}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
              {today.proposals.length ? (
                <section aria-labelledby="today-proposals">
                  <h3 id="today-proposals" className="type-label mb-2 text-muted-foreground">Socrat suggests</h3>
                  <ProposalList compact proposals={today.proposals.slice(0, 3)} onDecided={load} />
                  {today.proposals.length > 3 ? (
                    <Link href="/plan#proposals" className="mt-2 inline-block text-[14px] font-semibold underline underline-offset-4">
                      See all {today.proposals.length} suggestions
                    </Link>
                  ) : null}
                </section>
              ) : null}
            </div>
          </Card>
        </Reveal>
      ) : null}

      <div className="grid grid-cols-12 gap-3 sm:gap-4 lg:gap-6">
        {/* 3. Week strip (phone and tablet). */}
        <Card className="col-span-12 lg:hidden" size="sm" aria-label="This week">
          <div className="px-(--card-spacing)"><WeekStrip studiedToday={today.streak.studied_today} /></div>
        </Card>

          {/* 4. Hero: the next recommended activity. */}
        <Reveal index={1} className="col-span-12 lg:col-span-8">
          {next ? (
            <Card tone="hero" className="relative h-full min-h-72 lg:min-h-80" aria-labelledby="next-heading">
              {/* Soc on his books, cheering the next step on. */}
              <div aria-hidden="true" className="pointer-events-none absolute right-8 -bottom-3 hidden w-[230px] sm:block lg:right-12 lg:w-[250px]">
                <SocFigure books mood="happy" idle className="h-auto w-full drop-shadow-[0_18px_24px_rgb(0_0_0/0.25)]" />
              </div>
              <div className="pointer-events-none absolute top-6 right-6 hidden font-hand text-[24px] text-white/90 rotate-6 lg:block" aria-hidden="true">you&apos;ve got this ↓</div>
              <div className="relative flex h-full flex-col gap-5 px-(--card-spacing) sm:max-w-[58%]">
                <p className="type-label text-(--card-muted)">Today, goal {today.minutes.goal} min</p>
                <div>
                  <h2 id="next-heading" className="type-display-l max-w-[14ch] pr-8 [overflow-wrap:anywhere] sm:pr-0">{next.title}</h2>
                  <p className="mt-3 max-w-md text-base text-(--card-muted)">{next.reason || 'Next in your plan.'}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge>{CHIP[next.kind] ?? KIND_LABEL[next.kind]}</Badge>
                  {next.minutes ? <Badge>{next.minutes} min</Badge> : null}
                </div>
                <div className="mt-auto">
                  <Button asChild variant="ink" size="lg">
                    <Link href={activityHref(next.id)} transitionTypes={['nav-forward']}>
                      {VERB[next.kind] ?? 'Continue'}
                      <ArrowCircle />
                    </Link>
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <Card tone="hero" className="relative" aria-labelledby="next-heading">
              <div aria-hidden="true" className="pointer-events-none absolute right-8 -bottom-3 hidden w-[200px] sm:block">
                <SocFigure books mood={today.study_day ? 'proud' : 'sleepy'} idle className="h-auto w-full" />
              </div>
              <div className="relative flex flex-col gap-4 px-(--card-spacing) sm:max-w-[60%]">
                <h2 id="next-heading" className="type-display-m">{today.study_day ? 'Done for today' : 'Rest day'}</h2>
                <p className="max-w-md text-(--card-muted)">
                  {today.study_day
                    ? 'Everything planned for today is complete. You can keep going from your plan.'
                    : 'Today is not one of your study days. You can work ahead from your plan.'}
                </p>
                <div><Button asChild variant="ink" size="lg"><Link href="/plan">Open {NAME.skills}<ArrowCircle /></Link></Button></div>
              </div>
            </Card>
          )}
        </Reveal>


        {/* Talk to your tutor. */}
        <Reveal index={2} className="col-span-12 hidden lg:col-span-4 lg:block">
          <Card className="relative h-full min-h-72 overflow-hidden lg:min-h-80" aria-labelledby="soc-heading">
            <div className="relative flex h-full flex-col gap-4 px-(--card-spacing)">
              <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">stuck? talk to me</p>
              <div className="max-w-[55%]">
                <h2 id="soc-heading" className="type-display-m">Ask Soc</h2>
                <p className="mt-3 text-base text-muted-foreground">Get unstuck, ask questions, or request a hint.</p>
              </div>
              {/* A bigger target for pointer users; keyboard users have the Ask Soc button below. */}
              <button type="button" tabIndex={-1} aria-hidden="true" onClick={() => setAskSoc(n => n + 1)} className="absolute -top-2 right-(--card-spacing) rounded-full">
                <Soc size={120} mood="curious" />
              </button>
              <button type="button" data-tour="tutor" onClick={() => setAskSoc(n => n + 1)} className="group/ask mt-auto flex h-14 items-center justify-between gap-3 rounded-full border border-border-strong bg-card pr-2 pl-6 text-[17px] font-medium transition-colors hover:border-foreground/40" aria-haspopup="dialog">
                Ask Soc
                <span className="grid size-10 place-items-center rounded-full bg-primary text-primary-foreground shadow-[var(--primary-glow)] transition-transform group-hover/ask:translate-x-0.5"><ArrowRight className="size-5" aria-hidden="true" /></span>
              </button>
            </div>
          </Card>
        </Reveal>

        {/* Skill map of the current module. */}
        {goal ? (
          <Reveal index={3} className="col-span-12 lg:col-span-8">
            <Card className="h-full" aria-labelledby="map-heading">
              <div className="flex flex-1 flex-col px-(--card-spacing)">
                <p id="map-heading" className="type-label mb-5 text-muted-foreground">Your skill map: {goal.title}</p>
                <SkillGrid
                  label={goal.title}
                  nodes={goal.concepts.map(c => ({ id: c.concept, title: c.title, href: conceptHref(c.concept), status: statusFromRoadmap(c), current: c.concept === goal.current, reviewDue: c.review_due }))}
                />
              </div>
            </Card>
          </Reveal>
        ) : null}

        {/* Proof and milestone. */}
        <div className={cn('col-span-12 grid content-start gap-3 sm:gap-4 lg:gap-6', goal ? 'lg:col-span-4' : 'lg:col-span-12 lg:grid-cols-2')}>
          <Reveal index={4}>
            <Link href="/progress" className="paper group flex items-center gap-4 rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6">
              <StatusIcon status="mastered" size={48} />
              <span className="font-display text-6xl leading-none font-semibold tracking-[-0.04em] tabular-nums">{mastered}</span>
              <span className="min-w-0 flex-1 font-display text-xl leading-tight font-semibold tracking-[-0.02em]">{mastered === 1 ? 'skill' : 'skills'} mastered</span>
              <ChevronRight className="size-5 flex-none text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
          </Reveal>
          {goal ? (
            <Reveal index={5}>
              <Card aria-labelledby="milestone-heading">
                <div className="grid gap-3 px-(--card-spacing)">
                  <p className="type-label text-muted-foreground">Next milestone</p>
                  <h2 id="milestone-heading" className="font-display text-2xl leading-tight font-semibold tracking-[-0.03em]">{goal.title}</h2>
                  <p className="text-[15px] text-muted-foreground">
                    {goal.total - goal.finished > 0 ? `Complete ${goal.total - goal.finished} more skill${goal.total - goal.finished === 1 ? '' : 's'} to reach this milestone.` : 'Milestone reached. The next module is opening up.'}
                  </p>
                  <div className="flex items-center gap-4">
                    <GradientBar value={goalPercent} label={`${goal.title}: ${goal.finished} of ${goal.total} skills`} />
                    <span className="text-sm font-semibold text-muted-foreground tabular-nums">{Math.round(goalPercent)}%</span>
                  </div>
                </div>
              </Card>
            </Reveal>
          ) : null}
        </div>

        {/* The rest of today. */}
        <div className="col-span-12 grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-3 sm:gap-4 lg:col-span-8 lg:gap-6">
          {/* 5. Review due and Playground. */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:gap-6">
            {review || today.reviews_due ? (
              <Link href={review ? activityHref(review.id) : '/plan'} className="group flex min-h-28 flex-col justify-between gap-3 rounded-card bg-cream text-cream-foreground p-5 transition-[background-color,transform] duration-200 hover:-translate-y-0.5 hover:bg-[color-mix(in_srgb,var(--cream),var(--foreground)_4%)] lg:p-6">
                <StatusIcon status="review" size={32} />
                <span>
                  <span className="block font-display text-lg leading-tight font-semibold tracking-[-0.02em]">
                    Review due{review ? `: ${review.title.replace(/^Review:?\s*/i, '')}` : ''}
                  </span>
                  {today.reviews_due > 1 ? <span className="mt-1 block text-sm text-muted-foreground">{today.reviews_due} reviews due</span> : null}
                </span>
              </Link>
            ) : null}
            <Link href="/playground" className={cn('paper doodle-host group relative flex min-h-28 flex-col justify-between gap-3 overflow-hidden rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6', !(review || today.reviews_due) && 'col-span-2')}>
              <span className="type-label text-brand">{NAME.playground}</span>
              <Illustration name="orbit" className="pointer-events-none absolute -top-3 -right-3 size-24 opacity-90" />
              <span className="flex items-end justify-between gap-3">
                <span className="font-display text-lg leading-tight font-semibold tracking-[-0.02em]">{weak ? `Explore ${weak.title} visually` : 'Ask about any concept'}</span>
                <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </span>
            </Link>
          </div>

          {/* 7. Weekly assessment: a card when open, a quiet line when not ready. */}
          {assessmentOpen ? (
            <Card aria-labelledby="assessment-heading">
              <div className="flex flex-wrap items-center justify-between gap-4 px-(--card-spacing)">
                <div className="min-w-0">
                  <div className="mb-2"><Badge>{assessment.state === 'in_progress' ? 'In progress' : 'Available'}</Badge></div>
                  <h2 id="assessment-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">{NAME.assessment}</h2>
                  <p className="truncate text-sm text-muted-foreground">On what you studied: {assessment.topics.slice(0, 3).join(', ')}{assessment.topics.length > 3 ? ', and more' : ''}</p>
                </div>
                <Button asChild variant="outline"><Link href="/assessments">{assessment.state === 'in_progress' ? 'Continue assessment' : 'Open assessment'}</Link></Button>
              </div>
            </Card>
          ) : assessment ? (
            <p className="px-1 text-sm text-muted-foreground">{NAME.assessment}: unlocks as you study more topics this week.</p>
          ) : null}

          {/* Today's plan: what the session holds, in order. */}
          {session.length ? (
            <Card aria-labelledby="agenda-heading">
              <div className="flex items-baseline justify-between gap-3 px-(--card-spacing)">
                <h2 id="agenda-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">Today&apos;s session</h2>
                <span className="text-sm font-semibold text-muted-foreground tabular-nums">{today.done.length ? `${today.done.length} of ${session.length} done` : `${session.length} step${session.length === 1 ? '' : 's'}, in order`}</span>
              </div>
              <ul className="grid px-[calc(var(--card-spacing)-12px)]">
                {session.map(({ a, done }) => <SessionRow key={a.id} activity={a} done={done} />)}
              </ul>
            </Card>
          ) : null}

          {/* 8. Practice recommendations. */}
          {recs?.problems.length ? (
            <section aria-labelledby="practice-heading" className="min-w-0">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <h2 id="practice-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Practice picked for you</h2>
                <Link href="/library" className="text-[15px] font-semibold underline underline-offset-4">See all problems</Link>
              </div>
              <ul className="-mx-4 flex scroll-pl-4 snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 sm:pb-0">
                {recs.problems.map(p => (
                  <li key={p.id} className="flex w-[78%] flex-none snap-start flex-col gap-3 paper rounded-card p-5 sm:w-auto">
                    <div className="flex items-start justify-between gap-3">
                      <ProblemName problem={p} className="text-base" />
                      <StatusIcon status={p.status === 'solved' ? 'practised' : 'not_seen'} size={22} title={p.status === 'solved' ? 'Solved' : 'Not solved yet'} />
                    </div>
                    <p className="text-sm text-muted-foreground">{p.reason}</p>
                    <div className="mt-auto flex flex-wrap items-center gap-2"><PlatformTag platform={p.platform} /><Level problem={p} /></div>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        {/* Support column. */}
        <aside className="col-span-12 grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-3 sm:gap-4 lg:col-span-4 lg:gap-6" aria-label="Support">
          <Card className="hidden lg:flex" aria-labelledby="week-heading">
            <div className="grid gap-4 px-(--card-spacing)">
              <div className="flex items-center justify-between gap-3">
                <h2 id="week-heading" className="flex items-center gap-2 font-display text-lg font-semibold tracking-[-0.02em]">
                  <Flame className="size-5" strokeWidth={1.5} aria-hidden="true" /> {fresh ? 'Start your streak today' : `${today.streak.current}-day streak`}
                </h2>
                <Ring value={minutePercent} size={56} ariaLabel={`${today.minutes.done} of ${today.minutes.goal} minutes today`} label={<span className="text-[13px]">{today.minutes.done}</span>} />
              </div>
              <WeekStrip studiedToday={today.streak.studied_today} />
              <p className="text-sm text-muted-foreground">
                {fresh ? `A ${today.minutes.goal}-minute session is all it takes. Your week goal is ${today.streak.week_goal} min.` : `${today.minutes.done} of ${today.minutes.goal} min today. ${today.streak.week_minutes} of ${today.streak.week_goal} min this week.`}
              </p>
            </div>
          </Card>

          {recs?.topics.length ? (
            <Card aria-labelledby="learn-next-heading">
              <div className="px-(--card-spacing)">
                <h2 id="learn-next-heading" className="mb-3 font-display text-lg font-semibold tracking-[-0.02em]">Skills to learn next</h2>
                <ul className="grid gap-1">
                  {recs.topics.map(t => (
                    <li key={t.id}>
                      <Link href={conceptHref(t.id)} className="-mx-2 flex min-h-12 items-start gap-3 rounded-[14px] px-2 py-2 transition-colors hover:bg-raised">
                        <StatusIcon status={statusFromBand(t.band)} size={22} className="mt-0.5" />
                        <span className="min-w-0">
                          <span className="block font-semibold">{t.title}</span>
                          <span className="block text-[13px] text-muted-foreground">{t.reason}</span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          ) : null}

          {/* 9. Course progress: ring with the real percent. */}
          <Card aria-labelledby="course-heading">
            <div className="flex items-center gap-5 px-(--card-spacing)">
              <Ring value={today.progress.percent} size={80} label={<span className="text-base">{today.progress.percent}%</span>} ariaLabel={`Course ${today.progress.percent} percent complete`} />
              <div className="min-w-0">
                <h2 id="course-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">Course progress</h2>
                <p className="text-sm text-muted-foreground">{fresh ? `${today.progress.total} skills ahead of you.` : `${today.progress.finished} of ${today.progress.total} skills. ${PACE_LABEL[today.pace]} pace.`}</p>
                <p className="mt-1 text-sm text-muted-foreground" data-visual-mask="">Projected finish {formatDate(today.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })}</p>
              </div>
            </div>
          </Card>
          <Link href="/progress" className="flex min-h-12 items-center justify-between gap-3 rounded-card border border-dashed border-border-strong px-5 py-3 text-[15px] font-medium transition-colors hover:border-foreground/40 hover:bg-card">
            Check your progress in {NAME.evidence}
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </aside>
      </div>
      <CommunityCard className="mt-6" />
      <Assistant scope="general" title="Ask Soc" openSignal={askSoc} launcher="phone" />
    </Page>
  );
}
