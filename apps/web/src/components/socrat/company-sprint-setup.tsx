'use client';

import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { api, explain } from '@/lib/api';
import type { CompanySprintOverview, CompanySprintView } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Pill } from '@/components/choice';
import { ErrorNote } from '@/components/common';
import { ArrowCircle, Button } from '@/components/ui/button';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';

/** Pick a company, a role and a length; the server plans the weeks. */
export function CompanySprintSetup({ overview, onStarted }: { overview: CompanySprintOverview; onStarted: (view: CompanySprintView) => void }) {
  const [query, setQuery] = useState('');
  const [companies, setCompanies] = useState(overview.companies);
  const [company, setCompany] = useState(overview.companies.find(c => c.slug === 'amazon')?.slug ?? overview.companies[0]?.slug ?? '');
  const [role, setRole] = useState('sde1');
  const [weeks, setWeeks] = useState(6);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!query) { setCompanies(overview.companies); return; }
    const timer = setTimeout(() => {
      api.get<CompanySprintOverview>(`/library/company-sprints?q=${encodeURIComponent(query)}`)
        .then(r => setCompanies(r.companies))
        .catch(e => setError(explain(e)));
    }, 200);
    return () => clearTimeout(timer);
  }, [query, overview.companies]);

  const chosen = companies.find(c => c.slug === company) ?? overview.companies.find(c => c.slug === company);
  const roleLabel = overview.roles.find(r => r.id === role)?.label ?? '';

  async function start() {
    setBusy(true);
    setError('');
    try { onStarted(await api.post<CompanySprintView>('/library/company-sprints', { company, role, weeks })); }
    catch (e) { setError(explain(e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <section aria-labelledby="company-pick" className="paper rounded-card p-4 sm:p-5">
        <h2 id="company-pick" className="font-display text-xl font-semibold tracking-[-0.03em]">1. Company</h2>
        <div className="relative mt-3">
          <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <input type="search" placeholder="Search companies" aria-label="Search companies" value={query} onChange={e => setQuery(e.target.value)} className="h-12 w-full rounded-control border border-border-strong bg-card pr-3 pl-10 text-[15px] outline-none focus-visible:border-ring" />
        </div>
        <ul className="mt-2 grid max-h-[50dvh] gap-0.5 overflow-y-auto" aria-label="Companies">
          {companies.map(c => (
            <li key={c.slug}>
              <button
                type="button"
                aria-pressed={company === c.slug}
                onClick={() => setCompany(c.slug)}
                className={cn('flex min-h-11 w-full items-center justify-between gap-2 rounded-[14px] px-3 py-2 text-left text-[15px] transition-colors hover:bg-raised', company === c.slug && 'bg-primary font-bold text-primary-foreground hover:bg-primary')}
              >
                <span className="truncate">{c.name}</span>
                <span className="text-[13px] tabular-nums">{c.questions}<span className="sr-only"> questions</span></span>
              </button>
            </li>
          ))}
          {!companies.length ? <li className="px-3 py-3 text-sm text-muted-foreground">No companies match. Companies need at least 15 questions that use skills in your course.</li> : null}
        </ul>
      </section>

      <section aria-labelledby="sprint-shape" className="flex flex-col gap-6 rounded-card bg-forest p-6 text-forest-foreground lg:p-8" data-tone="hero">
        <div>
          <h2 id="sprint-shape" className="type-label">2. Role and length</h2>
          <label className="mt-4 block text-[15px] font-semibold" htmlFor="sprint-role">Role</label>
          <NativeSelect id="sprint-role" value={role} onChange={e => setRole(e.target.value)} className="mt-2 w-full max-w-xs bg-background text-foreground">
            {overview.roles.map(r => <NativeSelectOption key={r.id} value={r.id}>{r.label}</NativeSelectOption>)}
          </NativeSelect>
          <p className="mt-4 text-[15px] font-semibold" id="sprint-weeks">Weeks</p>
          <div className="mt-2 flex flex-wrap gap-2 text-foreground" role="group" aria-labelledby="sprint-weeks">
            {overview.weeks.map(w => <Pill key={w} pressed={weeks === w} onClick={() => setWeeks(w)}>{w} weeks</Pill>)}
          </div>
        </div>
        <div className="mt-auto">
          <p className="type-display-m">{chosen ? `${chosen.name} ${roleLabel} in ${weeks} weeks` : 'Pick a company'}</p>
          <p className="mt-2 max-w-md text-[15px]">Socrat lays the skills this company asks about most across the weeks, adds its most frequent questions as you unlock them, and keeps the last week for review. Your roadmap only changes if you accept.</p>
          <Button variant="ink" size="lg" className="mt-5" disabled={!company || busy} aria-busy={busy} onClick={start}>Plan my sprint<ArrowCircle loading={busy} /></Button>
        </div>
        {error ? <ErrorNote message={error} /> : null}
      </section>
    </div>
  );
}
