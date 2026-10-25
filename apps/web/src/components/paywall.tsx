'use client';

import Link from 'next/link';
import { useEffect, useState, type ReactNode } from 'react';
import { Check, Lock, Minus, ShieldCheck } from 'lucide-react';
import { PAYWALL_EVENT, api, explain, openPaywall } from '@/lib/api';
import { money, subscribe } from '@/lib/billing';
import { COMPARE, PAYWALL_REASON, PLAN_NAME, PLUS_WAS_INR } from '@/lib/plans';
import { useSession } from '@/lib/session';
import type { BillingStatus, PlanId } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';

const WELCOME_KEY = 'socrat:paywall-welcome:';

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

/** The paywall: opens on any locked feature (402), on the weekly chat limit, and once after first sign-in. */
export function PaywallHost() {
  const { profile, refresh } = useSession();
  const [reason, setReason] = useState<string | null>(null);
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const show = (e: Event) => setReason(current => current ?? String((e as CustomEvent).detail));
    window.addEventListener(PAYWALL_EVENT, show);
    return () => window.removeEventListener(PAYWALL_EVENT, show);
  }, []);

  useEffect(() => {
    if (!profile) return setStatus(null);
    api.get<BillingStatus>('/billing/status').then(s => {
      setStatus(s);
      // Right after sign-in, once per account: the plans, before the learner settles into Free.
      let seen = true;
      try { seen = localStorage.getItem(WELCOME_KEY + profile.id) !== null; localStorage.setItem(WELCOME_KEY + profile.id, '1'); } catch { /* storage unavailable: skip the welcome */ }
      if (s.enabled && s.plan === 'free' && !seen) setReason(current => current ?? 'welcome');
    }).catch(() => undefined);
  }, [profile]);

  const copy = reason ? PAYWALL_REASON[reason] ?? PAYWALL_REASON.upgrade_required : null;
  const plan = copy?.plan === 'pro' || status?.plan === 'plus' ? 'pro' : 'plus';
  const minor = status?.prices[plan].month.INR;
  const open = Boolean(copy && status?.enabled && status.plan !== 'pro');

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
    <Dialog open={open} onOpenChange={next => { if (!next) setReason(null); }}>
      <DialogContent className="max-h-[92dvh] gap-0 overflow-y-auto p-0 sm:max-w-[560px]">
        <div className="px-6 pt-6 pb-4">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground"><Lock className="size-3.5" aria-hidden="true" /> {status?.plan === 'plus' ? `You're a ${PLAN_NAME.plus}` : "You're on Free"}</p>
          <DialogTitle className="mt-2 font-display text-2xl font-bold tracking-[-0.03em]">{copy?.title}</DialogTitle>
          <DialogDescription className="mt-1.5 text-[15px]">{copy?.body}</DialogDescription>
        </div>

        <section aria-label={`${PLAN_NAME[plan]} plan`} className="mx-6 rounded-[18px] border-[1.5px] border-proof-stroke bg-proof text-proof-foreground p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-display text-lg font-bold">{PLAN_NAME[plan]}</p>
            <span className="rounded-full bg-proof-foreground px-2.5 py-0.5 text-[11px] font-bold text-proof">{plan === 'plus' ? 'Founding price · most popular' : 'Interview season'}</span>
          </div>
          <p className="mt-1 font-display text-3xl font-bold tabular-nums">
            {plan === 'plus' ? <s className="mr-2 text-lg font-medium text-proof-foreground/60" aria-label={`was ${money(PLUS_WAS_INR, 'INR')}`}>{money(PLUS_WAS_INR, 'INR')}</s> : null}
            {minor === undefined ? '—' : money(minor, 'INR')}<span className="text-base font-medium text-proof-foreground/70"> / month</span>
          </p>
          <p className="mt-1 text-[13px] text-proof-foreground/75">
            {plan === 'plus' ? 'Less than ₹4 a day. Your founding price stays the same for as long as you stay subscribed.' : 'Everything in Founding Member, plus every company question and sprint plan.'}
          </p>
          {error ? <p role="alert" className="mt-3 text-sm text-destructive">{error}</p> : null}
          <Button size="lg" variant="ink" className="mt-4 w-full" onClick={() => void buy()} disabled={busy || minor === undefined} aria-busy={busy}>
            {busy ? 'Opening checkout' : plan === 'plus' ? 'Become a Founding Member' : 'Get Pro'}
          </Button>
        </section>

        <div className="px-6 pt-5">
          <PlanCompare highlight={plan} />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 px-6 pt-4 pb-6">
          <p className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"><ShieldCheck className="size-3.5" aria-hidden="true" /> Secure checkout by Razorpay · cancel any time</p>
          <div className="flex gap-2">
            <Button asChild variant="ghost" size="sm" onClick={() => setReason(null)}><Link href="/pricing">Compare plans</Link></Button>
            <Button variant="ghost" size="sm" onClick={() => setReason(null)}>Maybe later</Button>
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
