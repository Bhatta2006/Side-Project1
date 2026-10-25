'use client';

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';
import { NAME } from '@/lib/routes';
import { useSession } from '@/lib/session';
import { Button } from '@/components/ui/button';
import { Soc } from '@/components/socrat/illustration';

/** Settings › "Replay tour" fires this; the shell's Tour listens. */
export const TOUR_EVENT = 'socrat:tour';
/** Set once the tour is done in this browser, so a failed save never shows it twice. */
const SEEN_KEY = 'socrat:tour-seen';

function seenHere() {
  try { return localStorage.getItem(SEEN_KEY) === '1'; } catch { return false; }
}

interface Step {
  /** `data-tour` value of the element to spotlight; the first visible match wins. None: centred card. */
  target?: string;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    title: 'Welcome to Socrat',
    body: 'A quick look at where everything lives. It takes under a minute, and you can replay it from Settings.',
  },
  {
    target: 'today',
    title: NAME.today,
    body: 'Your plan for the day: the next lesson, check or problem, sized to your daily minutes. Start here each time you sit down.',
  },
  {
    target: 'skills',
    title: NAME.skills,
    body: 'Your course roadmap. Lessons teach each skill, then a check or checkpoint proves it before the next one unlocks.',
  },
  {
    target: 'practice',
    title: NAME.practice,
    body: 'Problems from LeetCode, CSES and Codeforces matched to the skills you have unlocked, plus company questions and timed focus sprints.',
  },
  {
    target: 'evidence',
    title: NAME.evidence,
    body: 'What you have proven so far: skill mastery, your streak and history. Your weekly assessment appears here when it is ready.',
  },
  {
    target: 'tutor',
    title: 'Ask Soc, your tutor',
    body: 'Stuck? Soc nudges you with questions and hints rather than handing over answers. Press Ctrl K (⌘K on a Mac) any time to search. Settings has your schedule and replays this tour.',
  },
  {
    title: 'You are all set',
    body: 'Start with Today. Learn it, then prove it.',
  },
];

const PAD = 6;
const GAP = 14;
const WIDTH = 340;

function visibleTarget(name: string | undefined): HTMLElement | null {
  if (!name) return null;
  for (const el of document.querySelectorAll<HTMLElement>(`[data-tour="${name}"]`)) {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) return el;
  }
  return null;
}

type Place = { left: number; top?: number; bottom?: number };

/** Puts the card beside a sidebar target, or above/below anything else, inside the viewport. */
function placeCard(rect: DOMRect | null, height: number): Place | null {
  if (!rect) return null;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(WIDTH, vw - 32);
  const clampX = (x: number) => Math.max(16, Math.min(x, vw - width - 16));
  const clampY = (y: number) => Math.max(16, Math.min(y, vh - height - 16));
  if (rect.right + GAP + width + 16 <= vw && rect.left < vw / 3 && rect.height < vh / 2) {
    return { left: rect.right + PAD + GAP, top: clampY(rect.top + rect.height / 2 - height / 2) };
  }
  const left = clampX(rect.left + rect.width / 2 - width / 2);
  if (rect.top > vh / 2) return { left, bottom: vh - rect.top + PAD + GAP };
  return { left, top: clampY(rect.bottom + PAD + GAP) };
}

/**
 * First-run tour of the app. Shows once per account (the server records it when the learner
 * finishes or skips), starting on Today; Settings can replay it.
 */
