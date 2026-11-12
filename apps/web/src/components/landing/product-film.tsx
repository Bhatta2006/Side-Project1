'use client';

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { Check } from '@/components/icons';
import { prefersReducedMotion } from '@/lib/motion';
import { Soc } from '@/components/socrat/illustration';
import { SocFigure, type SocMood } from '@/components/socrat/soc';
import { StatusIcon } from '@/components/socrat/status';
import { cn } from '@/lib/utils';

/*
 * A scripted film of one day with Soc, in five short scenes, played like a video: the chapter
 * bars below fill as each scene runs, and the bar finishing is what moves to the next scene.
 * Nothing here calls the API. It plays only while on screen, pauses on hover or focus, and with
 * reduced motion it waits on the first scene for the viewer to pick one.
 */

const SCENE_MS = 4600;

// `soc` is what Soc, narrating from the corner of the sheet, says while the scene plays.
const SCENES: readonly { id: 'goal' | 'plan' | 'check' | 'code' | 'prove'; title: string; text: string; soc: string; mood: SocMood }[] = [
  { id: 'goal', title: 'Tell Soc your goal', text: 'Three quick questions and a placement check find where you start.', soc: 'First I ask what you want to do.', mood: 'curious' },
  { id: 'plan', title: 'Get one next step', text: 'Your plan fits the time you have. Missed days never pile up.', soc: 'Then I pick today’s one next step.', mood: 'happy' },
  { id: 'check', title: 'Learn, then check', text: 'Short lessons, then a check that proves you got it.', soc: 'You read it. I check it stuck.', mood: 'thinking' },
  { id: 'code', title: 'Code with Soc beside you', text: 'Stuck? Soc asks a question first. Help grows one step at a time.', soc: 'Stuck? I ask. I don’t tell.', mood: 'wink' },
  { id: 'prove', title: 'Prove it, then keep it', text: 'Judged tests mark it learned. Spaced reviews make it stick.', soc: 'Proven! I’ll ask again in 3 days.', mood: 'proud' },
];

/** Delay for the nth beat inside a scene. */
const at = (ms: number): CSSProperties => ({ animationDelay: `${ms}ms` });

function GoalScene() {
  const goals = ['Learn to code from zero', 'Crack DSA interviews', 'Win coding contests'];
  return (
    <div className="grid h-full content-center gap-5 px-6 sm:px-10">
      <div className="film-beat flex items-center gap-3" style={at(0)}>
        <Soc size={44} mood="curious" />
        <p className="rounded-[16px_16px_16px_4px] border bg-cream px-4 py-2 text-[15px] text-cream-foreground sm:text-[17px]">What do you want to be able to do?</p>
      </div>
      <div className="flex flex-wrap gap-2.5">
        {goals.map((g, i) => (
          <span
            key={g}
            className={cn('film-beat rounded-full border px-4 py-2 text-[14px] sm:text-[15px]', i === 1 ? 'film-pick border-border-strong bg-card' : 'border-border-strong bg-card')}
            style={at(500 + i * 180)}
          >
            {g}
          </span>
        ))}
      </div>
      <p className="film-beat font-hand text-[22px] text-pen" style={at(2300)}>DSA it is. Python, 45 min a day.</p>
    </div>
  );
}

function PlanScene() {
  const rows = [['Hash maps', 'lesson · 10 min', true], ['Two pointers', 'check · 5 min', false], ['Review: arrays', 'review · 5 min', false]] as const;
  return (
    <div className="grid h-full content-center gap-3 px-6 sm:px-10">
      <div className="film-beat flex items-baseline justify-between" style={at(0)}>
        <p className="text-[20px] font-medium tracking-[-0.02em] sm:text-[24px]">Today</p>
        <p className="text-[13px] text-muted-foreground tabular-nums">0 of 45 min</p>
      </div>
      {rows.map(([title, meta, first], i) => (
        <div key={title} className={cn('film-beat flex items-center gap-3 rounded-[4px] border bg-card px-4 py-3', first && 'film-glow')} style={at(350 + i * 260)}>
          <StatusIcon status="not_seen" size={20} />
          <span className="font-medium">{title}</span>
          <span className="ml-auto text-[13px] text-muted-foreground">{meta}</span>
        </div>
      ))}
      <p className="film-beat font-hand text-[21px] text-pen" style={at(2200)}>one next step, already picked</p>
    </div>
  );
}

