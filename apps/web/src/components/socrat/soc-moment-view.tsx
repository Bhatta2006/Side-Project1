'use client';

import { useEffect, useState } from 'react';
import { SocFigure, type SocMood } from '@/components/socrat/soc';
import type { Moment, MomentKind } from '@/components/socrat/soc-moment';

/** Soc's moment on screen, with its lines. Loaded on first use so pages do not carry the jokes. */

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

const LINES: Record<MomentKind, string[]> = { celebrate: CELEBRATE, mock: MOCK, paste: PASTE };

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

const LOOK: Record<MomentKind, { mood: SocMood; size: number; ms: number }> = {
  celebrate: { mood: 'wink', size: 168, ms: 4200 },
  mock: { mood: 'angry', size: 150, ms: 3600 },
  paste: { mood: 'worried', size: 104, ms: 2200 },
};

export default function SocMomentView({ moment, onDone }: { moment: Moment | null; onDone(): void }) {
  // One line per moment, from that kind's shuffle bag.
  const [said, setSaid] = useState<{ id: number; line: string } | null>(null);
  useEffect(() => {
    if (moment) setSaid({ id: moment.id, line: nextLine(LINES[moment.kind], `socrat:soc-lines:${moment.kind}`) });
  }, [moment]);
  useEffect(() => {
    if (!moment) return;
    const timer = setTimeout(onDone, LOOK[moment.kind].ms);
    return () => clearTimeout(timer);
  }, [moment, onDone]);
  if (!moment || said?.id !== moment.id) return null;
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
        className="soc-moment-say max-w-[260px] rounded-[4px] rounded-br-sm border border-border-strong bg-card px-4 py-3 font-hand text-[19px] leading-snug text-foreground shadow-floating"
        style={{ animation: 'soc-say 260ms 320ms both ease-out' }}
      >
        {said.line}
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
