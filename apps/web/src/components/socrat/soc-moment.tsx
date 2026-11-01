'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { SocFigure, type SocMood } from '@/components/socrat/soc';

/**
 * Soc reacting to a moment: flies in from the corner, grows, says one line, leaves.
 * Used for an accepted solution (a wink and a joke) and for a screenshot during a test
 * (a little bigger, angry, one line of mock). Reduced motion gets a plain fade.
 */

const CELEBRATE = [
  'Accepted. The compiler and I are both mildly impressed.',
  'All tests green. Somewhere a rubber duck just retired.',
  'Accepted! I would high-five you, but I am a marble bust.',
  'That ran faster than my last philosophy lecture.',
  'Accepted. Your future self says thanks, and also drink water.',
  'Clean solve. Even the edge cases clapped.',
  'Accepted. I checked twice. I am a statue, I have time.',
  'You and the judge agree. Rare. Savour it.',
  'Accepted! Off-by-one errors fear you now.',
  'Green across the board. Very Greek of you: logical and dramatic.',
  'Accepted. I knew you could. I said nothing, as is my method.',
  'The tests asked hard questions. You had answers. Socratic.',
  'Accepted. That loop knew exactly when to stop. Respect.',
  'Solved. If code could blush, the judge would be pink.',
  'Accepted. Write it down somewhere: you did that.',
  'Nailed it. Even the hidden tests came out to wave.',
  'Accepted. I have seen empires fall slower than that runtime.',
  'All green. Plato would have written a dialogue about this.',
  'Accepted. Your variables were named, your bugs were not.',
  'Solved. I am adding this to my list of favourite moments. It is a short list.',
  'Accepted. The stack did not overflow, and neither did my pride.',
  'That is a pass. Treat yourself to one (1) smug grin.',
  'Accepted. Know thyself? You know loops, at least.',
  'Ding. Accepted. That was the sound of a skill levelling up.',
  'Accepted. My beard approves, and it is very hard to please.',
  'Green! Somewhere a recruiter felt a disturbance in the force.',
  'Accepted. Hemlock-free, bug-free. A good day.',
  'Solved on your terms. The judge just signed off.',
  'Accepted. I would wink twice, but I only have the one move.',
  'Pass. Your code survived cross-examination. I am the cross-examiner.',
];

const MOCK = [
  'A screenshot? Your memory is cheaper, and it is in your head already.',
  'Snapping the question will not snap the answer into your brain.',
  'I saw that. Statues see everything. We have nothing else to do.',
  'Screenshots do not count as studying. Neither does staring at me.',
  'Save the question in your head, not your gallery.',
  'A picture is worth a thousand words. None of them the answer.',
  'Bold move. Wrong test. Eyes on the question.',
  'You know I am made of stone, not stupidity, right?',
  'Even Plato took notes by hand. Put the camera away.',
  'Screenshot taken. Integrity: still loading.',
  'I did not survive two thousand years to watch this.',
  'Interesting technique. Have you tried thinking instead?',
];

const PASTE = [
  'No pasting in a test. Your own keystrokes only.',
  'Copy and paste are on a break until you submit.',
  'Nice try. Type it, prove it.',
];

/** A shuffle bag per list, kept in this browser: every line plays once before any repeats. */
function nextLine(lines: string[], bag: string): string {
  let order: number[] = [];
  try { order = JSON.parse(localStorage.getItem(bag) ?? '[]'); } catch { /* fresh bag */ }
  if (!Array.isArray(order) || !order.length || order.some(i => typeof i !== 'number' || i >= lines.length)) {
    order = lines.map((_, i) => i);
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
  }
  const [pick, ...rest] = order;
  try { localStorage.setItem(bag, JSON.stringify(rest)); } catch { /* still random */ }
  return lines[pick];
}

export type MomentKind = 'celebrate' | 'mock' | 'paste';

interface Moment { kind: MomentKind; line: string; id: number }

const LOOK: Record<MomentKind, { mood: SocMood; size: number; ms: number }> = {
  celebrate: { mood: 'wink', size: 168, ms: 4200 },
  mock: { mood: 'angry', size: 150, ms: 3600 },
  paste: { mood: 'worried', size: 104, ms: 2200 },
};

