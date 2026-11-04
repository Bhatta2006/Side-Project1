'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, Check, Flame, Lightbulb, Loader2, Lock, RotateCcw, Sparkles, Star, X } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import type { DrillOverview, DrillQuestion, DrillSet } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';

/**
 * Practice for any course that is not a programming course: pick a topic you have unlocked and
 * Socrat writes a short set of questions for that course and topic alone. One question at a
 * time, answered once, graded on the server; stars and a streak make it feel like a game.
 */
export function Drills({ initialConcept }: { initialConcept?: string }) {
  const [overview, setOverview] = useState<DrillOverview | null>(null);
  const [error, setError] = useState('');
  const [concept, setConcept] = useState(initialConcept ?? '');
  const [set, setSet] = useState<DrillSet | null>(null);
  const [making, setMaking] = useState(false);

  const load = useCallback(() => {
    api.get<DrillOverview>('/drills').then(o => {
      setOverview(o);
      setConcept(c => c || o.concepts.filter(x => !x.locked).at(-1)?.concept || '');
    }).catch(e => setError(explain(e)));
  }, []);
  useEffect(load, [load]);

  async function make() {
    if (!concept) return;
    setMaking(true);
    try { setSet(await api.post<DrillSet>('/drills', { concept })); }
    catch (e) { toast.error(explain(e)); }
    finally { setMaking(false); }
  }

  async function open(id: string) {
    try { setSet(await api.get<DrillSet>(`/drills/${id}`)); } catch (e) { toast.error(explain(e)); }
  }

  if (error) return <ErrorNote message={error} retry={() => { setError(''); load(); }} />;
  if (!overview) return <Loading variant="article" label="Opening practice" />;

  if (set) return <Play set={set} onChange={setSet} onDone={() => { setSet(null); load(); }} onAgain={() => { setSet(null); void make(); }} />;

  const open_ = overview.concepts.filter(c => !c.locked);
  if (!open_.length) {
    return (
      <EmptyState title="Practice opens with your first topic">
        Start your first lesson from Today. Every topic you open can be practised here.
      </EmptyState>
    );
  }

  return (
    <div className="grid gap-8">
      <section aria-labelledby="new-set" className="paper grid gap-4 rounded-card p-5 sm:p-6">
        <div className="grid gap-1">
          <h2 id="new-set" className="font-display text-xl font-semibold tracking-[-0.02em]">New practice set</h2>
          <p className="text-[15px] text-muted-foreground">Pick a topic. Socrat writes {5} fresh questions for {overview.course}, easiest first.</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid min-w-0 flex-1 gap-1.5 text-sm font-medium sm:max-w-md">
            Topic
            <NativeSelect value={concept} onChange={e => setConcept(e.target.value)} aria-label="Topic to practise">
              {overview.concepts.map(c => (
                <NativeSelectOption key={c.concept} value={c.concept} disabled={c.locked}>{c.title}{c.locked ? ' (locked)' : ''}</NativeSelectOption>
              ))}
            </NativeSelect>
          </label>
          <Button size="lg" disabled={making || !concept} onClick={() => void make()}>
            {making ? <Loader2 className="animate-spin" data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
            {making ? 'Writing your questions' : 'Start practising'}
          </Button>
        </div>
      </section>

      {overview.sets.length ? (
        <section aria-labelledby="past-sets" className="grid gap-3">
          <h2 id="past-sets" className="text-sm font-semibold">Your recent sets</h2>
          <ul className="grid gap-2 sm:grid-cols-2">
            {overview.sets.map(s => (
              <li key={s.id}>
                <button type="button" onClick={() => void open(s.id)} className="flex w-full items-center justify-between gap-3 rounded-[16px] border bg-card px-4 py-3 text-left transition-colors hover:bg-raised">
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{s.title}</span>
                    <span className="block text-[13px] text-muted-foreground">
                      {s.answered < s.questions ? `${s.answered} of ${s.questions} answered` : `${s.correct} of ${s.questions} right`}
                    </span>
                  </span>
                  <Stars got={s.correct} of={s.questions} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="flex items-center gap-2 text-[13px] text-muted-foreground"><Lock className="size-3.5" aria-hidden="true" /> Locked topics open as you pass the checks before them.</p>
    </div>
  );
}

function Stars({ got, of }: { got: number; of: number }) {
  const shown = of ? Math.round((3 * got) / of) : 0;
  return (
    <span className="flex flex-none gap-0.5" aria-label={`${shown} of 3 stars`}>
      {[0, 1, 2].map(i => <Star key={i} className={cn('size-4', i < shown ? 'fill-[var(--highlight)] text-[var(--soc-outline)]' : 'text-border-strong')} aria-hidden="true" />)}
    </span>
  );
}

function Play({ set, onChange, onDone, onAgain }: { set: DrillSet; onChange: (s: DrillSet) => void; onDone: () => void; onAgain: () => void }) {
  const firstOpen = set.items.findIndex(q => q.correct === undefined);
  const [index, setIndex] = useState(firstOpen < 0 ? set.items.length : firstOpen);
  const finished = index >= set.items.length;
  const streak = useMemo(() => {
    let run = 0;
    for (const q of set.items) { if (q.correct === undefined) break; run = q.correct ? run + 1 : 0; }
    return run;
  }, [set.items]);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">Practising</p>
          <h2 className="font-display text-2xl font-semibold tracking-[-0.02em]">{set.title}</h2>
        </div>
        <div className="flex items-center gap-3">
          {streak >= 2 ? <span className="inline-flex items-center gap-1 rounded-full border border-border-strong px-3 py-1 text-sm font-bold"><Flame className="size-4" aria-hidden="true" /> {streak} in a row</span> : null}
          <Stars got={set.correct} of={set.questions} />
        </div>
      </div>

      <ol className="flex gap-1.5" aria-label="Questions">
        {set.items.map(q => (
          <li key={q.index} className="flex-1">
            <button
              type="button"
              onClick={() => setIndex(q.index)}
              aria-label={`Question ${q.index + 1}${q.correct === undefined ? '' : q.correct ? ', right' : ', not right'}`}
              aria-current={index === q.index ? 'step' : undefined}
              className={cn(
                'h-2.5 w-full rounded-full transition-colors',
                q.correct === true ? 'bg-primary' : q.correct === false ? 'bg-attention' : 'bg-border',
                index === q.index && 'ring-2 ring-[var(--soc-outline)] ring-offset-2 ring-offset-background',
              )}
            />
          </li>
        ))}
      </ol>

      {finished ? (
        <section className="paper grid justify-items-center gap-3 rounded-card p-8 text-center" aria-live="polite">
          <Stars got={set.correct} of={set.questions} />
          <p className="font-display text-2xl font-semibold">{set.correct} of {set.questions} right</p>
          <p className="max-w-md text-[15px] text-muted-foreground">
            {set.correct === set.questions ? 'A perfect set. Try another topic, or a fresh set on this one.' : 'Look back at the ones you missed, then try a fresh set.'}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button onClick={onAgain}><RotateCcw data-icon="inline-start" /> New set on this topic</Button>
            <Button variant="outline" onClick={onDone}>Pick another topic</Button>
          </div>
        </section>
      ) : (
        <QuestionCard
          key={`${set.id}-${index}`}
          setId={set.id}
          question={set.items[index]}
          number={index + 1}
          total={set.items.length}
          onAnswered={onChange}
          onNext={() => setIndex(i => {
            const next = set.items.findIndex((q, j) => j > i && q.correct === undefined);
            return next < 0 ? set.items.length : next;
          })}
        />
      )}

      {set.source === 'checks' ? <p className="text-[13px] text-muted-foreground">These come from this topic&apos;s own concept checks while new questions can&apos;t be written.</p> : null}
      {!finished ? <div><Button variant="ghost" size="sm" className="-ml-3" onClick={onDone}>Back to topics</Button></div> : null}
    </div>
  );
}

function QuestionCard({ setId, question, number, total, onAnswered, onNext }: {
  setId: string; question: DrillQuestion; number: number; total: number; onAnswered: (s: DrillSet) => void; onNext: () => void;
}) {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState(false);
  const answered = question.correct !== undefined;

  async function send(given: string) {
    if (!given.trim() || busy || answered) return;
    setBusy(true);
    try {
      const r = await api.post<{ correct: boolean; set: DrillSet }>(`/drills/${setId}/answers`, { question: question.index, answer: given });
      onAnswered(r.set);
    } catch (e) { toast.error(explain(e)); }
    finally { setBusy(false); }
  }

  return (
    <section className="paper grid gap-5 rounded-card p-5 sm:p-7" aria-labelledby={`q-${question.index}`}>
      <p className="text-sm font-semibold text-muted-foreground tabular-nums">Question {number} of {total}</p>
      <h3 id={`q-${question.index}`} className="text-xl font-semibold whitespace-pre-wrap text-pretty sm:text-2xl">{question.prompt}</h3>

      {question.kind === 'choice' ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {question.options.map(option => {
            const picked = question.given === option;
            const right = answered && option === question.expected;
            return (
              <button
                key={option}
                type="button"
                disabled={busy || answered}
                onClick={() => void send(option)}
                className={cn(
                  'flex min-h-14 items-center justify-between gap-3 rounded-[16px] border-2 bg-card px-4 py-3 text-left text-[17px] font-medium transition-colors enabled:hover:border-[var(--soc-outline)]',
                  right && 'border-primary bg-[color-mix(in_srgb,var(--primary)_10%,var(--card))]',
                  picked && !right && 'border-attention',
                )}
              >
                {option}
                {right ? <Check className="size-5 flex-none text-primary" aria-label="Right answer" /> : picked ? <X className="size-5 flex-none" aria-label="Your answer" /> : null}
              </button>
            );
          })}
        </div>
      ) : (
        <form className="flex flex-wrap gap-2" onSubmit={e => { e.preventDefault(); void send(value); }}>
          <Input
            value={answered ? question.given ?? '' : value}
            onChange={e => setValue(e.target.value)}
            disabled={busy || answered}
            inputMode={question.kind === 'number' ? 'decimal' : 'text'}
            autoComplete="off"
            placeholder={question.kind === 'number' ? 'Your number' : 'Your answer'}
            aria-label="Your answer"
            className="h-12 max-w-xs text-lg"
          />
          {!answered ? <Button type="submit" size="lg" disabled={busy || !value.trim()}>{busy ? <Loader2 className="animate-spin" data-icon="inline-start" /> : null} Check</Button> : null}
        </form>
      )}

      {!answered && question.hint ? (
        hint
          ? <p className="flex gap-2 rounded-[16px] bg-raised px-4 py-3 text-[15px]"><Lightbulb className="mt-0.5 size-4 flex-none" aria-hidden="true" /> {question.hint}</p>
          : <div><Button variant="ghost" size="sm" className="-ml-3" onClick={() => setHint(true)}><Lightbulb data-icon="inline-start" /> Show a hint</Button></div>
      ) : null}

      {answered ? (
        <div role="status" className={cn('grid gap-2 rounded-[16px] border px-4 py-3', question.correct ? 'border-primary' : 'border-attention')}>
          <p className="font-semibold">{question.correct ? 'Right!' : `Not quite. The answer is ${question.expected}.`}</p>
          {question.explanation ? <p className="text-[15px] text-muted-foreground">{question.explanation}</p> : null}
          <div className="mt-1"><Button onClick={onNext}>{number < total ? 'Next question' : 'See my score'} <ArrowRight data-icon="inline-end" /></Button></div>
        </div>
      ) : null}
    </section>
  );
}
