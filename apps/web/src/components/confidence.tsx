'use client';

import { Pill } from '@/components/choice';

const SURE = ['Guessing', 'Unsure', 'Fairly sure', 'Certain'];

/**
 * "How sure are you?" before checking an answer. Optional, never part of the score: it is
 * compared later with how often the learner was right (confidence calibration). 1..4 or null.
 */
export function ConfidencePicker({ value, onChange }: { value: number | null; onChange(value: number | null): void }) {
  return (
    <div role="group" aria-labelledby="quiz-sure" className="grid gap-2">
      <span id="quiz-sure" className="text-sm text-muted-foreground">How sure are you? (optional)</span>
      <div className="flex flex-wrap gap-2">
        {SURE.map((label, i) => (
          <Pill key={label} pressed={value === i + 1} onClick={() => onChange(value === i + 1 ? null : i + 1)} className="h-9 px-3 text-sm">
            {label}
          </Pill>
        ))}
      </div>
    </div>
  );
}
