'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
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
import { Spinner } from '@/components/ui/spinner';
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

function ProjectCard({ project, onChange }: { project: ProjectView; onChange: () => void }) {
  return (
    <Card className="grid gap-5 p-6">
      <header className="grid gap-2">
        <h2 className="type-title">{project.title}</h2>
        <p className="text-[15px]">{project.summary}</p>
        <p className="text-sm text-muted-foreground">
          Brings together: {project.concepts.map((c, i) => <span key={c.id}>{i ? ', ' : ''}<Link href={conceptHref(c.id)} className="underline underline-offset-4">{c.title}</Link></span>)}
        </p>
        {project.constraints.length ? <p className="text-sm text-muted-foreground">Constraints: {project.constraints.join('; ')}</p> : null}
        {project.ai_generated ? <p className="text-xs text-muted-foreground">{project.attribution}</p> : null}
      </header>
      <section className="grid gap-1.5 text-sm">
        <h3 className="font-semibold">How every milestone is graded</h3>
        <ul className="grid gap-1">
          {project.rubric.map(r => <li key={r.criterion}><span className="font-medium">{r.criterion} ({r.weight})</span>: <span className="text-muted-foreground">{r.full_marks}</span></li>)}
        </ul>
      </section>
      {project.preparing ? <p className="text-[15px] text-muted-foreground">Some of its lessons are still being written. It opens when they are ready.</p> : null}
      <ol className="grid gap-4">
        {project.milestones.map((m, i) => (
          <li key={m.id} className="grid gap-3 rounded-[16px] border p-4">
            <p className="flex flex-wrap items-center gap-2 font-semibold">
              {i + 1}. {m.title}
              {m.done ? <Badge><CheckCircle2 /> Done</Badge> : !m.available ? <Badge variant="outline">After milestone {i}</Badge> : null}
            </p>
            {m.available && !project.preparing ? (
              <MilestoneForm project={project.id} milestone={m} onDone={onChange} />
            ) : (
              <ul className="list-disc pl-5 text-[15px] text-muted-foreground">{m.checklist.map(x => <li key={x}>{x}</li>)}</ul>
            )}
          </li>
        ))}
      </ol>
      {project.self_review.length ? (
        <details className="text-[15px]">
          <summary className="cursor-pointer font-medium">Before you submit, ask yourself</summary>
          <ul className="mt-2 list-disc pl-5">{project.self_review.map(x => <li key={x}>{x}</li>)}</ul>
        </details>
      ) : null}
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
