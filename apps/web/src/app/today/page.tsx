'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, ChevronRight, Flame } from '@/components/icons';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { StreakExtras } from '@/components/socrat/streak-extras';
import { useCourse } from '@/lib/course';
import { useI18n } from '@/lib/i18n';
import { KIND_LABEL, NAME, PACE_LABEL, activityHref, conceptHref, formatDate } from '@/lib/routes';
import type { Activity, AssessmentStatus, PlanView, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, Reveal, Ring } from '@/components/common';
import { ReasonChip } from '@/components/socrat/reason-chip';
import { Illustration } from '@/components/socrat/illustration';
import { StatusIcon, statusFromBand, statusFromRoadmap } from '@/components/socrat/status';
import { CoursePath, type PathModule } from '@/components/socrat/course-path';
import { GameBar } from '@/components/socrat/game-bar';
import { GoalReachedMoment, LevelUpMoment } from '@/components/socrat/game-moments';
import { usePlanLocks } from '@/lib/plan-locks';
import { WeekStrip } from '@/components/socrat/week-strip';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { CommunityCard } from '@/components/community-link';
import { usePreparing } from '@/lib/preparing';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// The chat loads on demand, as on the problem page: it opens only when asked, and its code
// otherwise sits in Today's first load. An early openSignal still opens it once it arrives.
const Assistant = dynamic(() => import('@/components/assistant'), { ssr: false });
// "What Socrat noticed" sits below the fold and brings the Markdown renderer with it. It loads
// while Today's data is fetched (see the effect in TodayPage), so it is ready when the page shows.
const loadAdapting = () => import('@/components/socrat/adapting').then(m => m.AdaptingCard);
const AdaptingCard = dynamic(loadAdapting, { ssr: false });

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
  transfer: 'Start the check',
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
  transfer: 'check',
};

function greeting(name: string) {
  const hour = new Date().getHours();
  return `${hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'}, ${name}`;
}

/** The module the next step is in (from the server), with real counts only. */
function milestone(plan: PlanView | null, current?: string | null) {
  if (!plan) return null;
  const module = plan.modules.find(m => m.id === (current ?? plan.current_module)) ?? plan.modules.find(m => m.concepts.some(c => c.concept === plan.current_concept));
  if (!module) return null;
  const finished = module.concepts.filter(c => ['mastered', 'practiced'].includes(c.status)).length;
  return { id: module.id, title: module.title, finished, total: module.concepts.length, concepts: module.concepts, current: plan.current_concept };
}

