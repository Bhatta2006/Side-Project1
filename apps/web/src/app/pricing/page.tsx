'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { Currency, Interval, money, subscribe } from '@/lib/billing';
import { useSession } from '@/lib/session';
import type { BillingStatus, PlanId } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Page, PageHeader } from '@/components/common';
import { SuccessLine } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';

const PLANS: { id: PlanId; name: string; blurb: string; features: string[] }[] = [
  { id: 'free', name: 'Free', blurb: 'Try Socrat.', features: ['First 2 modules of every course', '5 messages with Soc each week', 'Visual playground locked'] },
  { id: 'plus', name: 'Plus', blurb: 'Everything, at a steady pace.', features: ['Every topic and skill unlocked', '10 messages with Soc a day', '3 playground visuals a day'] },
  { id: 'pro', name: 'Pro', blurb: 'For daily, serious practice.', features: ['Every topic and skill unlocked', '50 messages with Soc a day', '15 playground visuals a day'] },
];

export default function PricingPage() {
  const { profile, refresh } = useSession();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [currency, setCurrency] = useState<Currency>('INR');
  const [interval, setInterval] = useState<Interval>('month');
  const [busy, setBusy] = useState<PlanId | null>(null);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

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

  const prices = status?.prices;
  return (
    <Page wide>
      <PageHeader title="Plans" description="Start free. Upgrade when you want every topic and more time with Soc. Plans renew automatically and you can cancel any time." />
      <div className="mt-6 flex flex-wrap gap-3" role="group" aria-label="Billing options">
        <div className="inline-flex rounded-full border p-1">
          {(['month', 'year'] as const).map(i => (
            <Button key={i} size="sm" variant={interval === i ? 'default' : 'ghost'} aria-pressed={interval === i} onClick={() => setInterval(i)}>{i === 'month' ? 'Monthly' : 'Yearly'}</Button>
          ))}
        </div>
        <div className="inline-flex rounded-full border p-1">
          {(['INR', 'USD'] as const).map(c => (
            <Button key={c} size="sm" variant={currency === c ? 'default' : 'ghost'} aria-pressed={currency === c} onClick={() => setCurrency(c)}>{c}</Button>
          ))}
        </div>
      </div>
      {error ? <ErrorNote message={error} className="mt-4" /> : null}
      {done ? <div className="mt-4"><SuccessLine>You're on {status?.plan === 'pro' ? 'Pro' : 'Plus'}. Everything is unlocked.</SuccessLine></div> : null}
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {PLANS.map(plan => {
          const minor = plan.id === 'free' ? 0 : prices?.[plan.id]?.[interval]?.[currency];
          const current = status?.plan === plan.id;
          return (
            <section key={plan.id} aria-labelledby={`plan-${plan.id}`} className={cn('flex flex-col rounded-card border bg-card p-5 lg:p-6', plan.id === 'plus' && 'border-border-strong')}>
              <h2 id={`plan-${plan.id}`} className="font-display text-xl font-bold tracking-[-0.03em]">{plan.name}</h2>
              <p className="mt-1 text-[15px] text-muted-foreground">{plan.blurb}</p>
              <p className="mt-4 font-display text-3xl font-bold tabular-nums">
                {plan.id === 'free' ? 'Free' : minor === undefined ? '—' : money(minor, currency)}
                {plan.id === 'free' || minor === undefined ? null : <span className="text-base font-medium text-muted-foreground"> / {interval}</span>}
              </p>
              <ul className="mt-4 grid gap-2 text-[15px]">
                {plan.features.map(f => <li key={f} className="flex gap-2"><Check className="mt-1 size-4 shrink-0" aria-hidden="true" />{f}</li>)}
              </ul>
              <div className="mt-auto pt-6">
                {current ? (
                  <Button variant="outline" disabled>Your plan</Button>
                ) : plan.id === 'free' ? null : !profile ? (
                  <Button asChild><Link href="/login?next=/pricing">Log in to upgrade</Link></Button>
                ) : status?.plan !== 'free' ? (
                  <Button variant="outline" asChild><Link href="/settings#plan-heading">Manage in Settings</Link></Button>
                ) : (
                  <Button onClick={() => void choose(plan.id as 'plus' | 'pro')} disabled={busy !== null || !status?.enabled} aria-busy={busy === plan.id}>
                    {busy === plan.id ? 'Opening checkout' : `Get ${plan.name}`}
                  </Button>
                )}
              </div>
            </section>
          );
        })}
      </div>
      <p className="mt-6 max-w-2xl text-[13px] text-muted-foreground">
        Payments are handled by Razorpay. Yearly plans cost about 7.5 months. Cancel in Settings and you keep access until the period you paid for ends. See the <Link href="/terms" className="underline underline-offset-4">terms</Link>.
      </p>
    </Page>
  );
}
