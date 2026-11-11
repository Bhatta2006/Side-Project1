'use client';

import { useState, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import { PartyPopper } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';

// Brand colours only: royal blue, highlighter yellow, red pen, ink.
const COLOURS = ['var(--primary)', 'var(--highlight)', 'var(--pen)', '#15161E'];

/** Pieces fired between two angles (degrees, 0 = right, -90 = up), `reach` px at most. */
function confetti(from: number, to: number, reach: number, count: number, delay = 0) {
  return Array.from({ length: count }, (_, i) => {
    const angle = (from + Math.random() * (to - from)) * (Math.PI / 180);
    const distance = reach * (0.45 + Math.random() * 0.55);
    return {
      id: i,
      style: {
        background: COLOURS[i % COLOURS.length],
        '--x': `${Math.round(Math.cos(angle) * distance)}px`,
        '--y': `${Math.round(Math.sin(angle) * distance)}px`,
        '--r': `${Math.round(Math.random() * 720 - 360)}deg`,
        animationDelay: `${delay + Math.round(Math.random() * 140)}ms`,
      } as CSSProperties,
      round: i % 3 === 0,
    };
  });
}

/** Confetti flying out of one point, then falling away. Plain CSS (`.confetti` in globals). */
function Burst({ className, from, to, reach, count, delay }: { className: string; from: number; to: number; reach: number; count: number; delay?: number }) {
  const [pieces] = useState(() => confetti(from, to, reach, count, delay));
  return (
    <span className={cn('pointer-events-none', className)} aria-hidden="true">
      {pieces.map(p => (
        <span key={p.id} className={cn('confetti absolute', p.round ? 'size-2 rounded-full' : 'h-3 w-1.5 rounded-[1px]')} style={p.style} />
      ))}
    </span>
  );
}

/** A popper in a screen corner that kicks back as it fires across the screen. */
function CornerPopper({ side }: { side: 'left' | 'right' }) {
  const left = side === 'left';
  return (
    <span className={cn('pointer-events-none fixed bottom-6 z-[60]', left ? 'left-6' : 'right-6')} aria-hidden="true">
      <Burst className="absolute left-1/2 top-0" from={left ? -80 : -170} to={left ? -10 : -100} reach={520} count={40} delay={250} />
      <span className={cn('popper-fire inline-block text-highlight', !left && '-scale-x-100')}>
        <PartyPopper className="size-12 drop-shadow" strokeWidth={1.75} />
      </span>
    </span>
  );
}

/** The celebration itself; `LaunchGift` loads this on demand, only for a learner who has an
 * unseen offer, so Today does not carry it for everyone else. */
export default function LaunchGiftDialog({ endsAt, onClose }: { endsAt: number; onClose: () => void }) {
  const [open, setOpen] = useState(true);
  const toggle = (next: boolean) => {
    setOpen(next);
    if (!next) onClose();
  };
  const until = new Date(endsAt * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'long' });

  return (
    <Dialog open={open} onOpenChange={toggle}>
      {/* Above the dialog's dimmed overlay, so the corner poppers stay bright. */}
      {open ? createPortal(<><CornerPopper side="left" /><CornerPopper side="right" /></>, document.body) : null}
      <DialogContent className="overflow-visible text-center sm:max-w-md">
        <div className="relative mx-auto mt-2 grid size-20 place-items-center rounded-full bg-highlight">
          {open ? <Burst className="absolute left-1/2 top-1/2" from={-150} to={-30} reach={240} count={44} delay={380} /> : null}
          <span className="popper-in text-[#15161E]">
            <PartyPopper className="size-10" strokeWidth={1.75} aria-hidden="true" />
          </span>
        </div>
        <div className="grid gap-2">
          <DialogTitle className="font-display text-2xl font-semibold tracking-[-0.02em]">
            You unlocked 1 month of Plus, free
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            You are one of our first 20 learners, so Plus is on us until {until}: every topic in
            every course, 10 messages a day with Soc, the weekly assessment and the visual playground.
          </DialogDescription>
        </div>
        <Button className="w-full" onClick={() => toggle(false)}>Start learning</Button>
      </DialogContent>
    </Dialog>
  );
}
