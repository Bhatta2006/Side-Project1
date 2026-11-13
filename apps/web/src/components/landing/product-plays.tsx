'use client';

import { useState, type CSSProperties, type ReactNode } from 'react';
import { Check, Play, RotateCcw } from '@/components/icons';
import { Soc } from '@/components/socrat/illustration';
import { SocFigure, type SocMood } from '@/components/socrat/soc';
import { StatusIcon } from '@/components/socrat/status';
import { cn } from '@/lib/utils';

/*
 * Six small "plays" of the product that the visitor runs by pressing things: pick a goal, start
 * today's step, answer a check, ask Soc for help, run the hidden tests, come back for a review.
 * Nothing moves until a button is pressed, and each press advances that play by one step, so the
 * visitor is doing what a learner does instead of watching a film go by. Nothing here calls the
 * API. Every play keeps its own step, so going back to one finds it where it was left.
 */

type PlayId = 'goal' | 'plan' | 'check' | 'help' | 'tests' | 'review';

interface PlayView {
  /** What the sheet shows at this step. */
  scene: ReactNode;
  /** What Soc says from the corner, and how he looks saying it. */
  soc: string;
  mood: SocMood;
  /** The button that advances the play; absent when the scene's own buttons do, or at the end. */
  action?: string;
  done?: boolean;
}

const PLAYS: readonly { id: PlayId; title: string; text: string }[] = [
  { id: 'goal', title: 'Pick a goal', text: 'Three quick questions and a placement check find where you start.' },
  { id: 'plan', title: 'Start today', text: 'Your plan fits the time you have. Missed days never pile up.' },
  { id: 'check', title: 'Answer a check', text: 'Short lessons, then a check that proves you got it.' },
  { id: 'help', title: 'Ask for help', text: 'Soc asks a question first. Help grows one step at a time.' },
  { id: 'tests', title: 'Run the tests', text: 'Hidden tests judge your code. Passing them is what marks a skill learned.' },
  { id: 'review', title: 'Come back later', text: 'Spaced reviews bring a skill back just before you would forget it.' },
];

/** Delay for the nth beat inside a step. */
const at = (ms: number): CSSProperties => ({ animationDelay: `${ms}ms` });

const chip = 'min-h-11 rounded-full border border-border-strong bg-card px-4 py-2 text-left text-[14px] transition-colors hover:bg-hi-select sm:text-[15px]';
const note = 'film-beat font-hand text-[21px] text-pen';

const GOALS = [
  { label: 'Learn to code from zero', reply: 'From zero it is. Python, 30 min a day.' },
  { label: 'Crack DSA interviews', reply: 'DSA it is. Python, 45 min a day.' },
  { label: 'Win coding contests', reply: 'Contests it is. C++, an hour a day.' },
] as const;

function goalPlay(step: number, set: (step: number) => void): PlayView {
  const picked = step > 0 ? GOALS[step - 1] : null;
  return {
    soc: picked ? 'Good. Now I know where to start you.' : 'First I ask what you want to do.',
    mood: picked ? 'happy' : 'curious',
    done: !!picked,
    scene: (
      <div className="grid h-full content-center gap-5">
        <div className="flex items-center gap-3">
          <Soc size={44} mood="curious" />
          <p className="rounded-[16px_16px_16px_4px] border bg-cream px-4 py-2 text-[15px] text-cream-foreground sm:text-[17px]">What do you want to be able to do?</p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          {GOALS.map((g, i) => (
            <button key={g.label} type="button" onClick={() => set(i + 1)} aria-pressed={step === i + 1} className={cn(chip, step === i + 1 && 'border-ink bg-ink text-ink-foreground hover:bg-ink')}>
              {g.label}
            </button>
          ))}
        </div>
        {picked ? <p key={step} className={note}>{picked.reply}</p> : <p className="text-[14px] text-muted-foreground">Press one.</p>}
      </div>
    ),
  };
}

const PLAN_ROWS = [['Hash maps', 'lesson', 10], ['Two pointers', 'check', 5], ['Review: arrays', 'review', 5]] as const;