function CheckScene() {
  const options = ['O(n²)', 'O(n log n)', 'O(n)'];
  return (
    <div className="grid h-full content-center gap-4 px-6 sm:px-10">
      <p className="film-beat text-[13px] text-muted-foreground" style={at(0)}>Check · Hash maps</p>
      <p className="film-beat text-[17px] font-medium sm:text-[20px]" style={at(150)}>Two-sum with a hash map runs in…</p>
      <div className="grid gap-2">
        {options.map((o, i) => (
          <div key={o} className={cn('film-beat flex items-center gap-3 rounded-[4px] border bg-card px-4 py-2.5 font-mono text-[14px]', i === 2 && 'film-correct')} style={at(400 + i * 160)}>
            <span className="grid size-5 place-items-center rounded-full border border-border-strong text-[11px]">{String.fromCharCode(65 + i)}</span>
            {o}
            {i === 2 ? <Check className="film-tick ml-auto size-4" strokeWidth={3} /> : null}
          </div>
        ))}
      </div>
      <p className="film-beat font-hand text-[21px] text-pen" style={at(2600)}>check passed ✓</p>
    </div>
  );
}

function CodeScene() {
  const code = ['def two_sum(nums, target):', '    seen = {}', '    for i, x in enumerate(nums):', '        if target - x in seen:'];
  return (
    <div className="grid h-full content-center gap-3 px-4 sm:grid-cols-[1.2fr_1fr] sm:items-center sm:gap-5 sm:px-8">
      <pre className="overflow-hidden rounded-[4px] bg-[var(--code-bg)] px-4 py-3 font-mono text-[12px] leading-[21px] text-[var(--code-fg)] sm:text-[13px]">
        {code.map((line, i) => (
          <div key={i} className="film-type overflow-hidden whitespace-pre" style={{ ...at(150 + i * 520), '--chars': line.length } as CSSProperties}>{line}</div>
        ))}
        <span className="film-caret" />
      </pre>
      <div className="grid gap-2.5">
        <p className="film-beat justify-self-end rounded-[16px_16px_4px_16px] bg-raised px-3.5 py-2 text-[14px]" style={at(800)}>I&apos;m stuck. Why so slow?</p>
        <div className="film-beat flex items-end gap-2" style={at(1700)}>
          <Soc size={30} mood="thinking" />
          <p className="rounded-[16px_16px_16px_4px] border bg-cream px-3.5 py-2 text-[14px] text-cream-foreground">What are you really searching for?</p>
        </div>
        <div className="film-beat flex items-center gap-2 text-[12px] text-muted-foreground" style={at(2500)}>
          <span className="flex gap-[3px]">{[0, 1, 2, 3, 4, 5].map(i => <span key={i} className={cn('h-[5px] w-3.5 rounded-full', i === 0 ? 'bg-primary' : 'bg-border-strong')} />)}</span>
          help 1 of 6 · no answer given
        </div>
      </div>
    </div>
  );
}

function ProveScene() {
  return (
    <div className="grid h-full content-center gap-4 px-6 sm:px-10">
      <div className="flex flex-wrap items-center gap-2">
        {[0, 1, 2, 3].map(i => (
          <span key={i} className="film-pass grid size-8 place-items-center rounded-[6px] text-[var(--proof-foreground)]" style={at(150 + i * 260)}>
            <Check className="size-4" strokeWidth={3} />
          </span>
        ))}
        <span className="film-beat ml-1 font-mono text-[13px] text-muted-foreground" style={at(1250)}>4 / 4 hidden tests passed</span>
      </div>
      <div className="film-beat flex items-center gap-3 rounded-[4px] border bg-card px-4 py-3" style={at(1600)}>
        <StatusIcon status="mastered" size={24} />
        <span className="font-medium">Hash maps</span>
        <span className="ml-auto text-[13px] text-muted-foreground">learned · 1 hint used</span>
      </div>
      <div className="film-beat flex items-center gap-3 rounded-[4px] border border-dashed px-4 py-3 text-[14px] text-muted-foreground" style={at(2200)}>
        <StatusIcon status="review" size={20} />
        Review in 3 days, then 1 week
      </div>
      <p className="film-beat font-hand text-[22px] text-pen" style={at(2800)}>proven, not just read.</p>
    </div>
  );
}

