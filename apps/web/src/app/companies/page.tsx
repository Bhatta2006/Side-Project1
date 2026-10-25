'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, Lock, Search } from 'lucide-react';
import { api, explain, openPaywall } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, conceptHref } from '@/lib/routes';
import type { CompanyProblem } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Difficulty, ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { ProblemName } from '@/components/practice';
import { PracticeNav } from '@/components/socrat/practice-nav';
import { EmptyState } from '@/components/socrat/states';
import { StatusIcon, statusFromBand } from '@/components/socrat/status';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Company { slug: string; name: string; problems: number }
interface CompanyView { slug: string; name: string; total: number; items: CompanyProblem[] }

const WINDOWS = [
  ['thirty-days', 'Last 30 days'],
  ['three-months', 'Last 3 months'],
  ['six-months', 'Last 6 months'],
  ['all', 'All time'],
] as const;
const PAGE = 50;

function Frequency({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-2">
      <span className="relative h-1.5 w-16 overflow-hidden rounded-full bg-raised" aria-hidden="true">
        <span className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${value}%` }} />
      </span>
      <span className="text-[13px] font-semibold tabular-nums">{Math.round(value)}%<span className="sr-only"> frequency</span></span>
    </span>
  );
}

/** Not on Pro: the companies and how many questions each has, behind a lock that opens the paywall. */
function LockedCompanies({ companies, query, onQuery }: { companies: Company[]; query: string; onQuery: (q: string) => void }) {
  const total = companies.reduce((sum, c) => sum + c.problems, 0);
  return (
    <Page wide>
      <PracticeNav />
      <PageHeader eyebrow={NAME.practice} title={NAME.companies} description="The questions top companies actually ask, ordered by how often and how recently." />
      <section className="mb-6 flex flex-col gap-4 rounded-card border-[1.5px] border-proof-stroke bg-proof text-proof-foreground p-5 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <p className="inline-flex items-center gap-1.5 text-xs font-bold"><Lock className="size-3.5" aria-hidden="true" /> Pro feature</p>
          <p className="mt-1 font-display text-xl font-bold tracking-[-0.02em]">{total.toLocaleString()}+ real interview questions from {companies.length}{companies.length >= 60 ? '+' : ''} companies</p>
          <p className="mt-1 text-[15px] text-proof-foreground/75">See what Google, Amazon and others asked in the last 30 days, and get a week-by-week sprint plan for your target company.</p>
        </div>
        <Button size="lg" variant="ink" onClick={() => openPaywall('pro_required')}>Unlock with Pro</Button>
      </section>
      <div className="relative mb-4 max-w-sm">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <input value={query} onChange={e => onQuery(e.target.value)} placeholder="Find a company" aria-label="Find a company" className="h-11 w-full rounded-full border border-border-strong bg-card pr-4 pl-9 text-[15px]" />
      </div>
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {companies.map(c => (
          <li key={c.slug}>
            <button type="button" onClick={() => openPaywall('pro_required')} className="flex w-full items-center justify-between gap-3 rounded-[14px] border bg-card px-4 py-3 text-left transition-colors hover:border-foreground/40">
              <span className="min-w-0 truncate font-semibold">{c.name}</span>
              <span className="inline-flex flex-none items-center gap-1.5 text-[13px] text-muted-foreground tabular-nums"><Lock className="size-3.5" aria-hidden="true" />{c.problems} questions</span>
            </button>
          </li>
        ))}
      </ul>
    </Page>
  );
}

export default function Companies() {
  const allowed = useGuard('active');
  const [query, setQuery] = useState('');
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [selected, setSelected] = useState<string>('');
  const [range, setRange] = useState<(typeof WINDOWS)[number][0]>('three-months');
  const [difficulty, setDifficulty] = useState<'all' | 'easy' | 'medium' | 'hard'>('all');
  const [view, setView] = useState<CompanyView | null>(null);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [phone, setPhone] = useState(false);
  const [locked, setLocked] = useState(false);

  // Selection lives in the URL so back and reload keep it.
  useEffect(() => {
    setPhone(window.matchMedia('(max-width: 1023px)').matches);
    const company = new URLSearchParams(window.location.search).get('company');
    if (company) setSelected(company);
    const onPop = () => setSelected(new URLSearchParams(window.location.search).get('company') ?? '');
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  function choose(slug: string) {
    setSelected(slug);
    setOffset(0);
    window.history.pushState(null, '', slug ? `/companies?company=${encodeURIComponent(slug)}` : '/companies');
  }

  useEffect(() => {
    if (!allowed) return;
    const timer = setTimeout(() => {
      api.get<{ items: Company[]; locked: boolean }>(`/companies?q=${encodeURIComponent(query)}&limit=60`)
        .then(r => {
          setCompanies(r.items);
          setLocked(r.locked);
          if (r.locked) return;
          // Desktop shows a company straight away; phones start with the list.
          if (!window.matchMedia('(max-width: 1023px)').matches) setSelected(s => s || r.items[0]?.slug || '');
        })
        .catch(e => setError(explain(e)));
    }, 200);
    return () => clearTimeout(timer);
  }, [allowed, query]);

  const load = useCallback(() => {
    if (!selected || locked) { setView(null); return; }
    setError('');
    api.get<CompanyView>(`/companies/${selected}?window=${range}&difficulty=${difficulty}&offset=${offset}&limit=${PAGE}`)
      .then(setView)
      .catch(e => setError(explain(e)));
  }, [selected, range, difficulty, offset, locked]);
  useEffect(load, [load]);

  if (!allowed || !companies) return <Loading variant="list" label="Loading company questions" />;
  if (locked) return <LockedCompanies companies={companies} query={query} onQuery={setQuery} />;

  const unlocked = companies.reduce((sum, c) => sum + c.problems, 0);
  const nothingUnlocked = !companies.length && !query;
  const showList = !phone || !selected;
  const showResults = !phone || Boolean(selected);
  const filtered = range !== 'all' || difficulty !== 'all';

  return (
    <Page wide>
      <PracticeNav />
      <PageHeader eyebrow={NAME.practice} title={NAME.companies} description="Interview questions for skills you have finished, ordered by how often they are asked." />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-card bg-raised px-5 py-4">
        <p className="font-semibold">Questions appear as you finish skills.</p>
        {!nothingUnlocked ? <p className="text-sm font-semibold text-muted-foreground tabular-nums">{unlocked.toLocaleString()} unlocked{query ? ' in matching companies' : ''}</p> : null}
      </div>

      {nothingUnlocked ? (
        <EmptyState title="Nothing unlocked yet" action={<Button asChild variant="outline"><Link href="/plan">Go to {NAME.skills}</Link></Button>}>
          Nothing unlocked yet. Questions appear as you finish skills.
        </EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          {showList ? (
            <aside aria-label="Companies" className="h-fit paper rounded-card p-3 lg:sticky lg:top-24">
              <div className="relative mb-2">
                <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <input type="search" placeholder="Search companies" aria-label="Search companies" value={query} onChange={e => setQuery(e.target.value)} className="h-12 w-full rounded-control border border-border-strong bg-card pr-3 pl-10 text-[15px] outline-none focus-visible:border-ring" />
              </div>
              <ul className="grid max-h-[60dvh] gap-0.5 overflow-y-auto">
                {companies.map(c => (
                  <li key={c.slug}>
                    <button
                      type="button"
                      className={cn('flex min-h-11 w-full items-center justify-between gap-2 rounded-[14px] px-3 py-2 text-left text-[15px] transition-colors hover:bg-raised', selected === c.slug && 'bg-primary font-bold text-primary-foreground hover:bg-primary')}
                      aria-pressed={selected === c.slug}
                      onClick={() => choose(c.slug)}
                    >
                      <span className="truncate">{c.name}</span>
                      <span className="text-[13px] tabular-nums">{c.problems}<span className="sr-only"> unlocked</span></span>
                    </button>
                  </li>
                ))}
                {!companies.length ? <li className="px-3 py-3 text-sm text-muted-foreground">No companies match that search.</li> : null}
              </ul>
            </aside>
          ) : null}

          {showResults ? (
            <section className="min-w-0" aria-labelledby="company-heading">
              {phone ? (
                <Button variant="ghost" size="sm" className="-ml-3 mb-2" onClick={() => choose('')}><ArrowLeft data-icon="inline-start" /> All companies</Button>
              ) : null}
              <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                <h2 id="company-heading" className="font-display text-2xl font-semibold tracking-[-0.03em]">
                  {view?.name ?? 'Loading'} {view ? <span className="text-base font-semibold text-muted-foreground tabular-nums">{view.total} unlocked</span> : null}
                </h2>
                <div className="flex flex-wrap gap-2">
                  <NativeSelect value={range} onChange={e => { setRange(e.target.value as typeof range); setOffset(0); }} aria-label="Time window">
                    {WINDOWS.map(([id, label]) => <NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}
                  </NativeSelect>
                  <NativeSelect value={difficulty} onChange={e => { setDifficulty(e.target.value as typeof difficulty); setOffset(0); }} aria-label="Difficulty">
                    <NativeSelectOption value="all">Any difficulty</NativeSelectOption>
                    <NativeSelectOption value="easy">Easy</NativeSelectOption>
                    <NativeSelectOption value="medium">Medium</NativeSelectOption>
                    <NativeSelectOption value="hard">Hard</NativeSelectOption>
                  </NativeSelect>
                </div>
              </div>

              <div className="hidden overflow-hidden paper rounded-card md:block">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="pl-5">Problem</TableHead>
                      <TableHead>Difficulty</TableHead>
                      <TableHead>Frequency</TableHead>
                      <TableHead className="pr-5">Skill</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {view?.items.map(p => (
                      <TableRow key={p.id}>
                        <TableCell className="min-w-56 py-3 pl-5 whitespace-normal">
                          <span className="flex flex-wrap items-center gap-2"><ProblemName problem={p} />{p.striver ? <Badge variant="secondary">A2Z</Badge> : null}</span>
                        </TableCell>
                        <TableCell><Difficulty level={p.difficulty} /></TableCell>
                        <TableCell><Frequency value={p.frequency} /></TableCell>
                        <TableCell className="min-w-48 pr-5 whitespace-normal">
                          {p.concept ? (
                            <Link href={conceptHref(p.concept.id)} className="inline-flex items-center gap-2 text-[15px] underline-offset-4 hover:underline">
                              <StatusIcon status={statusFromBand(p.concept.band)} size={20} />{p.concept.title}
                            </Link>
                          ) : null}
                        </TableCell>
                      </TableRow>
                    ))}
                    {!view ? Array.from({ length: 8 }, (_, i) => (
                      <TableRow key={`s${i}`}><TableCell colSpan={4} className="px-5"><Skeleton className="h-7 w-full" /></TableCell></TableRow>
                    )) : null}
                  </TableBody>
                </Table>
              </div>
              <ul className="grid gap-3 md:hidden">
                {view?.items.map(p => (
                  <li key={p.id} className="grid gap-3 paper rounded-card p-4">
                    <ProblemName problem={p} className="text-base" />
                    <div className="flex flex-wrap items-center gap-3"><Difficulty level={p.difficulty} /><Frequency value={p.frequency} /></div>
                    {p.concept ? <Link href={conceptHref(p.concept.id)} className="inline-flex items-center gap-2 text-sm font-semibold underline underline-offset-4"><StatusIcon status={statusFromBand(p.concept.band)} size={20} />{p.concept.title}</Link> : null}
                  </li>
                ))}
                {!view ? Array.from({ length: 4 }, (_, i) => <li key={i}><Skeleton className="h-28 rounded-card" /></li>) : null}
              </ul>

              {view && !view.items.length ? (
                <EmptyState title="No questions match these filters" className="mt-4" action={filtered ? <Button variant="outline" onClick={() => { setRange('all'); setDifficulty('all'); setOffset(0); }}>Clear filters</Button> : undefined}>
                  Clear a filter to see more.
                </EmptyState>
              ) : null}
              {view && view.total > PAGE ? (
                <nav aria-label="Pages" className="mt-4 flex items-center justify-between text-sm">
                  <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - PAGE))}><ChevronLeft data-icon="inline-start" /> Previous</Button>
                  <span className="font-semibold text-muted-foreground tabular-nums">{offset + 1} to {Math.min(offset + PAGE, view.total)} of {view.total}</span>
                  <Button variant="outline" size="sm" disabled={offset + PAGE >= view.total} onClick={() => setOffset(o => o + PAGE)}>Next <ChevronRight data-icon="inline-end" /></Button>
                </nav>
              ) : null}
              {error ? <ErrorNote message={error} retry={load} /> : null}
              <p className="mt-4 text-[13px] text-muted-foreground">Frequency data comes from community-maintained LeetCode snapshots. Problems open on LeetCode.</p>
            </section>
          ) : null}
        </div>
      )}
    </Page>
  );
}
