'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { conceptHref } from '@/lib/routes';
import type { Grade, ProjectMilestone, ProjectView } from '@/lib/types';
import { ErrorNote, Loading, Page } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { GradeCard } from '@/components/graded-work';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import { Textarea } from '@/components/ui/textarea';

function MilestoneForm({ project, milestone, onDone }: { project: string; milestone: ProjectMilestone; onDone: () => void }) {
  const [work, setWork] = useState('');
  const [link, setLink] = useState('');
  const [ticked, setTicked] = useState<boolean[]>(milestone.checklist.map(() => false));
  const [sending, setSending] = useState(false);
  const [grade, setGrade] = useState<Grade | null>(milestone.last?.grade ?? null);
  const id = `work-${project}-${milestone.id}`;

  async function submit() {
    setSending(true);
    try {
      const [course, name] = project.split(':');
      const result = await api.post<{ grade: Grade; passed: boolean }>(
        `/projects/${course}/${name}/milestones/${milestone.id}`,
        { work, link: link.trim(), checklist: ticked },
      );
      setGrade(result.grade);
      toast.success(result.passed ? 'Milestone done.' : 'Graded. See what to improve, then try again.');
      onDone();
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid gap-3">
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-sm font-medium">Your submission covers</legend>
        {milestone.checklist.map((item, i) => (
          <label key={item} className="flex items-start gap-2.5 text-[15px]">
            <Checkbox checked={ticked[i]} onCheckedChange={v => setTicked(t => t.map((x, j) => (j === i ? v === true : x)))} className="mt-1" />
            {item}
          </label>
        ))}
      </fieldset>
      <label htmlFor={id} className="text-sm font-medium">Your work: explanation, results, code pasted in</label>
      <Textarea id={id} rows={8} value={work} onChange={e => setWork(e.target.value)} maxLength={8000} />
      <label className="grid gap-1.5 text-sm font-medium">
        Link (optional, public https)
        <Input type="url" value={link} onChange={e => setLink(e.target.value)} placeholder="https://" />
      </label>
      <Button className="justify-self-start" onClick={submit} disabled={sending || work.trim().length < 40 || !ticked.every(Boolean)}>
        {sending ? <Spinner /> : null} Submit for grading
      </Button>
      {grade ? <GradeCard grade={grade} /> : null}
    </div>
  );
}

/** A small disclosure for reference text that most visits do not need open. */
function Fold({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details className="group rounded-[16px] bg-raised">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 px-4 text-[14px] font-semibold [&::-webkit-details-marker]:hidden">
        {title}
        <ChevronDown className="size-4 flex-none transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="px-4 pb-4 text-[14px]">{children}</div>
    </details>
  );
}

function ProjectCard({ project, onChange }: { project: ProjectView; onChange: () => void }) {
  const done = project.milestones.filter(m => m.done).length;
  const total = project.milestones.length;
  // Only the milestone being worked on opens its form; the rest stay one line each.
  const current = project.preparing ? -1 : project.milestones.findIndex(m => m.available && !m.done);
  return (
    <Card className="grid gap-6 p-5 lg:p-7">
      <header className="grid gap-3">
        <h2 className="type-title text-balance">{project.title}</h2>
        <p className="max-w-2xl text-[15px] text-muted-foreground">{project.summary}</p>
        <ul className="flex flex-wrap gap-1.5" aria-label="Skills it brings together">
          {project.concepts.map(c => (
            <li key={c.id}><Link href={conceptHref(c.id)}><Badge variant="secondary" className="hover:bg-primary/15">{c.title}</Badge></Link></li>
          ))}
        </ul>
        <div className="grid gap-1.5 pt-1">
          <p className="flex justify-between text-[13px] font-semibold tabular-nums"><span>Milestones</span><span>{done} of {total}</span></p>
          <Progress value={total ? (100 * done) / total : 0} aria-label={`${done} of ${total} milestones done`} />
        </div>
      </header>

      {project.preparing ? <p className="rounded-[16px] bg-raised p-4 text-[15px] text-muted-foreground">Some of its lessons are still being written. It opens when they are ready.</p> : null}

      <ol className="grid">
        {project.milestones.map((m, i) => {
          const open = i === current;
          return (
            <li key={m.id} className="relative grid grid-cols-[2rem_1fr] gap-x-3 pb-5 last:pb-0">
              {i < total - 1 ? <span className="absolute top-8 bottom-0 left-[15px] w-0.5 bg-border" aria-hidden="true" /> : null}
              <span
                className={cn(
                  'relative grid size-8 place-items-center rounded-full text-[14px] font-semibold tabular-nums',
                  m.done ? 'bg-primary text-primary-foreground' : open ? 'border-2 border-primary text-primary' : 'border-2 border-border text-muted-foreground',
                )}
                aria-hidden="true"
              >
                {m.done ? <Check className="size-4" strokeWidth={3} /> : i + 1}
              </span>
              <div className="grid min-w-0 gap-3 pt-1">
                <p className={cn('font-semibold', !m.done && !open && 'text-muted-foreground')}>
                  <span className="sr-only">Milestone {i + 1}{m.done ? ', done' : !m.available ? ', locked' : ''}: </span>{m.title}
                </p>
                {open ? (
                  <div className="grid gap-4 rounded-[16px] border p-4">
                    <MilestoneForm project={project.id} milestone={m} onDone={onChange} />
                    {project.self_review.length ? (
                      <Fold title="Before you submit, ask yourself">
                        <ul className="grid list-disc gap-1 pl-5">{project.self_review.map(x => <li key={x}>{x}</li>)}</ul>
                      </Fold>
                    ) : null}
                  </div>
                ) : m.done && m.last?.grade ? (
                  <details className="text-[14px]">
                    <summary className="cursor-pointer text-muted-foreground underline-offset-4 hover:underline">See your grade</summary>
                    <div className="mt-2"><GradeCard grade={m.last.grade} /></div>
                  </details>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="grid gap-2 sm:grid-cols-2">
        {project.constraints.length ? (
          <Fold title="Constraints">
            <ul className="grid list-disc gap-1 pl-5 text-muted-foreground">{project.constraints.map(c => <li key={c}>{c}</li>)}</ul>
          </Fold>
        ) : null}
        <Fold title="How each milestone is graded">
          <ul className="grid gap-2">
            {project.rubric.map(r => (
              <li key={r.criterion}>
                <p className="flex justify-between gap-2 font-semibold"><span>{r.criterion}</span><span className="tabular-nums text-muted-foreground">{r.weight}</span></p>
                <p className="text-muted-foreground">{r.full_marks}</p>
              </li>
            ))}
          </ul>
        </Fold>
      </div>
      {project.ai_generated ? <p className="text-xs text-muted-foreground">{project.attribution}</p> : null}
    </Card>
  );
}

export default function ProjectsPage() {
  const allowed = useGuard('active');
  const [projects, setProjects] = useState<ProjectView[] | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<{ projects: ProjectView[] }>('/projects').then(r => setProjects(r.projects)).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!projects && !error)) return <Loading label="Loading your projects" />;
  if (!projects) return <Page><ErrorNote message={error} retry={load} /></Page>;

  return (
    <Page>
      <header className="mb-8">
        <h1 className="type-display-l">Projects</h1>
        <p className="mt-2 text-[15px] text-muted-foreground">Real work that ties a module together. Each milestone is graded against the rubric; up to three graded tries a day.</p>
      </header>
      {projects.length ? (
        <div className="grid gap-6">{projects.map(p => <ProjectCard key={p.id} project={p} onChange={load} />)}</div>
      ) : (
        <EmptyState title="No projects in this course yet">
          <p className="text-[15px] text-muted-foreground">Projects appear when you finish the modules that have one.</p>
        </EmptyState>
      )}
    </Page>
  );
}
