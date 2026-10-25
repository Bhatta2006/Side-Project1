'use client';

import { useEffect, useState } from 'react';
import { Link2, RefreshCw, Unlink } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import type { CodeforcesAccount } from '@/lib/types';
import { AttentionIcon } from '@/components/socrat/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';

function ago(seconds: number | null): string {
  if (!seconds) return 'never';
  const minutes = Math.round((Date.now() / 1000 - seconds) / 60);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hoursAgo = Math.round(minutes / 60);
  return hoursAgo < 48 ? `${hoursAgo} h ago` : `${Math.round(hoursAgo / 24)} days ago`;
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-[16px] bg-raised px-3 py-2.5">
      <p className="text-[13px] text-muted-foreground">{label}</p>
      <p className="text-base font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export default function CodeforcesLink() {
  const [account, setAccount] = useState<CodeforcesAccount | null | undefined>(undefined);
  const [handle, setHandle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<{ account: CodeforcesAccount | null }>('/library/codeforces').then(r => setAccount(r.account)).catch(() => setAccount(null));
  }, []);

  async function run(action: () => Promise<{ account: CodeforcesAccount; synced?: boolean }>) {
    setBusy(true);
    setError('');
    try {
      const result = await action();
      setAccount(result.account);
      if (result.synced === false) toast.info('Synced recently. Try again in a few minutes.');
      else toast.success(`Synced. ${result.account.solved} solved problems imported.`);
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card id="codeforces" className="scroll-mt-24" aria-labelledby="codeforces-heading">
      <CardHeader>
        <CardTitle as="h2" id="codeforces-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Codeforces</CardTitle>
        <CardDescription>Link your public handle and Socrat reads your rating and accepted solutions to pitch problems at the right level. Public data only. No password.</CardDescription>
        {account ? <CardAction><Badge variant="outline" className="capitalize">{account.rank}</Badge></CardAction> : null}
      </CardHeader>
      <CardContent className="grid gap-4">
        {account === undefined ? null : account ? (
          <>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Handle" value={account.handle} />
              <Stat label="Rating" value={account.rating ?? 'Unrated'} />
              <Stat label="Max rating" value={account.max_rating ?? '—'} />
              <Stat label="Solved" value={account.solved} />
            </div>
            {account.weak_tags.length ? (
              <div className="flex flex-wrap items-center gap-1.5 text-sm">
                <span className="text-muted-foreground">Tags you most often miss:</span>
                {account.weak_tags.map(t => <Badge key={t} variant="secondary">{t}</Badge>)}
              </div>
            ) : null}
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" disabled={busy} onClick={() => run(() => api.post('/library/codeforces/sync'))}>
                {busy ? <Spinner /> : <RefreshCw data-icon="inline-start" />} Sync now
              </Button>
              <Button variant="ghost" size="sm" disabled={busy} onClick={async () => { await api.del('/library/codeforces'); setAccount(null); toast('Codeforces unlinked.'); }}>
                <Unlink data-icon="inline-start" /> Unlink
              </Button>
              <span className="text-[13px] text-muted-foreground">Last synced {ago(account.synced_at)}{account.sync_error ? '. The last sync failed, so earlier data is shown' : ''}</span>
            </div>
          </>
        ) : (
          <form className="flex flex-wrap items-end gap-2" onSubmit={e => { e.preventDefault(); if (handle.trim()) run(() => api.post('/library/codeforces', { handle: handle.trim() })); }}>
            <label className="grid gap-1.5">
              <span className="text-[15px] font-semibold">Your handle</span>
              <Input className="w-64" value={handle} onChange={e => setHandle(e.target.value)} placeholder="e.g. tourist" autoComplete="off" maxLength={24} />
            </label>
            <Button size="lg" disabled={busy || !handle.trim()} aria-busy={busy}>
              {busy ? <Spinner /> : <Link2 data-icon="inline-start" />} Link
            </Button>
          </form>
        )}
        {error ? <p role="alert" className="flex items-center gap-2 rounded-[16px] border border-attention px-3 py-2 text-sm"><AttentionIcon size={20} /> {error}</p> : null}
      </CardContent>
    </Card>
  );
}
