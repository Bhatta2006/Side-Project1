'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, ChevronDown, ExternalLink, ThumbsDown, ThumbsUp, TriangleAlert } from 'lucide-react';
import { toast } from 'sonner';
import { ApiError, api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { useCourse } from '@/lib/course';
import { Listen } from '@/components/listen';
import { useI18n } from '@/lib/i18n';
import { LANGUAGE_LABEL, NAME, activityHref, conceptHref, joinSegments } from '@/lib/routes';
import type { ConceptView, Resource } from '@/lib/types';
import { cn } from '@/lib/utils';
import { defaultBlocks, orderBlocks } from '@/lib/sequence';
import { strongSoFar } from '@/lib/strong-so-far';
import Markdown from '@/components/markdown';
import { LessonPages } from '@/components/lesson-pages';
import { Difficulty, ErrorNote, Loading } from '@/components/common';
import { Level, PlatformTag, ProblemName, StatusControl } from '@/components/practice';
import { Illustration, Soc } from '@/components/socrat/illustration';
import { ConceptVisual } from '@/components/socrat/concept-visual';
import { StatusIcon, StatusLabel, statusFromBand, type Status } from '@/components/socrat/status';
import { EmptyState, LockedState } from '@/components/socrat/states';
import { openReportProblem } from '@/components/report-problem';
import { WrittenAnswers } from '@/components/graded-work';
import { FeelControls, SupportStep } from '@/components/socrat/support-step';
import { SUPPORT_STEPS } from '@/lib/routes';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';

const Assistant = dynamic(() => import('@/components/assistant'), { ssr: false });
// Most lessons have no visuals, so their renderers load only with a lesson that does.
// Tasks (reflections, real work a person judges) load only for lessons that have them.
const LessonTasks = dynamic(() => import('@/components/lesson-tasks'), { ssr: false });
const VisualizationHost = dynamic(() => import('@/components/visualization-host').then(m => m.VisualizationHost), { ssr: false });

const STYLES = [
  ['simpler', 'More simply'],
  ['example', 'Another example'],
  ['deeper', 'Go deeper'],
] as const;

function ReadingProgress() {
  const bar = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      if (bar.current) bar.current.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => { window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', onScroll); cancelAnimationFrame(frame); };
  }, []);
  return <div ref={bar} className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left scale-x-0 bg-primary" aria-hidden="true" />;
}

/** Read → Check → Practice: reading is separate from proving. */
function Stepper({ concept, className }: { concept: ConceptView; className?: string }) {
  const locked = Boolean(concept.locked);
  const solved = concept.problems.some(p => p.solved);
  const steps: { label: string; status: Status; detail: string }[] = [
    { label: 'Read', status: concept.lesson_done ? 'read' : 'not_seen', detail: concept.lesson_done ? 'Lesson read' : 'Not read yet' },
    { label: 'Check', status: locked ? 'locked' : concept.quiz_done ? 'practised' : 'not_seen', detail: locked ? 'Locked' : concept.quiz_done ? 'Concept check done' : 'Not taken yet' },
    { label: 'Practice', status: locked ? 'locked' : concept.band === 'strong' ? (strongSoFar(concept) ? 'learned' : 'mastered') : solved ? 'practised' : 'not_seen', detail: locked ? 'Locked' : concept.band === 'strong' ? (strongSoFar(concept) ? 'Strong so far' : 'Mastered') : solved ? 'Practised' : 'Not started' },
  ];
  return (
    <ol className={cn('flex items-start gap-2', className)} aria-label="Lesson steps">
      {steps.map((step, i) => (
        <li key={step.label} className="flex min-w-0 flex-1 items-start gap-2">
          <StatusIcon status={step.status} size={24} />
          <span className="min-w-0">
            <span className="block text-[15px] font-bold">{step.label}</span>
            <span className="block text-[13px] text-muted-foreground">{step.detail}</span>
          </span>
          {i < steps.length - 1 ? <span aria-hidden="true" className="mt-3 hidden h-px flex-1 bg-border-strong sm:block" /> : null}
        </li>
      ))}
    </ol>
  );
}

