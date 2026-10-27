'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Check, Copy, Lock, Share2 } from 'lucide-react';
import { ApiError, api, explain } from '@/lib/api';
import { money } from '@/lib/billing';
import { PLAN_NAME, PLUS_WAS_INR } from '@/lib/plans';
import type { PlanId } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';

interface Rung { key: string; kind: 'active' | 'paid'; need: number; plan: PlanId; days: number; reached: boolean; granted: boolean }
interface Overview {
  code: string; friends: { joined: number; active: number; paid: number }; active_after: number;
  welcome: { plan: PlanId; days: number }; rungs: Rung[];
}

// What a reward is worth at list price: Plus at its pre-founding price, Pro at its monthly price (paise).
const MONTH: Partial<Record<PlanId, number>> = { plus: PLUS_WAS_INR, pro: 99900 };
const worth = (plan: PlanId, days: number) => Math.round(((MONTH[plan] ?? 0) * days) / 30);
// Old account, own link, already invited: nothing the visitor can act on.
const QUIET = ['referral_already_used', 'referral_own_code', 'referral_not_new'];
const span = (days: number) => (days === 7 ? '1 week' : days % 30 === 0 ? `${days / 30} month${days > 30 ? 's' : ''}` : `${days} days`);

/** Mounted once per shell (lazily): the invite link and the reward ladder. */
export default function ReferralDialog() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Overview | null>(null);

  useEffect(() => {
    const show = () => {
      setOpen(true);
      api.get<Overview>('/referrals').then(setData).catch(e => toast.error(explain(e)));
    };
    window.addEventListener('socrat:refer', show);
    return () => window.removeEventListener('socrat:refer', show);
  }, []);

  // Mounted only for signed-in learners: claims the invite code proxy.ts saved from /?ref=, once.
  useEffect(() => {
    const code = /(?:^|; )socrat_ref=([A-Za-z0-9]+)/.exec(document.cookie)?.[1];
    if (!code) return;
    api.post<{ welcomed: boolean; days: number; referrer: string }>('/referrals/claim', { code })
      .then(r => {
        const from = r.referrer ? `${r.referrer} invited you` : 'You were invited';
        if (r.welcomed) toast.success(`${from}: ${r.days} days of ${PLAN_NAME.plus} are yours, free.`);
      })
      .catch(e => {
        if (e instanceof ApiError && QUIET.includes(e.code)) return;
        toast.error(e instanceof ApiError && e.code === 'referral_code_invalid' ? 'That invite link is not valid. Ask your friend to send it again.' : explain(e));
      })
      .finally(() => { document.cookie = 'socrat_ref=; Max-Age=0; path=/'; });
  }, []);

  const link = data ? `${window.location.origin}/?ref=${data.code}` : '';
  const gift = data ? `${span(data.welcome.days)} of ${PLAN_NAME[data.welcome.plan]}` : `1 week of ${PLAN_NAME.plus}`;
  const pitch = `I'm learning to code with Socrat, an AI tutor that makes you think instead of handing you answers. Join with my link and get ${gift} free: ${link}`;
  const total = data?.rungs.reduce((sum, r) => sum + worth(r.plan, r.days), 0) ?? 0;

  function copy() {
    navigator.clipboard.writeText(link).then(() => toast.success('Link copied. Send it to a friend.'), () => toast.error('Could not copy. Select the link and copy it.'));
  }
  async function share() {
    if (navigator.share) {
      try { await navigator.share({ title: 'Socrat', text: pitch }); return; } catch { /* dismissed: copy instead */ }
    }
    copy();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto [&>*]:min-w-0">
        <DialogHeader>
          <DialogTitle>{total ? `Invite friends, earn up to ${money(total, 'INR')} of Socrat free` : 'Invite friends'}</DialogTitle>
          <DialogDescription>Your friend gets {gift} free the moment they join. Every reward below is yours to unlock, and they all stack.</DialogDescription>
        </DialogHeader>
        {data ? (
          <>
            <div className="grid gap-2">
              <div className="flex min-w-0 items-center gap-2 rounded-xl border border-border-strong bg-card p-1.5 pl-3">
                <span className="min-w-0 flex-1 truncate font-mono text-sm">{link}</span>
                <Button size="sm" variant="outline" onClick={copy} aria-label="Copy invite link"><Copy aria-hidden="true" />Copy</Button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button onClick={() => void share()}><Share2 aria-hidden="true" />Share</Button>
                <Button asChild variant="outline"><a href={`https://wa.me/?text=${encodeURIComponent(pitch)}`} target="_blank" rel="noopener noreferrer">WhatsApp</a></Button>
              </div>
            </div>
            <dl className="grid grid-cols-3 gap-2 text-center">
              {([['Joined', data.friends.joined], ['Learning', data.friends.active], ['Members', data.friends.paid]] as const).map(([label, n]) => (
                <div key={label} className="flex flex-col-reverse rounded-xl border border-border-strong p-2">
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="font-display text-2xl tabular-nums">{n}</dd>
                </div>
              ))}
            </dl>
            {(['active', 'paid'] as const).map(kind => {
              const rungs = data.rungs.filter(r => r.kind === kind);
              const have = data.friends[kind];
              const next = rungs.find(r => !r.reached);
              const title = kind === 'active' ? 'Friends who start learning' : `Friends who become ${PLAN_NAME.plus}s`;
              return (
                <section key={kind} className="grid gap-2" aria-label={title}>
                  <div>
                    <h3 className="text-sm font-semibold">{title}</h3>
                    <p className="text-xs text-muted-foreground">
                      {kind === 'active' ? `A friend counts once they finish ${data.active_after} lessons.` : 'The big ones: Pro, on us.'}
                      {next ? ` ${next.need - have} more to your next reward.` : ' All unlocked. Legend.'}
                    </p>
                  </div>
                  {next ? <Progress value={(100 * have) / next.need} aria-label={`${have} of ${next.need} friends`} /> : null}
                  <ol className="grid gap-1.5">
                    {rungs.map(r => (
                      <li key={r.key} className={cn('flex items-center gap-3 rounded-xl border px-3 py-2 text-sm', r.reached ? 'border-[var(--soc-outline)] bg-[var(--highlight)] text-[#15161E]' : 'border-border-strong')}>
                        <span className="grid size-7 flex-none place-items-center rounded-full border border-current text-xs font-bold tabular-nums" aria-hidden="true">{r.reached ? <Check className="size-4" /> : r.need}</span>
                        <span className="min-w-0 flex-1">
                          <span className="font-medium">{span(r.days)} of {PLAN_NAME[r.plan]}</span>
                          <span className="block text-xs opacity-75">{r.need} friend{r.need > 1 ? 's' : ''} · worth {money(worth(r.plan, r.days), 'INR')}</span>
                        </span>
                        {r.reached ? <span className="text-right text-xs font-semibold">{r.granted ? 'Yours' : 'Starts when your paid plan ends'}</span> : <Lock className="size-4 opacity-50" aria-label="Locked" />}
                      </li>
                    ))}
                  </ol>
                </section>
              );
            })}
          </>
        ) : <p className="py-8 text-center text-sm text-muted-foreground">Loading your invite link…</p>}
      </DialogContent>
    </Dialog>
  );
}
