'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect } from 'react';
import { useGuard } from '@/lib/session';
import { useCourse } from '@/lib/course';
import { NAME } from '@/lib/routes';
import { Loading, Page, PageHeader } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Drills } from '@/components/studio/drills';
import { EVIDENCE_TEXT, LOOP_TEXT, STUDIOS } from '@/components/studio/registry';

/**
 * Practice for every course that is not practised in the problem library: practice sets
 * written for this course, then the studio's own tools (math workbench, physics lab) if it has
 * them. Nothing from another course (company questions, Codeforces, a code editor) shows here.
 */
function StudioPage() {
  const allowed = useGuard('active');
  const { shape, features, ready } = useCourse();
  const router = useRouter();
  const concept = useSearchParams().get('concept') ?? undefined;
  // Programming courses practise in the library.
  useEffect(() => { if (allowed && ready && features.library) router.replace('/library'); }, [allowed, ready, features.library, router]);
  if (!allowed || !ready || features.library) return <Loading variant="article" label="Opening practice" />;

  const studio = shape && shape.studio !== 'code' ? shape : null;
  const Tools = studio && studio.studio !== 'reading' ? STUDIOS[studio.studio] : undefined;
  return (
    <Page>
      <PageHeader
        eyebrow={NAME.practice}
        title={studio?.name ?? NAME.practice}
        description={studio ? LOOP_TEXT[studio.loop] ?? '' : 'Practise the topics you have opened with questions written for your course.'}
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

export default function Studio() {
  return <Suspense fallback={<Loading variant="article" label="Opening practice" />}><StudioPage /></Suspense>;
}
