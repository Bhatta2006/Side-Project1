'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Check, ExternalLink, Star } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import type { ExternalProblem, Level, PracticeStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Difficulty } from './common';

/** Platform as a plain outlined chip; platforms are not colour-coded. */
export function PlatformTag({ platform }: { platform: string }) {
  return <Badge variant="outline" className="font-medium">{platform}</Badge>;
}

/** Difficulty label plus the rating when the platform provides one. */
export function Level({ problem }: { problem: Pick<ExternalProblem, 'difficulty' | 'rating'> }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Difficulty level={problem.difficulty} />
      {problem.rating ? <span className="text-[13px] font-semibold text-muted-foreground tabular-nums" title="Codeforces rating">{problem.rating}</span> : null}
    </span>
  );
}

/**
 * A problem shown by name. External problems open on the official site in a new tab and
 * are recorded as attempted; the address itself is never displayed.
 */
export function ProblemName({
  problem,
  className = '',
  onOpened,
}: {
  problem: Pick<ExternalProblem, 'id' | 'title' | 'url' | 'platform'>;
  className?: string;
  onOpened?: () => void;
}) {
  const classes = cn('font-semibold underline-offset-4 transition-colors hover:underline', className);
  if (problem.url.startsWith('/')) return <Link href={problem.url} className={classes}>{problem.title}</Link>;
  return (
    <a
      href={problem.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(classes, 'group/link inline-flex items-center gap-1')}
      onClick={() => {
        api.post(`/library/problems/${problem.id}/opened`).then(() => onOpened?.()).catch(() => undefined);
      }}
    >
      {problem.title}
      <span className="sr-only">, opens on {problem.platform} in a new tab</span>
      <ExternalLink aria-hidden="true" className="size-3.5 flex-none text-muted-foreground" strokeWidth={1.75} />
    </a>
  );
}

export function StatusControl({
  id,
  status,
  bookmarked,
  onChange,
  compact = false,
}: {
  id: string;
  status: PracticeStatus | null;
  bookmarked: boolean;
  onChange?: (next: { status: PracticeStatus | null; bookmarked: boolean }) => void;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  if (id.startsWith('socrat:')) return null; // judged in the app; status comes from submissions
  async function save(body: { status?: PracticeStatus; bookmarked?: boolean }) {
    setBusy(true);
    try {
      const result = await api.put<{ status: PracticeStatus; bookmarked: boolean }>(`/library/problems/${id}`, body);
      onChange?.(result);
      if (body.status === 'solved') toast.success('Marked solved.', { description: 'A self-reported solve counts lightly toward this skill.' });
      else if (body.bookmarked) toast.success('Saved to your list.');
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy(false);
    }
  }
  const solved = status === 'solved';
  return (
    <span className="inline-flex items-center gap-1">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size={compact ? 'icon-sm' : 'sm'}
            variant={solved ? 'secondary' : 'ghost'}
            className={cn(solved && 'font-bold')}
            disabled={busy}
            aria-pressed={solved}
            onClick={() => save({ status: solved ? 'attempted' : 'solved' })}
          >
            <Check />
            {compact ? <span className="sr-only">{solved ? 'Solved' : 'Mark as solved'}</span> : solved ? 'Solved' : 'Mark solved'}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{solved ? 'Solved. Select to undo' : 'Mark as solved'}</TooltipContent>
      </Tooltip>
      <Button
        type="button"
        size="icon-sm"
        variant="ghost"
        className={cn(bookmarked ? 'text-foreground' : 'text-muted-foreground')}
        disabled={busy}
        aria-pressed={bookmarked}
        aria-label={bookmarked ? 'Remove from my list' : 'Save to my list'}
        onClick={() => save({ bookmarked: !bookmarked })}
      >
        <Star className={cn(bookmarked && 'fill-current')} />
      </Button>
    </span>
  );
}

export function LevelCard({ level, solved }: { level: Level; solved?: number }) {
  return (
    <div>
      <p className="type-label text-muted-foreground">Practice level</p>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-2">
        <span className="font-display text-3xl font-semibold tracking-[-0.03em]">{level.name}</span>
        <span className="text-sm font-semibold whitespace-nowrap text-muted-foreground tabular-nums">about {level.rating}</span>
      </div>
      {level.next_name ? (
        <>
          <Progress value={level.progress * 100} className="mt-3 h-1.5" aria-label={`Progress to ${level.next_name}`} />
          <p className="mt-2 text-[13px] text-muted-foreground">
            {Math.round(level.progress * 100)}% of the way to <span className="font-semibold text-foreground">{level.next_name}</span>
            {solved ? `. ${solved} solved` : ''}
          </p>
        </>
      ) : null}
    </div>
  );
}
