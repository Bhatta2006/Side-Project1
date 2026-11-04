'use client';

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { NAME, NAV } from '@/lib/routes';
import { useSession } from '@/lib/session';
import { useCourse } from '@/lib/course';
import type { CourseFeatures } from '@/lib/types';
import { cn } from '@/lib/utils';
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
  /** Page the step lives on; the tour walks the learner there through the sidebar. */
  route: string;
  /** `data-tour` of the sidebar link for `route`, spotlit while the tour travels there. */
  nav?: string;
  /** `data-tour` value of the element to spotlight; the first visible match wins. None: centred card. */
  target?: string;
  title: string;
  body: string;
}

/** The Practice step describes the learner's own course's Practice, nothing from another course. */
function practiceStep(features: CourseFeatures, studio?: string): Step {
  const extras = features.companies
    ? ' The tabs above add problems from LeetCode, CSES and Codeforces, company questions and timed sprints.'
    : features.library
      ? ' The tabs above add problems from LeetCode, CSES and Codeforces and timed focus sprints.'
      : '';
  return {
    route: '/studio', nav: 'practice', target: features.library ? 'practice-nav' : undefined,
    title: studio ?? NAME.practice,
    body: `Pick any topic you have opened and Socrat writes fresh practice questions for your course. Earn stars and keep your streak going.${extras}`,
  };
}

const STEPS: Step[] = [
  {
    route: '/today',
    title: 'Welcome to Socrat',
    body: 'Let me walk you through every page. I will move around for you, so just follow along. You can replay this from Settings.',
  },
  {
    route: '/today', nav: 'today', target: 'today-next',
    title: NAME.today,
    body: 'Your plan for the day, sized to your daily minutes. This card is always your next lesson, check or problem. Start here each time you sit down.',
  },
  {
    route: '/today', target: 'tutor',
    title: 'Ask Soc, your tutor',
    body: 'Stuck? Soc nudges you with questions and hints rather than handing over answers.',
  },
  {
    route: '/plan', nav: 'skills', target: 'skills-current',
    title: NAME.skills,
    body: 'Your course roadmap. Lessons teach each skill, then a check or checkpoint proves it before the next one unlocks.',
  },
  { route: '/studio', nav: 'practice', title: NAME.practice, body: '' }, // replaced per course
  {
    route: '/playground', nav: 'playground', target: 'playground-ask',
    title: NAME.playground,
    body: 'Ask about any concept and Socrat draws an interactive explanation you can change and replay.',
  },
  {
    route: '/progress', nav: 'evidence', target: 'evidence-course',
    title: NAME.evidence,
    body: 'What you have proven so far: skill mastery, your streak and history. Your weekly assessment appears here when it is ready.',
  },
  {
    route: '/settings', nav: 'settings', target: 'settings-schedule',
    title: NAME.settings,
    body: 'Your schedule and appearance live here. Press Ctrl K (⌘K on a Mac) any time to search everything.',
  },
  {
    route: '/today', nav: 'today',
    title: 'You are all set',
    body: 'Back to Today. Learn it, then prove it.',
  },
];

/** How long the spotlight rests on the sidebar link before the page changes, so the move reads as a click. */
const TRAVEL_MS = 450;
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

