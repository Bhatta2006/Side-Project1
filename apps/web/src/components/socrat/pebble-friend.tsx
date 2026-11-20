// The pebble family of the game layer: Soc's friends, each a polished stone with its own shape
// and job, so a colour on screen always means the same thing.
//   soc: the tutor (the dark speckled pebble)    ember: streaks    jade: review and correct answers
//   amethyst: levels    amber: quests and XP    sky: checkpoints
// Plain SVG, no ink layer: they look the same in every palette and in dark mode.
import * as React from 'react';

import { cn } from '@/lib/utils';

export type PebbleKind = 'soc' | 'ember' | 'jade' | 'amethyst' | 'amber' | 'sky';
export type PebbleFriendMood = 'idle' | 'happy';

const SHAPES = {
  round: 'M50 5 C75 4 95 22 95 49 C95 76 76 95 49 95 C23 95 5 76 6 49 C7 23 26 6 50 5 Z',
  flame: 'M51 3 C55 14 66 22 78 34 C92 48 94 66 86 79 C78 91 65 96 50 96 C35 96 22 91 14 79 C6 66 8 49 20 36 C26 29 31 30 34 34 C34 22 42 12 51 3 Z',
  bean: 'M27 13 C40 6 52 13 61 13 C74 12 82 6 90 16 C99 28 97 52 89 69 C80 87 64 95 46 95 C24 95 7 81 5 59 C3 39 12 21 27 13 Z',
  gem: 'M43 5 Q50 2 57 5 L84 19 Q91 23 91 30 L92 63 Q92 71 85 75 L57 94 Q50 98 43 94 L15 75 Q8 71 8 63 L9 30 Q9 23 16 19 Z',
  cushion: 'M50 7 C80 6 93 14 93 47 C93 81 82 93 50 93 C18 93 7 81 7 47 C7 14 20 6 50 7 Z',
  shield: 'M50 96 C36 89 13 69 8 43 C4 21 20 6 50 6 C80 6 96 21 92 43 C87 69 64 89 50 96 Z',
} as const;

interface KindSpec { shape: keyof typeof SHAPES; body: string; fleck: string; mica: string; sheen: string; eye: string; dy: number; sheenDy: number; name: string; role: string }

export const PEBBLE_FRIENDS: Record<PebbleKind, KindSpec> = {
  soc: { shape: 'round', body: '#2B2622', fleck: '#8F8A82', mica: '#FFFFFF', sheen: '#8F8A82', eye: '#F7F3EC', dy: 0, sheenDy: 0, name: 'Soc', role: 'your tutor' },
  ember: { shape: 'flame', body: '#F0602A', fleck: '#FFAA74', mica: '#FFF1DC', sheen: '#FFC4A0', eye: '#FFF8EE', dy: 12, sheenDy: 14, name: 'Ember', role: 'keeps your streak' },
  jade: { shape: 'bean', body: '#17995A', fleck: '#6FDDA3', mica: '#EFFFF6', sheen: '#8DEBBC', eye: '#F4FFF8', dy: 4, sheenDy: 4, name: 'Jade', role: 'brings back what you learned' },
  amethyst: { shape: 'gem', body: '#5B3BE6', fleck: '#A58BFF', mica: '#FFFFFF', sheen: '#B5A2FF', eye: '#FBF9FF', dy: 0, sheenDy: 0, name: 'Ami', role: 'marks your level' },
  amber: { shape: 'cushion', body: '#F5A219', fleck: '#FFD98A', mica: '#FFFFFF', sheen: '#FFE5A8', eye: '#3A2408', dy: 2, sheenDy: 0, name: 'Amber', role: 'hands out quests' },
  sky: { shape: 'shield', body: '#2580E6', fleck: '#86C6FF', mica: '#FFFFFF', sheen: '#A8D6FF', eye: '#F5FAFF', dy: -6, sheenDy: -6, name: 'Lazuli', role: 'guards checkpoints' },
};

const SHEEN = 'M21 37 C25 28 33 21 43 18 C36 25 29 31 24 38 C23 39.5 21 39 21 37 Z';
const FLECKS: readonly (readonly [number, number, number])[] = [[57, 19, 2.2], [56, 24, 2], [52, 28, 1.8], [64, 28, 2.2], [63, 32, 2.2], [74, 25, 1.8], [75, 37, 2.3], [83, 41, 1.8], [82, 47, 1.8], [78, 49, 1.8], [76, 57, 2.3], [31, 51, 2.3], [19, 52, 1.1], [30, 75, 2.3], [41, 76, 1.9], [49, 73, 1.9], [48, 67, 1.1], [61, 66, 1.1], [63, 77, 1.1], [78, 73, 1.1], [35, 76, 2.3], [27, 68, 1.1]];
const MICA: readonly (readonly [number, number, number])[] = [[32, 35, 1.1], [70, 29, 0.8], [25, 49, 0.7], [28, 64, 1.1], [32, 75, 1.1], [36, 73, 0.7], [53, 68, 0.7], [65, 81, 1.1], [60, 85, 1.1], [52, 85, 0.7], [82, 46, 0.7]];

const dots = (list: readonly (readonly [number, number, number])[]) =>
  list.map(([x, y, r]) => `M${x - r} ${y} a${r} ${r} 0 1 0 ${2 * r} 0 a${r} ${r} 0 1 0 ${-2 * r} 0`).join(' ');
const FLECK_D = dots(FLECKS);
const MICA_D = dots(MICA);
const shiftY = (d: string, dy: number) => (dy ? d.replace(/(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)/g, (_, x, y) => `${x} ${Number(y) + dy}`) : d);

export function PebbleFriend({
  kind = 'soc',
  mood = 'idle',
  size = 64,
  shadow = true,
  className,
  title,
  ...props
}: Omit<React.ComponentProps<'svg'>, 'children'> & { kind?: PebbleKind; mood?: PebbleFriendMood; size?: number; shadow?: boolean; title?: string }) {
  const k = PEBBLE_FRIENDS[kind];
  const d = SHAPES[k.shape];
  const clip = `pebble-${kind}-${React.useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      data-slot="pebble-friend"
      data-kind={kind}
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      className={cn('shrink-0 overflow-visible', className)}
      style={shadow ? { filter: 'drop-shadow(0 6px 8px rgba(34,26,58,0.18))' } : undefined}
      {...props}
    >
      <defs><clipPath id={clip}><path d={d} /></clipPath></defs>
      <path d={d} fill="none" stroke="#D8D0C2" strokeWidth="6" strokeLinejoin="round" />
      <path d={d} fill={k.body} stroke="#FFFBF2" strokeWidth="4" strokeLinejoin="round" />
      <g clipPath={`url(#${clip})`}>
        <path d={shiftY(SHEEN, k.sheenDy)} fill={k.sheen} />
        <path d={FLECK_D} fill={k.fleck} />
        <path d={MICA_D} fill={k.mica} />
      </g>
      <g transform={`translate(0 ${k.dy})`}>
        {mood === 'happy' ? (
          <path d="M38.5 50 Q44.5 40 50.5 50 M54 51 Q60 41 66 51" fill="none" stroke={k.eye} strokeWidth="3.6" strokeLinecap="round" />
        ) : (
          <>
            <ellipse cx="44.5" cy="47" rx="5.6" ry="7.6" fill={k.eye} />
            <ellipse cx="60" cy="48" rx="5.8" ry="7.8" fill={k.eye} />
          </>
        )}
      </g>
    </svg>
  );
}
