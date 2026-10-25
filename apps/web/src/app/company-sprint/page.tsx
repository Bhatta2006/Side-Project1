'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME } from '@/lib/routes';
import type { CompanySprintOverview } from '@/lib/types';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { CompanySprintPlan } from '@/components/socrat/company-sprint-plan';
import { CompanySprintSetup } from '@/components/socrat/company-sprint-setup';
import { PracticeNav } from '@/components/socrat/practice-nav';
import { UpgradeBanner } from '@/components/paywall';
import { EmptyState } from '@/components/socrat/states';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';

export default function CompanySprint() {
  const allowed = useGuard('active');
  const [overview, setOverview] = useState<CompanySprintOverview | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError('');
    api.get<CompanySprintOverview>('/library/company-sprints').then(setOverview).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  async function stop() {
    if (!overview?.current) return;
    setBusy(true);
    try { await api.post(`/library/company-sprints/${overview.current.id}/stop`); load(); }
    catch (e) { setError(explain(e)); }
    finally { setBusy(false); }
  }

  if (!allowed || (!overview && !error)) return <Loading variant="list" label="Loading your company sprint" />;
  const current = overview?.current;
  return (
    <Page wide>
      <PracticeNav />
      <PageHeader
        eyebrow={NAME.practice}
        title={NAME.companySprint}
        description="A week-by-week plan aimed at one company's interviews, built on your roadmap and that company's most asked questions."
        actions={current ? (
          <AlertDialog>
            <AlertDialogTrigger asChild><Button variant="outline" disabled={busy}>Stop this sprint</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Stop {current.title}?</AlertDialogTitle>
                <AlertDialogDescription>Your skills and solves stay. Any goal you accepted for this sprint stays in your plan until you change it.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep going</AlertDialogCancel>
                <AlertDialogAction onClick={stop}>Stop sprint</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : null}
      />
      {error ? <ErrorNote message={error} retry={load} className="mb-6" /> : null}
      {overview?.locked && !current ? (
        <UpgradeBanner reason="pro_required" title="Plan your sprint for a target company" className="mb-6">
          Pick Google, Amazon or any of hundreds of companies and get a week-by-week plan built from the questions they actually ask.
        </UpgradeBanner>
      ) : null}
      {current ? <CompanySprintPlan sprint={current} onDecided={load} /> : overview && overview.companies.length ? (
        <CompanySprintSetup overview={overview} onStarted={view => setOverview({ ...overview, current: view })} />
      ) : overview ? (
        <EmptyState title="No company banks fit this course">
          Company sprints use interview question banks, which map to the DSA for Interviews course. Switch course in Settings to plan one.
        </EmptyState>
      ) : null}
    </Page>
  );
}
