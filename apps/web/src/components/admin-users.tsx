'use client';

import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { money } from '@/lib/billing';
import { PLAN_NAME } from '@/lib/plans';
import type { PlanId } from '@/lib/types';
import { ErrorNote } from '@/components/common';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, StatCard, StatRow, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, day, field, when } from '@/components/admin/ui';
import { Button } from '@/components/ui/button';

interface Row {
  id: string; name: string; subject: string; joined_at: number; plan: PlanId; status: string | null;
  interval: string | null; ends_at: number | null; cancelling: boolean; comped: boolean;
}
interface Users { items: Row[]; totals: { users: number; plus: number; pro: number; comped: number; mrr_inr: number } }
interface Note { id: string; title: string; body: string; created_at: number; seen_at: number | null }
interface Detail extends Row {
  email: string | null;
  sign_in: string;
  timezone: string;
  admin: boolean;
  effective_plan: PlanId;
  launch_offer: { slot: number; ends_at: number } | null;
  last_active_at: number | null;
  signed_in_devices: number;
  enrollments: { course: string; language: string; level: string; status: string }[];
  counts: { evidence: number; study_days: number; reports: number };
  activity: { kind: string; at: number }[];
  generations: { id: string; prompt: string; mode: string; status: string; error: string; at: number }[];
  notifications: Note[];
}

const select = 'h-9 rounded-[6px] border border-border-strong bg-card px-2 text-sm';
const planLabel = (r: Row) => `${PLAN_NAME[r.plan]}${r.comped ? ' (granted)' : ''}${r.cancelling ? ' (cancelling)' : ''}${r.ends_at ? `, until ${day(r.ends_at)}` : ''}`;