export function Tour() {
  const { profile, refresh } = useSession();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [height, setHeight] = useState(220);
  const card = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const recorded = useRef(false);

  const steps = STEPS;
  const step = steps[index];

  const start = useCallback(() => {
    returnFocus.current = document.activeElement as HTMLElement | null;
    setIndex(0);
    setOpen(true);
  }, []);

  // Auto-start once, on Today, for a learner who has not seen it.
  useEffect(() => {
    if (!profile || profile.tour_seen || recorded.current || pathname !== '/today' || seenHere()) return;
    const timer = window.setTimeout(start, 600);
    return () => window.clearTimeout(timer);
  }, [profile, pathname, start]);

  useEffect(() => {
    window.addEventListener(TOUR_EVENT, start);
    return () => window.removeEventListener(TOUR_EVENT, start);
  }, [start]);

  const close = useCallback(() => {
    setOpen(false);
    returnFocus.current?.focus?.();
    try { localStorage.setItem(SEEN_KEY, '1'); } catch { /* the server record is enough */ }
    if (recorded.current || profile?.tour_seen) return;
    recorded.current = true;
    api.post('/me/tour').then(() => refresh()).catch(() => undefined);
  }, [profile?.tour_seen, refresh]);

  // Track the spotlighted element through resizes and scrolling.
  useLayoutEffect(() => {
    if (!open) return;
    const measure = () => {
      const el = visibleTarget(step.target);
      setRect(el ? el.getBoundingClientRect() : null);
      if (card.current) setHeight(card.current.offsetHeight);
    };
    visibleTarget(step.target)?.scrollIntoView({ block: 'nearest' });
    measure();
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    return () => {
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
    };
  }, [open, step]);

  useEffect(() => {
    if (open) card.current?.focus();
  }, [open, index]);

  const last = index === steps.length - 1;
  const next = useCallback(() => (last ? close() : setIndex(i => i + 1)), [last, close]);
  const back = useCallback(() => setIndex(i => Math.max(0, i - 1)), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); close(); }
      else if (event.key === 'ArrowRight') { event.preventDefault(); next(); }
      else if (event.key === 'ArrowLeft') { event.preventDefault(); back(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, next, back, close]);

  const place = placeCard(rect, height);
  const centred = !place;

  return (
    // CSS only: the shell renders this on every route, so it must not pull in motion's engine.
    open ? (
        <div className="fixed inset-0 z-[70] animate-in fade-in duration-200">
          {/* Blocks the page while the tour is open; the scrim comes from the spotlight's ring. */}
          <div className={centred ? 'absolute inset-0 bg-ink/60' : 'absolute inset-0'} aria-hidden="true" />
          {rect ? (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute rounded-[20px] ring-2 ring-primary transition-[left,top,width,height] duration-300 ease-[var(--ease-soft)]"
              style={{
                boxShadow: '0 0 0 9999px color-mix(in srgb, var(--ink), transparent 40%)',
                left: rect.left - PAD, top: rect.top - PAD, width: rect.width + PAD * 2, height: rect.height + PAD * 2,
              }}
            />
          ) : null}
          <div
            ref={card}
            role="dialog"
            aria-modal="true"
            aria-labelledby="tour-title"
            aria-describedby="tour-body"
            tabIndex={-1}
            className={
              centred
                ? 'absolute top-1/2 left-1/2 w-[min(400px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 paper rounded-card p-6 text-card-foreground shadow-floating outline-none'
                : 'absolute paper rounded-card p-5 text-card-foreground shadow-floating outline-none'
            }
            style={centred ? undefined : { left: place.left, top: place.top, bottom: place.bottom, width: Math.min(WIDTH, window.innerWidth - 32) }}
          >
            <Soc size={56} mood={last ? 'happy' : index === 0 ? 'wink' : 'curious'} className="float-right -mt-1 -mr-1 ml-3" />
            <p className="font-hand text-[19px] text-pen tabular-nums" aria-live="polite">
              {index + 1} of {steps.length}
            </p>
            <h2 id="tour-title" className="mt-1 font-display text-xl font-semibold tracking-[-0.03em]">{step.title}</h2>
            <p id="tour-body" className="mt-2 text-[15px] text-muted-foreground">{step.body}</p>
            <div className="mt-4 flex items-center gap-1" aria-hidden="true">
              {steps.map((_, i) => (
                <span key={i} className={i === index ? 'h-1.5 w-5 rounded-full bg-primary' : 'size-1.5 rounded-full bg-border-strong'} />
              ))}
            </div>
            <div className="mt-5 flex items-center gap-2">
              {last ? null : <Button variant="link" size="sm" onClick={close}>Skip tour</Button>}
              <div className="ml-auto flex gap-2">
                {index > 0 ? <Button variant="outline" size="sm" onClick={back}>Back</Button> : null}
                <Button size="sm" onClick={next}>{last ? 'Start learning' : index === 0 ? 'Show me' : 'Next'}</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null
  );
}
