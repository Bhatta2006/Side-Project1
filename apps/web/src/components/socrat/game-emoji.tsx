// Socrat's own emoji for the game layer: flat, chunky stickers with a cream rim, drawn to sit
// beside the pebble family. Use these instead of system emoji or stock icons for game moments
// (streak, XP, goals, levels, results). Flat colour only: no gradients, no glow.
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type GameEmojiName = 'flame' | 'bolt' | 'target' | 'gem' | 'check' | 'cross' | 'star' | 'lock' | 'review' | 'trophy' | 'clock' | 'book'
  | 'home' | 'map' | 'bulb' | 'flag' | 'chart' | 'gear' | 'blocks' | 'code' | 'snow';

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
  ),  home: (
    <>
      <path {...RIM} fill="#FF8A4C" d="M16 3.6 3.6 14.2c-.9.8-.3 2.2.9 2.2H6.6v9.6c0 1.2 1 2.2 2.2 2.2h14.4c1.2 0 2.2-1 2.2-2.2v-9.6h2.1c1.2 0 1.8-1.4.9-2.2L16 3.6Z" />
      <path fill="#E8621F" d="M25.4 16.4v9.6c0 1.2-1 2.2-2.2 2.2H19c2.4-.6 3.6-2.2 3.6-4.6v-7.2h2.8Z" />
      <rect x="12.8" y="18.4" width="6.4" height="9.8" rx="2" fill="#FFFBF2" />
      <path fill="#fff" opacity=".55" d="M8.6 14.6 15 9.2l.9 1.1-5.6 4.8-1.7-.5Z" />
    </>
  ),
  map: (
    <>
      <path {...RIM} fill="#2FB57A" d="M4 7.6 11 5l10 3 7-2.6v19L21 27l-10-3-7 2.6v-19Z" />
      <path fill="#1E9461" d="M21 8v19l7-2.6v-19L21 8Z" />
      <path fill="#57CC95" d="M11 5v19l10 3V8L11 5Z" />
      <path d="M7.4 20.6c2.4-3 5.4-1.4 7.4-4.4s4.6-2.8 6.8-1.6" fill="none" stroke="#FFFBF2" strokeWidth="2" strokeDasharray="2.4 2.4" strokeLinecap="round" />
      <circle cx="23" cy="13.6" r="2.2" fill="#F0484F" />
    </>
  ),
  bulb: (
    <>
      <path {...RIM} fill="#FFC531" d="M16 3a9.6 9.6 0 0 0-5.6 17.4c.8.6 1.2 1.4 1.2 2.4h8.8c0-1 .4-1.8 1.2-2.4A9.6 9.6 0 0 0 16 3Z" />
      <path fill="#F29F00" d="M21.6 20.4A9.6 9.6 0 0 0 19 3.5a9.6 9.6 0 0 1-1.8 18.3l-.2 1h3.4c0-1 .4-1.8 1.2-2.4Z" />
      <rect {...RIM} x="11.6" y="22.6" width="8.8" height="6" rx="2.4" fill="#B9AE9C" />
      <path d="M12 25.6h8" stroke="#9F937F" strokeWidth="1.4" />
      <ellipse cx="11.6" cy="10.6" rx="1.6" ry="2.6" fill="#fff" opacity=".65" transform="rotate(28 11.6 10.6)" />
    </>
  ),
  flag: (
    <>
      <path d="M7.4 4v24.6" fill="none" stroke="#FFFBF2" strokeWidth="5.6" strokeLinecap="round" />
      <path d="M7.4 4v24.6" fill="none" stroke="#8F8A82" strokeWidth="2.8" strokeLinecap="round" />
      <path {...RIM} fill="#F0484F" d="M8.6 5.2c5.6-2.4 9 2.4 16.2-.2v12.4c-7.2 2.6-10.6-2.2-16.2.2V5.2Z" />
      <path fill="#C42A32" d="M24.8 5v12.4c-3 1.1-5.2 1-7.2.6 2.4-.4 4.4-1.6 4.4-4.4V5.8c1-.1 1.9-.4 2.8-.8Z" />
    </>
  ),
  chart: (
    <>
      <rect {...RIM} x="4" y="16" width="6.4" height="12" rx="2.2" fill="#FFB224" />
      <rect {...RIM} x="12.8" y="9.6" width="6.4" height="18.4" rx="2.2" fill="#6C4CF5" />
      <rect {...RIM} x="21.6" y="4" width="6.4" height="24" rx="2.2" fill="#1FAF5F" />
      <path fill="#fff" opacity=".5" d="M14 11.2h1.6v6H14zM22.8 5.6h1.6v6h-1.6zM5.2 17.6h1.6v4H5.2z" />
    </>
  ),
  gear: (
    <>
      <path {...RIM} fill="#8F8A82" d="M13.8 3h4.4l.7 3.4 2.4 1 2.9-1.9 3.1 3.1-1.9 2.9 1 2.4 3.4.7v4.4l-3.4.7-1 2.4 1.9 2.9-3.1 3.1-2.9-1.9-2.4 1-.7 3.4h-4.4l-.7-3.4-2.4-1-2.9 1.9-3.1-3.1 1.9-2.9-1-2.4L3 18.2v-4.4l3.4-.7 1-2.4-1.9-2.9 3.1-3.1 2.9 1.9 2.4-1 .7-3.4Z" />
      <circle cx="16" cy="16" r="4.6" fill="#FFFBF2" />
    </>
  ),
  blocks: (
    <>
      <rect {...RIM} x="3.6" y="15.6" width="11.6" height="11.6" rx="3" fill="#2E8BF0" />
      <circle {...RIM} cx="22.6" cy="21.4" r="6" fill="#F0484F" />
      <path {...RIM} fill="#FFB224" d="M15.4 3.4c.3-.5 1-.5 1.3 0l6.4 10.6c.3.5-.1 1.1-.7 1.1H9.7c-.6 0-1-.6-.7-1.1l6.4-10.6Z" />
    </>
  ),
  code: (
    <>
      <rect {...RIM} x="3" y="5" width="26" height="22" rx="5" fill="#2B2622" />
      <path d="M10.4 12.4 6.8 16l3.6 3.6M21.6 12.4l3.6 3.6-3.6 3.6" fill="none" stroke="#6FDDA3" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M17.6 10.6 14.4 21.4" fill="none" stroke="#FFC531" strokeWidth="2.6" strokeLinecap="round" />
    </>
  ),
  snow: (
    <>
      <circle {...RIM} cx="16" cy="16" r="12.8" fill="#9ED3FF" />
      <path d="M16 7.4v17.2M8.6 11.7l14.8 8.6M8.6 20.3l14.8-8.6" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="16" cy="16" r="2.4" fill="#2580E6" />
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