function sameRect(a: DOMRect | null, b: DOMRect | null) {
  if (!a || !b) return a === b;
  return a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

type Place = { left: number; top?: number; bottom?: number };

/**
 * Puts the card beside a sidebar target, else below, above or beside anything else. A target too
 * big for any of those gets the card pinned to the viewport's bottom edge, over its lower part.
 */
function placeCard(rect: DOMRect | null, height: number): Place | null {
  if (!rect) return null;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(WIDTH, vw - 32);
  const clampX = (x: number) => Math.max(16, Math.min(x, vw - width - 16));
  const clampY = (y: number) => Math.max(16, Math.min(y, vh - height - 16));
  const space = PAD + GAP;
  const below = rect.bottom + space + height + 16 <= vh;
  const above = rect.top - space - height - 16 >= 0;
  const right = rect.right + space + width + 16 <= vw;
  const sideTop = clampY(rect.top + rect.height / 2 - height / 2);
  const centreX = clampX(rect.left + rect.width / 2 - width / 2);
  if (right && (rect.left < vw / 3 && rect.height < vh / 2 || !below && !above)) return { left: rect.right + space, top: sideTop };
  if (below) return { left: centreX, top: rect.bottom + space };
  if (above) return { left: centreX, bottom: vh - rect.top + space };
  if (rect.left - space - width - 16 >= 0) return { left: rect.left - space - width, top: sideTop };
  return { left: centreX, bottom: 16 };
}

/**
 * First-run tour that walks the learner through every page, navigating for them. Shows once per
 * account (the server records it when the learner finishes or skips), starting on Today; Settings
 * can replay it.
 */
export function Tour() {
  const { profile, refresh } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [height, setHeight] = useState(220);
  const card = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const recorded = useRef(false);
  const scrolled = useRef(-1);
  const lastTop = useRef<number | undefined>(undefined);
  const tries = useRef(0);

  const { features, shape } = useCourse();
  const steps = STEPS.map(step => (step.nav === 'practice' ? practiceStep(features, shape && shape.studio !== 'code' ? shape.name : undefined) : step));
  const step = steps[index];
  const travelling = open && pathname !== step.route;

  const start = useCallback(() => {
    returnFocus.current = document.activeElement as HTMLElement | null;
    scrolled.current = -1;
    setIndex(0);
    setOpen(true);
  }, []);

  // Auto-start once, on Today, for a learner who has not seen it.
  useEffect(() => {
    if (open || !profile || profile.tour_seen || recorded.current || pathname !== '/today' || seenHere()) return;
    const timer = window.setTimeout(start, 600);
    return () => window.clearTimeout(timer);
  }, [open, profile, pathname, start]);

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

  // Walk to the step's page: the spotlight lands on its sidebar link first, then the page changes.
  useEffect(() => {
    if (!travelling) return;
    const timer = window.setTimeout(() => router.push(step.route), TRAVEL_MS);
    return () => window.clearTimeout(timer);
  }, [travelling, step.route, router]);

  // Track the spotlighted element. Polling also catches content that loads after navigation;
  // until the target appears the spotlight rests on the sidebar link.
  useLayoutEffect(() => {
    if (!open) return;
    const measure = () => {
      if (scrolled.current !== index) { scrolled.current = index; tries.current = 0; }
      const target = travelling ? null : visibleTarget(step.target);
      const box = target?.getBoundingClientRect();
      // Scroll only once the target has held still for a poll: loading content and the router's
      // scroll reset can move it. A few retries cover a reset that lands after our scroll.
      const settled = box !== undefined && box.top === lastTop.current;
      lastTop.current = box?.top;
      const offscreen = box && (box.top < 0 || (box.top > 104 && box.bottom > window.innerHeight));
      if (target && settled && offscreen && tries.current < 3) {
        tries.current += 1;
        const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        // Top of the viewport (under the sticky header, see globals.css) leaves room for the card below.
        target.scrollIntoView({ block: 'start', behavior: smooth ? 'smooth' : 'auto' });
      }
      const el = target ?? (step.target || travelling ? visibleTarget(step.nav) : null);
      const next = el ? el.getBoundingClientRect() : null;
      setRect(prev => (sameRect(prev, next) ? prev : next));
      if (card.current) setHeight(card.current.offsetHeight);
    };
    measure();
    const timer = window.setInterval(measure, 150);
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
    };
  }, [open, step, index, travelling]);

  useEffect(() => {
    if (open && !travelling) card.current?.focus({ preventScroll: true });
  }, [open, index, travelling]);

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
  const destination = NAV.find(item => item.href === step.route)?.label;

  return (
    // CSS only: the shell renders this on every route, so it must not pull in motion's engine.
    open ? (
        <div className="fixed inset-0 z-[70] animate-in fade-in duration-200">
          {/* Blocks the page while the tour is open; the scrim comes from the spotlight's ring. */}
          <div className={cn('absolute inset-0 transition-colors duration-300', !rect && 'bg-ink/60')} aria-hidden="true" />
          {rect ? (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute rounded-[20px] ring-2 ring-primary transition-[left,top,width,height] duration-500 ease-[var(--ease-soft)] motion-reduce:transition-none"
              style={{
                boxShadow: '0 0 0 9999px color-mix(in srgb, var(--ink), transparent 40%)',
                left: rect.left - PAD, top: rect.top - PAD, width: rect.width + PAD * 2, height: rect.height + PAD * 2,
              }}
            >
              {/* A ripple on the sidebar link while travelling, like a click; a slow glow once landed. */}
              <span
                key={`${index}-${travelling}`}
                className={cn(
                  'absolute inset-0 rounded-[inherit] ring-2 ring-primary motion-reduce:hidden',
                  travelling ? 'animate-ping' : 'animate-[pulse-slow_2.4s_ease-in-out_infinite]',
                )}
              />
            </div>
          ) : null}
          {travelling ? (
            <p role="status" className="absolute bottom-24 left-1/2 -translate-x-1/2 rounded-full bg-card px-4 py-2 font-hand text-[19px] whitespace-nowrap text-pen shadow-floating animate-in fade-in slide-in-from-bottom-2 duration-300 md:bottom-8">
              {destination ? `Heading to ${destination}…` : 'One moment…'}
            </p>
          ) : null}
          <div
            ref={card}
            role="dialog"
            aria-modal="true"
            aria-labelledby="tour-title"
            aria-describedby="tour-body"
            tabIndex={-1}
            className={cn(
              'absolute paper rounded-card text-card-foreground shadow-floating outline-none transition-[left,top,bottom,opacity,scale] duration-500 ease-[var(--ease-soft)] motion-reduce:transition-none',
              centred ? 'top-1/2 left-1/2 w-[min(400px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 p-6' : 'p-5',
              travelling && 'pointer-events-none scale-95 opacity-0',
            )}
            style={centred ? undefined : { left: place.left, top: place.top, bottom: place.bottom, width: Math.min(WIDTH, window.innerWidth - 32) }}
          >
            <div key={index} className="animate-in fade-in slide-in-from-bottom-2 duration-300 motion-reduce:animate-none">
              <Soc size={56} mood={last ? 'happy' : index === 0 ? 'wink' : 'curious'} className="float-right -mt-1 -mr-1 ml-3" />
              <p className="font-hand text-[19px] text-pen tabular-nums" aria-live="polite">
                {index + 1} of {steps.length}
              </p>
              <h2 id="tour-title" className="mt-1 font-display text-xl font-semibold tracking-[-0.03em]">{step.title}</h2>
              <p id="tour-body" className="mt-2 text-[15px] text-muted-foreground">{step.body}</p>
            </div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-border-strong" aria-hidden="true">
              <div className="h-full rounded-full bg-primary transition-[width] duration-500 ease-[var(--ease-soft)]" style={{ width: `${((index + 1) / steps.length) * 100}%` }} />
            </div>
            <div className="mt-5 flex items-center gap-2">
              {last ? null : <Button variant="link" size="sm" onClick={close}>Skip tour</Button>}
              <div className="ml-auto flex gap-2">
                {index > 0 ? <Button variant="outline" size="sm" onClick={back}>Back</Button> : null}
                <Button size="sm" onClick={next}>{last ? 'Start learning' : index === 0 ? 'Show me around' : 'Next'}</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null
  );
}