function planPlay(step: number): PlayView {
  const minutes = PLAN_ROWS.slice(0, step).reduce((sum, row) => sum + row[2], 0);
  const next = PLAN_ROWS[step];
  return {
    soc: step === 0 ? 'I pick today’s one next step.' : next ? 'Done. Here is the next one.' : 'That is today. See you tomorrow.',
    mood: next ? 'happy' : 'proud',
    action: next ? `Do “${next[0]}”` : undefined,
    done: !next,
    scene: (
      <div className="grid h-full content-center gap-3">
        <div className="flex items-baseline justify-between">
          <p className="text-[20px] font-medium tracking-[-0.02em] sm:text-[24px]">Today</p>
          <p className="text-[13px] text-muted-foreground tabular-nums">{minutes} of 45 min</p>
        </div>
        {PLAN_ROWS.map(([title, kind, mins], i) => (
          <div key={title} className={cn('flex items-center gap-3 rounded-[4px] border bg-card px-4 py-3', i === step && 'ring-2 ring-[color-mix(in_srgb,var(--highlight)_70%,transparent)]')}>
            <StatusIcon status={i < step ? 'mastered' : 'not_seen'} size={20} />
            <span className={cn('min-w-0 font-medium', i < step && 'text-muted-foreground line-through')}>{title}</span>
            <span className="ml-auto flex-none text-[13px] text-muted-foreground">{kind} · {mins} min</span>
          </div>
        ))}
        <p key={step} className={note}>{next ? 'one next step, already picked' : 'no backlog, no guilt'}</p>
      </div>
    ),
  };
}

const CHECK_OPTIONS = ['O(n²)', 'O(n log n)', 'O(n)'];
const CHECK_RIGHT = 2;

