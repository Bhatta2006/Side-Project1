'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { Check, Lightbulb, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { conceptHref } from '@/lib/routes';
import type { Today } from '@/lib/types';
import { Loading } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Scene, type Run } from './scene';
import type { StudioProps } from './registry';

interface Quantity { value: number; unit: string }
interface Experiment {
  id: string; prompt: string; title: string; model: string; difficulty: number; hints: string[]; done: boolean;
  params: Record<string, Quantity>;
  predict: { name: string; unit: string };
  vary: string;
  knobs: Record<string, { unit: string; low: number; high: number; value: number }>;
}
interface Listing { concept: string; title: string; experiments: Experiment[] }
interface Observed extends Run { title: string; params: Record<string, Quantity> }
interface Outcome { verdict: 'correct' | 'incorrect' | 'unreadable' | 'unavailable'; reason?: string; evidence: boolean; observed?: Observed; result?: Quantity & { name: string }; explanation?: string }

const words = (name: string) => name.replace(/_/g, ' ');
const show = (q: Quantity) => `${Number(q.value.toPrecision(4))} ${q.unit}`;

function Readout({ observed, before, highlight }: { observed: Observed; before?: Observed; highlight?: string }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
      {Object.entries(observed.outputs).map(([name, q]) => (
        <div key={name} className={name === highlight ? 'font-medium' : 'text-muted-foreground'}>
          <dt className="text-xs uppercase tracking-wide">{words(name)}</dt>
          <dd>{show(q)}{before && before.outputs[name] && before.outputs[name].value !== q.value ? <span className="text-xs text-muted-foreground"> (was {Number(before.outputs[name].value.toPrecision(4))})</span> : null}</dd>
        </div>
      ))}
    </dl>
  );
}

