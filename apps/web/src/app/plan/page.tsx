'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, MessageCircle } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { KIND_LABEL, NAME, PACE_LABEL, STYLE_LABEL, activityHref, conceptHref, formatDate, formatStamp, hours } from '@/lib/routes';
import type { PlanView, RoadmapItem } from '@/lib/types';
import { Milestones, PathStyles, WeeklyReviewPanel } from '@/components/socrat/plan-adaptive';
import { ProposalList } from '@/components/socrat/proposals';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, Reveal } from '@/components/common';
import { LockedState } from '@/components/socrat/states';
import { NodeMap } from '@/components/socrat/node-map';
import { usePlanLocks } from '@/lib/plan-locks';
import { StatusLabel, StatusLegend, statusFromRoadmap } from '@/components/socrat/status';
import { Badge } from '@/components/ui/badge';
import { Soc } from '@/components/socrat/illustration';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ReasonChip } from '@/components/socrat/reason-chip';

const Assistant = dynamic(() => import('@/components/assistant'), { ssr: false });

const FINISHED = ['mastered', 'practiced'];
const FOCUS_LABEL = { foundations: 'programming foundations', interview: 'coding interviews', contest: 'contests' } as const;

/** Learner-owned changes to one concept, each with a way to take it back. */
function OverrideBadges({ item, undo }: { item: RoadmapItem; undo: (kind: string, concept: string) => void }) {
  const chips: { label: string; kind?: string }[] = [];
  if (item.status === 'optional') chips.push({ label: 'Optional for your goal' });
  if (item.status === 'skipped') chips.push({ label: 'Dropped', kind: 'skip' });
  if (item.priority) chips.push({ label: 'Focus', kind: 'prioritize' });
  if (item.deferred) chips.push({ label: 'Set aside', kind: 'defer' });
  return (
    <>
      {chips.map(c => (
        <span key={c.label} className="inline-flex items-center gap-1">
          <Badge variant="secondary">{c.label}</Badge>
          {c.kind ? (
            <button
              type="button"
              className="text-[13px] font-semibold underline underline-offset-4"
              onClick={e => { e.preventDefault(); undo(c.kind!, item.concept); }}
            >
              Undo<span className="sr-only"> {c.label.toLowerCase()} for {item.title}</span>
            </button>
          ) : null}
        </span>
      ))}
    </>
  );
}

