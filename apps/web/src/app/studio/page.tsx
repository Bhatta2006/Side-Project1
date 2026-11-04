'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useGuard } from '@/lib/session';
import { useCourse } from '@/lib/course';
import { NAME } from '@/lib/routes';
import { Loading, Page, PageHeader } from '@/components/common';
import { PracticeNav } from '@/components/socrat/practice-nav';
import { Badge } from '@/components/ui/badge';
import { Drills } from '@/components/studio/drills';
import { EVIDENCE_TEXT, LOOP_TEXT, STUDIOS } from '@/components/studio/registry';

/**
 * Practice, the same page for every course: practice sets written for the learner's course,
 * then the course's own tools (math workbench, physics lab) if it has them. The tabs above add
 * only the extras the course has (the problem library in programming courses, company
 * questions in DSA); nothing from another course shows here.
 */
function PracticePage() {
  const allowed = useGuard('active');
  const { shape, features, ready } = useCourse();
  const concept = useSearchParams().get('concept') ?? undefined;
  if (!allowed || !ready) return <Loading variant="article" label="Opening practice" />;

  const studio = shape && shape.studio !== 'code' ? shape : null;
  const Tools = studio && studio.studio !== 'reading' ? STUDIOS[studio.studio] : undefined;
  return (
    <Page>
      <PracticeNav />
      <PageHeader
        eyebrow={NAME.practice}
        title={studio?.name ?? NAME.practiceSets}
        description={studio ? LOOP_TEXT[studio.loop] ?? '' : 'Fresh questions written for your course, on any topic you have opened.'}
      />
      {studio ? (
        <section aria-labelledby="proof" className="mb-8 grid gap-2">
          <h2 id="proof" className="text-sm font-semibold">What counts as proof</h2>
          <ul className="flex flex-wrap gap-2">
            {studio.evidence.map(kind => <li key={kind}><Badge variant="secondary">{EVIDENCE_TEXT[kind] ?? kind}</Badge></li>)}
          </ul>
        </section>
      ) : null}
      {features.drills ? <Drills initialConcept={concept} /> : null}
      {Tools && studio ? (
        <section aria-labelledby="tools" className="mt-12 grid gap-4">
          <h2 id="tools" className="font-display text-xl font-semibold tracking-[-0.02em]">{studio.name} tools</h2>
          <Tools shape={studio} />
        </section>
      ) : null}
    </Page>
  );
}

export default function Practice() {
  return <Suspense fallback={<Loading variant="article" label="Opening practice" />}><PracticePage /></Suspense>;
}
