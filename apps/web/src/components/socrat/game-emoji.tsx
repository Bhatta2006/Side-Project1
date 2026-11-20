// Socrat's own emoji for the game layer: flat, chunky stickers with a cream rim, drawn to sit
// beside the pebble family. Use these instead of system emoji or stock icons for game moments
// (streak, XP, goals, levels, results). Flat colour only: no gradients, no glow.
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type GameEmojiName = 'flame' | 'bolt' | 'target' | 'gem' | 'check' | 'cross' | 'star' | 'lock' | 'review' | 'trophy' | 'clock' | 'book';

const RIM = { stroke: '#FFFBF2', strokeWidth: 2.6, strokeLinejoin: 'round' as const, paintOrder: 'stroke' as const };

const ART: Record<GameEmojiName, ReactNode> = {
  flame: (
    <>
      <path {...RIM} fill="#FF6B35" d="M16 2.5C18 7 23 9.5 25.5 14.5 28.5 20.5 25.5 29 16 29.5 6.5 29 3.5 21 6.5 15 8 12 10 11.5 11 13 11 9 13 5.5 16 2.5Z" />
      <path fill="#E8501F" d="M25.5 14.5C28.5 20.5 25.5 29 16 29.5 21.5 27 24 21.5 22.6 16.4 23.6 15.6 24.6 14.9 25.5 14.5Z" />
      <path fill="#FFC94D" d="M16 14c1.5 3 5 4.5 5 8.5 0 3.5-2.2 5.1-5 5.1s-5-1.6-5-4.8c0-2.3 1.5-3.3 2.3-2 .3-2.8 1.3-4.8 2.7-6.8Z" />
      <ellipse cx="10.4" cy="17.6" rx="1.2" ry="2.3" fill="#fff" opacity=".55" transform="rotate(18 10.4 17.6)" />
    </>
  ),
  bolt: (
    <>
      <path {...RIM} fill="#FFB224" d="M18.6 2.5 6.5 18h8l-2 11.5L25.5 13H17l1.6-10.5Z" />
      <path fill="#F29500" d="M14.5 18l-2 11.5L25.5 13h-4.2l-6.2 7.6Z" />
      <path fill="#fff" opacity=".6" d="M16.4 6.4 10.6 15h1.8l4-8.6Z" />
    </>
  ),
  target: (
    <>
      <circle {...RIM} cx="16" cy="16" r="12.8" fill="#1FAF5F" />
      <path fill="#148A49" d="M28.8 16A12.8 12.8 0 0 1 6.9 25.1 12.8 12.8 0 0 0 26 9.1 12.7 12.7 0 0 1 28.8 16Z" />
      <circle cx="16" cy="16" r="8.4" fill="#FFFBF2" />
      <circle cx="16" cy="16" r="4.4" fill="#1FAF5F" />
      <circle cx="11.2" cy="9.4" r="1.5" fill="#fff" opacity=".6" />
    </>
  ),
  gem: (
    <>
      <path {...RIM} fill="#5B3BE6" d="M9 4.5h14l6 6.8L16 28.5 3 11.3l6-6.8Z" />
      <path fill="#8B72FF" d="M9 4.5h14l6 6.8H3l6-6.8Z" />
      <path fill="#7458FF" d="M10.6 11.3h10.8L16 28.5l-5.4-17.2Z" />
      <path fill="#4A2CCB" d="M21.4 11.3H29L16 28.5l5.4-17.2Z" />
      <path fill="#fff" opacity=".65" d="M10.2 6.4h3.4l-2.2 3.4H7.4l2.8-3.4Z" />
    </>
  ),
  check: (
    <>
      <circle {...RIM} cx="16" cy="16" r="12.8" fill="#1FAF5F" />
      <path fill="#148A49" d="M28.8 16A12.8 12.8 0 0 1 6.9 25.1 12.8 12.8 0 0 0 26 9.1 12.7 12.7 0 0 1 28.8 16Z" />
      <path d="M9.6 16.6 14 21l8.4-9.6" fill="none" stroke="#fff" strokeWidth="3.6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  cross: (
    <>
      <circle {...RIM} cx="16" cy="16" r="12.8" fill="#F0484F" />
      <path fill="#C42A32" d="M28.8 16A12.8 12.8 0 0 1 6.9 25.1 12.8 12.8 0 0 0 26 9.1 12.7 12.7 0 0 1 28.8 16Z" />
      <path d="M11 11l10 10M21 11 11 21" fill="none" stroke="#fff" strokeWidth="3.6" strokeLinecap="round" />
    </>
  ),
  star: (
    <>
      <path {...RIM} fill="#FFB224" d="M16 3.2l3.7 7.8 8.5 1-6.3 5.9 1.7 8.4L16 22.1l-7.6 4.2 1.7-8.4-6.3-5.9 8.5-1L16 3.2Z" />
      <path fill="#F29500" d="M16 22.1l7.6 4.2-1.7-8.4 6.3-5.9-6.4.4-2 7.1L16 22.1Z" />
      <path fill="#fff" opacity=".6" d="M14.6 8.6l-1.6 3.5-3.6.5 2.8.6 2.4-4.6Z" />
    </>
  ),
  lock: (
    <>
      <path d="M10.5 14v-3.2a5.5 5.5 0 0 1 11 0V14" fill="none" stroke="#FFFBF2" strokeWidth="6.4" strokeLinecap="round" />
      <path d="M10.5 14v-3.2a5.5 5.5 0 0 1 11 0V14" fill="none" stroke="#B9AE9C" strokeWidth="3.4" strokeLinecap="round" />
      <rect {...RIM} x="6.5" y="13" width="19" height="15" rx="4.5" fill="#E4DACB" />
      <rect x="6.5" y="22" width="19" height="6" rx="3" fill="#D4C7B2" />
      <circle cx="16" cy="19.6" r="2.2" fill="#9F937F" />
    </>
  ),
  review: (
    <>
      <circle {...RIM} cx="16" cy="16" r="12.8" fill="#17995A" />
      <path fill="#0F7A47" d="M28.8 16A12.8 12.8 0 0 1 6.9 25.1 12.8 12.8 0 0 0 26 9.1 12.7 12.7 0 0 1 28.8 16Z" />
      <path d="M22.2 13.4A6.8 6.8 0 1 0 22 19" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" />
      <path d="M23.6 8.6v5.4h-5.4" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  trophy: (
    <>
      <path d="M8 8.5H4.6v2.2c0 3.2 2.3 5.6 5.4 5.9M24 8.5h3.4v2.2c0 3.2-2.3 5.6-5.4 5.9" fill="none" stroke="#FFFBF2" strokeWidth="5.4" strokeLinecap="round" />
      <path d="M8 8.5H4.6v2.2c0 3.2 2.3 5.6 5.4 5.9M24 8.5h3.4v2.2c0 3.2-2.3 5.6-5.4 5.9" fill="none" stroke="#E08A00" strokeWidth="2.6" strokeLinecap="round" />
      <path {...RIM} fill="#FFB224" d="M8 4h16v6.5a8 8 0 0 1-16 0V4Z" />
      <path {...RIM} fill="#FFB224" d="M13.6 18h4.8l.8 5.2h-6.4l.8-5.2ZM9.6 23.2h12.8a1.8 1.8 0 0 1 1.8 1.8v3H7.8v-3a1.8 1.8 0 0 1 1.8-1.8Z" />
      <path fill="#F29500" d="M24 4v6.5a8 8 0 0 1-8 8c3.2-1.2 5-4.3 5-8V4h3Z" />
      <path fill="#fff" opacity=".6" d="M10.6 6.4h2v5.2c0 .9.2 1.8.6 2.6-1.6-.8-2.6-2.4-2.6-4.4V6.4Z" />
    </>
  ),
  clock: (
    <>
      <circle {...RIM} cx="16" cy="16" r="12.8" fill="#2E8BF0" />
      <path fill="#1D6AC2" d="M28.8 16A12.8 12.8 0 0 1 6.9 25.1 12.8 12.8 0 0 0 26 9.1 12.7 12.7 0 0 1 28.8 16Z" />
      <circle cx="16" cy="16" r="8.6" fill="#FFFBF2" />
      <path d="M16 11v5.4l3.4 2.2" fill="none" stroke="#1D5FA8" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  book: (
    <>
      <path {...RIM} fill="#6C4CF5" d="M5 6.5c3.8-1.4 7.6-1 11 1.6 3.4-2.6 7.2-3 11-1.6v19c-3.8-1.4-7.6-1-11 1.6-3.4-2.6-7.2-3-11-1.6v-19Z" />
      <path fill="#4B30C7" d="M16 8.1c3.4-2.6 7.2-3 11-1.6v19c-3.8-1.4-7.6-1-11 1.6V8.1Z" />
      <path d="M8.4 11.2c1.9-.4 3.8-.2 5.4.7M8.4 15.2c1.9-.4 3.8-.2 5.4.7" fill="none" stroke="#fff" strokeOpacity=".7" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
};

export function GameEmoji({ name, size = 24, className, label }: { name: GameEmojiName; size?: number; className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      data-slot="game-emoji"
      data-name={name}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn('inline-block shrink-0 overflow-visible align-[-0.2em] [filter:drop-shadow(0_1.5px_0_rgb(34_26_58/0.14))]', className)}
    >
      {ART[name]}
    </svg>
  );
}
