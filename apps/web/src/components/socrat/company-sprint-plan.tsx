'use client';

import Link from 'next/link';
import { Check, Lock } from '@/components/icons';
import { conceptHref, formatDate } from '@/lib/routes';
import type { CompanySprintView, CompanySprintWeek } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Difficulty } from '@/components/common';
import { ProblemName } from '@/components/practice';
import { ProposalList } from '@/components/socrat/proposals';
import { StatusIcon, statusFromBand } from '@/components/socrat/status';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

function Week({ week, current }: { week: CompanySprintWeek; current: boolean }) {
  const done = week.concepts.filter(c => c.done).length;
  return (
    <li className={cn('grid gap-4 paper rounded-card p-5 lg:p-6', current && 'border-primary ring-1 ring-primary')} aria-current={current ? 'step' : undefined}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-xl font-semibold tracking-[-0.03em]">
          Week {week.number}{week.review ? ': review and mixed practice' : ''}
        </h3>
        <span className="flex items-center gap-2 text-[13px] text-muted-foreground">
          {current ? <Badge>This week</Badge> : null}
          {formatDate(week.starts)} to {formatDate(week.ends)}
        </span>
      </div>

      {week.concepts.length ? (
        <div>
          <p className="text-[13px] font-semibold text-muted-foreground">Skills <span className="tabular-nums">{done} of {week.concepts.length} finished</span></p>
          <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
            {week.concepts.map(c => (
              <li key={c.id}>
                <Link href={conceptHref(c.id)} className="flex min-h-11 items-center gap-2.5 rounded-[4px] px-2 text-[15px] transition-colors hover:bg-raised">
                  <StatusIcon status={statusFromBand(c.band)} size={22} />
                  <span className={cn('min-w-0 flex-1', c.done && 'text-muted-foreground')}>{c.title}</span>
                  {c.done ? <Check className="size-4 text-primary" aria-label="Finished" /> : null}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {week.questions.length || week.locked_questions ? (
        <div>
          <p className="text-[13px] font-semibold text-muted-foreground">Company questions</p>
          <ul className="mt-2 grid gap-2">
            {week.questions.map(q => (
              <li key={q.id} className="flex min-h-11 flex-wrap items-center gap-3">
                {q.solved ? <StatusIcon status="practised" size={20} title="Solved" /> : <StatusIcon status="not_seen" size={20} title="Not solved yet" />}
                <ProblemName problem={q} className="min-w-0 flex-1 text-[15px]" />
                <Difficulty level={q.difficulty} />
              </li>
            ))}
          </ul>
          {week.locked_questions ? (
            <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
              <Lock className="size-4" aria-hidden="true" />
              {week.locked_questions} question{week.locked_questions === 1 ? '' : 's'} unlock when you finish the skills they use.
            </p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

export function CompanySprintPlan({ sprint, onDecided }: { sprint: CompanySprintView; onDecided: () => void }) {
  const c = sprint.counts;
  const percent = Math.round(sprint.progress * 100);
  return (
    <div className="grid gap-6">
      <section data-tone="hero" aria-labelledby="sprint-title" className="grid gap-5 rounded-card bg-forest p-6 text-forest-foreground lg:p-8">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="type-label">Week {sprint.current_week} of {sprint.weeks_total}</p>
            <h2 id="sprint-title" className="type-display-l mt-2">{sprint.title}</h2>
            <p className="mt-2 text-base">{formatDate(sprint.started_on, { month: 'long', day: 'numeric' })} to {formatDate(sprint.ends_on, { month: 'long', day: 'numeric', year: 'numeric' })}</p>
          </div>
          <span className="inline-flex items-center rounded-full border border-current px-3 py-1 text-[13px] font-semibold">
            {sprint.finished ? 'Finished' : sprint.on_track ? 'On track' : 'Behind: catch up this week'}
          </span>
        </div>
        <div>
          <div className="flex items-baseline justify-between text-sm font-semibold"><span>Sprint progress</span><span className="tabular-nums">{percent}%</span></div>
          <Progress value={percent} className="mt-2 h-2 bg-[color-mix(in_srgb,var(--forest-foreground),transparent_75%)]" aria-label={`Sprint ${percent} percent complete`} />
          <p className="mt-3 text-[15px] tabular-nums">
            {c.concepts_done} of {c.concepts} skills finished, {c.questions_solved} of {c.questions} company questions solved.
            {c.already_known ? ` ${c.already_known} skills you already had are not repeated.` : ''}
          </p>
        </div>
      </section>

      {sprint.proposal?.status === 'pending' ? (
        <section aria-labelledby="sprint-proposal" className="paper rounded-card p-5 lg:p-6">
          <h2 id="sprint-proposal" className="font-display text-xl font-semibold tracking-[-0.03em]">Point your roadmap at this sprint?</h2>
          <p className="mt-1 mb-4 text-[15px] text-muted-foreground">Nothing in your plan changes until you accept.</p>
          <ProposalList proposals={[sprint.proposal]} onDecided={onDecided} />
        </section>
      ) : null}

      <ol className="grid gap-4" aria-label="Weekly plan">
        {sprint.weeks.map(w => <Week key={w.number} week={w} current={!sprint.finished && w.number === sprint.current_week} />)}
      </ol>
    </div>
  );
}
