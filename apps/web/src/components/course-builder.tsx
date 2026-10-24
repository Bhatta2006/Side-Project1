'use client';

import { useCallback, useEffect, useState } from 'react';
import { BookPlus, CheckCircle2, Loader2, RotateCcw, Save, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { ErrorNote } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';

type CourseStatus = 'drafting' | 'review' | 'published';
type JobState = 'queued' | 'running' | 'done' | 'failed';
interface LogEntry {
  role: 'architect' | 'critic' | 'system';
  round?: number;
  at: number;
  event?: string;
  verdict?: 'pass' | 'revise';
  summary?: string;
  issues?: string[];
  concepts?: number;
  modules?: number;
}
interface Job { id: string; kind: string; state: JobState; log: LogEntry[]; cost_usd: number; error: string; created_at: number; updated_at: number }
interface Summary { id: string; title: string; status: CourseStatus; concepts: number | null; job: Job | null; spent_usd: number; budget_usd: number }
interface Brief { id: string; title: string; audience: string; outcome: string; background: string; languages: string[]; reuse: string[]; references: string[]; notes: string; budget_usd: number }
interface OutlineConcept {
  id: string; title: string; summary: string; module: string; prerequisites: string[]; difficulty: number; estimated_minutes: number;
  outline: { depth: string; objectives: string[]; misconceptions: string[]; assessment: string[] } | null;
}
interface CourseJson {
  title: string; tagline: string; description: string;
  levels: { id: string; label: string; description: string; start_concept: string | null }[];
  modules: { id: string; title: string; summary: string; concepts: string[] }[];
  concepts: OutlineConcept[];
}
interface Detail { id: string; status: CourseStatus; brief: Brief; course: CourseJson | null; jobs: Job[]; spent_usd: number }

const STATUS_LABEL: Record<CourseStatus, string> = { drafting: 'Drafting', review: 'Ready to review', published: 'Published' };
const busyJob = (job: Job | null | undefined) => job?.state === 'queued' || job?.state === 'running';
const usd = (n: number) => `$${n.toFixed(2)}`;
const lines = (s: string) => s.split(/[\n,]/).map(x => x.trim()).filter(Boolean);

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="grid gap-2"><h3 className="text-sm font-semibold">{title}</h3>{children}</section>;
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium">
      {label}
      {children}
      {hint ? <span className="text-xs font-normal text-muted-foreground">{hint}</span> : null}
    </label>
  );
}

const EMPTY = { id: '', title: '', audience: '', outcome: '', background: '', languages: 'python', reuse: '', references: '', notes: '', budget: '5' };