const VIEWS: Record<(typeof SCENES)[number]['id'], () => ReactNode> = {
  goal: GoalScene, plan: PlanScene, check: CheckScene, code: CodeScene, prove: ProveScene,
};

export function ProductFilm({ className }: { className?: string }) {
  const [scene, setScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [held, setHeld] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReducedMotion() || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(([entry]) => setPlaying(entry.isIntersecting), { threshold: 0.4 });
    if (root.current) io.observe(root.current);
    return () => io.disconnect();
  }, []);

  const running = playing && !held;
  const View = VIEWS[SCENES[scene].id];

  return (
    <div
      ref={root}
      className={cn('product-film relative', className)}
      data-running={running ? '' : undefined}
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={() => setHeld(false)}
    >
      <figure className="paper relative overflow-hidden rounded-[4px] shadow-floating">
        <figcaption className="sr-only">
          A sample day with Socrat in five scenes: choose a goal, get one next step, learn and pass a check,
          code with Soc asking questions instead of giving the answer, then pass the hidden tests and get a review scheduled.
        </figcaption>
        <div className="flex items-center gap-2 border-b px-4 py-2.5">
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="ml-2 hidden text-[13px] text-muted-foreground sm:inline">socrat · {SCENES[scene].title.toLowerCase()}</span>
          <span className="font-hand ml-auto text-[18px] text-pen">sample day</span>
        </div>
        <div key={scene} aria-hidden="true" className="film-scene relative h-[330px] sm:h-[360px] sm:pr-[190px]">
          <View />
        </div>
        {/* Soc narrates from the corner of the sheet; a new mood replays his reaction. */}
        <div aria-hidden="true" className="pointer-events-none absolute right-5 bottom-3 hidden w-[170px] sm:grid sm:justify-items-end">
          <p key={`say-${scene}`} className="film-beat soc-bubble mb-4 w-full rounded-[4px] border-2 border-[var(--soc-outline)] bg-card px-3 py-2 text-[15px] leading-snug" data-side="right" style={at(250)}>
            {SCENES[scene].soc}
          </p>
          <SocFigure mood={SCENES[scene].mood} size={136} idle />
        </div>
      </figure>

      <ol className="mt-5 grid grid-cols-5 gap-2 sm:gap-3" aria-label="Scenes">
        {SCENES.map((s, i) => (
          <li key={s.id} className="min-w-0">
            <button
              type="button"
              onClick={() => setScene(i)}
              aria-current={i === scene ? 'step' : undefined}
              className={cn('group grid w-full gap-2 text-left', i !== scene && 'opacity-60 hover:opacity-100')}
            >
              <span className="block h-[3px] overflow-hidden rounded-full bg-border-strong">
                <span
                  key={i === scene ? `on-${scene}` : 'off'}
                  className={cn('film-bar block h-full bg-ink', i < scene ? 'w-full' : 'w-0', i === scene && 'film-bar-on')}
                  style={{ animationDuration: `${SCENE_MS}ms` }}
                  onAnimationEnd={() => setScene(n => (n + 1) % SCENES.length)}
                />
              </span>
              <span className="hidden text-[14px] font-medium sm:block">{s.title}</span>
              <span className="sr-only sm:hidden">{s.title}</span>
            </button>
          </li>
        ))}
      </ol>
      <p aria-hidden="true" className="mt-4 flex items-center gap-2 sm:hidden"><Soc size={32} mood={SCENES[scene].mood} /><span className="font-hand text-[20px] text-pen">{SCENES[scene].soc}</span></p>
      <p className="mt-2 min-h-[3rem] text-[15px] text-muted-foreground sm:hidden">
        <span className="font-medium text-foreground">{SCENES[scene].title}.</span> {SCENES[scene].text}
      </p>
      <p className="mt-2 hidden text-[15px] text-muted-foreground sm:block">{SCENES[scene].text}</p>
    </div>
  );
}