function Run({ concept, experiment }: { concept: string; experiment: Experiment }) {
  const [given, setGiven] = useState('');
  const [shown, setShown] = useState(0);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);
  const [knobs, setKnobs] = useState<Record<string, number>>(() => Object.fromEntries(Object.entries(experiment.knobs).map(([k, v]) => [k, v.value])));
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [rerun, setRerun] = useState<Observed | null>(null);

  async function commit() {
    setBusy(true);
    try {
      setOutcome(await api.post<Outcome>('/lab/predict', { concept, experiment: experiment.id, given, hints_used: shown }));
    } catch (e) { toast.error(explain(e)); }
    finally { setBusy(false); }
  }

  function tune(name: string, next: number) {
    const values = { ...knobs, [name]: next };
    setKnobs(values);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const out = await api.post<{ ok: boolean; observed?: Observed }>('/lab/vary', { concept, experiment: experiment.id, values });
        if (out.ok && out.observed) setRerun(out.observed);
      } catch { /* exploring is optional; keep the last picture */ }
    }, 150);
  }
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const revealed = outcome?.observed && outcome.verdict !== 'unreadable' && outcome.verdict !== 'unavailable';
  const observed = rerun ?? outcome?.observed;
  return (
    <section className="grid gap-3 rounded-card border p-5" aria-label={experiment.prompt}>
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium">{experiment.prompt}</p>
        <Badge variant="secondary">{'●'.repeat(experiment.difficulty)}</Badge>
      </div>
      <ul className="flex flex-wrap gap-2 text-xs text-muted-foreground" aria-label="Setup">
        {Object.entries(experiment.params).map(([name, q]) => <li key={name} className="rounded-full bg-muted px-2 py-0.5">{words(name)} {show(q)}</li>)}
      </ul>
      {!revealed ? (
        <>
          <Scene model={experiment.model} params={Object.fromEntries(Object.entries(experiment.params).map(([k, q]) => [k, q.value]))} run={null} label={`Setup: ${experiment.title}`} />
          <div className="flex items-center gap-2">
            <Input value={given} onChange={e => setGiven(e.target.value)} placeholder={`Your prediction for ${words(experiment.predict.name)}`}
              aria-label={`Predict ${words(experiment.predict.name)}`} inputMode="decimal"
              onKeyDown={e => { if (e.key === 'Enter' && given.trim()) void commit(); }} />
            <span className="text-sm text-muted-foreground">{experiment.predict.unit}</span>
          </div>
          {shown > 0 ? <ul className="grid gap-1 text-sm text-muted-foreground">{experiment.hints.slice(0, shown).map(h => <li key={h}>Hint: {h}</li>)}</ul> : null}
          {outcome?.verdict === 'unreadable' ? <p role="status" className="text-sm text-muted-foreground">{outcome.reason || 'Enter a number.'}</p> : null}
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy || !given.trim()} onClick={() => void commit()}>
              {busy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Check data-icon="inline-start" />} Lock in and run
            </Button>
            {shown < experiment.hints.length ? <Button variant="outline" onClick={() => setShown(n => n + 1)}><Lightbulb data-icon="inline-start" /> Hint</Button> : null}
          </div>
        </>
      ) : (
        <div className="grid gap-3">
          <p role="status" className={outcome.verdict === 'correct' ? 'text-sm font-medium text-success' : 'text-sm'}>
            {outcome.verdict === 'correct' ? 'Your prediction held.' : 'Not quite.'} You predicted {given || 'a value'} {experiment.predict.unit}; the experiment gave {outcome.result ? show(outcome.result) : ''}.
          </p>
          {observed ? <Scene model={experiment.model} params={Object.fromEntries(Object.entries(observed.params).map(([k, q]) => [k, q.value]))} run={observed} ghost={rerun ? outcome.observed : null} label={`${experiment.title}, simulated`} /> : null}
          {observed ? <Readout observed={observed} before={rerun ? outcome.observed : undefined} highlight={experiment.predict.name} /> : null}
          <div className="rounded-md bg-muted p-3 text-sm"><p className="mb-1 font-medium">Why</p><p>{outcome.explanation}</p></div>
          <fieldset className="grid gap-2">
            <legend className="text-sm font-medium">Now play with it. Change anything and watch what moves.</legend>
            {Object.entries(experiment.knobs).map(([name, k]) => (
              <label key={name} className="grid grid-cols-[7rem_1fr_6rem] items-center gap-2 text-sm">
                <span className={name === experiment.vary ? 'font-medium' : 'text-muted-foreground'}>{words(name)}</span>
                <input type="range" min={k.low} max={k.high} step={(k.high - k.low) / 200} value={knobs[name]} aria-label={`${words(name)} (${k.unit})`} onChange={e => tune(name, Number(e.target.value))} />
                <span className="tabular-nums">{Number(knobs[name].toPrecision(3))} {k.unit}</span>
              </label>
            ))}
          </fieldset>
        </div>
      )}
    </section>
  );
}

/** The physics studio: predict a result, run a vetted simulation, compare, then explore why. */
export function Lab({ shape }: StudioProps) {
  void shape;
  const [listing, setListing] = useState<Listing | null | undefined>(undefined);
  useEffect(() => {
    api.get<Today>('/today')
      .then(today => {
        const concept = today.next?.concept;
        return concept ? api.get<Listing>(`/lab/${concept.replace(':', '/')}`) : null;
      })
      .then(setListing)
      .catch(() => setListing(null));
  }, []);

  if (listing === undefined) return <Loading variant="article" label="Setting up your experiments" />;
  if (!listing || !listing.experiments.length) {
    return <EmptyState title="No experiments for this topic yet">Read the lesson first; experiments appear here once the topic has them.</EmptyState>;
  }
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        {listing.title} · <Link className="underline" href={conceptHref(listing.concept)}>read the lesson</Link>
      </p>
      {listing.experiments.map(e => <Run key={e.id} concept={listing.concept} experiment={e} />)}
    </div>
  );
}
