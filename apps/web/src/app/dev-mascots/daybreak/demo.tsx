'use client';
import { useState } from 'react';
import { FeedbackSheet, RunTally, StampButton } from '@/components/socrat/answer-flow';
import { GoalReachedMoment, LevelUpMoment } from '@/components/socrat/game-moments';
import { Choice } from '@/components/choice';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { play } from '@/lib/game-sound';
import { Celebrate } from '@/components/socrat/celebrate';

/** Development only: try the answer feel (sheet, sound, combo) without a course. */
export function AnswerDemo() {
  const [run, setRun] = useState(0);
  const [sheet, setSheet] = useState<null | 'correct' | 'wrong'>(null);
  const [party, setParty] = useState(0);
  const answer = (right: boolean) => { setRun(r => (right ? r + 1 : 0)); setSheet(right ? 'correct' : 'wrong'); };
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => answer(true)}>Answer right</Button>
        <Button variant="outline" onClick={() => answer(false)}>Answer wrong</Button>
        <Button variant="secondary" onClick={() => play('finish')}>Finish sound</Button>
        <Button variant="secondary" onClick={() => play('streak')}>Streak sound</Button>
        <Button variant="ghost" onClick={() => play('tap')}>Tap</Button>
        <Button variant="ghost" onClick={() => setParty(n => n + 1)}>Celebrate</Button>
      </div>
      {party ? <Celebrate key={party} kind="jade" emoji="star" sound="finish" /> : null}
      <RunTally run={run} />
      {sheet ? (
        <FeedbackSheet key={`${sheet}-${run}`} tone={sheet} run={run} title={sheet === 'correct' ? (run >= 3 ? `${run} in a row.` : 'Nice work.') : 'Not quite'} action="Continue" onContinue={() => setSheet(null)}>
          {sheet === 'wrong' ? <p>The status code for a created resource is 201.</p> : null}
        </FeedbackSheet>
      ) : null}
    </div>
  );
}

/** Development only: the daily-goal and level-up moments, reset on each press. */
export function MomentDemo() {
  const [n, setN] = useState(0);
  const show = () => {
    try { localStorage.removeItem('socrat:goal-moment'); localStorage.setItem('socrat:level-seen', '1'); } catch { /* blocked */ }
    setN(v => v + 1);
  };
  return (
    <div className="grid gap-4">
      <div><Button variant="secondary" onClick={show}>Show the moments</Button></div>
      {n ? (
        <div key={n}>
          <LevelUpMoment on proven={9} />
          <GoalReachedMoment on reached day={`demo-${n}`} minutes={10} />
        </div>
      ) : null}
    </div>
  );
}

/** Development only: the quiz pieces with a run on the bar. */
export function ChoiceDemo() {
  const [choice, setChoice] = useState<number | null>(null);
  const options = ['200 OK', '201 Created', '404 Not Found'];
  return (
    <div className="grid gap-4" data-slot="quiz-head">
      <div className="db-only db-lesson-bar" style={{ '--db-lesson-done': '60%' } as React.CSSProperties}><span /></div>
      <Progress value={70} tone="hi" aria-label="Progress on a run" />
      <div className="grid gap-3" role="radiogroup" aria-label="Answer choices">
        {options.map((o, i) => (
          <Choice key={o} role="radio" aria-checked={choice === i} selected={choice === i} marker={String.fromCharCode(65 + i)} onClick={() => setChoice(i)}>
            <span className="choice-title">{o}</span>
          </Choice>
        ))}
      </div>
      <div data-slot="answer-bar"><StampButton disabled={choice === null}>Check</StampButton></div>
    </div>
  );
}