function checkPlay(step: number, set: (step: number) => void): PlayView {
  const choice = step - 1;
  const right = choice === CHECK_RIGHT;
  return {
    soc: step === 0 ? 'You read it. I check it stuck.' : right ? 'Yes. One pass, one lookup each.' : 'Close. How many times do you visit each number?',
    mood: step === 0 ? 'thinking' : right ? 'proud' : 'curious',
    done: right,
    scene: (
      <div className="grid h-full content-center gap-4">
        <p className="text-[13px] text-muted-foreground">Check · Hash maps</p>
        <p className="text-[17px] font-medium sm:text-[20px]">Two-sum with a hash map runs in…</p>
        <div className="grid gap-2">
          {CHECK_OPTIONS.map((o, i) => {
            const chosen = choice === i;
            return (
              <button
                key={o}
                type="button"
                disabled={right}
                onClick={() => set(i + 1)}
                aria-pressed={chosen}
                className={cn(
                  'flex min-h-11 items-center gap-3 rounded-[4px] border bg-card px-4 py-2.5 text-left font-mono text-[14px] transition-colors enabled:hover:bg-hi-select',
                  chosen && right && 'border-proof bg-[color-mix(in_srgb,var(--proof)_14%,var(--card))]',
                  chosen && !right && 'border-pen',
                )}
              >
                <span className="grid size-5 flex-none place-items-center rounded-full border border-border-strong text-[11px]">{String.fromCharCode(65 + i)}</span>
                {o}
                {chosen && right ? <Check className="ml-auto size-4" strokeWidth={3} aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
        {step === 0 ? <p className="text-[14px] text-muted-foreground">Press your answer.</p> : <p key={step} className={note}>{right ? 'check passed ✓' : 'not yet. try another'}</p>}
      </div>
    ),
  };
}

const HELP = [
  'What are you really searching for?',
  'For each number, which other number would finish the pair?',
  'Could you remember the numbers you have already seen?',
  'Keep them in a hash map: look up target − x before you store x.',
] as const;

function helpPlay(step: number): PlayView {
  const shown = HELP.slice(0, step);
  return {
    soc: step === 0 ? 'Stuck? I ask. I don’t tell.' : step < HELP.length ? 'Still stuck? Ask again.' : 'Enough to finish it yourself.',
    mood: step === 0 ? 'wink' : step < HELP.length ? 'thinking' : 'happy',
    action: step === 0 ? 'Ask Soc' : step < HELP.length ? 'Ask for more help' : undefined,
    done: step >= HELP.length,
    scene: (
      <div className="grid h-full content-center gap-3">
        <p className="justify-self-end rounded-[16px_16px_4px_16px] bg-raised px-3.5 py-2 text-[14px]">I&apos;m stuck. Why is my two-sum so slow?</p>
        <div className="grid min-h-[168px] content-start gap-2">
          {shown.map((line, i) => (
            <div key={line} className={cn('flex items-end gap-2', i === step - 1 && 'film-beat')}>
              <Soc size={28} mood="thinking" />
              <p className="rounded-[16px_16px_16px_4px] border bg-cream px-3.5 py-2 text-[14px] text-cream-foreground">{line}</p>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
          <span className="flex gap-[3px]">{[0, 1, 2, 3, 4, 5].map(i => <span key={i} className={cn('h-[5px] w-3.5 rounded-full', i < step ? 'bg-primary' : 'bg-border-strong')} />)}</span>
          {step ? `help ${step} of 6 · no answer given` : 'help grows one rung at a time'}
        </div>
      </div>
    ),
  };
}

function testsPlay(step: number): PlayView {
  const ran = step > 0;
  return {
    soc: ran ? 'Proven. That one is yours now.' : 'Think it works? Let the tests say.',
    mood: ran ? 'proud' : 'curious',
    action: ran ? undefined : 'Run hidden tests',
    done: ran,
    scene: (
      <div className="grid h-full content-center gap-4">
        <pre className="overflow-hidden rounded-[4px] bg-[var(--code-bg)] px-4 py-3 font-mono text-[12px] leading-[21px] text-[var(--code-fg)] sm:text-[13px]">
          {'def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i'}
        </pre>
        <div className="flex min-h-8 flex-wrap items-center gap-2">
          {ran ? (
            <>
              {[0, 1, 2, 3].map(i => (
                <span key={i} className="film-pass grid size-8 place-items-center rounded-[6px] bg-proof text-[var(--proof-foreground)]" style={at(150 + i * 260)}>
                  <Check className="size-4" strokeWidth={3} aria-hidden="true" />
                </span>
              ))}
              <span className="film-beat ml-1 font-mono text-[13px] text-muted-foreground" style={at(1250)}>4 / 4 hidden tests passed</span>
            </>
          ) : <span className="font-mono text-[13px] text-muted-foreground">4 hidden tests, not run yet</span>}
        </div>
        {ran ? (
          <div className="film-beat flex items-center gap-3 rounded-[4px] border bg-card px-4 py-3" style={at(1600)}>
            <StatusIcon status="mastered" size={24} />
            <span className="font-medium">Hash maps</span>
            <span className="ml-auto text-[13px] text-muted-foreground">learned</span>
          </div>
        ) : null}
      </div>
    ),
  };
}

const REVIEWS = [
  { when: 'Today', next: 'in 3 days' },
  { when: '3 days later', next: 'in 1 week' },
  { when: '1 week later', next: 'in 3 weeks' },
  { when: '3 weeks later', next: 'in 2 months' },
] as const;

function reviewPlay(step: number): PlayView {
  const now = REVIEWS[step];
  const last = step === REVIEWS.length - 1;
  return {
    soc: step === 0 ? 'Learned today. I’ll ask again soon.' : last ? 'Each time, the gap grows.' : 'Still got it? Good. Longer gap next.',
    mood: step === 0 ? 'happy' : last ? 'proud' : 'wink',
    action: last ? undefined : `Skip ahead: ${REVIEWS[step + 1].when}`,
    done: last,
    scene: (
      <div className="grid h-full content-center gap-4">
        <p key={step} className="film-beat text-[20px] font-medium tracking-[-0.02em] sm:text-[24px]">{now.when}</p>
        <div className="flex items-center gap-3 rounded-[4px] border bg-card px-4 py-3">
          <StatusIcon status={step === 0 ? 'mastered' : 'review'} size={24} />
          <span className="font-medium">Hash maps</span>
          <span className="ml-auto text-[13px] text-muted-foreground">{step === 0 ? 'learned' : 'review passed'}</span>
        </div>
        <div className="flex items-center gap-3 rounded-[4px] border border-dashed px-4 py-3 text-[14px] text-muted-foreground">
          <StatusIcon status="review" size={20} />
          Next review {now.next}
        </div>
        <ol className="flex flex-wrap gap-1.5" aria-label="Review gaps so far">
          {REVIEWS.map((r, i) => (
            <li key={r.next} className={cn('rounded-full border px-2.5 py-0.5 text-[12px] tabular-nums', i <= step ? 'border-ink bg-ink text-ink-foreground' : 'border-border-strong text-muted-foreground')}>{r.next.replace('in ', '')}</li>
          ))}
        </ol>
      </div>
    ),
  };
}

const START: Record<PlayId, number> = { goal: 0, plan: 0, check: 0, help: 0, tests: 0, review: 0 };

export function ProductPlays({ className }: { className?: string }) {
  const [play, setPlay] = useState(0);
  const [steps, setSteps] = useState(START);
  const current = PLAYS[play];
  const step = steps[current.id];
  const set = (value: number) => setSteps(s => ({ ...s, [current.id]: value }));

  const view: PlayView = (() => {
    switch (current.id) {
      case 'goal': return goalPlay(step, set);
      case 'plan': return planPlay(step);
      case 'check': return checkPlay(step, set);
      case 'help': return helpPlay(step);
      case 'tests': return testsPlay(step);
      case 'review': return reviewPlay(step);
    }
  })();
  const following = PLAYS[(play + 1) % PLAYS.length];

  return (
    <div className={cn('relative', className)}>
      <div className="paper relative overflow-hidden rounded-[4px] shadow-floating">
        <div className="flex items-center gap-2 border-b px-4 py-2.5">
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="ml-2 hidden text-[13px] text-muted-foreground sm:inline">socrat · {current.title.toLowerCase()}</span>
          <span className="font-hand ml-auto text-[18px] text-pen">you press, it plays</span>
        </div>

        <div className="grid sm:grid-cols-[minmax(0,1fr)_190px]">
          <div role="group" aria-label={current.title} className="min-h-[340px] px-5 py-5 sm:min-h-[380px] sm:px-10">
            {view.scene}
          </div>
          {/* Soc narrates from the side of the sheet; a new mood replays his reaction. */}
          <div aria-hidden="true" className="pointer-events-none hidden content-end justify-items-end pr-5 pb-3 sm:grid">
            <p key={`${current.id}-${step}`} className="film-beat soc-bubble mb-4 w-full rounded-[4px] border-2 border-[var(--soc-outline)] bg-card px-3 py-2 text-[15px] leading-snug" data-side="right">
              {view.soc}
            </p>
            <SocFigure mood={view.mood} size={136} idle />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 border-t px-5 py-3 sm:px-10">
          {view.action ? (
            <button type="button" onClick={() => set(step + 1)} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-ink px-5 text-[15px] font-semibold text-ink-foreground transition-transform active:scale-[0.97]">
              <Play className="size-4" aria-hidden="true" /> {view.action}
            </button>
          ) : null}
          {view.done ? (
            <button type="button" onClick={() => setPlay((play + 1) % PLAYS.length)} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-ink px-5 text-[15px] font-semibold text-ink-foreground transition-transform active:scale-[0.97]">
              <Play className="size-4" aria-hidden="true" /> Next: {following.title}
            </button>
          ) : null}
          {step > 0 ? (
            <button type="button" onClick={() => set(0)} className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border-strong px-4 text-[15px] transition-colors hover:bg-hi-select">
              <RotateCcw className="size-4" aria-hidden="true" /> Start over
            </button>
          ) : null}
          <p role="status" className="sr-only">{view.soc}</p>
        </div>
      </div>

      <ol className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-6 sm:gap-3" aria-label="Plays">
        {PLAYS.map((p, i) => (
          <li key={p.id} className="min-w-0">
            <button
              type="button"
              onClick={() => setPlay(i)}
              aria-current={i === play ? 'step' : undefined}
              className={cn('grid w-full gap-2 text-left', i !== play && 'opacity-60 hover:opacity-100')}
            >
              <span className={cn('block h-[3px] rounded-full', i === play ? 'bg-ink' : 'bg-border-strong')} />
              <span className="flex items-baseline gap-1.5 text-[13px] font-medium sm:text-[14px]">
                <span className="text-muted-foreground tabular-nums">{i + 1}</span>
                <span className="min-w-0 [overflow-wrap:anywhere]">{p.title}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
      <p aria-hidden="true" className="mt-4 flex items-center gap-2 sm:hidden"><Soc size={32} mood={view.mood} /><span className="font-hand text-[20px] text-pen">{view.soc}</span></p>
      <p className="mt-2 text-[15px] text-muted-foreground">{current.text}</p>
    </div>
  );
}