/** One account: its record, and everything an admin can do to it. */
function Account({ id, onClose, onChanged, onDeleted }: { id: string; onClose: () => void; onChanged: () => void; onDeleted: () => void }) {
  const [data, setData] = useState<Detail | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [plan, setPlan] = useState<PlanId>('plus');
  const [days, setDays] = useState(30);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [confirm, setConfirm] = useState('');

  const load = useCallback(() => {
    api.get<Detail>(`/admin/users/${id}`).then(setData).catch(e => setError(explain(e)));
  }, [id]);
  useEffect(() => { setData(null); setError(''); setConfirm(''); load(); }, [load]);

  async function run(name: string, action: () => Promise<unknown>, done: string) {
    setBusy(name);
    setError('');
    try {
      await action();
      toast.success(done);
      return true;
    } catch (e) {
      setError(explain(e));
      return false;
    } finally {
      setBusy('');
    }
  }

  async function applyPlan() {
    if (plan === 'free' && !window.confirm('End this learner\'s plan now? A paying learner must also be cancelled in the Razorpay dashboard.')) return;
    if (await run('plan', () => api.post(`/admin/users/${id}/plan`, { plan, days }), plan === 'free' ? 'Plan ended.' : `${PLAN_NAME[plan]} granted for ${days} days.`)) { load(); onChanged(); }
  }
  async function send() {
    if (await run('note', () => api.post(`/admin/users/${id}/notify`, { title: title.trim(), body: body.trim() }), 'Note sent. They will see it when they next open the app.')) { setTitle(''); setBody(''); load(); }
  }
  async function signOut() {
    if (await run('signout', () => api.post(`/admin/users/${id}/sign-out`, {}), 'Signed out on every device.')) load();
  }
  async function remove() {
    if (await run('delete', () => api.del(`/admin/users/${id}`), 'Account deleted.')) onDeleted();
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="[overflow-wrap:anywhere]">{data ? data.name || 'No name' : 'Loading…'}{data?.admin ? ' · admin' : ''}</CardTitle>
            {data ? <CardDescription className="[overflow-wrap:anywhere]">{data.email ?? data.subject} · {data.sign_in} · joined {day(data.joined_at)}</CardDescription> : null}
          </div>
          <Button size="sm" variant="outline" onClick={onClose}>Close</Button>
        </div>
      </CardHeader>
      {error ? <CardContent><ErrorNote message={error} /></CardContent> : null}
      {data ? (
        <>
          <CardContent>
            <StatRow>
              <StatCard label="Plan" value={PLAN_NAME[data.effective_plan]} hint={data.launch_offer && data.plan === 'free' ? `Launch offer, slot ${data.launch_offer.slot}, until ${day(data.launch_offer.ends_at)}` : planLabel(data)} />
              <StatCard label="Last active" value={data.last_active_at ? day(data.last_active_at) : 'Never'} hint={`${data.signed_in_devices} signed-in ${data.signed_in_devices === 1 ? 'device' : 'devices'}`} />
              <StatCard label="Results recorded" value={data.counts.evidence.toLocaleString()} hint={`${data.counts.study_days} study days`} />
              <StatCard label="Course" value={data.enrollments[0]?.course ?? 'None'} hint={data.enrollments[0] ? `${data.enrollments[0].language}, ${data.enrollments[0].status === 'active' ? 'placement done' : 'in placement'}` : 'Not enrolled yet'} />
            </StatRow>
          </CardContent>

          <CardContent className="grid gap-5 lg:grid-cols-2">
            <div className="grid content-start gap-2">
              <h3 className="text-sm font-semibold">Plan</h3>
              <div className="flex flex-wrap items-center gap-2">
                <select className={select} value={plan} onChange={e => setPlan(e.target.value as PlanId)} aria-label="Plan">
                  <option value="plus">{PLAN_NAME.plus}</option>
                  <option value="pro">Pro</option>
                  <option value="free">Free (end now)</option>
                </select>
                {plan !== 'free' ? (
                  <select className={select} value={days} onChange={e => setDays(Number(e.target.value))} aria-label="Days">
                    {[7, 30, 90, 365].map(d => <option key={d} value={d}>{d} days</option>)}
                  </select>
                ) : null}
                <Button size="sm" variant="outline" disabled={busy === 'plan'} onClick={() => void applyPlan()}>Apply</Button>
              </div>
              <p className="text-[13px] text-muted-foreground">Granting adds days to the current plan. Billing itself is managed in Razorpay.</p>

              <h3 className="mt-3 text-sm font-semibold">Send a note</h3>
              <input className={field} value={title} onChange={e => setTitle(e.target.value)} maxLength={120} placeholder="Title (optional)" aria-label="Note title" />
              <textarea className={`${field} h-24 py-2`} value={body} onChange={e => setBody(e.target.value)} maxLength={2000} placeholder="Shown to this learner the next time they open the app" aria-label="Note" />
              <div><Button size="sm" disabled={!body.trim() || busy === 'note'} onClick={() => void send()}>Send note</Button></div>
            </div>

            <div className="grid content-start gap-2">
              <h3 className="text-sm font-semibold">Access</h3>
              <div><Button size="sm" variant="outline" disabled={busy === 'signout'} onClick={() => void signOut()}>Sign out on every device</Button></div>

              <h3 className="mt-3 text-sm font-semibold">Delete account</h3>
              {data.admin ? <p className="text-[13px] text-muted-foreground">An admin account cannot be deleted here.</p> : (
                <>
                  <p className="text-[13px] text-muted-foreground">Removes the account and everything it owns: progress, code, chats and visuals. This cannot be undone. Type DELETE to confirm.</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <input className={`${field} w-32`} value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="DELETE" aria-label="Type DELETE to confirm" />
                    <Button size="sm" variant="destructive" disabled={confirm !== 'DELETE' || busy === 'delete'} onClick={() => void remove()}>Delete account</Button>
                  </div>
                </>
              )}
            </div>
          </CardContent>

          <div className="grid lg:grid-cols-2">
            <div className="min-w-0">
              <h3 className="px-4 pb-2 text-sm font-semibold">Activity <span className="font-normal text-muted-foreground">(latest {data.activity.length})</span></h3>
              {data.activity.length ? (
                <div className="max-h-72 overflow-y-auto">
                  <Table>
                    <TableBody>
                      {data.activity.map((a, i) => (
                        <TableRow key={`${a.kind}-${a.at}-${i}`}><TableCell className="font-mono text-xs">{a.kind}</TableCell><TableCell className="text-right text-xs whitespace-nowrap text-muted-foreground">{when(a.at)}</TableCell></TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : <p className="px-4 text-sm text-muted-foreground">Nothing recorded yet.</p>}
            </div>
            <div className="min-w-0 max-lg:mt-4">
              <h3 className="px-4 pb-2 text-sm font-semibold">Playground generations</h3>
              {data.generations.length ? (
                <div className="max-h-72 overflow-y-auto">
                  <Table>
                    <TableBody>
                      {data.generations.map(g => (
                        <TableRow key={g.id}>
                          <TableCell className="[overflow-wrap:anywhere]">{g.prompt}</TableCell>
                          <TableCell className={`text-right text-xs whitespace-nowrap ${g.status === 'failed' ? 'font-semibold text-attention' : 'text-muted-foreground'}`}>{g.status}{g.error ? `: ${g.error}` : ''}<span className="block font-normal text-muted-foreground">{when(g.at)}</span></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : <p className="px-4 text-sm text-muted-foreground">None yet.</p>}
              {data.notifications.length ? (
                <>
                  <h3 className="px-4 pt-4 pb-2 text-sm font-semibold">Notes sent</h3>
                  <Table>
                    <TableBody>
                      {data.notifications.map(n => (
                        <TableRow key={n.id}>
                          <TableCell className="[overflow-wrap:anywhere]">{n.title ? <span className="font-medium">{n.title}. </span> : null}{n.body}</TableCell>
                          <TableCell className="text-right text-xs whitespace-nowrap text-muted-foreground">{n.seen_at ? `read ${day(n.seen_at)}` : 'not read yet'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </>
              ) : null}
            </div>
          </div>
        </>
      ) : null}
    </Card>
  );
}

/** Every account: search, open one to manage it. */
export function AdminUsers() {
  const [q, setQ] = useState('');
  const [data, setData] = useState<Users | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get<Users>(`/admin/users?q=${encodeURIComponent(q)}&limit=100`).then(setData).catch(e => setError(explain(e)));
  }, [q]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  const t = data?.totals;
  return (
    <div className="grid gap-6">
      {t ? (
        <StatRow>
          <StatCard label="Accounts" value={t.users.toLocaleString()} hint={t.comped ? `${t.comped} on a granted plan` : undefined} />
          <StatCard label={`Paying ${PLAN_NAME.plus}`} value={t.plus.toLocaleString()} />
          <StatCard label="Paying Pro" value={t.pro.toLocaleString()} />
          <StatCard label="Monthly recurring (INR)" value={money(t.mrr_inr, 'INR')} hint="Yearly plans counted as a twelfth" />
        </StatRow>
      ) : null}
      {error ? <ErrorNote message={error} /> : null}
      {open ? <Account id={open} onClose={() => setOpen(null)} onChanged={load} onDeleted={() => { setOpen(null); load(); }} /> : null}
      <Card className="pb-0">
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
          <CardDescription>Newest first. Open an account to see its activity, change its plan, send a note, sign it out or delete it.</CardDescription>
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name, account subject or id" aria-label="Search accounts" className={`${field} mt-2 max-w-sm`} />
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow><TableHead className="pl-4">Learner</TableHead><TableHead>Joined</TableHead><TableHead>Plan</TableHead><TableHead className="pr-4 text-right">Manage</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            {data?.items.map(r => (
              <TableRow key={r.id} className={open === r.id ? 'bg-raised' : undefined}>
                <TableCell className="pl-4"><p className="font-medium [overflow-wrap:anywhere]">{r.name || 'No name'}</p><p className="max-w-56 truncate font-mono text-xs text-muted-foreground">{r.subject}</p></TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{day(r.joined_at)}</TableCell>
                <TableCell>{planLabel(r)}</TableCell>
                <TableCell className="pr-4 text-right"><Button size="sm" variant="outline" onClick={() => { setOpen(r.id); window.scrollTo({ top: 0 }); }}>Open</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {data && !data.items.length ? <p className="px-4 pb-4 text-sm text-muted-foreground">No accounts match.</p> : null}
      </Card>
    </div>
  );
}
