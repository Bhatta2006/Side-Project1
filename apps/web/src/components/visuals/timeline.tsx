'use client';

import { useId, useState } from 'react';
import { cn } from '@/lib/utils';

const MAX_STEPS = 32;

/**
 * A small track editor: tap a step to place or remove a marker on a track. Long timelines are
 * shown in at most 32 steps (each covering several units). The marker list below is the
 * accessible form and the thing a learner can read aloud or copy. Nothing is stored or graded:
 * this is for thinking about timing, so no evidence is claimed from it.
 */
export function Timeline({ params }: { params: { unit: string; length: number; tracks: string[] } }) {
  const id = useId();
  const steps = Math.min(params.length, MAX_STEPS);
  const per = Math.ceil(params.length / steps);
  const [marks, setMarks] = useState<Record<string, number[]>>({});

  const toggle = (track: string, step: number) =>
    setMarks(m => {
      const have = m[track] ?? [];
      return { ...m, [track]: have.includes(step) ? have.filter(s => s !== step) : [...have, step].sort((a, b) => a - b) };
    });
  const at = (step: number) => (step * per + 1 === (step + 1) * per ? `${step * per + 1}` : `${step * per + 1}–${Math.min((step + 1) * per, params.length)}`);

  return (
    <div className="grid gap-3 text-sm">
      {params.tracks.map(track => (
        <div key={track} className="grid gap-1">
          <p id={`${id}-${track}`} className="font-medium">{track}</p>
          <div role="group" aria-labelledby={`${id}-${track}`} className="grid gap-1" style={{ gridTemplateColumns: `repeat(${steps}, minmax(0, 1fr))` }}>
            {Array.from({ length: steps }, (_, step) => {
              const on = (marks[track] ?? []).includes(step);
              return (
                <button
                  key={step}
                  type="button"
                  aria-pressed={on}
                  aria-label={`${track}, ${params.unit} ${at(step)}`}
                  onClick={() => toggle(track, step)}
                  className={cn('h-8 rounded border text-[10px] transition-colors', on ? 'border-primary bg-primary text-primary-foreground' : 'bg-background hover:bg-raised')}
                >
                  {step % 4 === 0 ? step * per + 1 : ''}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <p className="text-muted-foreground" aria-live="polite">
        {params.tracks.map(t => `${t}: ${(marks[t] ?? []).map(s => at(s)).join(', ') || 'no markers'}`).join(' · ')}
        {' '}({params.unit}s, 1 to {params.length})
      </p>
    </div>
  );
}
