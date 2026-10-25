'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { KIND_LABEL } from '@/lib/routes';
import type { ActivityKind } from '@/lib/types';
import Markdown from '@/components/markdown';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';

const STYLE_FOR: Record<string, string> = { example: 'example', explain: 'simpler' };
const INTRO: Record<string, string> = {
  example: 'You have been working hard on this. Walk through one complete example before trying again.',
  explain: 'Here is the same idea explained another way. Read it, then try the next problem fresh.',
  checkin: 'Tell Soc where it stops making sense. Talking it through often finds the gap faster than another attempt.',
  stretch: 'You asked for a weekly stretch. Pick one problem a step above your level and give it a real try.',
};

/**
 * A support step the planner added to this concept (worked example, another explanation,
 * a tutor check-in or a stretch problem). It shows on top of the lesson and the learner
 * marks it done.
 */
export function SupportStep({
  step,
  concept,
  language,
  onAsk,
}: {
  step: string;
  concept: string;
  language: string;
  onAsk: () => void;
}) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const style = STYLE_FOR[step];
    if (!style) return;
    setLoading(true);
    api
      .post<{ content: string }>(`/concepts/${concept}/explain`, { style })
      .then(r => setContent(r.content))
      .catch(e => toast.error(explain(e)))
      .finally(() => setLoading(false));
  }, [step, concept]);

  async function finish() {
    setBusy(true);
    try {
      await api.post(`/activities/${step}:${concept}/complete`);
      setDone(true);
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mb-8 rounded-card border-2 border-primary/40 p-5" aria-labelledby="support-step-heading">
      <p className="type-label text-muted-foreground">Added for you</p>
      <h2 id="support-step-heading" className="mt-1 font-display text-xl font-semibold tracking-[-0.03em]">
        {KIND_LABEL[step as ActivityKind] ?? 'Support step'}
      </h2>
      <p className="mt-2 text-[15px] text-muted-foreground">{INTRO[step]}</p>
      {loading ? <Spinner className="mt-4 size-5" /> : null}
      {content ? <div className="mt-4"><Markdown source={content} language={language} /></div> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {step === 'checkin' ? <Button variant="outline" onClick={onAsk}>Talk to Soc</Button> : null}
        {step === 'stretch' ? (
          <Button asChild variant="outline">
            <Link href={`/library?concept=${encodeURIComponent(concept)}`}>Find a harder problem</Link>
          </Button>
        ) : null}
        {done ? (
          <p className="flex items-center text-[15px] font-semibold" role="status">
            Done. <Link href="/today" className="ml-2 underline underline-offset-4">Back to Today</Link>
          </p>
        ) : (
          <Button disabled={busy} onClick={finish}>Mark as done</Button>
        )}
      </div>
    </section>
  );
}

/** G3: the learner tells Socrat how this concept feels; the plan adapts right away. */
export function FeelControls({ concept, onChanged }: { concept: string; onChanged?: () => void }) {
  const [busy, setBusy] = useState('');

  async function send(signal: 'too_easy' | 'too_hard' | 'know_this') {
    setBusy(signal);
    try {
      const result = await api.post<{ reason: string }>('/adaptive/feel', { concept, signal });
      toast.success(result.reason);
      onChanged?.();
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy('');
    }
  }

  return (
    <section aria-labelledby="feel-heading" className="mt-8 max-w-[68ch]">
      <h2 id="feel-heading" className="mb-1 font-display text-lg font-semibold tracking-[-0.02em]">How does this feel?</h2>
      <p className="mb-3 text-[14px] text-muted-foreground">Your plan adjusts to your answer.</p>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" disabled={!!busy} onClick={() => send('too_easy')}>Too easy</Button>
        <Button variant="outline" size="sm" disabled={!!busy} onClick={() => send('too_hard')}>Too hard</Button>
        <Button variant="outline" size="sm" disabled={!!busy} onClick={() => send('know_this')}>I know this already</Button>
      </div>
    </section>
  );
}
