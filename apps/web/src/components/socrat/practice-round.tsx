'use client';

import { useMemo, useState } from 'react';
import { Choice } from '@/components/choice';
import { Button } from '@/components/ui/button';
import { FeedbackSheet, KeyHint, StampButton, praise, useAnswerKeys, type PracticeItem } from '@/components/socrat/answer-flow';

/** A question can come back this many times in one round before its answer is simply shown. */
const MAX_TRIES = 3;

function shuffled<T>(items: readonly T[]): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

interface Turn { item: PracticeItem; order: number[]; tries: number }

/**
 * The questions missed in a check, asked again before the results, in a new option order.
 * A miss goes to the back of the line, like Duolingo's "previous mistake", but the round is
 * practice: it runs only in the browser, sends nothing, and the learner can leave it.
 */
export function PracticeRound({ items, onDone }: { items: PracticeItem[]; onDone(): void }) {
  const [queue, setQueue] = useState<Turn[]>(() => items.map(item => ({ item, order: shuffled(item.options.map((_, i) => i)), tries: 0 })));
  const [choice, setChoice] = useState<number | null>(null);
  const [result, setResult] = useState<'right' | 'wrong' | null>(null);
  const [cleared, setCleared] = useState(0);
  const total = items.length;
  const turn = queue[0];
  const picked = useMemo(() => (turn && choice !== null ? turn.order[choice] : null), [turn, choice]);

  function check() {
    if (!turn || picked === null || result) return;
    setResult(picked === turn.item.answer ? 'right' : 'wrong');
  }

  function next() {
    if (!turn || !result) return;
    const [head, ...rest] = queue;
    const tries = head.tries + 1;
    if (result === 'right' || tries >= MAX_TRIES) {
      setCleared(c => c + 1);
      setQueue(rest);
      if (!rest.length) onDone();
    } else {
      setQueue([...rest, { ...head, tries, order: shuffled(head.item.options.map((_, i) => i)) }]);
    }
    setChoice(null);
    setResult(null);
  }

  useAnswerKeys({
    enabled: Boolean(turn),
    count: turn?.order.length ?? 0,
    onPick: i => { if (!result) setChoice(i); },
    onSubmit: () => (result ? next() : check()),
  });

  if (!turn) return null;
  const { item, order } = turn;
  const lastTry = result === 'wrong' && turn.tries + 1 >= MAX_TRIES;
  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-semibold">Try the ones you missed <span className="font-medium text-muted-foreground">· practice, not counted · {cleared} of {total} done</span></p>
        <Button variant="ghost" size="sm" onClick={onDone}>Skip to results</Button>
      </div>
      <div key={`${item.key}:${turn.tries}`} className="grid gap-5 animate-in fade-in duration-200">
        <p className="w-fit rounded-full border border-dashed border-pen px-3 py-0.5 text-[13px] font-semibold text-pen">Previous mistake</p>
        <h1 className="type-title text-balance">{item.prompt}</h1>
        {item.code ? <pre className="code-block">{item.code}</pre> : null}
        <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
          {order.map((original, i) => {
            const tone = result && original === item.answer ? 'correct' : result && i === choice ? 'wrong' : 'idle';
            return (
              <Choice key={original} role="radio" aria-checked={choice === i} selected={choice === i && !result} tone={tone} marker={String.fromCharCode(65 + i)} disabled={Boolean(result)} onClick={() => setChoice(i)}>
                <span className="choice-title whitespace-pre-wrap">{item.options[original]}</span>
              </Choice>
            );
          })}
        </div>
        {!result ? (
          <div className="grid gap-3">
            <div><StampButton disabled={choice === null} onClick={check}>Check</StampButton></div>
            <KeyHint count={order.length} />
          </div>
        ) : null}
      </div>
      {result ? (
        <FeedbackSheet
          tone={result === 'right' ? 'correct' : 'wrong'}
          title={result === 'right' ? praise(0, cleared) : lastTry ? 'Here it is' : 'Not yet'}
          action={queue.length === 1 && (result === 'right' || lastTry) ? 'See results' : 'Continue'}
          onContinue={next}
        >
          {result === 'wrong' ? <p>Answer: <span className="font-semibold">{item.options[item.answer]}</span>{lastTry ? null : '. It comes back once more at the end.'}</p> : null}
          {item.explanation ? <p className="text-muted-foreground">{item.explanation}</p> : null}
        </FeedbackSheet>
      ) : null}
    </div>
  );
}
