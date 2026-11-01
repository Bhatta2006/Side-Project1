'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import type { Grade, WrittenPrompt } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Spinner } from '@/components/ui/spinner';

const count = (text: string) => (text.trim() ? text.trim().split(/\s+/).length : 0);

/** How a rubric grade reads to the learner: points per criterion, the grader's notes, feedback. */
export function GradeCard({ grade }: { grade: Grade }) {
  return (
    <div className="grid gap-2 rounded-[16px] bg-raised p-4 text-[15px]" aria-live="polite">
      <p className="font-semibold">Graded {Math.round(grade.score * 100)}% against the rubric</p>
      <ul className="grid gap-1.5">
        {grade.criteria.map(c => (
          <li key={c.criterion}>
            <span className="font-medium">{c.criterion}: {c.points}/{c.max}.</span>{' '}
            <span className="text-muted-foreground">{c.note}</span>
          </li>
        ))}
      </ul>
      {grade.feedback ? <p>{grade.feedback}</p> : null}
      {grade.copied ? <p className="text-attention">This answer repeats the model answer closely, so it counts for less. Explain it your own way.</p> : null}
      <p className="text-xs text-muted-foreground">Graded by an AI model. It counts as lighter evidence than checks and problems, and never masters a skill on its own.</p>
    </div>
  );
}

function PromptCard({ concept, prompt, onGraded }: { concept: string; prompt: WrittenPrompt; onGraded: () => void }) {
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ grade: Grade; model_answer: string } | null>(
    prompt.last ? { grade: prompt.last.grade, model_answer: prompt.last.model_answer } : null,
  );
  const words = count(text);
  const id = `prompt-${prompt.id}`;

  async function submit() {
    setSending(true);
    try {
      const graded = await api.post<{ grade: Grade; model_answer: string }>(`/concepts/${concept}/answers`, { prompt_id: prompt.id, answer: text });
      setResult(graded);
      setText('');
      onGraded();
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid gap-3">
      <label htmlFor={id} className="text-[17px] font-semibold">{prompt.prompt}</label>
      <p className="text-sm text-muted-foreground">Graded on: {prompt.rubric.map(r => `${r.criterion} (${r.points})`).join(' · ')}</p>
      <Textarea id={id} rows={5} value={text} onChange={e => setText(e.target.value)} maxLength={8000} placeholder="In your own words…" />
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={submit} disabled={sending || words < 10 || words > prompt.max_words}>
          {sending ? <Spinner /> : null} {result ? 'Answer again' : 'Get it graded'}
        </Button>
        <span className={words > prompt.max_words ? 'text-sm text-attention' : 'text-sm text-muted-foreground'}>
          {words}/{prompt.max_words} words{words && words < 10 ? ' (at least 10)' : ''}
        </span>
      </div>
      {result ? (
        <>
          <GradeCard grade={result.grade} />
          <details className="rounded-[16px] border p-4 text-[15px]">
            <summary className="cursor-pointer font-medium">A model answer</summary>
            <p className="mt-2 whitespace-pre-line">{result.model_answer}</p>
          </details>
        </>
      ) : null}
    </div>
  );
}

/** A concept's free-text prompts: answer in your own words, graded against a rubric. */
export function WrittenAnswers({ concept, prompts, onGraded }: { concept: string; prompts: WrittenPrompt[]; onGraded: () => void }) {
  return (
    <div className="grid gap-8">
      <p className="text-[15px] text-muted-foreground">Explaining an idea shows you understand it. Up to three graded tries per question each day.</p>
      {prompts.map(p => <PromptCard key={p.id} concept={concept} prompt={p} onGraded={onGraded} />)}
    </div>
  );
}