/** The owner's brief: everything the agents need to plan a course. */
function BriefForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState(EMPTY);
  const [sending, setSending] = useState(false);
  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm(f => ({ ...f, [key]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    try {
      await api.post('/admin/courses/briefs', {
        id: form.id.trim(), title: form.title.trim(), audience: form.audience.trim(), outcome: form.outcome.trim(),
        background: form.background.trim(), languages: lines(form.languages), reuse: lines(form.reuse),
        references: lines(form.references), notes: form.notes.trim(), budget_usd: Number(form.budget),
      });
      toast.success('Brief sent. The architect is planning the outline.');
      setForm(EMPTY);
      onCreated();
    } catch (err) {
      toast.error(explain(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2" className="flex items-center gap-2"><BookPlus className="size-4" /> New course</CardTitle>
        <CardDescription>Write the brief. Agents plan the whole outline, a critic reviews it, and it waits here for you. Nothing reaches learners until you publish.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Field label="Course id" hint="Lowercase and dashes, e.g. ai-basics"><Input required pattern="[a-z][a-z0-9-]{0,63}" value={form.id} onChange={set('id')} /></Field>
          <Field label="Title"><Input required minLength={2} maxLength={80} value={form.title} onChange={set('title')} /></Field>
          <Field label="Who it is for"><Textarea required minLength={10} maxLength={600} rows={3} value={form.audience} onChange={set('audience')} /></Field>
          <Field label="What learners can do at the end"><Textarea required minLength={10} maxLength={600} rows={3} value={form.outcome} onChange={set('outcome')} /></Field>
          <Field label="What they already know"><Textarea maxLength={600} rows={2} value={form.background} onChange={set('background')} /></Field>
          <Field label="Notes for the architect"><Textarea maxLength={2000} rows={2} value={form.notes} onChange={set('notes')} /></Field>
          <Field label="Code languages" hint="Comma separated: python, cpp, java"><Input value={form.languages} onChange={set('languages')} /></Field>
          <Field label="Existing concepts to build on" hint="Comma separated, e.g. zero:loops, dsa:complexity"><Input value={form.reuse} onChange={set('reuse')} /></Field>
          <Field label="References to align with" hint="One per line: docs, books, syllabi"><Textarea rows={2} value={form.references} onChange={set('references')} /></Field>
          <Field label="Budget (USD)" hint="Generation stops when this course has spent it"><Input type="number" min="0.5" max="1000" step="0.5" required value={form.budget} onChange={set('budget')} /></Field>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={sending}>{sending ? <Loader2 className="animate-spin" /> : <Sparkles />} Plan the outline</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function JobLog({ job }: { job: Job }) {
  return (
    <div className="grid gap-2 text-sm">
      <p className="text-muted-foreground">
        {job.kind} job · {job.state}{busyJob(job) ? '…' : ''} · {usd(job.cost_usd)}
        {job.error ? <span className="block font-medium text-attention">{job.error}</span> : null}
      </p>
      <ol className="grid gap-2">
        {job.log.map((e, i) => (
          <li key={i} className="rounded-[16px] bg-raised p-3">
            <p className="font-medium capitalize">
              {e.role}{e.round ? `, round ${e.round}` : ''}
              {e.verdict ? <Badge variant={e.verdict === 'pass' ? 'default' : 'outline'} className="ml-2">{e.verdict}</Badge> : null}
            </p>
            {e.event ? <p className="text-muted-foreground">{e.event.replaceAll('_', ' ')}</p> : null}
            {e.concepts ? <p className="text-muted-foreground">Outline with {e.concepts} concepts in {e.modules} module{e.modules === 1 ? '' : 's'}.</p> : null}
            {e.summary ? <p>{e.summary}</p> : null}
            {e.issues?.length ? <ul className="mt-1 list-disc pl-5 text-muted-foreground">{e.issues.map(x => <li key={x}>{x}</li>)}</ul> : null}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Outline({ course }: { course: CourseJson }) {
  const byId = Object.fromEntries(course.concepts.map(c => [c.id, c]));
  const minutes = course.concepts.reduce((sum, c) => sum + c.estimated_minutes, 0);
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">{course.tagline} {course.concepts.length} concepts, about {Math.round(minutes / 60)} hours.</p>
      <p className="text-sm">{course.description}</p>
      <p className="text-sm text-muted-foreground">Levels: {course.levels.map(l => `${l.label}${l.start_concept ? ` → ${l.start_concept}` : ''}`).join(' · ')}</p>
      {course.modules.map(m => (
        <section key={m.id} className="grid gap-2">
          <h4 className="font-semibold">{m.title} <span className="font-normal text-muted-foreground">— {m.summary}</span></h4>
          <ol className="grid gap-2">
            {m.concepts.map(id => {
              const c = byId[id];
              return (
                <li key={id} className="rounded-[16px] border p-3 text-sm">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    {c.title} <span className="font-mono text-xs text-muted-foreground">{c.id}</span>
                    {c.outline ? <Badge variant="outline">{c.outline.depth}</Badge> : null}
                    <span className="text-xs text-muted-foreground">{c.estimated_minutes} min · difficulty {c.difficulty}</span>
                  </p>
                  <p className="text-muted-foreground">{c.summary}</p>
                  {c.prerequisites.length ? <p className="text-xs text-muted-foreground">Needs: {c.prerequisites.join(', ')}</p> : null}
                  {c.outline ? (
                    <ul className="mt-1 list-disc pl-5">
                      {c.outline.objectives.map(o => <li key={o}>{o}</li>)}
                    </ul>
                  ) : null}
                  {c.outline?.misconceptions.length ? <p className="mt-1 text-xs text-muted-foreground">Misconceptions: {c.outline.misconceptions.join('; ')}</p> : null}
                  {c.outline ? <p className="text-xs text-muted-foreground">Assessed by: {c.outline.assessment.join(', ')}</p> : null}
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </div>
  );
}

/** Generated courses: brief → agent-planned outline → owner review → publish. */
export function CourseBuilder() {
  const [items, setItems] = useState<Summary[] | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<Detail | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState<'' | 'save' | 'revise' | 'publish'>('');

  const load = useCallback(() => {
    api.get<{ items: Summary[] }>('/admin/courses').then(r => setItems(r.items)).catch(e => setError(explain(e)));
  }, []);
  const show = useCallback(async (id: string) => {
    try { setOpen(await api.get<Detail>(`/admin/courses/${id}`)); } catch (e) { toast.error(explain(e)); }
  }, []);
  useEffect(load, [load]);

  // While agents work, refresh the list and the open course every few seconds.
  const working = items?.some(i => busyJob(i.job)) || busyJob(open?.jobs[0]);
  useEffect(() => {
    if (!working) return;
    const timer = setInterval(() => { load(); if (open) show(open.id); }, 5000);
    return () => clearInterval(timer);
  }, [working, load, show, open]);

  function close() { setOpen(null); setEditing(null); setProblems([]); setNotes(''); }

  async function act(kind: 'save' | 'revise' | 'publish') {
    if (!open) return;
    setBusy(kind);
    try {
      if (kind === 'save') {
        let course: unknown;
        try { course = JSON.parse(editing ?? ''); } catch { setProblems(['That is not valid JSON.']); return; }
        const result = await api.put<{ saved: boolean; errors: string[] }>(`/admin/courses/${open.id}/outline`, { course });
        setProblems(result.errors);
        if (result.saved) { toast.success('Outline saved.'); setEditing(null); }
      } else if (kind === 'revise') {
        await api.post(`/admin/courses/${open.id}/revise`, { notes });
        toast('Sent back to the architect with your notes.');
        setNotes('');
      } else {
        await api.post(`/admin/courses/${open.id}/publish`);
        toast.success('Published. Learners can enroll; lessons show as being prepared until they are generated.');
      }
      await show(open.id);
      load();
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy('');
    }
  }

  if (error) return <ErrorNote message={error} retry={load} />;
  const review = open?.status === 'review' && !busyJob(open.jobs[0]);
  return (
    <div className="grid gap-6">
      {items?.length ? (
        <Card className="gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3">
            <CardTitle as="h2">Generated courses</CardTitle>
            <CardDescription>Open one to follow the agents, read the outline, edit it, send it back, or publish it.</CardDescription>
          </CardHeader>
          <Table>
            <TableHeader><TableRow><TableHead className="pl-4">Course</TableHead><TableHead>Status</TableHead><TableHead>Agents</TableHead><TableHead className="text-right">Concepts</TableHead><TableHead className="pr-4 text-right">Spent</TableHead></TableRow></TableHeader>
            <TableBody>
              {items.map(c => (
                <TableRow key={c.id}>
                  <TableCell className="pl-4">
                    <button type="button" className="text-left font-semibold underline-offset-4 hover:underline" onClick={() => show(c.id)}>{c.title}</button>
                    <span className="block font-mono text-xs text-muted-foreground">{c.id}</span>
                  </TableCell>
                  <TableCell><Badge variant="outline">{STATUS_LABEL[c.status]}</Badge></TableCell>
                  <TableCell className="text-sm">{c.job ? <>{busyJob(c.job) ? <Loader2 className="mr-1 inline size-3.5 animate-spin" /> : null}{c.job.state}</> : '—'}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.concepts ?? '—'}</TableCell>
                  <TableCell className="pr-4 text-right tabular-nums">{usd(c.spent_usd)} / {usd(c.budget_usd)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
      <BriefForm onCreated={load} />

      <Sheet open={Boolean(open)} onOpenChange={o => { if (!o) close(); }}>
        <SheetContent className="w-full gap-0 sm:max-w-3xl">
          {open ? (
            <>
              <SheetHeader className="border-b">
                <SheetTitle>{open.course?.title ?? open.brief.title}</SheetTitle>
                <SheetDescription className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs">{open.id}</span>
                  <Badge variant="outline">{STATUS_LABEL[open.status]}</Badge>
                  <span>{usd(open.spent_usd)} of {usd(open.brief.budget_usd)} spent</span>
                </SheetDescription>
              </SheetHeader>
              <div className="grid flex-1 content-start gap-6 overflow-y-auto p-4">
                <Section title="Brief">
                  <dl className="grid gap-1 text-sm">
                    <div><dt className="inline font-medium">For: </dt><dd className="inline">{open.brief.audience}</dd></div>
                    <div><dt className="inline font-medium">Outcome: </dt><dd className="inline">{open.brief.outcome}</dd></div>
                    {open.brief.background ? <div><dt className="inline font-medium">Background: </dt><dd className="inline">{open.brief.background}</dd></div> : null}
                  </dl>
                </Section>
                {open.jobs[0] ? <Section title="Latest agent run"><JobLog job={open.jobs[0]} /></Section> : null}
                {open.course ? (
                  <Section title="Outline">
                    {editing !== null ? (
                      <>
                        <Textarea value={editing} onChange={e => setEditing(e.target.value)} rows={24} className="font-mono text-xs" aria-label="Outline JSON" />
                        {problems.length ? <ul className="list-disc pl-5 text-sm text-attention">{problems.map(p => <li key={p}>{p}</li>)}</ul> : null}
                        <div className="flex gap-2">
                          <Button size="sm" disabled={Boolean(busy)} onClick={() => act('save')}>{busy === 'save' ? <Loader2 className="animate-spin" /> : <Save />} Save outline</Button>
                          <Button size="sm" variant="outline" onClick={() => { setEditing(null); setProblems([]); }}>Cancel</Button>
                        </div>
                      </>
                    ) : (
                      <>
                        {review ? <Button size="sm" variant="outline" className="justify-self-start" onClick={() => setEditing(JSON.stringify(open.course, null, 2))}>Edit as JSON</Button> : null}
                        <Outline course={open.course} />
                      </>
                    )}
                  </Section>
                ) : null}
              </div>
              {review ? (
                <SheetFooter className="border-t">
                  <label className="grid gap-1.5 text-sm font-medium">
                    Notes for the architect
                    <Textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} maxLength={4000} placeholder="What to add, split, merge or reorder" />
                  </label>
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button variant="outline" disabled={Boolean(busy) || notes.trim().length < 3} onClick={() => act('revise')}>
                      {busy === 'revise' ? <Loader2 className="animate-spin" /> : <RotateCcw />} Request revision
                    </Button>
                    <Button disabled={Boolean(busy) || editing !== null} onClick={() => act('publish')}>
                      {busy === 'publish' ? <Loader2 className="animate-spin" /> : <CheckCircle2 />} Publish
                    </Button>
                  </div>
                </SheetFooter>
              ) : null}
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
