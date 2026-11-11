'use client';
import { Progress } from '@/components/ui/progress';
import { timeLeft, type PreparingLesson } from '@/lib/preparing';
import { cn } from '@/lib/utils';

/** One lesson being written: a bar that fills as it moves through its steps, the step, time left. */
export function LessonProgress({ lesson, compact, className }: { lesson: PreparingLesson; compact?: boolean; className?: string }) {
  const stuck = lesson.state === 'stuck';
  const waiting = lesson.state === 'queued' || lesson.state === 'scheduled';
  const pct = Math.round(lesson.progress * 100);
  const when = lesson.state === 'scheduled' && lesson.at
    ? `Starts ${new Date(lesson.at * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
    : '';
  const detail = [lesson.state === 'writing' ? `${pct}%` : '', lesson.state === 'writing' ? timeLeft(lesson.eta_seconds) : when].filter(Boolean).join(' · ');
  return (
    <div className={cn('grid gap-1.5', compact ? 'min-w-40 basis-56' : '', className)} role="status" aria-live="polite">
      <Progress
        value={stuck ? 0 : waiting ? undefined : pct}
        size="sm"
        tone="marker"
        seed={`prep-${lesson.concept}`}
        aria-label={`${lesson.title}: ${lesson.label}${detail ? `, ${detail}` : ''}`}
      />
      <p className={cn('flex flex-wrap justify-between gap-x-3 text-[13px]', stuck ? 'text-red' : 'text-muted-foreground')}>
        <span>{lesson.label}</span>
        {detail ? <span className="tabular-nums">{detail}</span> : null}
      </p>
    </div>
  );
}
