import Link from 'next/link';
import { activityHref, conceptHref } from '@/lib/routes';
import type { DailyReview, DailyReviewItem } from '@/lib/types';
import { Card } from '@/components/ui/card';

/**
 * The Daily Review (item 4 of docs/research/duolingo-teardown.md), behind
 * `features.daily_review`. The server orders practised concepts by a recall half-life model
 * (services/api/src/socrat/learn/recall.py); each one opens the ordinary review quiz.
 * The memory bar is the model's estimate, said as one.
 */
export function DailyReviewCard({ review }: { review: DailyReview }) {
  const [first] = review.items;
  const done = review.refreshed_today;
  return (
    <Card className="mb-8 grid gap-4 p-5 lg:p-6" aria-labelledby="daily-review-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <p className="type-label text-muted-foreground">Daily Review</p>
          <h2 id="daily-review-title" className="font-display text-2xl font-bold tracking-[-0.02em]">
            {first ? `${review.items.length} to refresh today` : done ? 'All refreshed for today' : 'Nothing has faded yet'}
          </h2>
          <p className="max-w-[60ch] text-[15px] text-muted-foreground">
            {first
              ? 'What you are most likely to have forgotten by now, most faded first.'
              : done
                ? `You refreshed ${done} ${done === 1 ? 'topic' : 'topics'} today. Come back tomorrow.`
                : 'Topics show up here a while after you practise them.'}
            {first && done ? ` ${done} refreshed so far today.` : ''}
          </p>
        </div>
        {first ? <Link href={activityHref(first.activity)} className="stamp">Start</Link> : null}
      </div>
      {first ? (
        <ol className="divide-y">
          {review.items.map(item => <Item key={item.concept} item={item} />)}
        </ol>
      ) : null}
    </Card>
  );
}

function Item({ item }: { item: DailyReviewItem }) {
  const percent = Math.round(item.recall * 100);
  return (
    <li className="grid gap-1.5 py-3 sm:grid-cols-[1fr_auto] sm:items-center sm:gap-4">
      <div className="grid gap-0.5">
        <Link href={conceptHref(item.concept)} className="font-semibold underline-offset-4 hover:underline">{item.title}</Link>
        <p className="text-sm text-muted-foreground">{item.reason}</p>
      </div>
      <div className="flex items-center gap-3">
        <div
          className="h-2 w-28 overflow-hidden rounded-full bg-raised"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={`Estimated memory of ${item.title}`}
        >
          <div className="h-full rounded-full bg-foreground/70" style={{ width: `${Math.max(4, percent)}%` }} />
        </div>
        <span className="w-32 text-sm">{item.state[0].toUpperCase() + item.state.slice(1)}</span>
        <Link href={activityHref(item.activity)} className="text-sm font-semibold underline underline-offset-4">Review</Link>
      </div>
    </li>
  );
}
