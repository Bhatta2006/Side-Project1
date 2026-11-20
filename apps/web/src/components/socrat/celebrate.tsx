'use client';
// The celebration at the end of a session: a pebble on a paper disc with highlighter rays, a
// burst of paper confetti, and one of Socrat's sounds. Still under reduced motion. Nothing here counts anything: it dresses what the server proved.
import { useEffect } from 'react';
import { play, type GameSound } from '@/lib/game-sound';
import { cn } from '@/lib/utils';
import { GameEmoji, type GameEmojiName } from './game-emoji';
import { PebbleFriend, type PebbleKind } from './pebble-friend';

const CONFETTI = ['var(--ll-hi)', 'var(--ll-marker)', 'var(--ll-sticky-green)', 'var(--ll-sticky-blue)', 'var(--ll-sticky-pink)', 'var(--ll-ink)'];
// Deterministic pieces, so the burst is the same on every render (no layout shift on re-render).
const PIECES = Array.from({ length: 22 }, (_, i) => ({
  x: ((i * 47) % 100) - 50,
  y: -40 - ((i * 29) % 70),
  r: (i * 67) % 360,
  c: CONFETTI[i % CONFETTI.length],
  w: 6 + (i % 3) * 2,
  round: i % 4 === 0,
  d: (i % 5) * 40,
}));

export function Celebrate({ kind, emoji, sound, className }: { kind: PebbleKind; emoji?: GameEmojiName; sound?: GameSound; className?: string }) {
  useEffect(() => { if (sound && document.documentElement.dataset.look === 'paper') play(sound); }, [sound]);
  return (
    <div aria-hidden="true" className={cn('relative mx-auto grid size-44 place-items-center', className)}>
      {/* Sun rays: alternating flat wedges, turning slowly. */}
      <span className="absolute inset-0 rounded-full [animation:db-spin_24s_linear_infinite] motion-reduce:animate-none" style={{ background: 'repeating-conic-gradient(color-mix(in srgb, var(--ll-hi) 55%, transparent) 0 10deg, transparent 10deg 30deg)', maskImage: 'radial-gradient(circle, #000 52%, transparent 70%)', WebkitMaskImage: 'radial-gradient(circle, #000 52%, transparent 70%)' }} />
      <span className="absolute size-28 rounded-full bg-[var(--ll-slip)] shadow-[inset_0_0_0_1.5px_var(--ll-ink),3px_3px_0_var(--ll-ink)]" />
      <PebbleFriend kind={kind} mood="happy" size={104} className="db-pop relative" />
      {emoji ? <GameEmoji name={emoji} size={40} className="db-pop absolute right-6 bottom-6 [animation-delay:180ms]" /> : null}
      {PIECES.map((p, i) => (
        <span
          key={i}
          className="db-confetti absolute top-1/2 left-1/2"
          style={{ '--x': `${p.x * 2.4}px`, '--y': `${p.y * 1.6}px`, '--r': `${p.r}deg`, width: p.w, height: p.round ? p.w : p.w * 1.7, background: p.c, borderRadius: p.round ? 999 : 2, animationDelay: `${p.d}ms` } as React.CSSProperties}
        />
      ))}
    </div>
  );
}
