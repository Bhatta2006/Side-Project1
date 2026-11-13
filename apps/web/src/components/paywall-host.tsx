'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { PAYWALL_EVENT, api } from '@/lib/api';
import { useSession } from '@/lib/session';
import type { BillingStatus } from '@/lib/types';

// The dialog only downloads when it first opens, keeping it out of every page's first load.
const PaywallDialog = dynamic(() => import('./paywall').then(m => m.PaywallDialog), { ssr: false });

const WELCOME_KEY = 'socrat:paywall-welcome:';

/** Opens the paywall on any locked feature (402), on the weekly chat limit, and once after first sign-in. */
export function PaywallHost() {
  const { profile } = useSession();
  const [reason, setReason] = useState<string | null>(null);
  const [status, setStatus] = useState<BillingStatus | null>(null);

  useEffect(() => {
    const show = (e: Event) => setReason(current => current ?? String((e as CustomEvent).detail));
    window.addEventListener(PAYWALL_EVENT, show);
    return () => window.removeEventListener(PAYWALL_EVENT, show);
  }, []);

  useEffect(() => {
    if (!profile) return setStatus(null);
    api.cached<BillingStatus>('/billing/status').then(s => {
      setStatus(s);
      // Right after sign-in, once per account: the plans, before the learner settles into Free.
      let seen = true;
      try { seen = localStorage.getItem(WELCOME_KEY + profile.id) !== null; localStorage.setItem(WELCOME_KEY + profile.id, '1'); } catch { /* storage unavailable: skip the welcome */ }
      if (s.enabled && s.plan === 'free' && !seen) setReason(current => current ?? 'welcome');
    }).catch(() => undefined);
  }, [profile]);

  if (!reason || !status?.enabled || status.plan === 'pro') return null;
  return <PaywallDialog reason={reason} status={status} onClose={() => setReason(null)} />;
}
