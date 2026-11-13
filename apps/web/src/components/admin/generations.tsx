'use client';

import { useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { ErrorNote } from '@/components/common';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, StatCard, StatRow, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, when } from '@/components/admin/ui';

interface Tally { failed: number; total: number }
interface Failed {
  playground: { id: string; user: { id: string; name: string } | null; prompt: string; mode: string; level: string; error: string; tries: number; shared: boolean; at: number }[];
  courses: { id: string; kind: string; course: string; target: string; error: string; at: number }[];
  summary: { last_day: Tally; last_week: Tally; reasons: { error: string; count: number }[] };
}

const share = (t: Tally) => (t.total ? `${Math.round((100 * t.failed) / t.total)}% of ${t.total}` : 'none run');

/** Generations that failed. The worker records each one as it gives up; nothing is entered by hand. */
export function FailedGenerations() {
  const [data, setData] = useState<Failed | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Failed>('/admin/generations/failed').then(setData).catch(e => setError(explain(e)));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const top = data.summary.reasons[0];
  return (
    <div className="grid gap-6">
      <StatRow>
        <StatCard label="Playground failures, last 24 hours" value={data.summary.last_day.failed} hint={share(data.summary.last_day)} />
        <StatCard label="Playground failures, last 7 days" value={data.summary.last_week.failed} hint={share(data.summary.last_week)} />
        <StatCard label="Most common reason, 30 days" value={top ? top.count : 0} hint={top ? top.error : 'No failures'} />
        <StatCard label="Course generation failures" value={data.courses.length} hint="Shown below" />
      </StatRow>

      <Card className="pb-0">
        <CardHeader>
          <CardTitle>Playground generations that failed</CardTitle>
          <CardDescription>Newest first. Logged by the worker the moment a generation gives up, with the reason it recorded.</CardDescription>
        </CardHeader>
        {data.playground.length ? (
          <Table>
            <TableHeader><TableRow><TableHead className="pl-4">When</TableHead><TableHead>Learner</TableHead><TableHead>Asked for</TableHead><TableHead>Reason</TableHead><TableHead className="pr-4 text-right">Tries</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.playground.map(j => (
                <TableRow key={j.id}>
                  <TableCell className="pl-4 text-xs whitespace-nowrap text-muted-foreground">{when(j.at)}</TableCell>
                  <TableCell className="whitespace-nowrap">{j.user?.name ?? 'Deleted account'}{j.shared ? <span className="block text-xs text-muted-foreground">shared visual</span> : null}</TableCell>
                  <TableCell className="min-w-56 [overflow-wrap:anywhere]">{j.prompt}<span className="block text-xs text-muted-foreground">{j.mode} · {j.level}</span></TableCell>
                  <TableCell className="font-mono text-xs [overflow-wrap:anywhere]">{j.error}</TableCell>
                  <TableCell className="pr-4 text-right tabular-nums">{j.tries}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <CardContent className="pb-4 text-sm text-muted-foreground">No playground generation has failed.</CardContent>}
      </Card>

      {data.summary.reasons.length > 1 ? (
        <Card className="pb-0">
          <CardHeader><CardTitle>Reasons, last 30 days</CardTitle></CardHeader>
          <Table>
            <TableBody>
              {data.summary.reasons.map(r => (
                <TableRow key={r.error}><TableCell className="pl-4 font-mono text-xs">{r.error}</TableCell><TableCell className="pr-4 text-right tabular-nums">{r.count}</TableCell></TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}

      {data.courses.length ? (
        <Card className="pb-0">
          <CardHeader><CardTitle>Course generation jobs that failed</CardTitle></CardHeader>
          <Table>
            <TableHeader><TableRow><TableHead className="pl-4">When</TableHead><TableHead>Job</TableHead><TableHead className="pr-4">Reason</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.courses.map(j => (
                <TableRow key={j.id}>
                  <TableCell className="pl-4 text-xs whitespace-nowrap text-muted-foreground">{when(j.at)}</TableCell>
                  <TableCell>{j.kind} · {j.course}{j.target ? ` · ${j.target}` : ''}</TableCell>
                  <TableCell className="pr-4 text-xs [overflow-wrap:anywhere]">{j.error}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}