function SessionRow({ activity, done, onLater }: { activity: Activity; done: boolean; onLater?: () => void }) {
  return (
    <li className="flex items-center gap-1">
      <Link href={activityHref(activity.id)} className="group flex min-h-14 min-w-0 flex-1 items-center gap-3 rounded-[4px] px-3 py-2 transition-colors hover:bg-raised">
        <StatusIcon status={done ? 'practised' : 'not_seen'} size={22} />
        <span className="min-w-0 flex-1">
          <span className={cn('block font-semibold', done && 'text-muted-foreground')}>{activity.title}</span>
          <span className="text-[13px] text-muted-foreground">{KIND_LABEL[activity.kind]}{activity.minutes ? `, ${activity.minutes} min` : ''}{done ? ', done' : ''}</span>
        </span>
        {!done ? <ReasonChip code={activity.code} className="hidden sm:inline-flex" /> : null}
        {!done ? <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" /> : null}
      </Link>
      {/* A review can wait a few days; the schedule itself is unchanged (learn/reviews.py). */}
      {onLater && !done ? (
        <button type="button" onClick={onLater} className="min-h-11 flex-none rounded-full px-3 text-[13px] font-medium text-muted-foreground underline-offset-4 hover:underline">
          Later<span className="sr-only">: remind me about {activity.title} in 3 days</span>
        </button>
      ) : null}
    </li>
  );
}

const TABS = ['map', 'session', 'practice', 'progress'] as const;
type TabId = (typeof TABS)[number];

export default function TodayPage() {
  const allowed = useGuard('active');
  const course = useCourse();
  const courseReady = course.ready;
  useEffect(() => { void loadAdapting(); }, []);
  const planLocked = usePlanLocks();
  const { profile, features } = useSession();
  const { t } = useI18n();
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState('');
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [assessment, setAssessment] = useState<AssessmentStatus | null>(null);
  const [askSoc, setAskSoc] = useState(0);
  const [tab, setTab] = useState<TabId>('map');

  const load = useCallback(() => {
    setError('');
    api.get<Today>('/today').then(setToday).catch(e => setError(explain(e)));
    api.get<PlanView>('/plan').then(setPlan).catch(() => undefined);
    api.get<{ current: AssessmentStatus }>('/assessments').then(r => setAssessment(r.current)).catch(() => undefined);
  }, []);
  useEffect(() => { if (allowed && courseReady) load(); }, [allowed, courseReady, load]);
  // Lessons still being written: a ring on their stone, and Today reloads when one goes live.
  const preparing = usePreparing(Boolean(allowed && courseReady), load);
  // The open section lives in the URL hash, so a link or a refresh lands where the learner was.
  useEffect(() => {
    const wanted = window.location.hash.slice(1) as TabId;
    if (TABS.includes(wanted)) setTab(wanted);
  }, []);
  const pick = (value: string) => {
    setTab(value as TabId);
    window.history.replaceState(null, '', `#${value}`);
  };

  if (!allowed || (!today && !error)) return <Loading label="Loading today" />;
  if (!today) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const name = profile?.display_name || today.greeting.split(', ').slice(1).join(', ') || 'there';
  const minutePercent = today.minutes.goal ? Math.min(100, (100 * today.minutes.done) / today.minutes.goal) : 0;
  const next = today.next;
  const review = today.queue.find(a => a.kind === 'review');
  const goal = milestone(plan, today.current_module);
  const learned = today.progress.finished;
  const mastered = today.progress.mastered ?? 0;
  const complete = today.progress.complete === true;
  const assessmentOpen = assessment && (assessment.state === 'available' || assessment.state === 'in_progress');
  const queue = next ? [...today.queue].sort((x, y) => Number(y.id === next.id) - Number(x.id === next.id)) : today.queue;
  const session = [...today.done.map(a => ({ a, done: true })), ...queue.map(a => ({ a, done: false }))];
  // A learner who has not started sees a plan, not a column of zeros.
  const fresh = today.streak.current === 0 && today.done.length === 0 && today.progress.finished === 0 && today.streak.week_minutes === 0;
  // Every module of the course, in order; a lesson still being written carries its progress.
  const writing = new Map(preparing.filter(l => l.state !== 'later').map(l => [l.concept, l]));
  // Nothing learned yet and the course's first lesson not live: the learner is waiting for it.
  const firstConcept = plan?.modules.find(m => m.concepts.length)?.concepts[0]?.concept;
  const firstWriting = firstConcept && today.progress.finished === 0 ? writing.get(firstConcept) : undefined;
  const pathModules: PathModule[] = (plan?.modules ?? []).filter(m => m.concepts.length).map(m => ({
    id: m.id,
    title: m.title,
    current: m.id === goal?.id,
    locked: Boolean(m.locked_by),
    nodes: m.concepts.map(c => ({ id: c.concept, title: c.title, href: conceptHref(c.concept), status: planLocked(c.concept) ? 'locked' : statusFromRoadmap(c), current: c.concept === plan?.current_concept, reviewDue: c.review_due, writing: writing.get(c.concept) })),
  }));
  const pathTotal = pathModules.reduce((n, m) => n + m.nodes.length, 0);
  const active: TabId = tab === 'map' && !pathModules.length ? 'session' : tab;

  // Each tab names what is inside it, so nothing is a mystery click.
  const tabs: { id: TabId; label: string; hint: string }[] = [
    ...(pathModules.length ? [{ id: 'map' as const, label: 'Path', hint: `${learned}/${pathTotal}` }] : []),
    { id: 'session', label: 'Session', hint: session.length ? (today.done.length ? `${today.done.length}/${session.length}` : `${session.length}`) : '' },
    { id: 'practice', label: 'Practice', hint: '' },
    { id: 'progress', label: 'Progress', hint: `${today.progress.percent}%` },
  ];

  return (
    <Page wide>
      {/* 1. Header: the greeting and one quiet line of numbers. */}
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
        </header>
        <GameBar streak={today.streak.current} fresh={fresh} studiedToday={today.streak.studied_today} minutesDone={today.minutes.done} minutesGoal={today.minutes.goal} learned={learned} mastered={mastered} />
        <LevelUpMoment on={features?.game_moments === true} proven={learned} />
        <GoalReachedMoment on={features?.game_moments === true} reached={today.minutes.reached === true} day={today.date} minutes={today.minutes.done} />
        <nav aria-label="Shortcuts" className="-mt-3 mb-6 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-muted-foreground lg:-mt-5 lg:mb-8">
          <Link href="/reviews" className="inline-flex items-center gap-1.5 underline-offset-4 hover:underline">
            {today.reviews_due ? <><StatusIcon status="review" size={16} />{today.reviews_due} review{today.reviews_due === 1 ? '' : 's'} due</> : 'Reviews'}
          </Link>
          <Link href="/notes" className="underline-offset-4 hover:underline">Notes</Link>
          <Link href="/courses" className="underline-offset-4 hover:underline">Courses</Link>
        </nav>
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

      <div className="grid grid-cols-12 gap-3 sm:gap-4 lg:gap-6">
        {/* 3. Nothing next: a short note in place of the stone that would say "Start". */}
        {!next ? (
          <Reveal index={1} className="col-span-12">
            <div role="status" className="paper flex flex-wrap items-center justify-between gap-3 rounded-card px-5 py-4">
              <span className="min-w-0">
                <span className="block font-display text-lg font-semibold tracking-[-0.02em]">{complete ? `${today.course.title} complete` : today.study_day ? 'Done for today' : 'Rest day'}</span>
                <span className="block text-sm text-muted-foreground">
                  {complete
                    ? today.finale?.graduated
                      ? `All ${today.progress.total} skills mastered: learned, then proven again after time away.`
                      : `All ${today.progress.total} skills learned. ${mastered} mastered so far; reviews prove the rest.`
                    : today.study_day
                      ? 'Everything planned for today is complete. Keep going from the path if you like.'
                      : 'Today is not one of your study days. You can work ahead from the path.'}
                </span>
              </span>
              {complete ? (
                <span className="flex flex-wrap gap-x-4 gap-y-1 text-sm font-semibold">
                  <Link href="/progress" className="underline underline-offset-4">See your evidence</Link>
                  <Link href="/assessments" className="underline underline-offset-4">{NAME.assessment}</Link>
                  {today.finale?.capstone ? <Link href="/projects" className="underline underline-offset-4">Capstone: {today.finale.capstone.title}</Link> : null}
                  {today.finale?.next_course ? <Link href={`/start?course=${today.finale.next_course.id}&next=1`} className="underline underline-offset-4">Start {today.finale.next_course.title}</Link> : null}
                </span>
              ) : null}
            </div>
          </Reveal>
        ) : null}

        {/* 4. Needs you: only things that are due or open, one line each. */}
        {review || today.reviews_due || assessmentOpen ? (
          <Reveal index={3} className="col-span-12 grid gap-3 sm:grid-cols-2 sm:gap-4 lg:gap-6">
            {review || today.reviews_due ? (
              <Link href={review ? activityHref(review.id) : '/plan'} className="group flex min-h-20 items-center gap-4 rounded-card bg-cream p-4 text-cream-foreground transition-[background-color,transform] duration-200 hover:-translate-y-0.5 hover:bg-[color-mix(in_srgb,var(--cream),var(--foreground)_4%)] lg:p-5">
                <StatusIcon status="review" size={32} />
                <span className="min-w-0 flex-1">
                  <span className="block font-display text-lg leading-tight font-semibold tracking-[-0.02em]">Review due{review ? `: ${review.title.replace(/^Review:?\s*/i, '')}` : ''}</span>
                  {today.reviews_due > 1 ? <span className="mt-0.5 block text-sm text-muted-foreground">{today.reviews_due} reviews due</span> : null}
                </span>
                <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </Link>
            ) : null}
            {assessmentOpen ? (
              <Link href="/assessments" className="group flex min-h-20 items-center gap-4 rounded-card border bg-card p-4 transition-transform duration-200 hover:-translate-y-0.5 lg:p-5" aria-label={`${NAME.assessment}: ${assessment.state === 'in_progress' ? 'continue' : 'open'}`}>
                <span className="min-w-0 flex-1">
                  <span className="mb-1 block"><Badge>{assessment.state === 'in_progress' ? 'In progress' : 'Available'}</Badge></span>
                  <span className="block font-display text-lg leading-tight font-semibold tracking-[-0.02em]">{NAME.assessment}</span>
                  <span className="block truncate text-sm text-muted-foreground">On what you studied: {assessment.topics.slice(0, 3).join(', ')}{assessment.topics.length > 3 ? ', and more' : ''}</span>
                </span>
                <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </Link>
            ) : null}
          </Reveal>
        ) : null}

        {/* A course whose first lesson is still being written: say so here, where the learner
            now waits after onboarding, and open the draft the moment there is one. */}
        {firstWriting ? (
          <div className="col-span-12">
            <Link
              href={conceptHref(firstWriting.concept)}
              role="status"
              aria-live="polite"
              className={cn('paper flex items-center justify-between gap-3 rounded-card px-5 py-4 transition-transform duration-200', firstWriting.draft && 'hover:-translate-y-0.5')}
              onClick={e => { if (!firstWriting.draft) e.preventDefault(); }}
              aria-disabled={!firstWriting.draft}
            >
              <span className="grid gap-0.5">
                <span className="font-display text-lg font-semibold tracking-[-0.02em]">
                  {firstWriting.draft ? 'Your first lesson is ready to read' : 'Your first lesson is being written for you'}
                </span>
                <span className="text-sm text-muted-foreground">
                  {firstWriting.draft
                    ? `${firstWriting.title}: a draft, still being checked. Its questions follow when the checks pass.`
                    : `${firstWriting.title}: ${firstWriting.label.toLowerCase()}${firstWriting.state === 'writing' ? ` (${Math.round(firstWriting.progress * 100)}%)` : ''}. Usually under three minutes.`}
                </span>
              </span>
              {firstWriting.draft ? <span className="flex flex-none items-center gap-1 font-semibold">Read it <ArrowRight className="size-5" aria-hidden="true" /></span> : <Ring value={Math.round(firstWriting.progress * 100)} label={`${Math.round(firstWriting.progress * 100)}%`} size={48} ariaLabel="Writing progress" />}
            </Link>
          </div>
        ) : null}

        {/* 5. Everything else, one section at a time. */}
        <Reveal index={4} className="col-span-12">
          <Tabs value={active} onValueChange={pick} className="gap-5">
            <TabsList className="w-full justify-start sm:w-fit" aria-label="Sections of today">
              {tabs.map(t => (
                <TabsTrigger key={t.id} value={t.id} className="flex-none px-4 sm:px-5">
                  {t.label}
                  {t.hint ? <span className="text-[13px] font-semibold text-muted-foreground tabular-nums">{t.hint}</span> : null}
                </TabsTrigger>
              ))}
            </TabsList>

            {/* Session: what today holds, in order, and why the plan looks like this. */}
            <TabsContent value="session" className="grid gap-3 sm:gap-4 lg:grid-cols-12 lg:gap-6">
              <div className="grid content-start gap-3 sm:gap-4 lg:col-span-7 lg:gap-6">
                {session.length ? (
                  <Card aria-labelledby="agenda-heading">
                    <div className="flex items-baseline justify-between gap-3 px-(--card-spacing)">
                      <h2 id="agenda-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">Today&apos;s session</h2>
                      <span className="text-sm font-semibold text-muted-foreground tabular-nums">{today.done.length ? `${today.done.length} of ${session.length} done` : `${session.length} step${session.length === 1 ? '' : 's'}, in order`}</span>
                    </div>
                    <ul className="grid px-[calc(var(--card-spacing)-12px)]">
                      {session.map(({ a, done }) => (
                        <SessionRow
                          key={a.id}
                          activity={a}
                          done={done}
                          onLater={a.kind === 'review' && a.concept ? () => api.post(`/reviews/${a.concept}/snooze`, { days: 3 }).then(load).catch(() => undefined) : undefined}
                        />
                      ))}
                    </ul>
                  </Card>
                ) : (
                  <p className="rounded-card border border-dashed px-5 py-6 text-[15px] text-muted-foreground">Nothing else is planned for today.</p>
                )}
              </div>
              <div className="grid content-start gap-3 sm:gap-4 lg:col-span-5 lg:gap-6">
                <AdaptingCard today={today} onDecided={load} onAsk={() => setAskSoc(n => n + 1)} />
              </div>
            </TabsContent>

            {/* The path: the whole course on one canvas, lessons being written ringed with their progress. */}
            {pathModules.length ? (
              <TabsContent value="map">
                <h2 className="sr-only">Your path</h2>
                <CoursePath modules={pathModules} startLabel={next ? (VERB[next.kind] ?? 'Start') : 'Start'} />
              </TabsContent>
            ) : null}

            {/* Practice: sets written for the course, and the Playground. */}
            <TabsContent value="practice" className="grid gap-3 sm:gap-4 lg:grid-cols-12 lg:gap-6">
              <div className="grid min-w-0 content-start gap-4 lg:col-span-8">
                <Link href="/studio" className="paper group flex flex-col gap-2 rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6">
                  <span className="type-label text-brand">{NAME.practice}</span>
                  <span className="flex items-end justify-between gap-3">
                    <span className="grid gap-1">
                      <span className="font-display text-xl font-semibold tracking-[-0.03em]">Practise what you have learned</span>
                      <span className="text-[15px] text-muted-foreground">Fresh questions written for your course, on any topic you have opened.</span>
                    </span>
                    <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                  </span>
                </Link>
              </div>
              <div className="lg:col-span-4">
                <Link href="/playground" className="paper doodle-host group relative flex min-h-40 flex-col justify-between gap-3 overflow-hidden rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6">
                  <span className="type-label text-brand">{NAME.playground}</span>
                  <Illustration name="orbit" className="pointer-events-none absolute -top-3 -right-3 size-24 opacity-90" />
                  <span className="flex items-end justify-between gap-3">
                    <span className="font-display text-lg leading-tight font-semibold tracking-[-0.02em]">Ask about any concept</span>
                    <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                  </span>
                </Link>
              </div>
            </TabsContent>

            {/* Progress: the streak, the course, and the way to the full evidence. */}
            <TabsContent value="progress" className="grid gap-3 sm:gap-4 lg:grid-cols-3 lg:gap-6">
              <Card aria-labelledby="week-heading">
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
                  {features?.streak_plus ? <StreakExtras streak={today.streak} /> : null}
                </div>
              </Card>

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

              <Link href="/progress" className="paper group flex items-center gap-4 rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6">
                <StatusIcon status="mastered" size={48} />
                <span className="font-display text-6xl leading-none font-semibold tracking-[-0.04em] tabular-nums">{learned}</span>
                <span className="min-w-0 flex-1">
                  <span className="block font-display text-xl leading-tight font-semibold tracking-[-0.02em]">{learned === 1 ? 'skill' : 'skills'} learned</span>
                  <span className="block text-[13px] text-muted-foreground">{mastered} mastered after review{today.progress.assumed ? `, ${today.progress.assumed} to confirm` : ''}</span>
                  <span className="mt-1 block text-[13px] font-semibold underline underline-offset-4">Open {NAME.evidence}</span>
                </span>
                <ChevronRight className="size-5 flex-none text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </Link>
            </TabsContent>
          </Tabs>
        </Reveal>
      </div>
      {features?.learning_requests ? (
        <Link
          href="/start"
          className="mt-6 flex min-h-14 items-center justify-between gap-4 rounded-[4px] border bg-card px-5 py-4 transition-colors hover:bg-raised"
        >
          <span>
            <span className="block font-semibold">{t('today.build.title')}</span>
            <span className="block text-sm text-muted-foreground">{t('today.build.body')}</span>
          </span>
          <span aria-hidden="true">→</span>
        </Link>
      ) : null}
      <CommunityCard className="mt-6" />
      <Assistant scope="general" title="Ask Soc" openSignal={askSoc} />
    </Page>
  );
}
