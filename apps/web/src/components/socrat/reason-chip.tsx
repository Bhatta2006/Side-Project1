import type { ReasonCode } from '@/lib/types';
import { cn } from '@/lib/utils';

/** Short learner-facing names for why Socrat put an item on the plan. */
export const REASON_LABEL: Record<ReasonCode, string> = {
  path: 'Next on your path',
  assumed_confirm: 'Confirming placement',
  failed_check_refresh: 'After a missed check',
  stuck_support: 'Extra support',
  review_due: 'Spaced review',
  checkpoint: 'Unlocks the next module',
  checkpoint_retry: 'Before your retry',
  chosen_testout: 'You asked to test out',
  probe: 'Finding the gap',
  approved_refresh: 'Refresher you approved',
  stretch: 'Stretch',
  transfer: 'Proves it transfers',
};

/** Outlined pill, text plus a dot: never colour alone. Plain path items get no chip. */
export function ReasonChip({ code, className }: { code?: ReasonCode; className?: string }) {
  if (!code || code === 'path' || !REASON_LABEL[code]) return null;
  return (
    <span className={cn('inline-flex w-fit items-center gap-1.5 rounded-full border border-border-strong px-2.5 py-0.5 text-[13px] font-semibold', className)}>
      <span aria-hidden="true" className="size-1.5 rounded-full bg-foreground" />
      <span><span className="sr-only">Why: </span>{REASON_LABEL[code]}</span>
    </span>
  );
}
