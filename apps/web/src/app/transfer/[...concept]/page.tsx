'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, formatStamp, joinSegments } from '@/lib/routes';
import type { TransferResult, TransferView } from '@/lib/types';
import { ErrorNote, Loading, Page } from '@/components/common';
import { Choice } from '@/components/choice';
import Markdown from '@/components/markdown';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type Classify = Extract<TransferView, { state: 'classify' }>;

function Problem({ problem }: { problem: Classify['problem'] }) {
  return (
    <div className="grid gap-4">
      <Markdown source={problem.statement} className="prose-compact" />
      <p className="text-[15px]"><span className="font-semibold">Input:</span> {problem.input_format}</p>
      <p className="text-[15px]"><span className="font-semibold">Output:</span> {problem.output_format}</p>
      {problem.constraints.length ? <ul className="list-disc pl-5 text-[15px]">{problem.constraints.map(c => <li key={c}>{c}</li>)}</ul> : null}
      {problem.examples.map((e, i) => (
        <pre key={i} className="overflow-x-auto rounded-[16px] bg-raised p-3 text-[14px]">{`Input\n${e.input}\nOutput\n${e.output}`}</pre>
      ))}
    </div>
  );
}

export default function TransferPage() {
  const allowed = useGuard('active');
  const params = useParams<{ concept: string[] }>();
  const concept = joinSegments(params.concept);
  const [view, setView] = useState<TransferView | null>(null);
  const [choice, setChoice] = useState<string | null>(null);
  const [result, setResult] = useState<TransferResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<TransferView>(`/transfer/${encodeURIComponent(concept)}`).then(setView).catch(e => setError(explain(e)));
  }, [concept]);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  const submit = (v: Classify) => {
    if (!choice) return;
    setBusy(true);
    api.post<TransferResult>(`/transfer/${encodeURIComponent(concept)}/classify`, { problem: v.problem.id, choice })
      .then(setResult)
      .catch(e => setError(explain(e)))
      .finally(() => setBusy(false));
  };

  if (!allowed || (!view && !error)) return <Loading label="Loading your check" />;
  if (!view) return <Page narrow><ErrorNote message={error} retry={load} /></Page>;

  const back = <Button asChild variant="outline"><Link href="/plan">Back to {NAME.skills}</Link></Button>;
  const solve = (problem: string) => (
    <Card>
      <div className="grid gap-4 px-(--card-spacing)">
        <h2 className="font-display text-xl font-semibold tracking-[-0.03em]">Now solve it</h2>
        <p className="text-[15px] text-muted-foreground">Write and submit the solution yourself. Asking the tutor about this problem, before or during, means this check does not count; you can take a new one tomorrow.</p>
        <div><Button asChild><Link href={`/problems/${problem}?check=${encodeURIComponent(`/transfer/${concept.split(':').join('/')}`)}`}>Open the problem</Link></Button></div>
      </div>
    </Card>
  );

  return (
    <Page narrow>
      <header className="mb-6">
        <p className="type-label text-muted-foreground">Transfer check</p>
        <h1 className="type-display-m mt-1 break-words">{view.title}</h1>
        <p className="mt-2 text-[15px] text-muted-foreground">Can you use it on a problem you have never seen? Name the technique first, then solve it, with no help.</p>
      </header>
      {error ? <ErrorNote message={error} retry={load} className="mb-4" /> : null}

      {view.state === 'verified' ? (
        <Card><div className="grid gap-3 px-(--card-spacing)"><h2 className="font-display text-xl font-semibold">Transfer verified</h2><p>You solved a new problem on your own with this skill.</p><div>{back}</div></div></Card>
      ) : null}
      {view.state === 'unavailable' ? (
        <Card><div className="grid gap-3 px-(--card-spacing)"><h2 className="font-display text-xl font-semibold">Nothing to check yet</h2><p>A check opens once this skill is mastered and a problem you have not seen is available.</p><div>{back}</div></div></Card>
      ) : null}
      {view.state === 'wait' ? (
        <Card><div className="grid gap-3 px-(--card-spacing)"><h2 className="font-display text-xl font-semibold">A fresh problem opens {formatStamp(view.retry_at)}</h2><p>Use the time to review the skill. You will get a different problem.</p><div>{back}</div></div></Card>
      ) : null}
      {view.state === 'solve' ? solve(view.problem) : null}

      {view.state === 'classify' && result ? (
        result.correct ? solve(result.problem!) : (
          <Card>
            <div className="grid gap-3 px-(--card-spacing)">
              <h2 className="font-display text-xl font-semibold">Not this time</h2>
              <p>That problem needed <span className="font-semibold">{result.answer}</span>. A new problem opens {formatStamp(result.retry_at!)}.</p>
              <div>{back}</div>
            </div>
          </Card>
        )
      ) : null}

      {view.state === 'classify' && !result ? (
        <div className="grid gap-6">
          <Card><div className="px-(--card-spacing)"><h2 className="mb-3 font-display text-xl font-semibold tracking-[-0.03em]">The problem</h2><Problem problem={view.problem} /></div></Card>
          <section aria-labelledby="which" className="grid gap-3">
            <h2 id="which" className="font-display text-xl font-semibold tracking-[-0.03em]">Which skill does this need?</h2>
            <div className="grid gap-3" role="radiogroup" aria-labelledby="which">
              {view.choices.map((c, i) => (
                <Choice key={c.id} role="radio" aria-checked={choice === c.id} selected={choice === c.id} marker={String.fromCharCode(65 + i)} onClick={() => setChoice(c.id)}>
                  <span className="choice-title">{c.title}</span>
                </Choice>
              ))}
            </div>
            <p className="text-[14px] text-muted-foreground">One answer. A wrong answer ends this attempt.</p>
            <div><Button disabled={!choice || busy} onClick={() => submit(view)}>Lock in my answer</Button></div>
          </section>
        </div>
      ) : null}
    </Page>
  );
}