const STEP_LABEL: Record<string, string> = {
  lesson: 'Read the lesson',
  quiz: 'Concept check',
  visual: 'Interactive',
  task: 'Task',
  prompt: 'Written answer',
  exercise: 'Exercise',
  experiment: 'Experiment',
  problem: 'Problem',
};

function ResourceList({ concept, resources, onChange }: { concept: string; resources: Resource[]; onChange: (url: string, patch: Partial<Resource>) => void }) {
  function send(url: string, action: 'open' | 'helpful' | 'unhelpful') {
    api.post(`/concepts/${concept}/resources`, { url, action }).catch(() => undefined);
  }
  return (
    <ul className="grid gap-4 text-[15px]">
      {resources.map(r => (
        <li key={r.url}>
          <a
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 font-semibold underline underline-offset-4"
            onClick={() => { send(r.url, 'open'); onChange(r.url, { opened: true }); }}
          >
            {r.title}<span className="sr-only">, opens in a new tab</span> <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
          <div className="flex items-center justify-between gap-2 text-[13px] text-muted-foreground">
            <span>
              {r.author ? `${r.author}, ` : ''}{r.source}{r.published ? ` (${r.published.slice(0, 4)})` : ''}, {r.kind}, {r.minutes} min{r.opened ? ', opened' : ''}
              {r.license ? <span className="block text-[12px]">Licence: {r.license}{r.why ? `. Chosen because: ${r.why}.` : ''}</span> : null}
            </span>
            {r.opened ? (
              <span className="flex gap-0.5">
                {([true, false] as const).map(value => {
                  const on = r.helpful === value;
                  const Icon = value ? ThumbsUp : ThumbsDown;
                  return (
                    <button
                      key={String(value)}
                      type="button"
                      aria-pressed={on}
                      aria-label={value ? `${r.title} was helpful` : `${r.title} was not helpful`}
                      className={cn('grid size-9 place-items-center rounded-full hover:bg-raised', on ? 'text-foreground' : 'text-muted-foreground')}
                      onClick={() => { send(r.url, value ? 'helpful' : 'unhelpful'); onChange(r.url, { helpful: value }); }}
                    >
                      <Icon className={cn('size-4', on && 'fill-current')} />
                    </button>
                  );
                })}
              </span>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Section({ id, title, children, collapsible = false }: { id: string; title: string; children: React.ReactNode; collapsible?: boolean }) {
  if (!collapsible) {
    return (
      <section aria-labelledby={id} className="paper rounded-card p-5 lg:p-6">
        <h2 id={id} className="mb-4 font-display text-xl font-semibold tracking-[-0.03em]">{title}</h2>
        {children}
      </section>
    );
  }
  return (
    <details className="group paper rounded-card">
      <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 lg:px-6 [&::-webkit-details-marker]:hidden">
        <h2 id={id} className="font-display text-xl font-semibold tracking-[-0.03em]">{title}</h2>
        <ChevronDown className="size-5 transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="px-5 pb-5 lg:px-6 lg:pb-6">{children}</div>
    </details>
  );
}

export default function Lesson() {
  const allowed = useGuard('signed-in');
  const { profile } = useSession();
  const { features } = useCourse();
  const { t } = useI18n();
  const [original, setOriginal] = useState(false);
  const params = useParams<{ concept: string[] }>();
  const qualified = joinSegments(params.concept);
  const [concept, setConcept] = useState<ConceptView | null>(null);
  const [error, setError] = useState('');
  const [upgrade, setUpgrade] = useState(false);
  const [locked, setLocked] = useState<'' | 'gate' | 'preparing'>('');
  // The first lesson's draft, readable while its checks run (only when the API offers one).
  const [draft, setDraft] = useState<{ title: string; lesson: string; key_points: string[] } | null>(null);
  const [variant, setVariant] = useState<{ style: string; content: string } | null>(null);
  const [explaining, setExplaining] = useState('');
  const [completing, setCompleting] = useState(false);
  const [askSoc, setAskSoc] = useState(0);
  const [step, setStep] = useState('');
  const active = profile?.enrollment?.status === 'active';

  // A support step from the plan (?step=example|explain|checkin|stretch) shows on top.
  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get('step') ?? '';
    setStep(SUPPORT_STEPS.includes(value) ? value : '');
    setOriginal(false);
  }, [qualified]);

  const load = useCallback(() => {
    setError('');
    api.get<ConceptView>(`/concepts/${qualified}${original ? '?locale=en' : ''}`).then(setConcept).catch(e => {
      setUpgrade(e instanceof ApiError && e.code === 'upgrade_required');
      setLocked(e instanceof ApiError && e.code === 'concept_locked' ? 'gate' : e instanceof ApiError && e.code === 'concept_preparing' ? 'preparing' : '');
      setError(explain(e));
    });
  }, [qualified, original]);
  useEffect(() => {
    if (!allowed) return;
    load();
    if (active) api.post(`/activities/lesson:${qualified}/start`).catch(() => undefined);
  }, [allowed, active, load, qualified]);

  // A lesson being prepared opens by itself when it is ready; meanwhile show its draft if
  // there is one. Nothing can be marked done from a draft.
  const preparing = !concept && locked === 'preparing';
  useEffect(() => {
    if (!preparing) {
      setDraft(null);
      return;
    }
    const look = () => {
      api.get<{ title: string; lesson: string; key_points: string[] }>(`/concepts/${qualified}/preview`).then(setDraft).catch(() => setDraft(null));
    };
    look();
    const timer = setInterval(() => {
      // Quietly: an answer replaces the page, a refusal leaves the draft where it is.
      api.get<ConceptView>(`/concepts/${qualified}`).then(setConcept).catch(look);
    }, 5000);
    return () => clearInterval(timer);
  }, [preparing, qualified]);

  // How the lesson is read, for the coach: counters only, never scored. The API answers
  // 404 while the feature is off, and a lost signal is never worth an error on screen.
  const signal = useCallback((kind: 'page' | 'simpler' | 'deeper' | 'reread' | 'question' | 'visual', page?: number) => {
    api.post(`/concepts/${qualified}/signals`, page ? { kind, page } : { kind }).catch(() => undefined);
  }, [qualified]);
  const loaded = concept?.id;
  const wasDone = useRef(false);
  useEffect(() => {
    if (!loaded) return;
    wasDone.current = Boolean(concept?.lesson_done);
    if (wasDone.current && active) signal('reread'); // opened again after finishing it
    // Only when a lesson loads: marking it read on this visit is not a reread.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, active, signal]);
  useEffect(() => {
    if (askSoc > 0) signal('question');
  }, [askSoc, signal]);

  async function reexplain(style: string) {
    if (style === 'simpler' || style === 'deeper') signal(style);
    setExplaining(style);
    try {
      const result = await api.post<{ content: string }>(`/concepts/${qualified}/explain`, { style });
      setVariant({ style, content: result.content });
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setExplaining('');
    }
  }

  function updateResource(url: string, patch: Partial<Resource>) {
    setConcept(c => (c ? { ...c, resources: c.resources.map(r => (r.url === url ? { ...r, ...patch } : r)) } : c));
  }

  async function complete() {
    setCompleting(true);
    try {
      await api.post(`/activities/lesson:${qualified}/complete`);
      setConcept(c => (c ? { ...c, lesson_done: true } : c));
      toast.success('Lesson marked as read.');
    } catch (e) {
      setError(explain(e));
    } finally {
      setCompleting(false);
    }
  }

  if (!allowed || (!concept && !error)) return <Loading variant="article" label="Loading the lesson" />;
  if (!concept && upgrade) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <EmptyState title="This topic is for Founding Members" action={<Button asChild><Link href="/pricing">Become a Founding Member</Link></Button>}>
          The free plan covers the first two modules of each course. Founding Members unlock every topic, checkpoint and practice problem for ₹99 a month.
        </EmptyState>
      </div>
    );
  }
  if (!concept && locked === 'preparing' && draft) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p role="status" className="mb-5 rounded-[16px] border border-border-strong px-4 py-3 text-[15px]">
          <span className="font-semibold">A first draft, still being checked.</span>{' '}
          <span className="text-muted-foreground">
            You can start reading now. The checked lesson, with its questions, replaces this page by itself. If a check finds a mistake, this draft is rewritten.
          </span>
        </p>
        <h1 className="type-display-m break-words">{draft.title}</h1>
        <article className="mt-5">
          <Markdown source={draft.lesson} rich />
        </article>
        {draft.key_points.length ? (
          <section className="mt-6" aria-label="Key points">
            <h2 className="font-display text-xl font-semibold tracking-[-0.03em]">Key points</h2>
            <ul className="mt-2 grid list-disc gap-1 pl-5">
              {draft.key_points.map(p => <li key={p}>{p}</li>)}
            </ul>
          </section>
        ) : null}
      </div>
    );
  }
  if (!concept && locked === 'preparing') {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <LockedState title="This lesson is being prepared" href="/plan" action="Back to your plan">
          It opens here by itself as soon as it is ready.
        </LockedState>
      </div>
    );
  }
  if (!concept && locked) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <LockedState title="This topic is locked for now" href="/plan" action="See checkpoints">
          It opens when you pass the checkpoint before it. Already know it? Take that checkpoint to unlock it now.
        </LockedState>
      </div>
    );
  }
  if (!concept) return <div className="mx-auto max-w-3xl p-6"><ErrorNote message={error} retry={load} /></div>;

  const weakPrereqs = concept.prerequisites.filter(p => p.band === 'needs_practice' || p.band === 'not_started');
  const practice = [
    ...concept.practice_links.map(p => ({
      id: p.url, title: p.title, url: p.url, platform: p.platform, difficulty: p.difficulty, rating: null,
      concepts: [] as string[], companies: 0, striver: false, status: null, bookmarked: false, concept: null,
    })),
    ...concept.more_practice,
  ]
    .filter((p, i, all) => all.findIndex(q => q.url.replace(/\/$/, '') === p.url.replace(/\/$/, '')) === i)
    .slice(0, 10);
  const canCheck = active && !concept.locked;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-6 pb-32 sm:px-6 md:pt-8 lg:px-10 lg:pb-16">
      <ReadingProgress />

      {/* Header card: the one blue element on this reading screen, with a doodle. */}
      <header className="doodle-host relative mb-6 overflow-hidden rounded-card bg-violet p-6 text-violet-foreground [--card-muted:color-mix(in_srgb,var(--violet-foreground),transparent_8%)] lg:p-8" data-tone="violet">
        <div className="relative max-w-[70%] lg:max-w-[75%]">
          <Link href="/plan" transitionTypes={['nav-back']} aria-label={`Back to ${NAME.skills}`} className="mb-5 grid size-11 place-items-center rounded-full bg-ink text-ink-foreground">
            <ArrowLeft className="size-5" strokeWidth={1.5} aria-hidden="true" />
          </Link>
          <h1 className="type-display-m break-words">
            {concept.title}
            {hasAbout(concept) ? (
              <a href="#about-lesson" className="ml-2 align-super text-[0.45em] font-semibold no-underline opacity-80 hover:opacity-100" aria-label="About this lesson: how it was written and checked">★</a>
            ) : null}
          </h1>
          <p className="mt-3 text-[15px] font-semibold text-(--card-muted)">{features.code ? `Lesson, ${LANGUAGE_LABEL[concept.language]}` : 'Lesson'}</p>
        </div>
        <Illustration name="bulb" draw="load" className="pointer-events-none absolute top-1/2 right-6 size-28 -translate-y-1/2 [--illo-line:#fff] sm:size-36 lg:right-10" />
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-10">
        <article className="min-w-0">
          <Stepper concept={concept} className="mb-8 lg:hidden" />
          <p className="type-body-l mb-6 max-w-[68ch] text-muted-foreground text-pretty">{concept.summary}</p>
          <Listen target="#step-lesson" />

          {/* The concept's shared visual sits above the reading; free-form requests stay in the Playground. */}
          <section className="mb-8" aria-label={`${concept.title}, visual`}>
            <ConceptVisual concept={concept.id} title={concept.title} onOpen={() => signal('visual')} />
          </section>

          {concept.locked ? (
            <LockedState title={`Preview only. Practice and checks unlock after ${concept.locked.module}.`} href={activityHref(concept.locked.gate)} className="mb-6">
              Read ahead freely. The checkpoint unlocks the rest.
            </LockedState>
          ) : null}

          {weakPrereqs.length ? (
            <div className="mb-6 rounded-[20px] border px-4 py-3.5 text-[15px]">
              This builds on{' '}
              {weakPrereqs.map((p, i, all) => (
                <span key={p.id}><Link className="font-semibold underline underline-offset-4" href={conceptHref(p.id)}>{p.title}</Link>{i < all.length - 1 ? ', ' : ''}</span>
              ))}
              . A quick look there first may help.
            </div>
          ) : null}

          {step && active && !concept.locked ? (
            <SupportStep step={step} concept={qualified} language={concept.language} onAsk={() => setAskSoc(n => n + 1)} />
          ) : null}

          {/* Safety notes are the one thing about how a lesson was made that stays in front:
              they must be read before acting. Everything else is in "About this lesson". */}
          {concept.safety?.length ? (
            <div className="mb-6 max-w-[68ch] rounded-[16px] border border-border-strong px-4 py-3 text-sm">
              {concept.safety.map(n => <p key={n}>{n}</p>)}
            </div>
          ) : null}
          {/* Lesson pages, then visuals and tasks in the order this concept was planned, then the recap. */}
          <LessonPages
            tool={concept.section_visuals ? (index, title) => (
              <ConceptVisual concept={concept.id} title={title || concept.title} section={index} onOpen={() => signal('visual')} />
            ) : undefined}
            onPage={page => signal('page', page)}
            id={qualified}
            source={concept.lesson}
            language={concept.language}
            extra={orderBlocks(concept.sequence, defaultBlocks(concept.visuals?.length ?? 0, (concept.tasks ?? []).map(t => t.id)))
              .filter(block => block.kind !== 'lesson')
              .map((block, i) => {
                if (block.kind === 'visual') {
                  const v = concept.visuals![block.index];
                  return { key: block.key, title: v.purpose || 'Try it', node: <div id={`step-visual-${block.index}`}><VisualizationHost spec={v} lesson={{ concept: concept.id, title: concept.title }} /></div> };
                }
                const task = concept.tasks![block.index];
                return { key: block.key, title: 'Your task', node: <div id={`step-task-${task.id}`}><LessonTasks concept={concept.id} tasks={[task]} heading={i === 0} /></div> };
              })}
            recap={
              <Recap
                concept={concept}
                active={active}
                canCheck={canCheck}
                completing={completing}
                onComplete={complete}
                feel={canCheck ? <FeelControls concept={qualified} /> : null}
              />
            }
          />

          {hasAbout(concept) ? (
            <AboutLesson concept={concept} onOriginal={() => setOriginal(true)} t={t} />
          ) : null}

          {/* Explain it differently. */}
          <section className="mt-10 max-w-[68ch]" aria-labelledby="reexplain-heading">
            <h2 id="reexplain-heading" className="mb-3 font-display text-xl font-semibold tracking-[-0.03em]">Explain it differently</h2>
            <div className="inline-flex max-w-full flex-wrap gap-1 rounded-[24px] bg-raised p-1" role="group" aria-label="Explanation style">
              {STYLES.map(([style, label]) => (
                <button
                  key={style}
                  type="button"
                  aria-pressed={variant?.style === style}
                  disabled={Boolean(explaining)}
                  onClick={() => reexplain(style)}
                  className={cn('inline-flex min-h-10 items-center gap-2 rounded-full border border-transparent px-4 text-sm font-semibold text-foreground transition-colors hover:bg-card disabled:opacity-50', variant?.style === style && 'border-border bg-card font-bold')}
                >
                  {explaining === style ? <Spinner className="size-4" /> : null}
                  {label}
                </button>
              ))}
            </div>
            {variant ? (
              <div className="mt-4 paper rounded-card p-5 lg:p-6">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="font-display text-lg font-semibold tracking-[-0.02em]">{STYLES.find(s => s[0] === variant.style)?.[1]}</h3>
                  <Button variant="ghost" size="sm" onClick={() => setVariant(null)}>Hide</Button>
                </div>
                <Markdown source={variant.content} language={concept.language} rich />
              </div>
            ) : null}
          </section>


          <div className="mt-10 grid gap-4">
            {concept.prompts?.length ? (
              <Section id="written-heading" title="Explain it in your own words">
                <WrittenAnswers concept={concept.id} prompts={concept.prompts} onGraded={load} />
              </Section>
            ) : null}
            {concept.problems.length ? (
              <Section id="judged-heading" title="Practice problems">
                <ul className="grid gap-2">
                  {concept.problems.map(p => (
                    <li key={p.id}>
                      <Link href={`/problems/${p.id}`} className="flex min-h-14 items-center gap-3 rounded-[16px] bg-raised px-4 py-2 transition-colors hover:bg-[color-mix(in_srgb,var(--raised),var(--foreground)_5%)]">
                        <StatusIcon status={p.solved ? 'practised' : 'not_seen'} size={22} title={p.solved ? 'Solved' : 'Not solved yet'} />
                        <span className="min-w-0 flex-1 font-semibold">{p.title}</span>
                        <Difficulty level={p.difficulty} />
                      </Link>
                    </li>
                  ))}
                </ul>
              </Section>
            ) : features.library ? (
              <Section id="judged-heading" title="Practice problems">
                <p className="text-[15px] text-muted-foreground">No judged problems for this skill yet. The concept check shows what you know; for practice, try the <Link href={`/library?concept=${concept.id}`} className="font-semibold underline underline-offset-4">external problems</Link> or ask Soc.</p>
              </Section>
            ) : null}
            {features.drills ? (
              <Section id="drills-heading" title="Practise this topic">
                <p className="mb-3 text-[15px] text-muted-foreground">Fresh questions on {concept.title}, written for your course. Answer them one at a time and earn stars.</p>
                <Button asChild><Link href={`/studio?concept=${encodeURIComponent(concept.id)}`}>Practise {concept.title}</Link></Button>
              </Section>
            ) : null}

            {concept.exercises?.length && features.code ? (
              <Section id="builders-heading" title="Python skill builders" collapsible>
                <p className="mb-3 text-sm text-muted-foreground">Selected exercises for this skill. Practise the idea before opening the upstream solution; some examples there use older Python syntax.</p>
                <ul className="grid divide-y">{concept.exercises.map(exercise => <li key={exercise.number} className="py-3"><a href={exercise.url} target="_blank" rel="noopener noreferrer" className="font-semibold underline underline-offset-4">{exercise.title}, exercise {exercise.number}<span className="sr-only">, opens in a new tab</span></a><p className="mt-1 text-sm text-muted-foreground">{exercise.guidance}</p></li>)}</ul>
                <p className="mt-3 text-[13px] text-muted-foreground">Source: zhiwehu/Python-programming-exercises. These optional exercises are ungraded.</p>
              </Section>
            ) : null}

            {practice.length && features.library ? (
              <Section id="more-practice-heading" title="External practice" collapsible>
                <p className="mb-3 text-sm text-muted-foreground">Picked for your current level from LeetCode, Codeforces, CSES and more, plus two challenges above it. External problems open on the original site. <Link href={`/library?concept=${concept.id}`} className="font-semibold underline underline-offset-4">All problems</Link></p>
                <ul className="grid divide-y">
                  {practice.map(p => (
                    <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-[15px]">
                      <span className="flex min-w-0 flex-wrap items-center gap-2">
                        <ProblemName problem={p} />
                        <PlatformTag platform={p.platform} />
                        {p.striver ? <Badge variant="secondary">A2Z sheet</Badge> : null}
                        {'stretch' in p && p.stretch ? <Badge variant="outline">Challenge</Badge> : null}
                      </span>
                      <span className="flex items-center gap-2">
                        <Level problem={p} />
                        {p.id.includes(':') && !p.id.startsWith('http') ? (
                          <StatusControl id={p.id} status={p.status} bookmarked={p.bookmarked} compact onChange={next => setConcept(c => (c ? { ...c, more_practice: c.more_practice.map(x => (x.id === p.id ? { ...x, ...next } : x)) } : c))} />
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {concept.resources.length || concept.handbook.length || concept.implementations.length ? (
              <Section id="resources-heading" title="Resources" collapsible>
                <div className="grid gap-5">
                  <ResourceList concept={concept.id} resources={concept.resources} onChange={updateResource} />
                  {concept.handbook.length ? (
                    <div className="border-t pt-4">
                      <h3 className="type-label mb-2 text-muted-foreground">Competitive Programmer&apos;s Handbook</h3>
                      <ul className="grid gap-2 text-[15px]">
                        {concept.handbook.map(h => (
                          <li key={h.url}>
                            <a href={h.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">Section {h.chapter}, {h.title}<span className="sr-only">, opens in a new tab</span></a>
                            <span className="text-[13px] text-muted-foreground">, page {h.page}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {concept.implementations.length ? (
                    <div className="border-t pt-4">
                      <h3 className="type-label mb-2 text-muted-foreground">Reference implementations</h3>
                      <ul className="grid gap-2 text-[15px]">
                        {concept.implementations.map(i => (
                          <li key={i.url}><a href={i.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">{i.title}<span className="sr-only">, opens in a new tab</span></a> <span className="text-[13px] text-muted-foreground">TheAlgorithms</span></li>
                        ))}
                      </ul>
                      <p className="mt-2 text-[13px] text-muted-foreground">Read these after you have solved a problem yourself.</p>
                    </div>
                  ) : null}
                </div>
              </Section>
            ) : null}
          </div>
          {error ? <ErrorNote message={error} /> : null}
        </article>

        {/* Desktop support column: stepper, on this page, Ask Soc, reminders. */}
        <aside className="hidden content-start gap-5 lg:sticky lg:top-24 lg:grid lg:self-start" aria-label="Lesson tools">
          <div className="paper rounded-card p-5">
            <StatusLabel status={strongSoFar(concept) ? 'learned' : statusFromBand(concept.band)} detail={strongSoFar(concept) ? 'Strong so far' : undefined} className="mb-4" />
            {concept.evidence?.reasons.length ? (
              <p className="-mt-2 mb-4 text-sm text-muted-foreground">{concept.evidence.reasons[0]}</p>
            ) : null}
            <Stepper concept={concept} className="flex-col gap-4" />
          </div>
          <button type="button" onClick={() => setAskSoc(n => n + 1)} className="flex items-center gap-4 paper rounded-card p-5 text-left transition-colors hover:bg-raised" aria-haspopup="dialog">
            <Soc size={48} />
            <span>
              <span className="block font-display text-lg font-semibold tracking-[-0.02em]">Ask Soc</span>
              <span className="block text-sm text-muted-foreground">Questions on this lesson</span>
            </span>
          </button>
        </aside>
      </div>
      {/* Desktop has the "Ask Soc" card in the side column; the floating launcher is for phones. */}
      <Assistant scope={`concept:${concept.id}`} title="Ask Soc" language={concept.language} openSignal={askSoc} launcher="phone" />
    </div>
  );
}

/** The last page: what to keep, the mistakes to avoid, and the one next step. */
function Recap({ concept, active, canCheck, completing, onComplete, feel }: {
  concept: ConceptView;
  active: boolean;
  canCheck: boolean;
  completing: boolean;
  onComplete: () => void;
  feel: React.ReactNode;
}) {
  return (
    <div className="grid gap-5">
      <KeyReminders concept={concept} />
      {concept.pitfalls.length ? <Pitfalls concept={{ ...concept, pitfalls: concept.pitfalls.slice(0, 2) }} /> : null}
      {feel}
      <section aria-labelledby="finish-heading">
        <h3 id="finish-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">{concept.lesson_done ? 'Lesson read' : 'Finished reading?'}</h3>
        <div className="mt-3 flex flex-wrap gap-3">
          {!concept.lesson_done ? (
            <Button variant="outline" size="lg" disabled={!active || completing || Boolean(concept.locked)} aria-busy={completing} onClick={onComplete}>
              {completing ? <><Spinner /> Saving</> : 'Mark lesson as read'}
            </Button>
          ) : null}
          {canCheck ? (
            <Button asChild size="lg">
              <Link href={activityHref(`quiz:${concept.id}`)} transitionTypes={['nav-forward']}>
                {concept.quiz_done ? 'Retake concept check' : 'Take concept check'}
                <ArrowCircle />
              </Link>
            </Button>
          ) : null}
        </div>
        {!active ? <p className="mt-3 text-sm text-muted-foreground">Choose a course to track lessons and checks.</p> : null}
        <p className="mt-3 text-[15px] text-muted-foreground">Reading does not count as mastery. The concept check shows it.</p>
      </section>
    </div>
  );
}

function hasAbout(concept: ConceptView): boolean {
  return Boolean(concept.ai_generated || concept.translation || concept.citations?.length || concept.teaching?.techniques.length);
}

/** ★ About this lesson: how it was written and checked, its sources and why it is taught this
 *  way. At the end of the lesson rather than above it; complete, never hidden. */
function AboutLesson({ concept, onOriginal, t }: {
  concept: ConceptView;
  onOriginal: () => void;
  t: ReturnType<typeof useI18n>['t'];
}) {
  return (
    <section id="about-lesson" aria-labelledby="about-heading" className="mt-10 max-w-[68ch] scroll-mt-24 border-t pt-6 text-sm text-muted-foreground">
      <h2 id="about-heading" className="mb-3 text-[15px] font-semibold text-foreground"><span aria-hidden="true">★ </span>About this lesson</h2>
      <div className="grid gap-3">
        {concept.ai_generated ? (
          <p>
            {concept.attribution || 'Written by Socrat AI and checked by AI models.'}{' '}
            {concept.validation ? <>{concept.validation.reviewer ? `Confirmed by ${concept.validation.reviewer}.` : concept.validation.label}{' '}</> : null}
            <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={() => openReportProblem()}>Report a problem</button> if something looks wrong.
          </p>
        ) : null}
        {concept.translation ? (
          <p dir={concept.translation.rtl ? 'rtl' : undefined}>
            {concept.translation.status === 'reviewed' && concept.translation.reviewer
              ? t('translation.reviewed', { name: concept.translation.reviewer })
              : t('translation.machine')}{' '}
            <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={onOriginal}>{t('translation.english')}</button>
          </p>
        ) : null}
        {concept.citations?.length ? (
          <details>
            <summary className="cursor-pointer font-medium text-foreground">Where each claim comes from</summary>
            <ul className="mt-3 grid gap-3">
              {concept.citations.map(c => (
                <li key={`${c.n}-${c.offset}`}>
                  <p>{c.claim} <a className="underline underline-offset-4" href={c.url} target="_blank" rel="noopener noreferrer">[{c.n}]<span className="sr-only">, opens in a new tab</span></a></p>
                  {c.passage ? <p className="mt-1">{c.basis === 'retrieved' ? 'Source text' : 'Summary of the source'}: {c.passage}</p> : null}
                  {!c.supported ? <p className="mt-1 text-attention">This source may not state this directly.</p> : null}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
        {concept.teaching?.techniques.length ? (
          <details>
            <summary className="cursor-pointer font-medium text-foreground">Why it is taught this way</summary>
            <ul className="mt-2 grid gap-1.5">
              {concept.teaching.techniques.map(x => <li key={x.name}><span className="font-medium text-foreground">{x.name}.</span> {x.why}</li>)}
            </ul>
          </details>
        ) : null}
      </div>
    </section>
  );
}

function KeyReminders({ concept }: { concept: ConceptView }) {
  if (!concept.key_points.length) return null;
  return (
    <Card tone="cream" size="sm" aria-label="Key reminders">
      <div className="px-(--card-spacing)">
        <h2 className="mb-3 font-display text-lg font-semibold tracking-[-0.02em]">Key reminders</h2>
        <ul className="grid gap-2.5 text-[15px]">
          {concept.key_points.map(p => <li key={p} className="flex gap-2.5"><span aria-hidden="true" className="mt-2.5 size-1.5 flex-none rounded-full bg-current" /><span>{p}</span></li>)}
        </ul>
      </div>
    </Card>
  );
}

function Pitfalls({ concept }: { concept: ConceptView }) {
  if (!concept.pitfalls.length) return null;
  return (
    <Card tone="raised" size="sm" aria-label="Common pitfalls">
      <div className="px-(--card-spacing)">
        <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold tracking-[-0.02em]"><TriangleAlert className="size-5" strokeWidth={1.5} aria-hidden="true" /> Common pitfalls</h2>
        <ul className="grid gap-2.5 text-[15px]">
          {concept.pitfalls.map(p => <li key={p} className="flex gap-2.5"><span aria-hidden="true" className="mt-2.5 size-1.5 flex-none rounded-full bg-muted-foreground" /><span>{p}</span></li>)}
        </ul>
      </div>
    </Card>
  );
}