/** A native disclosure styled as a card section; keyboard accessible by default. */
function Disclosure({ id, title, children, defaultOpen = false }: { id: string; title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  return (
    <details className="group paper rounded-card" open={defaultOpen} aria-labelledby={id}>
      <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 lg:px-6 [&::-webkit-details-marker]:hidden">
        <h2 id={id} className="font-display text-lg font-semibold tracking-[-0.02em]">{title}</h2>
        <ChevronDown className="size-5 flex-none transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="px-5 pb-5 lg:px-6 lg:pb-6">{children}</div>
    </details>
  );
}

export default function PlanPage() {
  const allowed = useGuard('active');
  const planLocked = usePlanLocks();
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [error, setError] = useState('');
  const [unlocked, setUnlocked] = useState<Set<string>>(new Set());
  const [planChat, setPlanChat] = useState(0);

  // Remember which modules were locked; one that opened since the last visit draws its outline once.
  useEffect(() => {
    if (!plan) return;
    const key = 'socrat:locked-modules';
    const locked = plan.modules.filter(m => m.locked_by).map(m => m.id);
    let before: string[] = [];
    try { before = JSON.parse(localStorage.getItem(key) ?? '[]') as string[]; } catch { /* per-viewer nicety only */ }
    const opened = before.filter(id => plan.modules.some(m => m.id === id && !m.locked_by));
    setUnlocked(new Set(opened));
    const save = setTimeout(() => {
      try { localStorage.setItem(key, JSON.stringify(locked)); } catch { /* ignore */ }
    }, opened.length ? 3000 : 0);
    return () => clearTimeout(save);
  }, [plan]);

  const load = useCallback(() => {
    setError('');
    api.get<PlanView>('/plan').then(setPlan).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  const undo = useCallback((kind: string, concept: string) => {
    api.post('/adaptive/overrides/undo', { kind, concept }).then(load).catch(e => setError(explain(e)));
  }, [load]);

  if (!allowed || (!plan && !error)) return <Loading label="Loading your skills" />;
  if (!plan) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const current = plan.modules.find(m => m.id === plan.current_module) ?? plan.modules.find(m => m.concepts.some(c => c.concept === plan.current_concept)) ?? plan.modules[0];
  const currentDone = current ? current.concepts.filter(c => FINISHED.includes(c.status)).length : 0;
  const guides = plan.modules.flatMap(m => m.concepts).filter(c => c.status !== 'locked' && c.roadmap_resources?.length);
  // The next checkpoint stays in view: the first locked module starts open.
  const firstLocked = plan.modules.find(m => m.locked_by)?.id;
  const pending = plan.proposals.pending;
  const behind = plan.forecast.on_track === false;
  const deadlineOptions = pending.some(p => p.group.startsWith('deadline'));
  const stretch = plan.proposals.overrides.stretch;

  return (
    <Page wide>
      <Reveal>
        <header className="mb-8">
          <p className="font-hand mb-2 origin-left -rotate-2 text-[22px] text-pen">{NAME.skills}</p>
          <h1 className="type-display-l">Your <span className="hl hl-draw">skills</span></h1>
          <p className="mt-3 max-w-2xl text-base text-muted-foreground">
            Your roadmap for {FOCUS_LABEL[plan.focus]}, on the {STYLE_LABEL[plan.style]} path. It adapts to your results, and Socrat asks before changing it.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setPlanChat(n => n + 1)}><MessageCircle data-icon="inline-start" /> Plan with Soc</Button>
            <Button asChild variant="outline"><Link href="/graph">Skill graph</Link></Button>
          </div>
        </header>
      </Reveal>

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="grid min-w-0 content-start gap-4 lg:col-span-8 lg:gap-6">
          {pending.length ? (
            <Card id="proposals" aria-labelledby="proposals-heading">
              <div className="grid gap-3 px-(--card-spacing)">
                <div>
                  <h2 id="proposals-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Socrat suggests</h2>
                  <p className="mt-1 text-[15px] text-muted-foreground">Based on how you&apos;re doing. Nothing changes unless you accept.</p>
                </div>
                <ProposalList proposals={pending} onDecided={load} />
              </div>
            </Card>
          ) : null}

          {/* Hero: the current module. */}
          {current ? (
            <Reveal index={1}>
              <Card tone="hero" data-tour="skills-current" className="relative" aria-labelledby="module-heading">
                <Soc size={176} mood="proud" className="pointer-events-none absolute top-1/2 right-8 hidden -translate-y-1/2 lg:block" />
                <div className="relative grid gap-5 px-(--card-spacing) lg:max-w-[62%]">
                  <p className="type-label text-(--card-muted)">Current module{current.bridge ? `, bridge from ${current.course}` : ''}</p>
                  <h2 id="module-heading" className="type-display-m break-words">{current.title}</h2>
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                    <div><dt className="text-sm text-(--card-muted)">Skills done</dt><dd className="type-display-m tabular-nums">{currentDone}/{current.concepts.length}</dd></div>
                    <div><dt className="text-sm text-(--card-muted)">Study left</dt><dd className="font-display text-2xl font-semibold tracking-[-0.03em] tabular-nums">{hours(plan.remaining_minutes)}</dd></div>
                    <div className="col-span-2 sm:col-span-1"><dt className="text-sm text-(--card-muted)">Likely finish</dt><dd className="font-display text-2xl font-semibold tracking-[-0.03em]" data-visual-mask="">{formatDate(plan.forecast.realistic_finish, { month: 'short', day: 'numeric', year: 'numeric' })}</dd></div>
                  </dl>
                  <p className="max-w-lg text-[15px] text-(--card-muted)">{PACE_LABEL[plan.pace]} pace. {plan.pace_reason}</p>
                  {plan.forecast.adherence < 0.95 ? (
                    <p className="max-w-lg text-[15px] text-(--card-muted)">
                      Based on your real rhythm (about {Math.round(plan.forecast.adherence * 100)}% of planned time). At full schedule: {formatDate(plan.forecast.planned_finish)}.
                    </p>
                  ) : null}
                  {plan.target_date ? (
                    <div><Badge>{plan.on_track ? 'On track for' : 'Behind your target of'} {formatDate(plan.target_date)}</Badge></div>
                  ) : null}
                </div>
              </Card>
            </Reveal>
          ) : null}
          {plan.target_date && behind ? (
            <p className="text-[15px]">
              {deadlineOptions
                ? 'To reach your target, pick one of the options Socrat suggests above.'
                : <>To reach your target, add a study day or more minutes per day in <Link href="/settings" className="font-semibold underline underline-offset-4">{NAME.settings}</Link>.</>}
            </p>
          ) : null}

          {/* Skill map of the current module, with an equivalent list. */}
          {current ? (
            <Card aria-labelledby="map-heading">
              <div className="px-(--card-spacing)">
                <h2 id="map-heading" className="mb-3 font-display text-xl font-semibold tracking-[-0.03em]">Skill map: {current.title}</h2>
                <NodeMap
                  label={current.title}
                  nodes={current.concepts.map(c => ({ id: c.concept, title: c.title, href: conceptHref(c.concept), status: planLocked(c.concept) ? 'locked' : statusFromRoadmap(c), current: c.concept === plan.current_concept, reviewDue: c.review_due }))}
                />
              </div>
            </Card>
          ) : null}

          {/* All modules, expandable. */}
          <section aria-labelledby="roadmap-heading" className="grid gap-4 lg:gap-6">
            <div>
              <h2 id="roadmap-heading" className="font-display text-2xl font-semibold tracking-[-0.03em]">Modules</h2>
              <p className="mt-1 text-[15px] text-muted-foreground">Your course and its foundation modules, updated from your learning evidence.</p>
            </div>
            {plan.modules.map((module, mi) => {
              const done = module.concepts.filter(c => FINISHED.includes(c.status)).length;
              const isCurrent = module.id === current?.id;
              return (
                <Reveal key={module.id} index={mi + 2}>
                  <details className={cn('group paper rounded-card', unlocked.has(module.id) && 'animate-unlock')} open={isCurrent || unlocked.has(module.id) || module.id === firstLocked}>
                    <summary className="flex min-h-16 cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 lg:px-6 [&::-webkit-details-marker]:hidden">
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="font-display text-lg font-semibold tracking-[-0.02em]">{module.title}</span>
                          {isCurrent ? <Badge>Current</Badge> : null}
                          {unlocked.has(module.id) ? <Badge>Unlocked</Badge> : null}
                          {module.locked_by ? <StatusLabel status="locked" muted className="text-[13px]" /> : null}
                        </span>
                        <span className="mt-0.5 block text-sm text-muted-foreground">{module.bridge ? `Bridge from ${module.course}. ` : ''}{module.summary}</span>
                      </span>
                      <span className="flex items-center gap-3 text-sm font-semibold tabular-nums">
                        {done} of {module.concepts.length}
                        <ChevronDown className="size-5 transition-transform group-open:rotate-180" aria-hidden="true" />
                      </span>
                      <Progress value={module.concepts.length ? (100 * done) / module.concepts.length : 0} className="basis-full" aria-label={`${module.title}: ${done} of ${module.concepts.length} skills`} />
                    </summary>
                    <div className="grid gap-3 px-5 pb-5 lg:px-6 lg:pb-6">
                      {module.locked_by ? (
                        module.locked_by.needs_transfer ? (
                          <LockedState
                            title={`Locked until you prove a ${module.locked_by.module} skill`}
                            href={module.locked_by.transfer ? activityHref(module.locked_by.transfer) : '/today'}
                            action={module.locked_by.transfer ? 'Take the transfer check' : 'See Today'}
                          >
                            The checkpoint is passed. Solve one problem you have not seen, unaided, to open this module.{module.locked_by.transfer ? '' : ' Your next problem opens tomorrow.'}
                          </LockedState>
                        ) : (
                          <LockedState title={`Locked until ${module.locked_by.module}`} href={activityHref(module.locked_by.gate)}>
                            Already know this? Pass the {module.locked_by.module} checkpoint (up to 10 questions) to unlock it now.
                          </LockedState>
                        )
                      ) : null}
                      <ul className="grid gap-2">
                        {module.concepts.map(c => {
                          const byPlan = planLocked(c.concept);
                          const status = byPlan ? 'locked' : statusFromRoadmap(c);
                          const here = c.concept === plan.current_concept;
                          return (
                            <li key={c.concept}>
                              <Link href={conceptHref(c.concept)} transitionTypes={['nav-forward']} className={cn('flex flex-wrap items-center gap-x-4 gap-y-2 rounded-[20px] bg-raised px-4 py-3.5 transition-colors hover:bg-[color-mix(in_srgb,var(--raised),var(--foreground)_5%)]', here && 'ring-1 ring-primary')}>
                                <span className="min-w-0 flex-1 basis-48">
                                  <span className="font-semibold">{c.title}</span>
                                  {c.why ? <span className="block text-[13px] text-muted-foreground">{c.why}</span> : null}
                                </span>
                                <StatusLabel status={status} detail={byPlan ? 'Founding Member' : status === 'locked' && module.locked_by ? `Locked until ${module.locked_by.module}` : undefined} className="text-[13px]" />
                                <span className="flex flex-wrap gap-1.5">
                                  {here ? <Badge>Current</Badge> : null}
                                  {c.review_due ? <Badge>Review due</Badge> : null}
                                  {c.transfer === 'verified' ? <Badge variant="secondary">Transfer verified</Badge> : null}
                                  {c.lesson_done ? <Badge variant="secondary">Lesson read</Badge> : null}
                                  {c.quiz_done ? <Badge variant="secondary">Concept check done</Badge> : null}
                                  {c.reason_codes?.map(code => <ReasonChip key={code} code={code} />)}
                                  <OverrideBadges item={c} undo={undo} />
                                </span>
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  </details>
                </Reveal>
              );
            })}
          </section>

          <Card size="sm" aria-label="Status legend"><div className="px-(--card-spacing)"><StatusLegend only={['not_seen', 'read', 'assumed', 'practised', 'mastered', 'review', 'locked']} /></div></Card>
        </div>

        <aside className="grid min-w-0 content-start gap-4 lg:col-span-4 lg:gap-6">
          <div id="review">
            <Disclosure id="review-heading" title={plan.weekly_review_ready ? 'Your weekly review (new)' : 'Weekly review'} defaultOpen={plan.weekly_review_ready}>
              <WeeklyReviewPanel onChanged={load} />
            </Disclosure>
          </div>
          <Disclosure id="milestones-heading" title="Weekly milestones" defaultOpen>
            <Milestones milestones={plan.milestones} />
          </Disclosure>
          <Disclosure id="path-heading" title="How you&apos;ll get there">
            <PathStyles onChanged={load} />
            {stretch ? (
              <p className="mt-3 text-[14px]">
                Weekly stretch problems are on.{' '}
                <button type="button" className="font-semibold underline underline-offset-4" onClick={() => undo('stretch', '')}>Turn off</button>
              </p>
            ) : null}
          </Disclosure>
          <Disclosure id="schedule-heading" title="Next two weeks" defaultOpen>
            <ol className="grid gap-4">
              {plan.days.map((day, index) => (
                <li key={day.date}>
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="font-semibold" data-visual-mask="">{index === 0 ? NAME.today : formatDate(day.date, { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                    <span className="text-[13px] text-muted-foreground tabular-nums">{day.minutes} min planned</span>
                  </div>
                  <ul className="grid gap-1">
                    {day.items.map(item => (
                      <li key={item.id} className="text-[15px]">
                        <Link href={activityHref(item.id)} className="underline-offset-4 hover:underline">{item.title}</Link>
                        <span className="text-[13px] text-muted-foreground">, {(KIND_LABEL[item.kind] ?? item.kind).toLowerCase()}</span>
                        {item.reason ? <span className="block text-[13px] text-muted-foreground">{item.reason}</span> : null}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </Disclosure>
          {plan.reasons.length || plan.revisions.length ? (
            <Disclosure id="why-heading" title="Why did my plan change?">
              <ul className="grid gap-2 text-[15px]">
                {plan.reasons.map(r => <li key={r}>{r}</li>)}
              </ul>
              {plan.revisions.length ? (
                <>
                  <h3 className="type-label mt-5 mb-2 text-muted-foreground">Recent changes</h3>
                  <ol className="grid gap-2 text-[15px]">
                    {plan.revisions.map(rev => (
                      <li key={rev.at} className="rounded-[16px] bg-raised p-3">
                        <p className="text-[13px] text-muted-foreground">{formatStamp(rev.at)}. {PACE_LABEL[rev.pace]}. Finish {formatDate(rev.projected_finish)}</p>
                        {rev.reasons.map(r => <p key={r} className="mt-1">{r}</p>)}
                        {rev.changes?.added?.length ? <p className="mt-1 text-[14px]"><span className="font-semibold">Added:</span> {rev.changes.added.join(', ')}</p> : null}
                        {rev.changes?.removed?.length ? <p className="mt-1 text-[14px]"><span className="font-semibold">Removed:</span> {rev.changes.removed.join(', ')}</p> : null}
                      </li>
                    ))}
                  </ol>
                </>
              ) : null}
            </Disclosure>
          ) : null}
          {guides.length ? (
            <Disclosure id="guides-heading" title="Selected topic guides">
              <p className="mb-3 text-sm text-muted-foreground">Chosen from <a className="underline underline-offset-4" href="https://github.com/nilbuild/developer-roadmap/tree/master/roadmaps" target="_blank" rel="noopener noreferrer">Developer Roadmap<span className="sr-only">, opens in a new tab</span></a>. Unrelated career paths are left out.</p>
              <ul className="grid gap-3 text-[15px]">
                {guides.map(c => (
                  <li key={c.concept}>
                    <p className="font-semibold">{c.title}</p>
                    <ul className="mt-1 grid gap-1">
                      {c.roadmap_resources.map(r => <li key={r.url}><a href={r.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">{r.title}<span className="sr-only">, opens in a new tab</span></a> <span className="text-[13px] text-muted-foreground">{r.source}</span></li>)}
                    </ul>
                  </li>
                ))}
              </ul>
            </Disclosure>
          ) : null}
        </aside>
      </div>
      <Assistant scope="plan" title="Plan with Soc" openSignal={planChat} />
    </Page>
  );
}
