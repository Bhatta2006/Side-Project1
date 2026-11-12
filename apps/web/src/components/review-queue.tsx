'use client';

import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, CircleAlert, CircleMinus, FileCheck2, Loader2, ShieldCheck, XCircle } from '@/components/icons';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { cn } from '@/lib/utils';
import Markdown from '@/components/markdown';
import { Difficulty, ErrorNote } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';

type Status = 'ready' | 'needs_validation' | 'failing' | 'changes_requested';
type GateStatus = 'pass' | 'warn' | 'fail' | 'skip';
interface Gate { name: string; status: GateStatus; detail: string }
interface Review { by: string; at: string; notes: string }
interface DraftSummary { id: string; course: string; title: string; difficulty: string | null; concepts: string[]; status: Status; review: Review | null }
interface DraftDetail {
  id: string;
  course: string;
  status: Status;
  validation: { verdict: GateStatus; gates: Gate[] } | null;
  review: Review | null;
  drafted: { model: string | null; idea: string | null; statement_check: Gate | null } | null;
  problem: {
    title: string; concepts: string[]; difficulty: string; statement: string; input_format: string; output_format: string;
    constraints: string[]; examples: { input: string; output: string; explanation?: string }[]; hints: string[];
    approach: string; reference: string; brute: string; time_limit_ms: number;
  };
}

const STATUS: Record<Status, { label: string; tone: string }> = {
  ready: { label: 'Ready to review', tone: 'border-foreground' },
  needs_validation: { label: 'Needs validation', tone: 'bg-muted text-muted-foreground' },
  failing: { label: 'Gates failing', tone: 'border-attention text-attention' },
  changes_requested: { label: 'Changes requested', tone: 'border-attention' },
};
const GATE_ICON: Record<GateStatus, { icon: typeof CheckCircle2; tone: string; label: string }> = {
  pass: { icon: CheckCircle2, tone: 'text-foreground', label: 'Pass' },
  warn: { icon: CircleAlert, tone: 'text-attention', label: 'Warning' },
  fail: { icon: XCircle, tone: 'text-attention', label: 'Fail' },
  skip: { icon: CircleMinus, tone: 'text-muted-foreground', label: 'Skipped' },
};

