'use client';
import { useState } from 'react';
import { FeedbackSheet, RunTally } from '@/components/socrat/answer-flow';
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
