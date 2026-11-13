'use client';

import { useEffect, useRef, useState } from 'react';
import { prefersReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { SocFigure, type SocMood } from '@/components/socrat/soc';

/** What Soc says when poked: questions, never answers. */
const POKES: [SocMood, string][] = [
  ['curious', 'Why did you click me?'],
  ['thinking', 'What would you try first?'],
  ['surprised', 'Is that your final answer?'],
  ['happy', 'Good question. What do you think?'],
  ['confused', 'And how do you know that?'],
  ['wink', 'I only give hints. Mostly.'],
];

/**
 * Soc, alive: his eyes follow the pointer, and a click makes him react with a question in a
 * handwritten speech bubble. `say` shows a line from outside (the landing hero's goal chips).
 * Reduced motion keeps him still; he still answers clicks.
 */
export function LiveSoc({
  mood = 'neutral',
  say,
  books = true,
  size,
  className,
  bubbleSide = 'left',
}: {
  mood?: SocMood;
  say?: string | null;
  books?: boolean;
  size?: number;
  className?: string;
  bubbleSide?: 'left' | 'right';
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const [look, setLook] = useState({ x: 0, y: 0 });
  const [poke, setPoke] = useState<number | null>(null);
  const [still, setStill] = useState(true);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    setStill(false);
    let frame = 0;
    const onMove = (event: PointerEvent) => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const box = ref.current?.getBoundingClientRect();
        if (!box) return;
        const cx = box.left + box.width / 2;
        const cy = box.top + box.height * 0.3;
        setLook({ x: (event.clientX - cx) / (window.innerWidth / 2), y: (event.clientY - cy) / (window.innerHeight / 2) });
      });
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => { cancelAnimationFrame(frame); window.removeEventListener('pointermove', onMove); };
  }, []);

  // A poke wears off after a few seconds; a new line from outside replaces it at once.
  useEffect(() => {
    if (poke === null) return;
    const timer = window.setTimeout(() => setPoke(null), 3200);
    return () => window.clearTimeout(timer);
  }, [poke]);
  useEffect(() => { setPoke(null); }, [say]);

  const current = poke !== null ? POKES[poke] : null;
  const line = current?.[1] ?? say ?? null;
  return (
    <div className={cn('relative', className)}>
      <button
        ref={ref}
        type="button"
        onClick={() => setPoke(p => ((p ?? -1) + 1) % POKES.length)}
        className="group block w-full rounded-[4px] outline-offset-4"
        aria-label="Soc, the tutor. Click for a question."
      >
        <SocFigure
          books={books}
          mood={current?.[0] ?? mood}
          look={look}
          idle={!still}
          size={size}
          className="h-auto w-full transition-transform duration-300 ease-[var(--ease-soft)] group-active:scale-[0.98]"
        />
      </button>
      {/* Beside him on wide screens; on a phone there is no room beside him, so the bubble sits over his top corner, inside the screen. */}
      <div
        aria-live="polite"
        className={cn(
          'pointer-events-none absolute top-[2%] w-max max-w-[min(15rem,70vw)] max-sm:top-[-6%] max-sm:max-w-[72%]',
          bubbleSide === 'left' ? 'right-[78%] max-sm:right-auto max-sm:left-0' : 'left-[78%] max-sm:left-auto max-sm:right-0',
        )}
      >
        {line ? (
          <p key={line} className="soc-bubble font-hand animate-in fade-in zoom-in-90 rounded-[4px] border-2 border-[var(--soc-outline)] bg-card px-4 py-2.5 text-[22px] leading-tight max-sm:px-3 max-sm:py-2 max-sm:text-[19px] text-foreground shadow-[3px_3px_0_var(--soc-outline)] duration-300" data-side={bubbleSide}>
            {line}
          </p>
        ) : null}
      </div>
    </div>
  );
}
