'use client';

import { useCallback, useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { money } from '@/lib/billing';
import { PLAN_NAME } from '@/lib/plans';
import type { PlanId } from '@/lib/types';
import { ErrorNote, StatCard } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Row {
  id: string; name: string; subject: string; joined_at: number; plan: PlanId; status: string | null;
  interval: string | null; ends_at: number | null; cancelling: boolean; comped: boolean;
}
interface Users { items: Row[]; totals: { users: number; plus: number; pro: number; comped: number; mrr_inr: number } }

const day = (s: number) => new Date(s * 1000).toLocaleDateString();

/** Learners and their plans; an admin can grant a plan for some days or end one now. */
export function AdminUsers() {
  const [q, setQ] = useState('');
  const [data, setData] = useState<Users | null>(null);
  const [error, setError] = useState('');
  const [grant, setGrant] = useState<Record<string, { plan: PlanId; days: number }>>({});
  const [busy, setBusy] = useState('');

  const load = useCallback(() => {
    api.get<Users>(`/admin/users?q=${encodeURIComponent(q)}&limit=100`).then(setData).catch(e => setError(explain(e)));
  }, [q]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  async function apply(id: string) {
    const choice = grant[id] ?? { plan: 'plus', days: 30 };
    if (choice.plan === 'free' && !window.confirm('End this learner\'s plan now? A paying learner must also be cancelled in the Razorpay dashboard.')) return;
    setBusy(id);
    setError('');
    try {
      const row = await api.post<Row>(`/admin/users/${id}/plan`, choice);
      setData(d => d && { ...d, items: d.items.map(r => (r.id === id ? row : r)) });
      load();
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy('');
    }
  }

  const t = data?.totals;
  return (
    <div className="grid gap-6">
      {t ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Accounts" value={t.users.toLocaleString()} hint={t.comped ? `${t.comped} on a granted plan` : undefined} />
          <StatCard label={`Paying ${PLAN_NAME.plus}s`} value={t.plus.toLocaleString()} />
          <StatCard label="Paying Pro" value={t.pro.toLocaleString()} />
          <StatCard label="Monthly recurring (INR)" value={money(t.mrr_inr, 'INR')} hint="Yearly plans counted as a twelfth" />
        </div>
      ) : null}
      {error ? <ErrorNote message={error} /> : null}
      <Card className="gap-0 overflow-hidden pb-0">
        <CardHeader className="pb-3">
          <CardTitle>Learners and plans</CardTitle>
          <CardDescription>Newest first. Granting adds days to the current plan; Free ends access now. Billing itself is managed in Razorpay.</CardDescription>
          <div className="relative mt-3 max-w-sm">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Name, account subject or id" aria-label="Search learners" className="h-10 w-full rounded-full border border-border-strong bg-card pr-4 pl-9 text-sm" />
          </div>
        </CardHeader>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow><TableHead className="pl-4">Learner</TableHead><TableHead>Joined</TableHead><TableHead>Plan</TableHead><TableHead className="pr-4">Change plan</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.map(r => {
                const choice = grant[r.id] ?? { plan: 'plus' as PlanId, days: 30 };
                const set = (next: Partial<typeof choice>) => setGrant(g => ({ ...g, [r.id]: { ...choice, ...next } }));
                return (
                  <TableRow key={r.id}>
                    <TableCell className="pl-4"><p className="font-medium">{r.name || 'No name'}</p><p className="max-w-56 truncate font-mono text-xs text-muted-foreground">{r.subject}</p></TableCell>
                    <TableCell className="tabular-nums">{day(r.joined_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant={r.plan === 'free' ? 'secondary' : 'default'}>{PLAN_NAME[r.plan]}</Badge>
                        {r.comped ? <Badge variant="outline">granted</Badge> : null}
                        {r.cancelling ? <Badge variant="outline">cancelling</Badge> : null}
                      </div>
                      {r.ends_at ? <p className="mt-0.5 text-xs text-muted-foreground">until {day(r.ends_at)}</p> : null}
                    </TableCell>
                    <TableCell className="pr-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <NativeSelect size="sm" value={choice.plan} onChange={e => set({ plan: e.target.value as PlanId })} aria-label={`Plan for ${r.name || r.subject}`}>
                          <NativeSelectOption value="plus">{PLAN_NAME.plus}</NativeSelectOption>
                          <NativeSelectOption value="pro">Pro</NativeSelectOption>
                          <NativeSelectOption value="free">Free (end now)</NativeSelectOption>
                        </NativeSelect>
                        {choice.plan !== 'free' ? (
                          <NativeSelect size="sm" value={String(choice.days)} onChange={e => set({ days: Number(e.target.value) })} aria-label="Days">
                            {[7, 30, 90, 365].map(d => <NativeSelectOption key={d} value={String(d)}>{d} days</NativeSelectOption>)}
                          </NativeSelect>
                        ) : null}
                        <Button size="sm" variant="outline" disabled={busy === r.id} aria-busy={busy === r.id} onClick={() => void apply(r.id)}>Apply</Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        {data && !data.items.length ? <p className="px-4 pb-6 text-sm text-muted-foreground">No learners match.</p> : null}
      </Card>
    </div>
  );
}
