'use client';

import { useEffect, useState } from 'react';
import { Check } from '@/components/icons';
import { SocFigure } from '@/components/socrat/soc';

export const BUILD_STEPS = [
  'Reading your answers',
  'Finding the edge of what you know',
  'Creating your plan',
  'Socrat is learning how you think',
  'Lining up your first lesson',
];
const STEP_MS = 850;

/** Plays the build steps once, then calls ``onDone``. Reduced motion plays them quickly. */
export function usePlanBuilding(onDone: () => void, steps = BUILD_STEPS.length) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const pace = reduced ? 200 : STEP_MS;
    let i = 0;
    const timer = window.setInterval(() => {
      i += 1;
      setStep(i);
      if (i >= steps) {
        window.clearInterval(timer);
        window.setTimeout(onDone, pace / 2);
      }
    }, pace);
    return () => window.clearInterval(timer);
    // Plays once per mount.
  }, []);
  return step;
}

/** Shown while a fresh plan is put together: after placement, and right after signing in. */
export function PlanBuilding({ step, eyebrow = 'one moment', title = 'Creating your plan' }: { step: number; eyebrow?: string; title?: string }) {
  return (
    <div className="mx-auto grid w-full max-w-md justify-items-center gap-8 px-4 pt-16 pb-32 text-center sm:px-6 md:pt-24" role="status" aria-live="polite">
      <SocFigure books mood="happy" idle size={150} />
      <div className="grid gap-1">
        <p className="font-hand -rotate-2 text-[22px] text-pen">{eyebrow}</p>
        <h1 className="type-display-m">{title}</h1>
      </div>
      <ol className="grid w-full gap-2 text-left">
        {BUILD_STEPS.map((label, i) => {
          const done = i < step;
          const now = i === step;
          return (
            <li key={label} className={`flex min-h-12 items-center gap-3 rounded-[4px] px-4 transition-all duration-500 motion-reduce:transition-none ${i > step ? 'opacity-35' : 'opacity-100'} ${now ? 'bg-raised' : ''}`}>
              <span className={`grid size-6 flex-none place-items-center rounded-full border-2 transition-colors duration-500 ${done ? 'border-primary bg-primary text-primary-foreground' : now ? 'border-primary' : 'border-border'}`} aria-hidden="true">
                {done ? <Check className="size-3.5" strokeWidth={3} /> : now ? <span className="size-2 animate-pulse rounded-full bg-primary motion-reduce:animate-none" /> : null}
              </span>
              <span className={now ? 'font-semibold' : 'text-muted-foreground'}>{label}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Mount to play the build steps once; ``onDone`` runs at the end. */
export function PlanBuildingRun({ onDone, title }: { onDone: () => void; title?: string }) {
  const step = usePlanBuilding(onDone);
  return <PlanBuilding step={step} title={title} />;
}
