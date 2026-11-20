// The home path: the skills of the current module as stones on a winding trail, top to bottom.
// Proven stones are filled, the current one glows and bobs, review stones wear Jade's green,
// locked ones are plain. The order is the module's order only; it never implies prerequisites.
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { STATUS_LABEL, type Status } from './status';
import type { MapNode } from './node-map';
import { PebbleFriend } from './pebble-friend';

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

const STONE: Record<Tone, string> = {
  done: 'bg-[var(--db-primary)] text-white shadow-[inset_0_-4px_0_rgb(0_0_0/0.12),0_6px_0_var(--db-ledge)]',
  current: 'bg-[var(--db-primary)] text-white shadow-[inset_0_-4px_0_rgb(0_0_0/0.12),0_6px_0_var(--db-ledge),0_0_0_10px_color-mix(in_srgb,var(--db-primary)_14%,transparent)]',
  review: 'bg-[var(--db-correct)] text-white shadow-[inset_0_-4px_0_rgb(0_0_0/0.12),0_6px_0_var(--db-correct-ledge)]',
  open: 'bg-[var(--db-surface)] text-[var(--db-primary)] shadow-[inset_0_0_0_3px_color-mix(in_srgb,var(--db-primary)_35%,transparent),0_6px_0_var(--db-line-strong)]',
  locked: 'bg-[#F3ECE1] text-[#B9AE9C] shadow-[0_6px_0_#E4DACB] dark:bg-[var(--db-raised)] dark:text-[var(--db-faint)] dark:shadow-[0_6px_0_var(--db-line-strong)]',
};

function Glyph({ tone }: { tone: Tone }) {
  const p = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 3, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, className: 'size-7', 'aria-hidden': true };
  if (tone === 'done') return <svg {...p}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>;
  if (tone === 'review') return <svg {...p}><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 5v6h-6" /></svg>;
  if (tone === 'locked') return <svg {...p} strokeWidth={2.6}><rect x="5" y="11" width="14" height="9" rx="2.5" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>;
  return <svg {...p} fill="currentColor" stroke="none"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" /></svg>;
}

export function SkillPath({ nodes, label, startLabel = 'Start' }: { nodes: MapNode[]; label: string; startLabel?: string }) {
  const height = Math.max(1, nodes.length) * STEP + 24;
  const xs = nodes.map((_, i) => SWAY[i % SWAY.length]);
  // The dotted trail through every stone centre, drawn behind them.
  const trail = xs.map((x, i) => `${i ? 'L' : 'M'}${160 + x} ${i * STEP + 46}`).join(' ');
  const name = (n: MapNode) => `${n.title}: ${n.status === 'locked' ? 'Locked' : STATUS_LABEL[n.status]}${n.reviewDue ? ', review due' : ''}${n.current ? ', current' : ''}`;
  return (
    <div className="relative mx-auto w-[320px] max-w-full" style={{ height }}>
      <svg aria-hidden="true" className="pointer-events-none absolute inset-0" width="320" height={height} viewBox={`0 0 320 ${height}`}>
        <path d={trail} fill="none" stroke="var(--db-line-strong, var(--border))" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="0.1 16" />
      </svg>
      <ol aria-label={`${label}, skill path`} className="relative">
        {nodes.map((n, i) => {
          const tone = toneOf(n);
          const x = xs[i];
          return (
            <li key={n.id} className="absolute flex flex-col items-center" style={{ top: i * STEP + 12, left: `calc(50% + ${x}px)`, translate: '-50% 0' }}>
              {tone === 'current' ? (
                <span className="db-bob absolute -top-11 z-20 rounded-xl bg-[var(--db-surface)] px-3 py-1.5 text-[13px] font-extrabold whitespace-nowrap text-[var(--db-primary)] shadow-[0_0_0_2px_var(--db-line),0_4px_0_var(--db-line)] after:absolute after:-bottom-1.5 after:left-1/2 after:size-3 after:-translate-x-1/2 after:rotate-45 after:bg-[var(--db-surface)] after:shadow-[2px_2px_0_0_var(--db-line)]">
                  {startLabel}
                </span>
              ) : null}
              <Link
                href={n.href}
                aria-label={name(n)}
                title={name(n)}
                aria-current={n.current ? 'step' : undefined}
                className={cn('relative z-10 grid size-[68px] place-items-center rounded-full transition-[translate,box-shadow] duration-100 active:translate-y-1', STONE[tone])}
              >
                {tone === 'current' ? (
                  <span aria-hidden="true" className="absolute -inset-[7px] rounded-full bg-[conic-gradient(var(--db-xp)_0_25%,transparent_25%)] [mask:radial-gradient(circle,transparent_38px,#000_39px)]" />
                ) : null}
                <Glyph tone={tone} />
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
