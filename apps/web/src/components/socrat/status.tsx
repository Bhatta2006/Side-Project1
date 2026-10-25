import type { Band, RoadmapItem } from '@/lib/types';
import { cn } from '@/lib/utils';

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
    case 'locked': return 'locked';
    case 'mastered': return 'mastered';
    case 'assumed': return 'assumed';
    case 'practiced': return 'learned';
    case 'in_progress': return item.quiz_done || !item.lesson_done ? 'practised' : 'read';
    default: return item.lesson_done ? 'read' : 'not_seen';
  }
}

export function StatusIcon({ status, size = 20, className, title }: { status: Status; size?: number; className?: string; title?: string }) {
  const common = { fill: 'none', strokeWidth: 1.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  const shape = {
    not_seen: <circle cx="12" cy="12" r="8.5" stroke="var(--status-muted, var(--muted-foreground))" strokeDasharray="3 2.6" {...common} />,
    locked: (
      <g {...common} stroke="var(--status-muted, var(--muted-foreground))">
        <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
        <rect x="8.5" y="11.5" width="7" height="5" rx="1.2" />
        <path d="M9.75 11.5V10a2.25 2.25 0 0 1 4.5 0v1.5" />
      </g>
    ),
    read: (
      <g {...common} stroke="currentColor">
        <circle cx="12" cy="12" r="8.5" />
        <circle cx="12" cy="12" r="2" fill="currentColor" data-fill="" stroke="none" />
      </g>
    ),
    assumed: (
      <g opacity="0.6" {...common} stroke="currentColor">
        <circle cx="12" cy="12" r="8.5" />
        <path d="M3.5 12a8.5 8.5 0 0 0 17 0Z" fill="currentColor" data-fill="" />
      </g>
    ),
    practised: <circle cx="12" cy="12" r="8" stroke="var(--status-practised, var(--primary))" fill="none" strokeWidth="2.5" />,
    learned: (
      <g fill="none" stroke="var(--status-practised, var(--primary))" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="8" strokeWidth="2.5" />
        <path d="M8.6 12.2l2.3 2.3 4.5-4.6" strokeWidth="2" />
      </g>
    ),
    mastered: (
      <g>
        <circle cx="12" cy="12" r="9" fill="var(--proof)" stroke="var(--proof-stroke)" strokeWidth="1.5" data-fill="" />
        <path d="M8 12.2l2.7 2.7L16 9.6" fill="none" stroke="var(--proof-foreground)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    ),
    review: (
      <g>
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="var(--proof-stroke)" strokeWidth="3.6" strokeDasharray="0.1 3.6" strokeLinecap="round" />
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="var(--proof)" strokeWidth="2.4" strokeDasharray="0.1 3.6" strokeLinecap="round" />
      </g>
    ),
    needs_practice: (
      <g {...common} stroke="var(--attention)">
        <path d="M10.3 4.4a2 2 0 0 1 3.4 0l7 12.1a2 2 0 0 1-1.7 3H5a2 2 0 0 1-1.7-3Z" />
        <path d="M12 9.5v4" />
        <circle cx="12" cy="16.6" r="0.6" fill="var(--attention)" data-fill="" />
      </g>
    ),
  }[status];
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={cn('status-icon flex-none', className)}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      data-status={status}
    >
      {shape}
    </svg>
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
