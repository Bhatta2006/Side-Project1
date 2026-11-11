'use client';

import Link from 'next/link';
import { useEffect, useState, type ComponentType } from 'react';
import { ArrowRight } from '@/components/icons';
import { api } from '@/lib/api';
import { activityHref } from '@/lib/routes';
import type { CourseShape, Today } from '@/lib/types';
import { Loading } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';
import { Lab } from './lab';
import { Workbench } from './workbench';

export type Studio = CourseShape['studio'];
export interface StudioProps { shape: CourseShape }

/** What a studio asks of the learner, in plain words (the "practice loop"). */
export const LOOP_TEXT: Record<string, string> = {
  solve: 'Solve problems, then check your answer.',
  derive: 'Work a problem line by line; every line is checked against the one before.',
  'predict-observe-explain': 'Predict what will happen, run the experiment, then explain what you saw.',
  'read-reflect': 'Read a lesson, then explain it back in your own words.',
};

/** What counts as proof that you can do it. */
export const EVIDENCE_TEXT: Record<string, string> = {
  tests: 'Your code passes the tests',
  derivation: 'Every step of your working follows',
  numeric: 'Your number is right, with units',
  explanation: 'You explain it in your own words',
  quiz: 'You answer concept checks',
};

/** The simplest studio: lessons and explaining back. Works for any subject with no tool yet. */
function Notebook() {
  const [today, setToday] = useState<Today | null | undefined>(undefined);
  useEffect(() => {
    api.get<Today>('/today').then(setToday).catch(() => setToday(null));
  }, []);
  if (today === undefined) return <Loading variant="article" label="Finding your next step" />;
  if (!today?.next) {
    return <EmptyState title="Nothing queued right now">Open your skills to pick the next topic.</EmptyState>;
  }
  return (
    <div className="grid gap-3 rounded-card border p-5">
      <p className="text-sm text-muted-foreground">Next in your notebook</p>
      <p className="font-display text-xl font-semibold tracking-[-0.02em]">{today.next.title}</p>
      <div>
        <Button asChild><Link href={activityHref(today.next.id)}>Open <ArrowRight /></Link></Button>
      </div>
    </div>
  );
}

/** Studios with their own tools register here (the math workbench and physics lab). */
export const STUDIOS: Partial<Record<Studio, ComponentType<StudioProps>>> = {
  reading: Notebook,
  workbench: Workbench,
  lab: Lab,
};
