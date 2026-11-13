'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, ChevronRight, Flame } from '@/components/icons';
import { api, explain, PAGE_MS } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { KIND_LABEL, NAME, PACE_LABEL, activityHref, conceptHref, formatDate } from '@/lib/routes';
import type { Activity, AssessmentStatus, PlanView, Recommendations, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, Reveal, Ring } from '@/components/common';
import { Level, PlatformTag, ProblemName } from '@/components/practice';
import { AdaptingCard } from '@/components/socrat/adapting';
import { ReasonChip } from '@/components/socrat/reason-chip';
import { Illustration, Soc } from '@/components/socrat/illustration';
import { SocFigure } from '@/components/socrat/soc';
import { StatusIcon, statusFromBand, statusFromRoadmap } from '@/components/socrat/status';
import { SkillGrid } from '@/components/socrat/skill-grid';
import { usePlanLocks } from '@/lib/plan-locks';
import { WeekStrip } from '@/components/socrat/week-strip';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { CommunityCard } from '@/components/community-link';
import { LaunchGift } from '@/components/launch-gift-host';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Decorations from the large sticker and doodle catalogues load on their own, after the page.
const Doodle = dynamic(() => import('@/components/ui/doodle').then(m => m.Doodle), { ssr: false });
const Sticker = dynamic(() => import('@/components/ui/sticker').then(m => m.Sticker), { ssr: false });

// The chat loads on demand, as on the problem page: it opens only when asked, and its code
// otherwise sits in Today's first load. An early openSignal still opens it once it arrives.
const Assistant = dynamic(() => import('@/components/assistant'), { ssr: false });

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
  return { title: module.title, finished, total: module.concepts.length, concepts: module.concepts, current: plan.current_concept };
}

/** Progress with a solid fill that grows in once on load (no gradients, per the design system). */
function GrowBar({ value, label }: { value: number; label: string }) {
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(frame);
  }, []);
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value)} className="h-2.5 flex-1 overflow-hidden rounded-full bg-raised">
      <div className="h-full rounded-full bg-primary transition-[width] duration-700 ease-[var(--ease-soft)]" style={{ width: drawn ? `${Math.max(2, Math.min(100, value))}%` : '0%' }} />
    </div>
  );
}

