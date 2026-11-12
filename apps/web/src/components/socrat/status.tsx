import type { Band, RoadmapItem } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Icon } from '@/components/ui/icon';

/**
 * The status system: one shape, label and colour per learning state, used everywhere a skill,
 * problem, review item or assessment outcome is shown. Mapping to backend data is documented
 * in docs/redesign/DESIGN-SYSTEM.md. "Mastered" is used instead of "Shown independently"
 * because the backend's mastery estimate also counts (down-weighted) assisted successes.
 */
export type Status = 'not_seen' | 'locked' | 'read' | 'assumed' | 'practised' | 'learned' | 'mastered' | 'review' | 'needs_practice';

export const STATUS_LABEL: Record<Status, string> = {
  not_seen: 'Not seen yet',
  locked: 'Locked',
  read: 'Read',
  assumed: 'To confirm (placement)',
  practised: 'Practised',
  learned: 'Learned, check passed',
  mastered: 'Mastered',
  review: 'Review due',
  needs_practice: 'Still building',
};

export function statusFromBand(band: Band, reviewDue = false): Status {
  if (reviewDue && band !== 'not_started') return 'review';
  return ({ not_started: 'not_seen', needs_practice: 'needs_practice', developing: 'practised', likely_known: 'assumed', strong: 'mastered' } as const)[band];
}

/** Base state of a roadmap item; review due is shown separately as a badge beside it. */
export function statusFromRoadmap(item: Pick<RoadmapItem, 'status' | 'lesson_done' | 'quiz_done'>): Status {
  switch (item.status) {
    case 'locked':
    case 'preparing': return 'locked';
    case 'mastered': return 'mastered';
    case 'assumed': return 'assumed';
    case 'practiced': return 'learned';
    case 'in_progress': return item.quiz_done || !item.lesson_done ? 'practised' : 'read';
    default: return item.lesson_done ? 'read' : 'not_seen';
  }
}

/** Each state as a hand-drawn mark in its own ink: pencil for not yet, blue pen for work in progress,
 *  green for a passed check, highlighter for mastered, red pen for what needs another look. */
const MARK: Record<Status, { icon: string; className: string; dashed?: boolean; dab?: boolean }> = {
  not_seen: { icon: 'circle', className: 'text-pencil-mark', dashed: true },
  locked: { icon: 'lock', className: 'text-pencil' },
  read: { icon: 'circle-dot', className: 'text-ink-you' },
  assumed: { icon: 'circle-question-mark', className: 'text-pencil' },
  practised: { icon: 'circle-play', className: 'text-ink-you' },
  learned: { icon: 'circle-check', className: 'text-green' },
  mastered: { icon: 'badge-check', className: 'text-ink', dab: true },
  review: { icon: 'rotate-ccw-clock', className: 'text-orange-text' },
  needs_practice: { icon: 'triangle-alert', className: 'text-red' },
};

export function StatusIcon({ status, size = 20, className, title }: { status: Status; size?: number; className?: string; title?: string }) {
  const mark = MARK[status];
  return (
    <span
      className={cn('status-icon relative inline-grid flex-none place-items-center', mark.className, mark.dashed && 'opacity-80', className)}
      style={{ width: size, height: size }}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      data-status={status}
    >
      {mark.dab ? <span className="absolute inset-[8%] -rotate-6 rounded-[45%_55%_50%_40%] bg-hi" aria-hidden="true" /> : null}
      <Icon name={mark.icon} size={size} seed={status} className={cn('relative', mark.dashed && '[stroke-dasharray:2_2.5]')} />
    </span>
  );
}

/** Icon plus its visible label. `detail` replaces the label, e.g. "Locked until First steps". */
export function StatusLabel({ status, detail, size = 20, className, muted = false }: { status: Status; detail?: string; size?: number; className?: string; muted?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2 text-sm font-semibold', muted && 'font-medium text-muted-foreground', className)}>
      <StatusIcon status={status} size={size} />
      <span>{detail ?? STATUS_LABEL[status]}</span>
    </span>
  );
}

const LEGEND_ORDER: Status[] = ['not_seen', 'read', 'assumed', 'practised', 'mastered', 'review', 'needs_practice', 'locked'];

/** Icons and labels in one row; shown wherever three or more states appear together. */
export function StatusLegend({ only, className }: { only?: Status[]; className?: string }) {
  const items = only ? LEGEND_ORDER.filter(s => only.includes(s)) : LEGEND_ORDER;
  return (
    <div className={cn('flex flex-wrap gap-x-5 gap-y-2 text-muted-foreground', className)} role="list" aria-label="Status legend">
      {items.map(s => (
        <span key={s} role="listitem" className="inline-flex items-center gap-2 text-[13px] font-medium">
          <StatusIcon status={s} size={18} />
          {STATUS_LABEL[s]}
        </span>
      ))}
    </div>
  );
}
