// The home path: skills as stones on a winding trail, top to bottom.
// Paper discs in ink: proven ones in marker, the current one ringed in highlighter, review ones
// on green stock, locked ones pencilled in. The order is the module's order only; it never implies prerequisites.
// A lesson still being written wears a progress ring around its stone instead of a separate bar.
import Link from 'next/link';
import { cn } from '@/lib/utils';
import type { PreparingLesson } from '@/lib/preparing';
import { STATUS_LABEL, type Status } from './status';
import type { MapNode } from './node-map';
import { PebbleFriend } from './pebble-friend';
import { GameEmoji, type GameEmojiName } from './game-emoji';

const SWAY = [0, 56, 84, 56, 0, -56, -84, -56];
export const PATH_STEP = 118;
const DONE: ReadonlySet<Status> = new Set(['mastered', 'practised', 'learned', 'assumed']);

type Tone = 'done' | 'current' | 'review' | 'open' | 'locked';
export type PathNode = MapNode & { writing?: PreparingLesson };

function toneOf(n: MapNode): Tone {
  if (n.status === 'locked') return 'locked';
  if (n.current) return 'current';
  if (n.reviewDue || n.status === 'review' || n.status === 'needs_practice') return 'review';
  if (DONE.has(n.status)) return 'done';
  return 'open';
}

/** Each stone carries a game emoji sticker: done, review due, locked, or a star still to earn. */
const GLYPH: Record<Tone, GameEmojiName> = { done: 'check', current: 'star', review: 'review', open: 'star', locked: 'lock' };

const RING_R = 39;
const RING_C = 2 * Math.PI * RING_R;

/** The writing ring: fills as the lesson is written; dashed and turning while it waits its turn. */
function WritingRing({ lesson }: { lesson: PreparingLesson }) {
  const waiting = lesson.state === 'queued' || lesson.state === 'scheduled';
  const stuck = lesson.state === 'stuck';
  const pct = Math.max(0.04, Math.min(1, lesson.progress));
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 88 88"
      className={cn('pointer-events-none absolute -inset-3 z-20 size-[88px]', waiting && 'motion-safe:animate-[spin_6s_linear_infinite]', stuck ? 'text-red' : 'text-[var(--ll-marker,var(--primary))]')}
    >
      <circle cx="44" cy="44" r={RING_R} fill="none" stroke="var(--ll-paper-shade, var(--border))" strokeWidth="6" />
      {waiting ? (
        <circle cx="44" cy="44" r={RING_R} fill="none" stroke="var(--ll-pencil-mark, var(--border))" strokeWidth="3" strokeDasharray="4 8" strokeLinecap="round" />
      ) : (
        <circle
          cx="44"
          cy="44"
          r={RING_R}
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={RING_C}
          strokeDashoffset={stuck ? 0 : RING_C * (1 - pct)}
          transform="rotate(-90 44 44)"
          className="transition-[stroke-dashoffset] duration-700 ease-[var(--ease-soft)]"
        />
      )}
      <circle cx="44" cy="44" r={RING_R + 3.5} fill="none" stroke="var(--pp-ink, var(--foreground))" strokeWidth="1.25" opacity="0.55" />
    </svg>
  );
}

function writingLine(l: PreparingLesson) {
  if (l.state === 'writing') return `Writing ${Math.round(l.progress * 100)}%`;
  if (l.state === 'stuck') return 'Writing paused';
  return l.label || 'Waiting its turn';
}

export function SkillPath({ nodes, label, startLabel = 'Start', offset = 0, friend = true }: { nodes: PathNode[]; label: string; startLabel?: string; offset?: number; friend?: boolean }) {
  const height = Math.max(1, nodes.length) * PATH_STEP + 24;
  // ``offset`` continues the sway from the previous module, so one long path never zigzags back.
  const xs = nodes.map((_, i) => SWAY[(i + offset) % SWAY.length]);
  // The dotted trail through every stone centre, drawn behind them.
  const trail = xs.map((x, i) => `${i ? 'L' : 'M'}${160 + x} ${i * PATH_STEP + 46}`).join(' ');
  const name = (n: PathNode) =>
    `${n.title}: ${n.status === 'locked' ? 'Locked' : STATUS_LABEL[n.status]}${n.reviewDue ? ', review due' : ''}${n.current ? ', current' : ''}${n.writing ? `, ${writingLine(n.writing)}` : ''}`;
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
            <li key={n.id} data-current={n.current ? '' : undefined} data-tour={n.current ? 'today-next' : undefined} className="absolute flex flex-col items-center" style={{ top: i * PATH_STEP + 12, left: `calc(50% + ${x}px)`, translate: '-50% 0' }}>
              {tone === 'current' ? (
                <span className="gm-say db-bob absolute -top-11 z-30 px-3 py-1.5 text-[13px] font-bold whitespace-nowrap">
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
                <GameEmoji name={n.writing ? 'book' : GLYPH[tone]} size={30} className={tone === 'locked' ? 'opacity-70' : undefined} />
                {n.writing ? <WritingRing lesson={n.writing} /> : null}
              </Link>
              <span
                aria-hidden="true"
                className={cn(
                  'absolute top-4 w-32 text-[13px] leading-tight font-semibold text-[var(--db-muted,var(--muted-foreground))]',
                  x > 0 ? 'right-[calc(100%+16px)] text-right' : 'left-[calc(100%+16px)]',
                  n.current && 'text-[var(--db-ink,var(--foreground))]',
                )}
              >
                <span className="line-clamp-2">{n.title}</span>
                {n.writing ? <span className={cn('mt-0.5 block text-[12px] font-medium tabular-nums', n.writing.state === 'stuck' ? 'text-red' : 'text-[var(--db-muted,var(--muted-foreground))]')}>{writingLine(n.writing)}</span> : null}
              </span>
            </li>
          );
        })}
      </ol>
      {friend && nodes.length >= 4 ? (
        <PebbleFriend kind="amber" size={52} className="db-bob absolute bottom-10 right-2 hidden sm:block" />
      ) : null}
    </div>
  );
}
