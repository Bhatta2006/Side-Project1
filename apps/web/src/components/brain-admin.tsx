'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

// The course brain's owner view (backlog 3.7): roots, their researched units, the correction
// path for a wrong unit, and why a request got its course. Reads the /admin/brain routes only.

interface Root { id: string; title: string; status: string; merged_into: string | null }
interface Unit {
  id: string; key: string; revision: number; status: string; topic: string; depth: string;
  concepts: string[]; items: Record<string, number>; problems: string[]; courses: string[];
  sources: { url: string; title: string }[];
}
interface Match {
  outcome: string; course: string | null; reason: string; root: string | null; units: string[];
  adaptations: string[]; private: string[];
  candidates: { course: string; passed?: boolean; why?: string; failed?: string[] }[];
}

function Units({ root }: { root: string }) {
  const [items, setItems] = useState<Unit[] | null>(null);
  const [reason, setReason] = useState('');
  const load = () =>
    api.get<{ items: Unit[] }>(`/admin/brain/units?root=${encodeURIComponent(root)}`)
      .then(r => setItems(r.items), e => toast.error(explain(e)));
  useEffect(() => { load(); }, [root]); // eslint-disable-line react-hooks/exhaustive-deps
  async function correct(id: string) {
    try {
      await api.post(`/admin/brain/units/${id}/correct`, { reason });
      toast.success('Withdrawn; a corrected revision is being researched.');
      setReason('');
      load();
    } catch (e) { toast.error(explain(e)); }
  }
  if (items === null) return <p className="text-sm text-muted-foreground">Loading units…</p>;
  if (!items.length) return <p className="text-sm text-muted-foreground">No researched units yet.</p>;
  return (
    <div className="space-y-3">
      <Input placeholder="Why a unit is wrong (5+ characters), then Correct" value={reason}
        onChange={e => setReason(e.target.value)} />
      {items.map(u => (
        <div key={u.id} className="rounded-md border p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{u.key}</span>
            <Badge variant={u.status === 'validated' ? 'secondary' : 'destructive'}>{u.status}</Badge>
            <span className="text-muted-foreground">rev {u.revision} · {u.depth}</span>
            <Button size="sm" variant="outline" className="ml-auto" disabled={reason.trim().length < 5}
              onClick={() => correct(u.id)}>Correct</Button>
          </div>
          <p className="mt-1 text-muted-foreground">
            {u.concepts.length} concepts · {Object.entries(u.items).map(([k, n]) => `${n} ${k}`).join(' · ')}
            {' · '}{u.sources.length} sources · used by {u.courses.length} course{u.courses.length === 1 ? '' : 's'}
          </p>
          {u.problems.length > 0 && <p className="mt-1 text-destructive">{u.problems.slice(0, 3).join('; ')}</p>}
        </div>
      ))}
    </div>
  );
}

function Why() {
  const [id, setId] = useState('');
  const [found, setFound] = useState<Match | null>(null);
  async function look() {
    try { setFound(await api.get<Match>(`/admin/brain/matches/${encodeURIComponent(id.trim())}`)); }
    catch (e) { setFound(null); toast.error(explain(e)); }
  }
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input placeholder="Learning request id" value={id} onChange={e => setId(e.target.value)} />
        <Button onClick={look} disabled={!id.trim()}>Explain</Button>
      </div>
      {found && (
        <div className="space-y-1 text-sm">
          <p><Badge>{found.outcome}</Badge> {found.course ?? 'no course'} · {found.reason}</p>
          {found.adaptations.length > 0 && <p>Adapted for this learner: {found.adaptations.join('; ')}</p>}
          <p className="text-muted-foreground">Private to the learner: {found.private.join(', ') || 'nothing'}</p>
          <ul className="list-disc pl-5">
            {found.candidates.map(c => (
              <li key={c.course}>
                {c.course}: {c.passed ? 'passed' : `not served (${[c.why, ...(c.failed ?? [])].filter(Boolean).join(', ')})`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function BrainAdmin() {
  const [roots, setRoots] = useState<Root[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    api.get<{ items: Root[] }>('/admin/brain/roots').then(r => setRoots(r.items), e => toast.error(explain(e)));
  }, []);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Subjects</CardTitle>
          <CardDescription>Roots created on demand, and the researched material each holds.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {roots === null && <p className="text-sm text-muted-foreground">Loading…</p>}
          {roots?.length === 0 && <p className="text-sm text-muted-foreground">No subjects yet.</p>}
          {roots?.map(r => (
            <div key={r.id}>
              <Button variant={open === r.id ? 'secondary' : 'ghost'} className="w-full justify-start"
                onClick={() => setOpen(open === r.id ? null : r.id)}>
                {r.title} {r.status !== 'active' && <Badge variant="outline" className="ml-2">merged into {r.merged_into}</Badge>}
              </Button>
              {open === r.id && <div className="mt-2"><Units root={r.id} /></div>}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Why this course?</CardTitle>
          <CardDescription>The decision for one request: every candidate and the check it failed.</CardDescription>
        </CardHeader>
        <CardContent><Why /></CardContent>
      </Card>
    </div>
  );
}
