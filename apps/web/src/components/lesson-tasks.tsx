'use client';

import { useState } from 'react';
import { api, explain } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export type LessonTask = {
  id: string;
  kind: 'reflection' | 'case-study' | 'oral' | 'performance' | 'portfolio' | 'practical';
  prompt: string;
  rubric: { criterion: string; points: number; look_for: string }[];
  safety: string | null;
  evaluator: 'self' | 'person';
  submission: { status: 'self_checked' | 'awaiting_person' | 'graded'; score: number | null; reviewer: string | null; feedback: string | null; met: string[] } | null;
};

const KIND: Record<LessonTask['kind'], string> = {
  reflection: 'Reflection',
  'case-study': 'Case study',
  oral: 'Explain it aloud',
  performance: 'Performance',
  portfolio: 'Portfolio piece',
  practical: 'Practical',
};

function Status({ s }: { s: NonNullable<LessonTask['submission']> }) {
  if (s.status === 'graded') {
    return <p role="status" className="text-sm">Graded by {s.reviewer}: {Math.round((s.score ?? 0) * 100)}%.{s.feedback ? ` ${s.feedback}` : ''}</p>;
  }
  if (s.status === 'awaiting_person') return <p role="status" className="text-sm text-muted-foreground">Sent. A person will judge it against the rubric; until then it does not count toward this skill.</p>;
  return <p role="status" className="text-sm text-muted-foreground">Saved. You checked {s.met.length} of the criteria yourself; self-checks do not count as evidence.</p>;
}

function TaskCard({ concept, task }: { concept: string; task: LessonTask }) {
  const [text, setText] = useState('');
  const [link, setLink] = useState('');
  const [met, setMet] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [submission, setSubmission] = useState(task.submission);
  const self = task.evaluator === 'self';

  async function send() {
    setBusy(true);
    setError('');
    try {
      const body = { text, ...(link ? { link } : {}), ...(self ? { met } : {}) };
      setSubmission(await api.post<NonNullable<LessonTask['submission']>>(`/tasks/${concept}/${task.id}`, body));
      setText('');
      setLink('');
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby={`task-${task.id}`} className="grid gap-3 rounded-[20px] border bg-card p-5">
      <h3 id={`task-${task.id}`} className="font-semibold">{KIND[task.kind]}</h3>
      <p className="text-[15px]">{task.prompt}</p>
      {task.safety ? <p className="text-sm font-medium">Safety: {task.safety}</p> : null}
      <div className="text-sm text-muted-foreground">
        <p>{self ? 'Check your own work against:' : 'A person will judge it on:'}</p>
        <ul className="mt-1 grid gap-1">
          {task.rubric.map(c => (
            <li key={c.criterion}>
              {self ? (
                <label className="flex items-start gap-2">
                  <input type="checkbox" className="mt-1" checked={met.includes(c.criterion)} onChange={e => setMet(m => (e.target.checked ? [...m, c.criterion] : m.filter(x => x !== c.criterion)))} />
                  <span><span className="font-medium text-foreground">{c.criterion}</span> ({c.points}): {c.look_for}</span>
                </label>
              ) : (
                <span><span className="font-medium text-foreground">{c.criterion}</span> ({c.points}): {c.look_for}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
      {submission ? <Status s={submission} /> : null}
      <label className="grid gap-1 text-sm font-medium" htmlFor={`task-text-${task.id}`}>
        {self ? 'Your answer' : 'Describe what you did'}
        <Textarea id={`task-text-${task.id}`} value={text} onChange={e => setText(e.target.value)} rows={4} maxLength={4000} />
      </label>
      {!self ? (
        <label className="grid gap-1 text-sm font-medium" htmlFor={`task-link-${task.id}`}>
          Link to your recording or work (optional, https)
          <Input id={`task-link-${task.id}`} type="url" value={link} onChange={e => setLink(e.target.value)} placeholder="https://" />
        </label>
      ) : null}
      {error ? <p role="alert" className="text-sm text-attention">{error}</p> : null}
      <Button className="w-fit" onClick={send} disabled={busy || text.trim().length < 10}>{self ? 'Save' : 'Send for review'}</Button>
    </section>
  );
}

/** Work a quiz cannot judge: self-checked reflections, and real work a person grades. */
export default function LessonTasks({ concept, tasks, heading = true }: { concept: string; tasks: LessonTask[]; heading?: boolean }) {
  return (
    <div className="mt-8 grid gap-4">
      {heading ? <h2 className="font-display text-xl font-semibold">Practise it for real</h2> : null}
      {tasks.map(t => <TaskCard key={t.id} concept={concept} task={t} />)}
    </div>
  );
}
