'use client';

import Link from 'next/link';
import { PACE_LABEL, activityHref } from '@/lib/routes';
import type { Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import Markdown from '@/components/markdown';
import { ProposalList } from '@/components/socrat/proposals';
import { Soc } from '@/components/socrat/illustration';
import { Card } from '@/components/ui/card';

interface Entry { key: string; noticed: string; changed: string; href?: string; action?: string }

/** What Socrat noticed and what it changed because of it, from real plan data only. */
function entries(today: Today): Entry[] {
  const out: Entry[] = [];
  const items = [today.next, ...today.queue].filter(a => a !== null);
  const firstOf = (code: string) => items.find(a => a?.code === code);
  const missed = firstOf('failed_check_refresh');
  if (missed) out.push({ key: 'missed', noticed: 'Your last check on this skill missed.', changed: `Added "${missed.title}" before a fresh check, instead of moving on.`, href: activityHref(missed.id), action: 'Open it' });
  const confirm = items.filter(a => a?.code === 'assumed_confirm');
  if (today.progress.assumed) {
    out.push({
      key: 'assumed',
      noticed: `Placement suggests you already know ${today.progress.assumed} skill${today.progress.assumed === 1 ? '' : 's'}.`,
      changed: 'They skip the lessons, but each one counts only after a short confirmation check.',
      ...(confirm[0] ? { href: activityHref(confirm[0].id), action: 'Confirm one now' } : {}),
    });
  }
  const support = firstOf('stuck_support');
  if (support) out.push({ key: 'support', noticed: support.reason || 'A few attempts in a row were hard.', changed: `Added "${support.title}" to help it click.`, href: activityHref(support.id), action: 'Open it' });
  if (today.pace !== 'steady') {
    out.push({ key: 'pace', noticed: today.pace_reason, changed: today.pace === 'fast' ? `${PACE_LABEL.fast}: warm-up problems are skipped and the plan moves faster.` : `${PACE_LABEL.support}: smaller steps, easier problems first, more time per skill.` });
  }
  const update = today.latest_update;
  // A plain "the plan changed" line only when nothing more specific explains it.
  if (!out.length && update?.changes && (update.changes.added?.length || update.changes.removed?.length)) {
    const added = update.changes.added?.length ?? 0;
    const removed = update.changes.removed?.length ?? 0;
    out.push({ key: 'update', noticed: 'Your latest results changed the plan.', changed: [added ? `${added} step${added === 1 ? '' : 's'} added` : '', removed ? `${removed} removed` : ''].filter(Boolean).join(', ') + '.', href: '/plan#why-heading', action: 'See why' });
  }
  if (today.minutes.reached) out.push({ key: 'goal', noticed: `You reached today's ${today.minutes.goal}-minute goal.`, changed: 'Anything more today is a bonus; stopping here keeps you on track.' });
  return out;
}

/** Today's "how Socrat is adapting to you": noticed, then changed, then what you can do. */
export function AdaptingCard({ today, onDecided, onAsk, className }: { today: Today; onDecided(): void; onAsk(): void; className?: string }) {
  const list = entries(today).slice(0, 4);
  const nudges = today.nudges.filter(n => n.kind !== 'proposals' && n.kind !== 'away');
  if (!list.length && !today.proposals.length && !nudges.length && !today.checkin) return null;
  return (
    <Card className={className} aria-labelledby="adapting-heading">
      <div className="grid gap-4 px-(--card-spacing)">
        <div className="flex items-start gap-3">
          <button type="button" onClick={onAsk} aria-haspopup="dialog" aria-label="Ask Soc about your plan" className="flex-none rounded-full"><Soc size={40} /></button>
          <div className="min-w-0">
            <h2 id="adapting-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">How Socrat is adapting to you</h2>
            {today.checkin ? <Markdown source={today.checkin.message} className="prose-compact mt-1 text-[15px] text-muted-foreground" /> : null}
          </div>
        </div>
        {list.length ? (
          <ul className="grid gap-2">
            {list.map(e => (
              <li key={e.key} className="grid gap-1 rounded-[16px] border px-4 py-3 sm:grid-cols-[1fr_auto] sm:items-center sm:gap-4">
                <div className="min-w-0">
                  <p className="text-[14px] text-muted-foreground"><span className="font-semibold text-foreground">Noticed:</span> {e.noticed}</p>
                  <p className="text-[15px]"><span className="font-semibold">Changed:</span> {e.changed}</p>
                </div>
                {e.href ? <Link href={e.href} className="w-fit text-[15px] font-semibold underline underline-offset-4">{e.action}</Link> : null}
              </li>
            ))}
          </ul>
        ) : null}
        {nudges.length ? (
          <ul className="grid gap-2" aria-label="Things to look at">
            {nudges.map(n => (
              <li key={n.kind + n.title}>
                <Link href={n.href} className={cn('block rounded-[16px] border px-4 py-3 transition-colors hover:bg-raised', n.severity === 'high' && 'border-attention')}>
                  <span className="font-semibold">{n.title}</span>
                  <span className="block text-[14px] text-muted-foreground">{n.body}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
        {today.proposals.length ? (
          <section aria-labelledby="today-proposals">
            <h3 id="today-proposals" className="type-label mb-2 text-muted-foreground">Socrat suggests. You decide.</h3>
            <ProposalList compact proposals={today.proposals.slice(0, 3)} onDecided={onDecided} />
            {today.proposals.length > 3 ? (
              <Link href="/plan#proposals" className="mt-2 inline-block text-[14px] font-semibold underline underline-offset-4">See all {today.proposals.length} suggestions</Link>
            ) : null}
          </section>
        ) : null}
        <Link href="/plan#why-heading" className="w-fit text-[14px] font-semibold underline underline-offset-4">Why did my plan change?</Link>
      </div>
    </Card>
  );
}
