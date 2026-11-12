'use client';

import Link from 'next/link';
import { useState, type ReactNode } from 'react';
import { Check, Lock, Minus, ShieldCheck } from '@/components/icons';
import { explain, openPaywall } from '@/lib/api';
import { money, subscribe } from '@/lib/billing';
import { PLAN_NAME, PLUS_WAS_INR } from '@/lib/plans';
import { useSession } from '@/lib/session';
import type { BillingStatus, PlanId } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';

// Mirrors `entitlements.PLANS`; kept here so the copy only loads with the paywall.
type Cell = boolean | string;
const COMPARE: { label: string; free: Cell; plus: Cell; pro: Cell }[] = [
  { label: 'Lessons and topics', free: 'First 2 modules', plus: 'Every topic, every course', pro: 'Every topic, every course' },
  { label: 'Messages with Soc', free: '5 a week', plus: '10 a day', pro: '50 a day' },
  { label: 'Checkpoints and module tests', free: 'First 2 modules', plus: true, pro: true },
  { label: 'Practice problem library', free: 'A few starter problems', plus: true, pro: true },
  { label: 'Weekly assessment', free: false, plus: true, pro: true },
  { label: 'Visual playground', free: false, plus: '3 a day', pro: '15 a day' },
  { label: 'Company interview questions', free: false, plus: false, pro: true },
  { label: 'Company sprint plans', free: false, plus: false, pro: true },
];

/** What a paywall says depending on what the learner just ran into. */
const PAYWALL_REASON: Record<string, { title: string; body: string; plan: 'plus' | 'pro' }> = {
  welcome: { title: 'Start with the whole course, not a sample', body: 'Free covers the first 2 modules. Founding Members unlock every topic, daily time with Soc and the weekly assessment.', plan: 'plus' },
  upgrade_required: { title: 'This part is for Founding Members', body: 'You have finished what the free plan covers here. Unlock every topic, checkpoint and practice problem to keep your streak going.', plan: 'plus' },
  pro_required: { title: 'Company questions are a Pro feature', body: 'See the questions top companies actually ask, sorted by how often and how recently, plus a sprint plan for your target company.', plan: 'pro' },
  chat_week_limit: { title: "You've used this week's messages with Soc", body: 'Free includes 5 a week. Founding Members get 10 every day, so you never get stuck mid-problem.', plan: 'plus' },
  assessment: { title: 'The weekly assessment is for members', body: 'A timed check built from what you studied this week, so you can prove it stuck. Included with Founding Member and Pro.', plan: 'plus' },
};

function Mark({ value }: { value: boolean | string }) {
  if (value === true) return <Check className="mx-auto size-4" aria-label="Included" />;
  if (value === false) return <Minus className="mx-auto size-4 text-muted-foreground/60" aria-label="Not included" />;
  return <span>{value}</span>;
}