function Code({ children }: { children: string }) {
  return <pre className="max-h-72 overflow-auto rounded-[4px] bg-raised p-3 font-mono text-xs leading-relaxed">{children}</pre>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

/** Drafted judge problems: run the gates, read everything, then approve or send back. */
export function ReviewQueue() {
  const [queue, setQueue] = useState<{ enabled: boolean; items: DraftSummary[] } | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<DraftDetail | null>(null);
  const [busy, setBusy] = useState<'' | 'validate' | 'approve' | 'changes'>('');
  const [notes, setNotes] = useState('');

  const load = useCallback(() => {
    api.get<{ enabled: boolean; items: DraftSummary[] }>('/admin/drafts').then(setQueue).catch(e => setError(explain(e)));
  }, []);
  useEffect(load, [load]);

  async function show(id: string) {
    setNotes('');
    try { setOpen(await api.get<DraftDetail>(`/admin/drafts/${id}`)); } catch (e) { toast.error(explain(e)); }
  }

  async function act(kind: 'validate' | 'approve' | 'changes') {
    if (!open) return;
    setBusy(kind);
    try {
      if (kind === 'validate') {
        setOpen(await api.post<DraftDetail>(`/admin/drafts/${open.id}/validate`, {}));
      } else if (kind === 'changes') {
        setOpen(await api.post<DraftDetail>(`/admin/drafts/${open.id}/request-changes`, { notes }));
        toast('Sent back to the author with your notes.');
      } else {
        await api.post(`/admin/drafts/${open.id}/approve`, { notes });
        toast.success('Approved. Run the content build and commit the new problem file.');
        setOpen(null);
      }
      load();
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy('');
    }
  }

  if (error) return <ErrorNote message={error} retry={load} />;
  if (!queue) return <div className="flex justify-center p-10"><Loader2 className="animate-spin text-muted-foreground" aria-label="Loading drafts" /></div>;
  if (!queue.items.length) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon"><FileCheck2 /></EmptyMedia>
          <EmptyTitle>No drafts waiting</EmptyTitle>
          <EmptyDescription>
            {queue.enabled
              ? 'Drafted problems appear here. Create them with scripts/content/draft_problem.py.'
              : 'There is no drafts folder on this server. Review runs on an authoring checkout with content/drafts.'}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  const p = open?.problem;
  const failing = open?.validation?.verdict === 'fail';
  return (
    <>
      <Card className="gap-0 overflow-hidden pb-0">
        <CardHeader className="pb-3">
          <CardTitle as="h2">Problems waiting for review</CardTitle>
          <CardDescription>Nothing ships without passing the gates and one human approval.</CardDescription>
        </CardHeader>
        <Table>
          <TableHeader><TableRow><TableHead className="pl-4">Problem</TableHead><TableHead>Course · concept</TableHead><TableHead>Difficulty</TableHead><TableHead className="pr-4">Status</TableHead></TableRow></TableHeader>
          <TableBody>
            {queue.items.map(d => (
              <TableRow key={d.id}>
                <TableCell className="pl-4">
                  <button type="button" className="text-left font-semibold underline-offset-4 hover:underline" onClick={() => show(d.id)}>{d.title}</button>
                  <span className="block font-mono text-xs text-muted-foreground">{d.id}</span>
                </TableCell>
                <TableCell>{d.course} · {d.concepts.join(', ')}</TableCell>
                <TableCell>{d.difficulty ? <Difficulty level={d.difficulty} /> : '—'}</TableCell>
                <TableCell className="pr-4"><Badge variant="outline" className={STATUS[d.status].tone}>{STATUS[d.status].label}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Sheet open={Boolean(open)} onOpenChange={o => { if (!o) setOpen(null); }}>
        <SheetContent className="w-full gap-0 sm:max-w-2xl">
          {open && p ? (
            <>
              <SheetHeader className="border-b">
                <SheetTitle>{p.title}</SheetTitle>
                <SheetDescription className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs">{open.course}/{open.id}</span>
                  <Difficulty level={p.difficulty} />
                  <Badge variant="outline" className={STATUS[open.status].tone}>{STATUS[open.status].label}</Badge>
                </SheetDescription>
              </SheetHeader>
              <div className="grid flex-1 content-start gap-6 overflow-y-auto p-4">
                <Section title="Quality gates">
                  {open.validation ? (
                    <ul className="grid gap-1.5">
                      {open.validation.gates.map(g => {
                        const m = GATE_ICON[g.status];
                        return (
                          <li key={g.name} className="flex items-start gap-2 text-sm">
                            <m.icon className={cn('mt-0.5 size-4 flex-none', m.tone)} aria-label={m.label} />
                            <span><span className="font-medium capitalize">{g.name}</span> <span className="text-muted-foreground">— {g.detail}</span></span>
                          </li>
                        );
                      })}
                    </ul>
                  ) : <p className="text-sm text-muted-foreground">Not validated since the last edit.</p>}
                  <Button variant="outline" size="sm" className="justify-self-start" disabled={Boolean(busy)} onClick={() => act('validate')}>
                    {busy === 'validate' ? <Loader2 className="animate-spin" /> : <ShieldCheck />} Run the gates
                  </Button>
                </Section>
                {open.drafted ? (
                  <Section title="Drafting">
                    <p className="text-sm text-muted-foreground">
                      Drafted by {open.drafted.model ?? 'a model'}{open.drafted.idea ? ` from the idea “${open.drafted.idea}”` : ''}.
                    </p>
                    {open.drafted.statement_check ? (
                      <p className="flex items-start gap-2 text-sm">
                        {(() => { const m = GATE_ICON[open.drafted.statement_check.status]; return <m.icon className={cn('mt-0.5 size-4 flex-none', m.tone)} aria-label={m.label} />; })()}
                        <span><span className="font-medium">Independent solver</span> <span className="text-muted-foreground">— {open.drafted.statement_check.detail}</span></span>
                      </p>
                    ) : null}
                  </Section>
                ) : null}
                {open.review ? (
                  <Section title="Earlier review">
                    <p className="rounded-[4px] bg-raised p-3 text-sm">{open.review.notes} <span className="text-muted-foreground">— {open.review.by}, {open.review.at}</span></p>
                  </Section>
                ) : null}
                <Section title="Statement"><Markdown source={p.statement} /></Section>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Section title="Input"><Markdown source={p.input_format} /></Section>
                  <Section title="Output"><Markdown source={p.output_format} /></Section>
                </div>
                {p.constraints?.length ? <Section title="Constraints"><ul className="list-disc pl-5 text-sm">{p.constraints.map(c => <li key={c}>{c}</li>)}</ul></Section> : null}
                <Section title="Examples">
                  {p.examples.map((e, i) => (
                    <div key={i} className="grid gap-2 sm:grid-cols-2"><Code>{e.input}</Code><Code>{e.output}</Code></div>
                  ))}
                </Section>
                <Section title="Hints (in order)"><ol className="list-decimal pl-5 text-sm">{p.hints.map(h => <li key={h}>{h}</li>)}</ol></Section>
                <Section title="Approach"><Markdown source={p.approach} /></Section>
                <Section title="Reference solution"><Code>{p.reference}</Code></Section>
                <Section title="Brute force">{p.brute ? <Code>{p.brute}</Code> : <p className="text-sm font-semibold text-attention">Missing — drafts need one.</p>}</Section>
              </div>
              <SheetFooter className="border-t">
                <label className="grid gap-1.5 text-sm font-medium">
                  Review notes
                  <Textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} maxLength={2000} placeholder="What to fix, or why it is good to ship" />
                </label>
                <div className="flex flex-wrap justify-end gap-2">
                  <Button variant="outline" disabled={Boolean(busy) || !notes.trim()} onClick={() => act('changes')}>
                    {busy === 'changes' ? <Loader2 className="animate-spin" /> : null} Request changes
                  </Button>
                  <Button disabled={Boolean(busy) || !open.validation || failing} onClick={() => act('approve')}>
                    {busy === 'approve' ? <Loader2 className="animate-spin" /> : <CheckCircle2 />} Approve
                  </Button>
                </div>
              </SheetFooter>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </>
  );
}
