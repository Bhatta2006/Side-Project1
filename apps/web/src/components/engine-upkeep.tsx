'use client';

import { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface Queue {
  enabled: boolean;
  dead_without_replacement: { concept: string; dead: string[]; good: number; needs: number }[];
  failing: { concept: string; url: string; failures: number }[];
  stale: { concept: string; age_days: number; review_after_days: number }[];
  unhelpful: { concept: string; url: string; helpful: number; unhelpful: number }[];
}
interface Version { id: string; version: number; reason: string; created_at: number }
interface Translation { concept: string; locale: string; status: 'machine' | 'reviewed'; reviewer: string | null; model: string; stale: boolean }

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

function Versions({ concept }: { concept: string }) {
  const [items, setItems] = useState<Version[] | null>(null);
  const [course, id] = concept.split(':');
  async function load() {
    try { setItems((await api.get<{ items: Version[] }>(`/admin/maintenance/${course}/${id}/versions`)).items); }
    catch (e) { toast.error(explain(e)); }
  }
  async function back(version: string) {
    try {
      await api.post(`/admin/maintenance/${course}/${id}/rollback`, { version });
      toast.success('Restored. The version you replaced is kept too.');
      await load();
    } catch (e) { toast.error(explain(e)); }
  }
  if (!items) return <Button size="sm" variant="outline" onClick={load}>Versions</Button>;
  return (
    <ul className="mt-2 grid gap-1 text-sm">
      {items.length === 0 ? <li className="text-muted-foreground">No earlier versions kept yet.</li> : null}
      {items.map(v => (
        <li key={v.id} className="flex items-center justify-between gap-3">
          <span>Version {v.version} · replaced by {v.reason} · {new Date(v.created_at * 1000).toLocaleDateString()}</span>
          <Button size="sm" variant="outline" onClick={() => back(v.id)}>Restore</Button>
        </li>
      ))}
    </ul>
  );
}

function Maintenance() {
  const [queue, setQueue] = useState<Queue | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    api.get<Queue>('/admin/maintenance').then(setQueue).catch(e => toast.error(explain(e)));
  }, []);
  useEffect(load, [load]);

  async function run() {
    setBusy(true);
    try {
      const r = await api.post<{ checked: number; failed: number; repaired: unknown[]; replaced?: unknown[] }>('/admin/maintenance/run');
      toast.success(`Checked ${r.checked} links, ${r.failed} failed, ${r.repaired.length} repaired, ${(r.replaced ?? []).length} replaced.`);
      load();
    } catch (e) { toast.error(explain(e)); } finally { setBusy(false); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Course maintenance</CardTitle>
        <CardDescription>
          Links of released generated lessons are checked on a schedule ({queue?.enabled ? 'on' : 'off'}). Dead links are
          removed when two good ones remain; everything else is listed here for you. Nothing is rewritten without you.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <div><Button onClick={run} disabled={busy}>{busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}Run a pass now</Button></div>
        {!queue ? <Empty>Loading…</Empty> : (
          <>
            <section aria-labelledby="m-stuck" className="grid gap-2">
              <h3 id="m-stuck" className="font-semibold">Dead links with no replacement</h3>
              {queue.dead_without_replacement.length === 0 ? <Empty>None.</Empty> : queue.dead_without_replacement.map(x => (
                <div key={x.concept} className="rounded-md border p-3 text-sm">
                  <p className="font-medium">{x.concept} <Badge variant="secondary">{x.good} of {x.needs} good links</Badge></p>
                  <ul className="mt-1 list-disc pl-5 text-muted-foreground">{x.dead.map(u => <li key={u} className="break-all">{u}</li>)}</ul>
                  <Versions concept={x.concept} />
                </div>
              ))}
            </section>
            <section aria-labelledby="m-stale" className="grid gap-2">
              <h3 id="m-stale" className="font-semibold">Due for a fresh look</h3>
              {queue.stale.length === 0 ? <Empty>None.</Empty> : queue.stale.map(x => (
                <div key={x.concept} className="rounded-md border p-3 text-sm">
                  <p className="font-medium">{x.concept}</p>
                  <p className="text-muted-foreground">Released {x.age_days} days ago; reviewed after {x.review_after_days}.</p>
                  <Versions concept={x.concept} />
                </div>
              ))}
            </section>
            <section aria-labelledby="m-bad" className="grid gap-2">
              <h3 id="m-bad" className="font-semibold">Resources learners mark unhelpful</h3>
              {queue.unhelpful.length === 0 ? <Empty>None.</Empty> : queue.unhelpful.map(x => (
                <p key={`${x.concept}${x.url}`} className="text-sm"><span className="font-medium">{x.concept}</span> · <span className="break-all">{x.url}</span> · {x.unhelpful} unhelpful, {x.helpful} helpful</p>
              ))}
            </section>
            {queue.failing.length ? <Empty>{queue.failing.length} link(s) failing but not dead yet; they are checked again before anything changes.</Empty> : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Translations() {
  const [items, setItems] = useState<Translation[] | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const load = useCallback(() => {
    api.get<{ items: Translation[] }>('/admin/translations').then(r => setItems(r.items)).catch(e => toast.error(explain(e)));
  }, []);
  useEffect(load, [load]);

  async function review(t: Translation) {
    const reviewer = (names[`${t.concept}/${t.locale}`] ?? '').trim();
    try {
      await api.post(`/admin/translations/${t.concept}/${t.locale}/review`, { reviewer });
      toast.success('Marked as reviewed.');
      load();
    } catch (e) { toast.error(explain(e)); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Translations</CardTitle>
        <CardDescription>
          A translation is shown as machine-translated until a named person confirms it, one at a time. If the English
          changes, the translation stops being shown and appears here as stale.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        {!items ? <Empty>Loading…</Empty> : items.length === 0 ? <Empty>No translations stored yet.</Empty> : items.map(t => {
          const key = `${t.concept}/${t.locale}`;
          return (
            <div key={key} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3 text-sm">
              <span>
                <span className="font-medium">{t.concept}</span> · {t.locale}{' '}
                <Badge variant={t.status === 'reviewed' ? 'default' : 'secondary'}>{t.status === 'reviewed' ? `reviewed by ${t.reviewer}` : 'machine'}</Badge>{' '}
                {t.stale ? <Badge variant="destructive">stale</Badge> : null}
              </span>
              {t.status === 'machine' && !t.stale ? (
                <span className="flex items-center gap-2">
                  <Input
                    aria-label={`Reviewer's full name for ${key}`}
                    className="h-9 w-48"
                    placeholder="Reviewer's full name"
                    value={names[key] ?? ''}
                    onChange={e => setNames(n => ({ ...n, [key]: e.target.value }))}
                  />
                  <Button size="sm" disabled={(names[key] ?? '').trim().length < 5} onClick={() => review(t)}>Confirm</Button>
                </span>
              ) : null}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

type Awaiting = { course_id: string; concept_id: string; label: string; findings: { source: string; problem: string }[] };

/** Released lessons that automated checks could not vouch for; a named person confirms each. */
function Validation() {
  const [items, setItems] = useState<Awaiting[] | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const load = useCallback(() => {
    api.get<{ items: Awaiting[] }>('/admin/maintenance/validation').then(r => setItems(r.items)).catch(e => toast.error(explain(e)));
  }, []);
  useEffect(load, [load]);

  async function confirm(a: Awaiting) {
    const key = `${a.course_id}/${a.concept_id}`;
    try {
      await api.post(`/admin/maintenance/validation/${a.course_id}/${a.concept_id}/confirm`, { reviewer: (names[key] ?? '').trim() });
      toast.success('Confirmed.');
      load();
    } catch (e) { toast.error(explain(e)); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Needs a person</CardTitle>
        <CardDescription>
          Generated lessons whose subject automated checks cannot vouch for (limited verification, hands-on skills,
          safety notes). Learners see them labelled until a named person confirms them.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        {!items ? <Empty>Loading…</Empty> : items.length === 0 ? <Empty>Nothing waiting for review.</Empty> : items.map(a => {
          const key = `${a.course_id}/${a.concept_id}`;
          return (
            <div key={key} className="grid gap-2 rounded-md border p-3 text-sm">
              <span className="font-medium">{key}</span>
              <ul className="list-disc pl-5 text-muted-foreground">
                {a.findings.slice(0, 4).map((f, i) => <li key={i}>{f.problem}</li>)}
              </ul>
              <span className="flex flex-wrap items-center gap-2">
                <Input
                  aria-label={`Reviewer's full name for ${key}`}
                  className="h-9 w-48"
                  placeholder="Reviewer's full name"
                  value={names[key] ?? ''}
                  onChange={e => setNames(n => ({ ...n, [key]: e.target.value }))}
                />
                <Button size="sm" disabled={(names[key] ?? '').trim().split(/\s+/).length < 2} onClick={() => confirm(a)}>Confirm</Button>
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

/** Admin-only: keep released courses healthy and translations honest. */
export function EngineUpkeep() {
  return <div className="grid gap-6"><Validation /><Maintenance /><Translations /></div>;
}
