'use client';

import { useEffect, useRef, useState } from 'react';
import { Check, X } from 'lucide-react';
import { prefersReducedMotion } from '@/lib/motion';
import { Soc } from '@/components/socrat/illustration';
import { cn } from '@/lib/utils';

/*
 * A scripted replay of one tutoring exchange: slow code, Soc answers with a question, the learner
 * finds the idea, the hidden tests pass. It is a sample, labelled as one, and shows the finished
 * state at once when motion is reduced.
 */

type Line = { text: string; tone?: 'slow' | 'fixed' };

const SLOW: Line[] = [
  { text: 'def two_sum(nums, target):' },
  { text: '    for i in range(len(nums)):' },
  { text: '        for j in range(i + 1, len(nums)):', tone: 'slow' },
  { text: '            if nums[i] + nums[j] == target:' },
  { text: '                return [i, j]' },
];

const FIXED: Line[] = [
  { text: 'def two_sum(nums, target):' },
  { text: '    seen = {}', tone: 'fixed' },
  { text: '    for i, x in enumerate(nums):' },
  { text: '        if target - x in seen:', tone: 'fixed' },
  { text: '            return [seen[target - x], i]' },
  { text: '        seen[x] = i', tone: 'fixed' },
];

const MESSAGES = [
  { from: 'you', text: 'Why does this time out?' },
  { from: 'soc', text: 'For each number, what are you really searching for?' },
  { from: 'you', text: 'target − x… so I could look it up instead of looping?' },
  { from: 'soc', text: 'Try it. I’ll run the hidden tests.' },
] as const;

// Milliseconds from the start of a loop at which each step begins.
const TIMELINE = [0, 700, 1900, 3400, 4600, 5800, 6500, 7700];
const LAST = TIMELINE.length - 1;
const LOOP = 13000;
const KEYWORDS = /\b(def|for|in|if|return|range|len|enumerate)\b/g;

function highlight(text: string) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(KEYWORDS)) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    const builtin = ['range', 'len', 'enumerate'].includes(match[0]);
    parts.push(<span key={match.index} style={{ color: builtin ? 'var(--syntax-function)' : 'var(--syntax-keyword)' }}>{match[0]}</span>);
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

export function SocraticDemo({ className }: { className?: string }) {
  const [step, setStep] = useState(LAST);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReducedMotion() || typeof IntersectionObserver === 'undefined') return;
    let timers: number[] = [];
    let visible = false;
    const clear = () => { timers.forEach(clearTimeout); timers = []; };
    const play = () => {
      clear();
      TIMELINE.forEach((at, i) => timers.push(window.setTimeout(() => setStep(i), at)));
      timers.push(window.setTimeout(() => { if (visible) play(); }, LOOP));
    };
    const observer = new IntersectionObserver(([entry]) => {
      const was = visible;
      visible = entry.isIntersecting;
      if (visible && !was) play();
      if (!visible) clear();
    }, { threshold: 0.35 });
    if (root.current) observer.observe(root.current);
    return () => { observer.disconnect(); clear(); };
  }, []);

  const fixed = step >= 5;
  const passed = step >= 6 ? 4 : 2;
  const lines = fixed ? FIXED : SLOW;

  return (
    <figure ref={root} className={cn('socratic-demo relative', className)}>
      <figcaption className="sr-only">
        Sample session. A learner asks why their two-sum solution times out. Soc replies with a question
        instead of the answer, the learner switches to a hash map lookup, and all four hidden tests pass with one hint used.
      </figcaption>
      <div aria-hidden="true" className="overflow-hidden rounded-[24px] border bg-card shadow-floating">
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="size-2.5 rounded-full bg-border-strong" />
          <span className="font-mono ml-2 text-[12px] text-muted-foreground">two_sum.py</span>
          <span className="font-hand ml-auto text-[18px] text-pen">sample session</span>
        </div>

        <pre className="min-h-[164px] overflow-x-auto bg-[var(--code-bg)] px-4 py-3 font-mono text-[13px] leading-[22px] text-[var(--code-fg)] [font-variant-ligatures:none]">
          {lines.map((line, i) => (
            <div
              key={`${fixed}-${i}`}
              className={cn(
                'code-line -mx-1.5 px-1.5',
                line.tone === 'slow' && 'bg-[color-mix(in_srgb,var(--attention)_12%,transparent)] shadow-[inset_2px_0_0_var(--attention)]',
                line.tone === 'fixed' && 'bg-[color-mix(in_srgb,var(--highlight)_12%,transparent)]',
              )}
            >
              {highlight(line.text)}
            </div>
          ))}
        </pre>

        <div className="grid min-h-[208px] content-start gap-2.5 border-t px-4 py-4">
          {MESSAGES.map((m, i) => (
            <div key={i} data-step data-hidden={step < i + 1} className={cn('flex items-end gap-2', m.from === 'you' && 'justify-end')}>
              {m.from === 'soc' ? <Soc size={28} className="mb-0.5" /> : null}
              <p
                className={cn(
                  'max-w-[82%] px-3.5 py-2 text-[14px] leading-snug',
                  m.from === 'soc'
                    ? 'rounded-[16px_16px_16px_4px] border border-[color-mix(in_srgb,var(--highlight)_60%,var(--border))] bg-cream text-[15px] text-cream-foreground'
                    : 'rounded-[16px_16px_4px_16px] bg-raised',
                )}
              >
                {m.text}
              </p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t px-4 py-3 text-[12px]">
          <span className="flex items-center gap-1.5">
            {[0, 1, 2, 3].map(i => (
              <span
                key={i}
                data-ok={i < passed}
                className="test-dot grid size-[18px] place-items-center rounded-[6px] bg-[color-mix(in_srgb,var(--attention)_22%,transparent)] text-[var(--proof-foreground)]"
              >
                {i < passed ? <Check className="size-3" strokeWidth={3} /> : <X className="size-3 text-attention" strokeWidth={3} />}
              </span>
            ))}
          </span>
          <span className="font-mono text-muted-foreground tabular-nums">
            {passed === 4 ? '4 / 4 passed · 1 hint used' : '2 / 4 · time limit on large input'}
          </span>
          <span className="ml-auto flex items-center gap-2">
            <span className="flex gap-[3px]">
              {[0, 1, 2, 3, 4, 5].map(i => (
                <span key={i} className={cn('h-[5px] w-3.5 rounded-full', i < (step >= 2 ? 1 : 0) ? 'bg-primary' : 'bg-border-strong')} />
              ))}
            </span>
            <span className="font-mono text-muted-foreground">Help {step >= 2 ? 1 : 0}/6</span>
          </span>
        </div>
      </div>

      <span
        aria-hidden="true"
        data-step
        data-hidden={step < LAST}
        className="font-hand absolute -bottom-10 right-6 rotate-[-5deg] rounded-[12px] border-2 border-pen bg-card px-3.5 py-1 text-[24px] text-pen shadow-[3px_3px_0_var(--pen)] sm:-right-5"
      >
        solved it! hash maps ✓
      </span>
    </figure>
  );
}
