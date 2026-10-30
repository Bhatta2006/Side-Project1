'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME } from '@/lib/routes';
import type { PlanView } from '@/lib/types';
import { ErrorNote, Loading, Page } from '@/components/common';
import { StatusLegend } from '@/components/socrat/status';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

const SkillGraph = dynamic(() => import('@/components/socrat/skill-graph'), { ssr: false, loading: () => <Skeleton className="size-full" /> });

export default function GraphPage() {
  const allowed = useGuard('active');
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    api.get<PlanView>('/plan').then(setPlan).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!plan && !error)) return <Loading label="Loading your skill graph" />;
  if (!plan) return <Page><ErrorNote message={error} retry={load} /></Page>;

  return (
    <Page wide>
      <header className="mb-6">
        <h1 className="type-display-l">Your skill <span className="hl hl-draw">graph</span></h1>
        <p className="mt-3 max-w-2xl text-base text-muted-foreground">
          Each arrow points from a skill to what it unlocks. The graph is rebuilt from your results each time, so when Socrat adds, repairs or sets aside a skill, it changes here. Faded skills are optional or set aside.
        </p>
        <Button asChild variant="outline" className="mt-4"><Link href="/plan">Back to {NAME.skills}</Link></Button>
      </header>
      <div className="h-[70vh] min-h-96 overflow-hidden rounded-card border" role="group" aria-label="Skill graph. The Skills page lists the same skills in order.">
        <SkillGraph plan={plan} />
      </div>
      <div className="mt-4"><StatusLegend only={['not_seen', 'read', 'assumed', 'practised', 'mastered', 'review', 'locked']} /></div>
    </Page>
  );
}