function SessionRow({ activity, done }: { activity: Activity; done: boolean }) {
  return (
    <li>
      <Link href={activityHref(activity.id)} className="group flex min-h-14 items-center gap-3 rounded-[4px] px-3 py-2 transition-colors hover:bg-raised">
        <StatusIcon status={done ? 'practised' : 'not_seen'} size={22} />
        <span className="min-w-0 flex-1">
          <span className={cn('block font-semibold', done && 'text-muted-foreground')}>{activity.title}</span>
          <span className="text-[13px] text-muted-foreground">{KIND_LABEL[activity.kind]}{activity.minutes ? `, ${activity.minutes} min` : ''}{done ? ', done' : ''}</span>
        </span>
        {!done ? <ReasonChip code={activity.code} className="hidden sm:inline-flex" /> : null}
        {!done ? <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" /> : null}
      </Link>
    </li>
  );
}

const TABS = ['session', 'map', 'practice', 'progress'] as const;
type TabId = (typeof TABS)[number];

/** A small headline number with a caption, for the compact status line. */
function Pill({ children }: { children: React.ReactNode }) {
  return <li className="inline-flex min-h-9 items-center gap-1.5 rounded-full border bg-card px-3.5 text-sm font-medium">{children}</li>;
}

export default function TodayPage() {
  const allowed = useGuard('active');
  const planLocked = usePlanLocks();
  const { profile } = useSession();
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState('');
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [assessment, setAssessment] = useState<AssessmentStatus | null>(null);
  const [askSoc, setAskSoc] = useState(0);
  const [tab, setTab] = useState<TabId>('session');

  const load = useCallback(() => {
    setError('');
    api.cached<Today>('/today', PAGE_MS).then(setToday).catch(e => setError(explain(e)));
    api.cached<Recommendations>('/library/recommendations?limit=4', PAGE_MS).then(setRecs).catch(() => undefined);
    api.cached<PlanView>('/plan', PAGE_MS).then(setPlan).catch(() => undefined);
    api.cached<{ current: AssessmentStatus }>('/assessments', PAGE_MS).then(r => setAssessment(r.current)).catch(() => undefined);
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

  if (!allowed || (!today && !error)) return <Loading label="Loading today" />;
  if (!today) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const name = profile?.display_name || today.greeting.split(', ').slice(1).join(', ') || 'there';
  const minutePercent = today.minutes.goal ? Math.min(100, (100 * today.minutes.done) / today.minutes.goal) : 0;
  const next = today.next;
  const review = today.queue.find(a => a.kind === 'review');
  const weak = recs?.topics.find(t => t.band === 'needs_practice');
  const goal = milestone(plan, today.current_module);
  const goalPercent = goal && goal.total ? (100 * goal.finished) / goal.total : 0;
  const learned = today.progress.finished;
  const mastered = today.progress.mastered ?? 0;
  const complete = today.progress.complete === true;
  // Soc's mood on the next-step card: sleepy after days away, a wink on a new day, proud once the goal is reached.
  const heroMood = today.days_away >= 3 ? 'sleepy' : today.minutes.reached ? 'proud' : today.done.length === 0 ? 'wink' : 'happy';
  const assessmentOpen = assessment && (assessment.state === 'available' || assessment.state === 'in_progress');
  const queue = next ? [...today.queue].sort((x, y) => Number(y.id === next.id) - Number(x.id === next.id)) : today.queue;
  const session = [...today.done.map(a => ({ a, done: true })), ...queue.map(a => ({ a, done: false }))];
  // A learner who has not started sees a plan, not a column of zeros.
  const fresh = today.streak.current === 0 && today.done.length === 0 && today.progress.finished === 0 && today.streak.week_minutes === 0;
  const active: TabId = tab === 'map' && !goal ? 'session' : tab;
  const practiceCount = (recs?.problems.length ?? 0) + (recs?.topics.length ?? 0);

  // Each tab names what is inside it, so nothing is a mystery click.
  const tabs: { id: TabId; label: string; hint: string }[] = [
    { id: 'session', label: 'Session', hint: session.length ? (today.done.length ? `${today.done.length}/${session.length}` : `${session.length}`) : '' },
    ...(goal ? [{ id: 'map' as const, label: 'Skill map', hint: `${goal.finished}/${goal.total}` }] : []),
    { id: 'practice', label: 'Practice', hint: practiceCount ? String(practiceCount) : '' },
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
        <ul className="-mt-2 mb-6 flex flex-wrap gap-2 lg:-mt-4 lg:mb-8" aria-label="Today at a glance">
          <Pill><Flame className="size-4" strokeWidth={1.5} aria-hidden="true" />{fresh ? 'Start your streak today' : `${today.streak.current}-day streak`}</Pill>
          <Pill><span className="tabular-nums">{today.minutes.done} of {today.minutes.goal} min today</span></Pill>
          {today.reviews_due ? <Pill><StatusIcon status="review" size={16} /> {today.reviews_due} review{today.reviews_due === 1 ? '' : 's'} due</Pill> : null}
        </ul>
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
        {/* 3. Hero: the next recommended activity. */}
        <Reveal index={1} className="col-span-12 lg:col-span-8">
          {next ? (
            <Card tone="hero" tape="corner" seed="today-next" data-tour="today-next" className="relative h-full min-h-72 lg:min-h-80" aria-labelledby="next-heading">
              {/* Soc on his books, waving the next step on, with a note pointing at him. */}
              <div aria-hidden="true" className="pointer-events-none absolute right-4 -bottom-3 hidden w-[170px] sm:block lg:w-[190px] xl:right-6 xl:w-[220px] 2xl:right-12 2xl:w-[250px]">
                <div className="absolute -top-14 -left-6 flex items-end gap-0 xl:-top-16 xl:-left-24">
                  <span className="font-script text-[22px] whitespace-nowrap text-red -rotate-6 xl:text-[24px]">you&apos;ve got this</span>
                  <Doodle name="arrow-bounce" size={44} rotate={70} seed="today-arrow" className="-mb-6 -scale-x-100" />
                </div>
                <SocFigure books mood={heroMood} still className="h-auto w-full" />
              </div>
              <div aria-hidden="true" className="pointer-events-none absolute right-5 bottom-2 sm:hidden">
                <SocFigure size={84} mood={heroMood === 'happy' ? 'curious' : heroMood} still />
              </div>
              <Sticker name="highlighter" size={56} rotate={-14} seed="today-hl" className="absolute -top-6 right-8 hidden sm:block xl:right-14" />
              <div className="relative flex h-full flex-col gap-5 px-(--card-spacing) sm:max-w-[60%] xl:max-w-[54%]">
                <p className="type-label text-(--card-muted)">{today.minutes.reached ? `Daily goal reached. Keep going or stop here.` : `Today, goal ${today.minutes.goal} min`}</p>
                <div>
                  <h2 id="next-heading" className="type-display-m max-w-[20ch] break-words">{next.title}</h2>
                  <p className="mt-3 max-w-md text-base text-(--card-muted)">{next.reason || 'Next in your plan.'}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{CHIP[next.kind] ?? KIND_LABEL[next.kind]}</Badge>
                  {next.minutes ? <Badge variant="outline">{next.minutes} min</Badge> : null}
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
            <Card tone="hero" data-tour="today-next" className="relative" aria-labelledby="next-heading">
              <div aria-hidden="true" className="pointer-events-none absolute right-8 -bottom-3 hidden w-[200px] sm:block">
                <SocFigure books mood={today.study_day ? 'proud' : 'sleepy'} still className="h-auto w-full" />
              </div>
              <div className="relative flex flex-col gap-4 px-(--card-spacing) sm:max-w-[60%]">
                <h2 id="next-heading" className="type-display-m">{complete ? `${today.course.title} complete` : today.study_day ? 'Done for today' : 'Rest day'}</h2>
                <p className="max-w-md text-(--card-muted)">
                  {complete
                    ? today.finale?.graduated
                      ? `All ${today.progress.total} skills mastered: learned, then proven again after time away.`
                      : `All ${today.progress.total} skills learned, each proven by a check. ${mastered} mastered so far; reviews over the coming weeks prove the other ${today.finale?.to_master ?? today.progress.total - mastered}.`
                    : today.study_day
                      ? 'Everything planned for today is complete. You can keep going from your plan.'
                      : 'Today is not one of your study days. You can work ahead from your plan.'}
                </p>
                <div className="flex flex-wrap gap-3">
                  {complete ? <Button asChild variant="ink" size="lg"><Link href="/progress">See your evidence<ArrowCircle /></Link></Button> : <Button asChild variant="ink" size="lg"><Link href="/plan">Open {NAME.skills}<ArrowCircle /></Link></Button>}
                  {complete ? <Button asChild variant="outline" size="lg"><Link href="/assessments">{NAME.assessment}</Link></Button> : null}
                  {complete && today.finale?.next_course ? <Button asChild variant="outline" size="lg"><Link href={`/start?course=${today.finale.next_course.id}&next=1`}>Start {today.finale.next_course.title}</Link></Button> : null}
                </div>
                {complete && today.finale?.capstone ? (
                  <div className="flex flex-col gap-1">
                    <p className="text-sm font-medium">Your capstone: {today.finale.capstone.title}</p>
                    <p className="text-sm text-(--card-muted)">{today.finale.capstone.summary}</p>
                    <Link href="/projects" className="text-sm underline underline-offset-4">
                      {today.finale.capstone.done === 0 ? 'Start the capstone' : today.finale.capstone.done === today.finale.capstone.total ? 'Capstone complete: review it' : `Continue the capstone (${today.finale.capstone.done} of ${today.finale.capstone.total} milestones)`}
                    </Link>
                  </div>
                ) : null}
                {complete && today.finale?.challenges.length ? (
                  <div className="flex flex-col gap-2">
                    <p className="text-sm font-medium">Still unsolved: the hardest problems in this course</p>
                    <ul className="flex flex-col gap-1">
                      {today.finale.challenges.map(p => (
                        <li key={p.id}><Link href={`/problems/${p.id}`} className="text-sm underline underline-offset-4">{p.title}</Link> <span className="text-xs text-(--card-muted)">{p.difficulty}</span></li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            </Card>
          )}
        </Reveal>

        {/* Talk to your tutor: beside the hero (8 + 4 columns). */}
        <Reveal index={2} className="col-span-12 hidden lg:col-span-4 lg:block">
          <Card tone="raised" tape="top" seed="today-ask" className="relative h-full min-h-72 lg:min-h-80" aria-labelledby="soc-heading">
            <div className="relative flex h-full flex-col gap-4 px-(--card-spacing)">
              <p className="font-script origin-left -rotate-2 text-[24px] text-red">stuck? talk to me</p>
              <div className="max-w-[55%]">
                <h2 id="soc-heading" className="type-display-m">Ask Soc</h2>
                <p className="mt-3 text-base text-muted-foreground">Get unstuck, ask questions, or request a hint.</p>
              </div>
              {/* A bigger target for pointer users; keyboard users have the Ask Soc button below. */}
              <button type="button" tabIndex={-1} aria-hidden="true" onClick={() => setAskSoc(n => n + 1)} className="absolute top-12 right-(--card-spacing) rounded-full">
                <Soc size={84} mood="curious" />
              </button>
              <Button type="button" variant="outline" size="lg" data-tour="tutor" onClick={() => setAskSoc(n => n + 1)} className="mt-auto w-full justify-between" aria-haspopup="dialog">
                Ask Soc
                <ArrowCircle />
              </Button>
            </div>
          </Card>
        </Reveal>

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
                      {session.map(({ a, done }) => <SessionRow key={a.id} activity={a} done={done} />)}
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

            {/* Skill map: where you are in the current module. */}
            {goal ? (
              <TabsContent value="map">
                <Card aria-labelledby="map-heading">
                  <div className="grid gap-5 px-(--card-spacing)">
                    <div className="flex flex-wrap items-end justify-between gap-3">
                      <div>
                        <p className="type-label text-muted-foreground">Next milestone</p>
                        <h2 id="map-heading" className="font-display text-2xl leading-tight font-semibold tracking-[-0.03em]">{goal.title}</h2>
                      </div>
                      <p className="text-[15px] text-muted-foreground">
                        {goal.total - goal.finished > 0 ? `${goal.total - goal.finished} more skill${goal.total - goal.finished === 1 ? '' : 's'} to reach it.` : 'Milestone reached. The next module is opening up.'}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <GrowBar value={goalPercent} label={`${goal.title}: ${goal.finished} of ${goal.total} skills`} />
                      <span className="text-sm font-semibold text-muted-foreground tabular-nums">{Math.round(goalPercent)}%</span>
                    </div>
                    <SkillGrid
                      label={goal.title}
                      nodes={goal.concepts.map(c => ({ id: c.concept, title: c.title, href: conceptHref(c.concept), status: planLocked(c.concept) ? 'locked' : statusFromRoadmap(c), current: c.concept === goal.current, reviewDue: c.review_due }))}
                    />
                  </div>
                </Card>
              </TabsContent>
            ) : null}

            {/* Practice: problems picked for you, skills worth learning, and the Playground. */}
            <TabsContent value="practice" className="grid gap-3 sm:gap-4 lg:grid-cols-12 lg:gap-6">
              <div className="grid min-w-0 content-start gap-4 lg:col-span-8">
                {recs?.problems.length ? (
                  <section aria-labelledby="practice-heading" className="min-w-0">
                    <div className="mb-3 flex items-baseline justify-between gap-3">
                      <h2 id="practice-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Practice picked for you</h2>
                      <Link href="/library" className="text-[15px] font-semibold underline underline-offset-4">See all problems</Link>
                    </div>
                    <ul className="grid gap-3 sm:grid-cols-2">
                      {recs.problems.map(p => (
                        <li key={p.id} className="flex flex-col gap-3 paper rounded-card p-5">
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
                ) : (
                  <p className="rounded-card border border-dashed px-5 py-6 text-[15px] text-muted-foreground">Practice picks appear here once you have studied a skill.</p>
                )}
                {recs?.topics.length ? (
                  <Card aria-labelledby="learn-next-heading">
                    <div className="px-(--card-spacing)">
                      <h2 id="learn-next-heading" className="mb-3 font-display text-lg font-semibold tracking-[-0.02em]">Skills to learn next</h2>
                      <ul className="grid gap-1 sm:grid-cols-2">
                        {recs.topics.map(t => (
                          <li key={t.id}>
                            <Link href={conceptHref(t.id)} className="-mx-2 flex min-h-12 items-start gap-3 rounded-[4px] px-2 py-2 transition-colors hover:bg-raised">
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
              </div>
              <div className="lg:col-span-4">
                <Link href="/playground" className="paper doodle-host group relative flex min-h-40 flex-col justify-between gap-3 overflow-hidden rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6">
                  <span className="type-label text-brand">{NAME.playground}</span>
                  <Illustration name="orbit" className="pointer-events-none absolute -top-3 -right-3 size-24 opacity-90" />
                  <span className="flex items-end justify-between gap-3">
                    <span className="font-display text-lg leading-tight font-semibold tracking-[-0.02em]">{weak ? `Explore ${weak.title} visually` : 'Ask about any concept'}</span>
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
      <CommunityCard className="mt-6" />
      <Assistant scope="general" title="Ask Soc" openSignal={askSoc} />
      <LaunchGift />
    </Page>
  );
}
