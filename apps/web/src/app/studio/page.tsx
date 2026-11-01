'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useGuard, useSession } from '@/lib/session';
import { Loading, Page, PageHeader } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EVIDENCE_TEXT, LOOP_TEXT, STUDIOS } from '@/components/studio/registry';

/** The course's own practice area: what you do here, what counts as proof, and its tools. */
export default function StudioPage() {
  const allowed = useGuard('active');
  const { profile } = useSession();
  const router = useRouter();
  const shape = profile?.enrollment?.shape;
  const isCode = !shape || shape.studio === 'code';
  // Programming courses practise in the library; this page is for the other studios.
  useEffect(() => { if (allowed && isCode) router.replace('/library'); }, [allowed, isCode, router]);
  if (!allowed || isCode || !shape) return <Loading variant="article" label="Opening your studio" />;

  const Studio = STUDIOS[shape.studio];
  return (
    <Page>
      <PageHeader eyebrow="Your studio" title={shape.name} description={LOOP_TEXT[shape.loop] ?? ''} />
      <section aria-labelledby="proof" className="mb-8 grid gap-2">
        <h2 id="proof" className="text-sm font-semibold">What counts as proof</h2>
        <ul className="flex flex-wrap gap-2">
          {shape.evidence.map(kind => <li key={kind}><Badge variant="secondary">{EVIDENCE_TEXT[kind] ?? kind}</Badge></li>)}
        </ul>
      </section>
      {Studio ? <Studio shape={shape} /> : (
        <EmptyState title={`The ${shape.name} tools are on their way`} action={<Button asChild variant="outline"><Link href="/plan">Back to your skills</Link></Button>}>
          Lessons, concept checks and your mentor work today. The hands-on tools for this subject are still being built.
        </EmptyState>
      )}
    </Page>
  );
}