/** Free vs Founding Member vs Pro, with the recommended column highlighted. */
export function PlanCompare({ highlight = 'plus', className }: { highlight?: PlanId; className?: string }) {
  const cols: PlanId[] = ['free', 'plus', 'pro'];
  return (
    <table className={cn('w-full border-separate border-spacing-0 text-left text-[13px]', className)}>
      <thead>
        <tr>
          <th scope="col" className="py-2 pr-2 font-medium text-muted-foreground"><span className="sr-only">Feature</span></th>
          {cols.map(c => (
            <th key={c} scope="col" className={cn('px-2 py-2 text-center font-display font-bold', c === highlight && 'rounded-t-[12px] bg-proof text-proof-foreground')}>{PLAN_NAME[c]}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {COMPARE.map((row, i) => (
          <tr key={row.label}>
            <th scope="row" className="border-t py-2 pr-2 font-normal">{row.label}</th>
            {cols.map(c => (
              <td key={c} className={cn('border-t px-2 py-2 text-center', c === highlight && 'bg-proof text-proof-foreground font-semibold', c === highlight && i === COMPARE.length - 1 && 'rounded-b-[12px]', c === 'free' && 'text-muted-foreground')}>
                <Mark value={row[c]} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The paywall dialog. Loaded on demand by `PaywallHost`, so pages don't carry it until it opens. */
export function PaywallDialog({ reason, status, onClose }: { reason: string; status: BillingStatus; onClose: () => void }) {
  const { refresh } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const copy = PAYWALL_REASON[reason] ?? PAYWALL_REASON.upgrade_required;
  const plan = copy.plan === 'pro' || status.plan === 'plus' ? 'pro' : 'plus';
  const minor = status.prices[plan].month.INR;

  async function buy() {
    setError('');
    setBusy(true);
    try {
      if (await subscribe(plan, 'month', 'INR')) {
        await refresh();
        window.location.reload(); // every page re-reads what is now unlocked
      }
    } catch (e) {
      setError(e instanceof Error && !('code' in e) ? e.message : explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={next => { if (!next) onClose(); }}>
      <DialogContent className="max-h-[92dvh] gap-0 overflow-y-auto p-0 sm:max-w-[560px]">
        <div className="px-6 pt-6 pb-4">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground"><Lock className="size-3.5" aria-hidden="true" /> {status.plan === 'plus' ? `You're a ${PLAN_NAME.plus}` : "You're on Free"}</p>
          <DialogTitle className="mt-2 font-display text-2xl font-bold tracking-[-0.03em]">{copy.title}</DialogTitle>
          <DialogDescription className="mt-1.5 text-[15px]">{copy.body}</DialogDescription>
        </div>

        <section aria-label={`${PLAN_NAME[plan]} plan`} className="mx-6 rounded-[4px] border-[1.5px] border-proof-stroke bg-proof text-proof-foreground p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-display text-lg font-bold">{PLAN_NAME[plan]}</p>
            <span className="rounded-full bg-proof-foreground px-2.5 py-0.5 text-[11px] font-bold text-proof">{plan === 'plus' ? 'Founding price · most popular' : 'Interview season'}</span>
          </div>
          <p className="mt-1 font-display text-3xl font-bold tabular-nums">
            {plan === 'plus' ? <s className="mr-2 text-lg font-medium text-proof-foreground/60" aria-label={`was ${money(PLUS_WAS_INR, 'INR')}`}>{money(PLUS_WAS_INR, 'INR')}</s> : null}
            {money(minor, 'INR')}<span className="text-base font-medium text-proof-foreground/70"> / month</span>
          </p>
          <p className="mt-1 text-[13px] text-proof-foreground/75">
            {plan === 'plus' ? 'Less than ₹4 a day. Your founding price stays the same for as long as you stay subscribed.' : 'Everything in Founding Member, plus every company question and sprint plan.'}
          </p>
          {error ? <p role="alert" className="mt-3 text-sm text-destructive">{error}</p> : null}
          <Button size="lg" variant="ink" className="mt-4 w-full" onClick={() => void buy()} disabled={busy} aria-busy={busy}>
            {busy ? 'Opening checkout' : plan === 'plus' ? 'Become a Founding Member' : 'Get Pro'}
          </Button>
        </section>

        <div className="px-6 pt-5">
          <PlanCompare highlight={plan} />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 px-6 pt-4 pb-6">
          <p className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"><ShieldCheck className="size-3.5" aria-hidden="true" /> Secure checkout by Razorpay · cancel any time</p>
          <div className="flex gap-2">
            <Button asChild variant="ghost" size="sm" onClick={() => onClose()}><Link href="/pricing">Compare plans</Link></Button>
            <Button variant="ghost" size="sm" onClick={() => onClose()}>Maybe later</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Inline lock on a page: what the feature does, in the highlighter, with a button that opens the paywall. */
export function UpgradeBanner({ title, children, reason = 'upgrade_required', action, className }: {
  title: string; children?: ReactNode; reason?: string; action?: string; className?: string;
}) {
  const pro = reason === 'pro_required';
  return (
    <section className={cn('flex flex-col gap-4 rounded-card border-[1.5px] border-proof-stroke bg-proof text-proof-foreground p-5 sm:flex-row sm:items-center', className)}>
      <div className="min-w-0 flex-1">
        <p className="inline-flex items-center gap-1.5 text-xs font-bold"><Lock className="size-3.5" aria-hidden="true" /> {pro ? 'Pro feature' : `${PLAN_NAME.plus} feature`}</p>
        <p className="mt-1 font-display text-xl font-bold tracking-[-0.02em]">{title}</p>
        {children ? <div className="mt-1 text-[15px] text-proof-foreground/75">{children}</div> : null}
      </div>
      <Button size="lg" variant="ink" onClick={() => openPaywall(reason)}>{action ?? (pro ? 'Unlock with Pro' : 'Become a Founding Member')}</Button>
    </section>
  );
}