export function SocMomentView({ moment, onDone }: { moment: Moment | null; onDone(): void }) {
  useEffect(() => {
    if (!moment) return;
    const timer = setTimeout(onDone, LOOK[moment.kind].ms);
    return () => clearTimeout(timer);
  }, [moment, onDone]);
  if (!moment) return null;
  const look = LOOK[moment.kind];
  return (
    <div className="pointer-events-none fixed right-4 bottom-[calc(88px+env(safe-area-inset-bottom))] z-[80] flex items-end gap-3 md:right-8 md:bottom-8" role="status" aria-live="polite">
      <style>{`
        @keyframes soc-fly { 0% { transform: translate(60px, 120px) scale(.4) rotate(-12deg); opacity: 0 }
          55% { transform: translate(0, -14px) scale(1.12) rotate(4deg); opacity: 1 }
          75% { transform: translate(0, 0) scale(.98) rotate(-2deg) } 100% { transform: none } }
        @keyframes soc-shake { 0%,100% { transform: scale(1.08) } 20% { transform: scale(1.14) rotate(-4deg) }
          40% { transform: scale(1.14) rotate(4deg) } 60% { transform: scale(1.12) rotate(-3deg) } 80% { transform: scale(1.1) rotate(2deg) } }
        @keyframes soc-say { from { opacity: 0; transform: translateY(8px) scale(.96) } to { opacity: 1; transform: none } }
        @media (prefers-reduced-motion: reduce) { .soc-moment, .soc-moment-say { animation: none !important } }
      `}</style>
      <p
        className="soc-moment-say max-w-[260px] rounded-[18px] rounded-br-sm border border-border-strong bg-card px-4 py-3 font-hand text-[19px] leading-snug text-foreground shadow-floating"
        style={{ animation: 'soc-say 260ms 320ms both ease-out' }}
      >
        {moment.line}
      </p>
      <div
        key={moment.id}
        className="soc-moment flex-none"
        style={{ animation: moment.kind === 'mock' ? 'soc-fly 520ms both cubic-bezier(.2,.9,.3,1.2), soc-shake 600ms 560ms 2 both' : 'soc-fly 620ms both cubic-bezier(.2,.9,.3,1.25)' }}
      >
        <SocFigure mood={look.mood} size={look.size} idle />
      </div>
    </div>
  );
}

/** Show Soc for a moment. `show('celebrate')` picks a line no one has seen in a while. */
export function useSocMoment() {
  const [moment, setMoment] = useState<Moment | null>(null);
  const counter = useRef(0);
  const show = useCallback((kind: MomentKind) => {
    const lines = kind === 'celebrate' ? CELEBRATE : kind === 'mock' ? MOCK : PASTE;
    counter.current += 1;
    setMoment({ kind, line: nextLine(lines, `socrat:soc-lines:${kind}`), id: counter.current });
  }, []);
  const done = useCallback(() => setMoment(null), []);
  return { show, element: <SocMomentView moment={moment} onDone={done} /> };
}

const SCREENSHOT_KEYS = (e: KeyboardEvent) =>
  e.key === 'PrintScreen'
  // Windows snipping (Win+Shift+S) and macOS captures (Cmd+Shift+3/4/5), when the page sees them.
  || (e.shiftKey && (e.metaKey || e.ctrlKey) && ['s', 'S', '3', '4', '5'].includes(e.key));

/**
 * While `active`: no copy, cut, paste, drag or right-click menu anywhere on the page
 * (including the code editor), and a screenshot shortcut earns an angry Soc.
 * Browsers cannot stop a screenshot; this makes the rule visible and the attempt awkward.
 */
export function useExamGuard(active: boolean) {
  const { show: showNow, element } = useSocMoment();
  const last = useRef(0);
  // One reaction per gesture: a shortcut fires both keydown and keyup.
  const show = useCallback((kind: MomentKind) => {
    if (Date.now() - last.current < 1500) return;
    last.current = Date.now();
    showNow(kind);
  }, [showNow]);
  useEffect(() => {
    if (!active) return;
    const block = (e: Event) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.type === 'paste' || e.type === 'copy' || e.type === 'cut') show('paste');
    };
    const keys = (e: KeyboardEvent) => {
      if (SCREENSHOT_KEYS(e)) {
        if (e.key === 'PrintScreen') {
          // Overwrite whatever the capture put on the clipboard, where the browser allows it.
          navigator.clipboard?.writeText('').catch(() => undefined);
        }
        show('mock');
      }
    };
    const events = ['copy', 'cut', 'paste', 'contextmenu', 'dragstart', 'drop'] as const;
    // Capture on window runs before the editor's own handlers, so its paste is blocked too.
    events.forEach(name => window.addEventListener(name, block, true));
    window.addEventListener('keyup', keys, true);
    window.addEventListener('keydown', keys, true);
    return () => {
      events.forEach(name => window.removeEventListener(name, block, true));
      window.removeEventListener('keyup', keys, true);
      window.removeEventListener('keydown', keys, true);
    };
  }, [active, show]);
  return element;
}

/** Drop-in for pages: `<ExamGuard active />` renders nothing until Soc has something to say. */
export function ExamGuard({ active }: { active: boolean }) {
  return useExamGuard(active);
}
