'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Check, Minus } from '@/components/icons';
import { api, explain } from '@/lib/api';
import { Currency, Interval, money, subscribe } from '@/lib/billing';
import { PLAN_BLURB, PLAN_NAME, PLUS_WAS_INR } from '@/lib/plans';
import { useSession } from '@/lib/session';
import type { BillingStatus, PlanId } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Page, PageHeader } from '@/components/common';
import { PlanCompare } from '@/components/paywall';
import { SuccessLine } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';

const RANK: Record<PlanId, number> = { free: 0, plus: 1, pro: 2 };
const PLANS: { id: PlanId; features: string[]; missing?: string[] }[] = [
  { id: 'free', features: ['First 2 modules of every course', '5 messages with Soc a week', 'A few starter practice problems'], missing: ['Weekly assessment', 'Visual playground', 'Company questions'] },
  { id: 'plus', features: ['Every topic in every course', '10 messages with Soc a day', 'Full practice library and checkpoints', 'Weekly assessment', '3 playground visuals a day'], missing: ['Company questions'] },
  { id: 'pro', features: ['Everything in Founding Member', 'Every company interview question', 'Company sprint plans', '50 messages with Soc a day', '15 playground visuals a day'] },
];

export default function PricingPage() {
  const { profile, refresh } = useSession();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [prices, setPrices] = useState<BillingStatus['prices'] | null>(null);
  const [currency, setCurrency] = useState<Currency>('INR');
  const [interval, setInterval] = useState<Interval>('month');
  const [busy, setBusy] = useState<PlanId | null>(null);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.get<BillingStatus['prices']>('/billing/prices').then(setPrices).catch(() => undefined); // public: shown before sign-in
  }, []);
  useEffect(() => {
    if (profile) api.get<BillingStatus>('/billing/status').then(setStatus).catch(() => undefined);
  }, [profile]);

  async function choose(plan: 'plus' | 'pro') {
    setError('');
    setBusy(plan);
    try {
      if (await subscribe(plan, interval, currency)) {
        setDone(true);
        setStatus(await api.get<BillingStatus>('/billing/status'));
        await refresh();
      }
    } catch (e) {
      setError(e instanceof Error && !('code' in e) ? e.message : explain(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Page wide>
      <PageHeader title="Plans" description="Free gets you started. Founding Members get the whole course for less than ₹4 a day, at a price that stays the same for as long as they stay subscribed. Cancel any time." />
      <div className="mt-6 flex flex-wrap gap-3" role="group" aria-label="Billing options">
        <div className="inline-flex rounded-full border p-1">
          {(['month', 'year'] as const).map(i => (
            <Button key={i} size="sm" variant={interval === i ? 'default' : 'ghost'} aria-pressed={interval === i} onClick={() => setInterval(i)}>{i === 'month' ? 'Monthly' : 'Yearly · save 20%'}</Button>
          ))}
        </div>
        <div className="inline-flex rounded-full border p-1">
          {(['INR', 'USD'] as const).map(c => (
            <Button key={c} size="sm" variant={currency === c ? 'default' : 'ghost'} aria-pressed={currency === c} onClick={() => setCurrency(c)}>{c}</Button>
          ))}
        </div>
      </div>
      {error ? <ErrorNote message={error} className="mt-4" /> : null}
      {done ? <div className="mt-4"><SuccessLine>You&apos;re on {PLAN_NAME[status?.plan ?? 'plus']}. Everything in it is unlocked.</SuccessLine></div> : null}
      <div className="mt-8 grid items-stretch gap-5 lg:grid-cols-3">
        {PLANS.map(plan => {
          const minor = plan.id === 'free' ? 0 : prices?.[plan.id]?.[interval]?.[currency];
          const current = status?.plan === plan.id;
          const featured = plan.id === 'plus';
          const name = PLAN_NAME[plan.id];
          return (
            <section
              key={plan.id}
              aria-labelledby={`plan-${plan.id}`}
              className={cn(
                'relative flex flex-col rounded-card border bg-card p-5 lg:p-6',
                // The plan to pick wears the highlighter and sits a little forward of the others.
                featured && 'border-[1.5px] border-proof-stroke bg-proof text-proof-foreground shadow-[6px_6px_0_var(--proof-stroke)] md:-my-3 md:py-8',
              )}
            >
              {featured ? <span className="absolute -top-3 left-5 rounded-full bg-proof-foreground px-3 py-1 text-xs font-bold whitespace-nowrap text-proof">Most popular · founding price</span> : null}
              <h2 id={`plan-${plan.id}`} className="font-display text-xl font-bold tracking-[-0.03em]">{name}</h2>
              <p className={cn('mt-1 text-[15px]', featured ? 'text-proof-foreground/75' : 'text-muted-foreground')}>{PLAN_BLURB[plan.id]}</p>
              <p className="mt-4 font-display text-3xl font-bold tabular-nums">
                {featured && interval === 'month' && currency === 'INR' ? <s className="mr-2 text-lg font-medium opacity-60" aria-label={`was ${money(PLUS_WAS_INR, 'INR')}`}>{money(PLUS_WAS_INR, 'INR')}</s> : null}
                {plan.id === 'free' ? (currency === 'INR' ? '₹0' : '$0') : minor === undefined ? '—' : money(minor, currency)}
                {plan.id === 'free' || minor === undefined ? null : <span className="text-base font-medium opacity-70"> / {interval}</span>}
              </p>
              {featured ? <p className="mt-1 text-[13px] font-medium">Founding price, kept for as long as you stay subscribed.</p> : null}
              <ul className="mt-4 grid gap-2 text-[15px]">
                {plan.features.map(f => <li key={f} className="flex gap-2"><Check className="mt-1 size-4 shrink-0" aria-hidden="true" />{f}</li>)}
                {plan.missing?.map(f => (
                  <li key={f} className="flex gap-2 line-through opacity-55">
                    <Minus className="mt-1 size-4 shrink-0" aria-hidden="true" /><span><span className="sr-only">Not included: </span>{f}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-auto pt-6">
                {current ? (
                  <Button variant="outline" className="w-full" disabled>Your plan</Button>
                ) : plan.id === 'free' ? null : !profile ? (
                  <Button asChild className="w-full" variant={featured ? 'default' : 'outline'}><Link href="/login?next=/pricing">Log in to upgrade</Link></Button>
                ) : status && RANK[plan.id] < RANK[status.plan] ? null : (
                  <Button size={featured ? 'lg' : 'default'} variant={featured ? 'ink' : 'outline'} className="w-full" onClick={() => void choose(plan.id as 'plus' | 'pro')} disabled={busy !== null || !status?.enabled} aria-busy={busy === plan.id}>
                    {busy === plan.id ? 'Opening checkout' : featured ? 'Become a Founding Member' : status && status.plan !== 'free' ? `Upgrade to ${name}` : `Get ${name}`}
                  </Button>
                )}
              </div>
            </section>
          );
        })}
      </div>
      <section aria-labelledby="compare-heading" className="mt-10 rounded-card border bg-card p-5 lg:p-6">
        <h2 id="compare-heading" className="font-display text-xl font-bold tracking-[-0.03em]">Compare plans</h2>
        <div className="mt-4 overflow-x-auto"><PlanCompare className="min-w-[520px] text-[14px]" /></div>
      </section>
      <p className="mt-6 max-w-2xl text-[13px] text-muted-foreground">
        Payments are handled by Razorpay. Yearly plans save 20%. Upgrading starts the new plan today and ends the old one. Cancel in Settings and you keep access until the period you paid for ends. See the <Link href="/terms" className="underline underline-offset-4">terms</Link> and the <Link href="/refunds" className="underline underline-offset-4">refund policy</Link>.
      </p>
    </Page>
  );
}
