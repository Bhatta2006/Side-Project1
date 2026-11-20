// The home path: the skills of the current module as stones on a winding trail, top to bottom.
// Paper discs in ink: proven ones in marker, the current one ringed in highlighter, review ones
// on green stock, locked ones pencilled in. The order is the module's order only; it never implies prerequisites.
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { STATUS_LABEL, type Status } from './status';
import type { MapNode } from './node-map';
import { PebbleFriend } from './pebble-friend';
import { GameEmoji, type GameEmojiName } from './game-emoji';

const SWAY = [0, 56, 84, 56, 0, -56, -84, -56];
const STEP = 118;
const DONE: ReadonlySet<Status> = new Set(['mastered', 'practised', 'learned', 'assumed']);

type Tone = 'done' | 'current' | 'review' | 'open' | 'locked';

function toneOf(n: MapNode): Tone {
  if (n.status === 'locked') return 'locked';
  if (n.current) return 'current';
  if (n.reviewDue || n.status === 'review' || n.status === 'needs_practice') return 'review';
  if (DONE.has(n.status)) return 'done';
  return 'open';
}

/** Each stone carries a game emoji sticker: done, review due, locked, or a star still to earn. */
const GLYPH: Record<Tone, GameEmojiName> = { done: 'check', current: 'star', review: 'review', open: 'star', locked: 'lock' };

export function SkillPath({ nodes, label, startLabel = 'Start' }: { nodes: MapNode[]; label: string; startLabel?: string }) {
  const height = Math.max(1, nodes.length) * STEP + 24;
  const xs = nodes.map((_, i) => SWAY[i % SWAY.length]);
  // The dotted trail through every stone centre, drawn behind them.
  const trail = xs.map((x, i) => `${i ? 'L' : 'M'}${160 + x} ${i * STEP + 46}`).join(' ');
  const name = (n: MapNode) => `${n.title}: ${n.status === 'locked' ? 'Locked' : STATUS_LABEL[n.status]}${n.reviewDue ? ', review due' : ''}${n.current ? ', current' : ''}`;
  return (
    <div className="relative mx-auto w-[320px] max-w-full" style={{ height }}>
      <svg aria-hidden="true" className="pointer-events-none absolute inset-0" width="320" height={height} viewBox={`0 0 320 ${height}`}>
        <path d={trail} fill="none" stroke="var(--ll-pencil-mark, var(--border))" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 9" />
      </svg>
      <ol aria-label={`${label}, skill path`} className="relative">
        {nodes.map((n, i) => {
          const tone = toneOf(n);
          const x = xs[i];
          return (
            <li key={n.id} className="absolute flex flex-col items-center" style={{ top: i * STEP + 12, left: `calc(50% + ${x}px)`, translate: '-50% 0' }}>
              {tone === 'current' ? (
                <span className="gm-say db-bob absolute -top-11 z-20 px-3 py-1.5 text-[13px] font-bold whitespace-nowrap">
                  {startLabel}
                </span>
              ) : null}
              <Link
                href={n.href}
                aria-label={name(n)}
                title={name(n)}
                aria-current={n.current ? 'step' : undefined}
                data-tone={tone}
                className="gm-stone relative z-10 grid size-[64px] place-items-center transition-[translate,box-shadow] duration-100"
              >
                <GameEmoji name={GLYPH[tone]} size={30} className={tone === 'locked' ? 'opacity-70' : undefined} />
              </Link>
              <span
                aria-hidden="true"
                className={cn(
                  'absolute top-5 w-28 text-[13px] leading-tight font-semibold text-[var(--db-muted,var(--muted-foreground))]',
                  x > 0 ? 'right-[calc(100%+12px)] text-right' : 'left-[calc(100%+12px)]',
                  n.current && 'text-[var(--db-ink,var(--foreground))]',
                )}
              >
                <span className="line-clamp-2">{n.title}</span>
              </span>
            </li>
          );
        })}
      </ol>
      {nodes.length >= 4 ? (
        <PebbleFriend kind="amber" size={52} className="db-bob absolute bottom-10 right-2 hidden sm:block" />
      ) : null}
    </div>
  );
}
