// The strip at the top of Today: streak, today's goal, level and evidence points. Every number
// comes from the server's proof of work (lib/game.ts); none can be bought or gamed.
import Link from 'next/link';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { evidencePoints, levelFor } from '@/lib/game';
import { GameEmoji, type GameEmojiName } from './game-emoji';

function Chip({ icon, children, className, href, label }: { icon: GameEmojiName; children: ReactNode; className?: string; href?: string; label: string }) {
  const body = (
    <>
      <GameEmoji name={icon} size={28} />
      <span className="flex min-w-0 flex-col leading-tight">{children}</span>
    </>
  );
  const cls = cn(
    'inline-flex min-h-12 items-center gap-2.5 rounded-2xl bg-[var(--db-surface,var(--card))] py-1.5 pr-4 pl-2.5 shadow-[inset_0_0_0_2px_var(--db-line,var(--border)),0_3px_0_var(--db-line,var(--border))] transition-transform',
    href && 'hover:-translate-y-0.5',
    className,
  );
  return (
    <li>
      {href ? <Link href={href} aria-label={label} className={cls}>{body}</Link> : <span aria-label={label} className={cls}>{body}</span>}
    </li>
  );
}

export function GameBar({
  streak, fresh, studiedToday, minutesDone, minutesGoal, learned, mastered,
}: { streak: number; fresh: boolean; studiedToday: boolean; minutesDone: number; minutesGoal: number; learned: number; mastered: number }) {
  const level = levelFor(learned);
  const xp = evidencePoints({ learned, mastered, minutesToday: minutesDone });
  const goalPct = minutesGoal ? Math.min(100, Math.round((100 * minutesDone) / minutesGoal)) : 0;
  return (
    <ul className="mb-6 flex flex-wrap gap-2.5 lg:mb-8" aria-label="Today at a glance">
      <Chip icon="flame" label={fresh ? 'Start your streak today' : `${streak}-day streak${studiedToday ? ', kept today' : ''}`} href="/progress">
        <span className={cn('text-[15px] font-extrabold tabular-nums', streak > 0 ? 'text-[var(--db-streak-ink,var(--foreground))]' : '')}>{fresh ? 'Start' : `${streak} day${streak === 1 ? '' : 's'}`}</span>
        <span className="text-[11.5px] font-semibold text-[var(--db-muted,var(--muted-foreground))]">{studiedToday ? 'streak kept' : 'streak'}</span>
      </Chip>
      <Chip icon="target" label={`${minutesDone} of ${minutesGoal} minutes today`}>
        <span className="flex items-center gap-2">
          <span className="text-[15px] font-extrabold tabular-nums">{minutesDone}/{minutesGoal} min</span>
        </span>
        <span className="mt-1 block h-1.5 w-20 overflow-hidden rounded-full bg-[var(--db-line,var(--muted))]">
          <span className="block h-full rounded-full bg-[var(--db-correct,var(--success))] transition-[width] duration-700" style={{ width: `${Math.max(goalPct, 4)}%` }} />
        </span>
      </Chip>
      <Chip icon="gem" label={`Level ${level.index + 1}, ${level.name}. ${level.next ? `${level.next - level.proven} more proven skills to ${level.nextName}` : 'Top level'}`} href="/progress">
        <span className="text-[15px] font-extrabold">{level.name}</span>
        <span className="text-[11.5px] font-semibold text-[var(--db-muted,var(--muted-foreground))]">{level.next ? `${level.next - level.proven} skill${level.next - level.proven === 1 ? '' : 's'} to ${level.nextName}` : 'top level'}</span>
      </Chip>
      <Chip icon="bolt" label={`${xp} evidence points`}>
        <span className="text-[15px] font-extrabold tabular-nums text-[var(--db-xp-ink,var(--foreground))]">{xp} XP</span>
        <span className="text-[11.5px] font-semibold text-[var(--db-muted,var(--muted-foreground))]">from proven work</span>
      </Chip>
    </ul>
  );
}
