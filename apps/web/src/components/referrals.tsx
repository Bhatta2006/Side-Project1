'use client';

import dynamic from 'next/dynamic';
import { useEffect } from 'react';
import { toast } from 'sonner';
import { Gift } from 'lucide-react';
import { ApiError, api, explain } from '@/lib/api';
import { useSession } from '@/lib/session';

const KEY = 'socrat:ref';
// Old account, own link, already invited: nothing the visitor can act on.
const QUIET = ['referral_already_used', 'referral_own_code', 'referral_not_new'];

export function openReferrals() {
  window.dispatchEvent(new Event('socrat:refer'));
}

/** Loads on first open, like the feedback dialog. */
export const Referrals = dynamic(() => import('@/components/referral-dialog'), { ssr: false });

/** Remembers a friend's `?ref=` code until the visitor has an account, then claims it once. */
export function useReferralCapture() {
  const { profile } = useSession();
  useEffect(() => {
    try {
      const code = new URLSearchParams(window.location.search).get('ref');
      if (code) localStorage.setItem(KEY, code.slice(0, 12));
    } catch { /* storage blocked: the link just does not count */ }
  }, []);
  useEffect(() => {
    if (!profile) return;
    let code: string | null = null;
    try { code = localStorage.getItem(KEY); } catch { return; }
    if (!code) return;
    api.post<{ welcomed: boolean; days: number; referrer: string }>('/referrals/claim', { code })
      .then(r => {
        const from = r.referrer ? `${r.referrer} invited you` : 'You were invited';
        if (r.welcomed) toast.success(`${from}: ${r.days} days of Founding Member are yours, free.`);
      })
      .catch(e => { if (!(e instanceof ApiError && QUIET.includes(e.code))) toast.error(explain(e)); })
      .finally(() => { try { localStorage.removeItem(KEY); } catch { /* nothing to clean */ } });
  }, [profile]);
}

/** Sits beside the feedback note: a blue sticky note that opens the invite ladder. */
export function ReferButton() {
  return (
    <button
      type="button"
      onClick={openReferrals}
      aria-label="Invite friends and earn free Founding Member and Pro"
      className="group inline-flex h-9 rotate-2 items-center gap-1.5 rounded-[12px_9px_14px_10px] border-2 border-[var(--soc-outline)] bg-primary px-3 text-primary-foreground shadow-[2px_2px_0_var(--soc-outline)] transition-[transform,box-shadow] duration-200 ease-[var(--ease-soft)] hover:-translate-y-0.5 hover:rotate-0 hover:shadow-[3px_4px_0_var(--soc-outline)] active:translate-y-0 active:shadow-none"
    >
      <Gift className="size-4 transition-transform group-hover:-rotate-12" strokeWidth={2} aria-hidden="true" />
      <span className="hidden font-hand text-[18px] leading-none sm:inline">Invite</span>
      <span className="hidden rounded-full border border-current px-1.5 text-[10px] font-bold tracking-wide uppercase md:inline">free pro</span>
    </button>
  );
}
