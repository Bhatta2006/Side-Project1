'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight, Search, SlidersHorizontal, Star, X } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { NAME, conceptHref } from '@/lib/routes';
import type { Contest, Level as PracticeLevel, LibraryProblem, Recommendations } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, PageHeader, Reveal } from '@/components/common';
import { Level, LevelCard, PlatformTag, ProblemName, StatusControl } from '@/components/practice';
import { PracticeNav } from '@/components/socrat/practice-nav';
import { EmptyState } from '@/components/socrat/states';
import { StatusIcon, statusFromBand } from '@/components/socrat/status';
import { Badge } from '@/components/ui/badge';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { NativeSelect, NativeSelectOptGroup, NativeSelectOption } from '@/components/ui/native-select';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Illustration } from '@/components/socrat/illustration';

interface Meta {
  platforms: Record<string, number>;
  sheets: Record<string, number>;
  concepts: { id: string; title: string; course: string; module: string; locked: boolean; problems: number }[];
}
interface PageData { total: number; items: LibraryProblem[]; level: PracticeLevel }

const PLATFORMS = ['LeetCode', 'CSES', 'Codeforces'] as const;
const STATUSES = [
  ['all', 'All'],
  ['unsolved', 'Unsolved'],
  ['bookmarked', 'My list'],
  ['attempted', 'Attempted'],
  ['solved', 'Solved'],
] as const;
const SORTS = [
  ['recommended', 'Best for me'],
  ['easiest', 'Easiest first'],
  ['hardest', 'Hardest first'],
  ['popular', 'Most asked'],
  ['title', 'A to Z'],
] as const;
const RATINGS = Array.from({ length: 28 }, (_, i) => 800 + i * 100);
const PAGE = 30;

type Filters = {
  q: string;
  platform: string[];
  concept: string;
  difficulty: string;
  rating_min: number;
  rating_max: number;
  sheet: string;
  status: (typeof STATUSES)[number][0];
  sort: (typeof SORTS)[number][0];
};
const EMPTY: Filters = { q: '', platform: [], concept: '', difficulty: '', rating_min: 0, rating_max: 0, sheet: '', status: 'all', sort: 'recommended' };

function fromLocation(): Filters {
  if (typeof window === 'undefined') return EMPTY;
  const params = new URLSearchParams(window.location.search);
  const status = params.get('status') ?? 'all';
  const sort = params.get('sort') ?? 'recommended';
  return {
    q: params.get('q') ?? '',
    platform: (params.get('platform') ?? '').split(',').filter(p => (PLATFORMS as readonly string[]).includes(p)),
    concept: params.get('concept') ?? '',
    difficulty: params.get('difficulty') ?? '',
    rating_min: Number(params.get('rating_min')) || 0,
    rating_max: Number(params.get('rating_max')) || 0,
    sheet: params.get('sheet') ?? '',
    status: (STATUSES.some(s => s[0] === status) ? status : 'all') as Filters['status'],
    sort: (SORTS.some(s => s[0] === sort) ? sort : 'recommended') as Filters['sort'],
  };
}

function query(f: Filters, offset = 0): string {
  const params = new URLSearchParams();
  if (f.q) params.set('q', f.q);
  if (f.platform.length) params.set('platform', f.platform.join(','));
  if (f.concept) params.set('concept', f.concept);
  if (f.difficulty) params.set('difficulty', f.difficulty);
  if (f.rating_min) params.set('rating_min', String(f.rating_min));
  if (f.rating_max) params.set('rating_max', String(f.rating_max));
  if (f.sheet) params.set('sheet', f.sheet);
  if (f.status !== 'all') params.set('status', f.status);
  if (f.sort !== 'recommended') params.set('sort', f.sort);
  if (offset) params.set('offset', String(offset));
  return params.toString();
}

function Pager({ total, offset, setOffset }: { total: number; offset: number; setOffset: (fn: (o: number) => number) => void }) {
  if (total <= PAGE) return null;
  return (
    <nav aria-label="Pages" className="flex items-center justify-between gap-3 text-sm">
      <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - PAGE))}><ChevronLeft data-icon="inline-start" /> Previous</Button>
      <span className="font-semibold text-muted-foreground tabular-nums">{offset + 1} to {Math.min(offset + PAGE, total)} of {total.toLocaleString()}</span>
      <Button variant="outline" size="sm" disabled={offset + PAGE >= total} onClick={() => setOffset(o => o + PAGE)}>Next <ChevronRight data-icon="inline-end" /></Button>
    </nav>
  );
}

export default function Library() {
  const allowed = useGuard('active');
  const [meta, setMeta] = useState<Meta | null>(null);
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [contests, setContests] = useState<Contest[]>([]);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState<PageData | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [more, setMore] = useState(false);
  const [sheet, setSheet] = useState(false);

  useEffect(() => {
    const initial = fromLocation();
    setFilters(initial);
    setSearch(initial.q);
    setMore(Boolean(initial.platform.length || initial.rating_min || initial.rating_max || initial.sheet || initial.sort !== 'recommended'));
  }, []);
  useEffect(() => {
    if (!allowed) return;
    api.get<Meta>('/library/meta').then(setMeta).catch(e => setError(explain(e)));
    api.get<Recommendations>('/library/recommendations?limit=6').then(r => {
      setRecs(r);
      // Rated rounds only once the learner is ready for them (or has linked Codeforces).
      if (r.codeforces || r.level.rating >= 1100) {
        api.get<{ items: Contest[] }>('/library/contests').then(c => setContests(c.items.slice(0, 3))).catch(() => undefined);
      }
    }).catch(() => undefined);
  }, [allowed]);
  useEffect(() => {
    const timer = setTimeout(() => setFilters(f => (f && f.q !== search.trim() ? { ...f, q: search.trim() } : f)), 250);
    return () => clearTimeout(timer);
  }, [search]);

  const load = useCallback(() => {
    if (!allowed || !filters) return;
    setLoading(true);
    setError('');
    const qs = query(filters);
    window.history.replaceState(null, '', qs ? `/library?${qs}` : '/library');
    api.get<PageData>(`/library?${query(filters, offset)}&limit=${PAGE}`)
      .then(setPage)
      .catch(e => setError(explain(e)))
      .finally(() => setLoading(false));
  }, [allowed, filters, offset]);
  useEffect(load, [load]);

  const update = (patch: Partial<Filters>) => { setOffset(0); setFilters(f => (f ? { ...f, ...patch } : f)); };
  const replaceItem = (id: string, patch: Partial<LibraryProblem>) =>
    setPage(p => (p ? { ...p, items: p.items.map(i => (i.id === id ? { ...i, ...patch } : i)) } : p));

  const grouped = useMemo(() => {
    const groups: Record<string, Meta['concepts']> = {};
    for (const c of meta?.concepts ?? []) (groups[c.module] ??= []).push(c);
    return groups;
  }, [meta]);

  if (!allowed || !filters) return <Loading variant="list" label="Loading problems" />;
  const unlocked = meta ? Object.values(meta.platforms).reduce((a, b) => a + b, 0) : 0;
  const conceptTitle = meta?.concepts.find(c => c.id === filters.concept)?.title;
  const chips: { label: string; clear: () => void }[] = [
    ...(filters.q ? [{ label: `"${filters.q}"`, clear: () => { setSearch(''); update({ q: '' }); } }] : []),
    ...filters.platform.map(p => ({ label: p, clear: () => update({ platform: filters.platform.filter(x => x !== p) }) })),
    ...(conceptTitle ? [{ label: conceptTitle, clear: () => update({ concept: '' }) }] : []),
    ...(filters.difficulty ? [{ label: filters.difficulty[0].toUpperCase() + filters.difficulty.slice(1), clear: () => update({ difficulty: '' }) }] : []),
    ...(filters.rating_min || filters.rating_max ? [{ label: `Rating ${filters.rating_min || 'any'} to ${filters.rating_max || 'any'}`, clear: () => update({ rating_min: 0, rating_max: 0 }) }] : []),
    ...(filters.sheet ? [{ label: 'Striver A2Z', clear: () => update({ sheet: '' }) }] : []),
  ];
  const clearAll = () => { setSearch(''); update({ ...EMPTY, status: filters.status, sort: filters.sort }); };
  const [top, ...rest] = recs?.problems ?? [];

  const conceptSelect = (
    <label className="grid gap-1.5">
      <span className="text-[13px] font-semibold text-muted-foreground">Skill</span>
      <NativeSelect className="w-full" value={filters.concept} onChange={e => update({ concept: e.target.value })}>
        <NativeSelectOption value="">Any skill</NativeSelectOption>
        {Object.entries(grouped).map(([course, concepts]) => (
          <NativeSelectOptGroup key={course} label={course}>
            {concepts.map(c => <NativeSelectOption key={c.id} value={c.id}>{c.title} ({c.problems})</NativeSelectOption>)}
          </NativeSelectOptGroup>
        ))}
      </NativeSelect>
    </label>
  );
  const difficultySelect = (
    <label className="grid gap-1.5">
      <span className="text-[13px] font-semibold text-muted-foreground">Difficulty</span>
      <NativeSelect className="w-full" value={filters.difficulty} onChange={e => update({ difficulty: e.target.value })}>
        <NativeSelectOption value="">Any</NativeSelectOption>
        <NativeSelectOption value="easy">Easy</NativeSelectOption>
        <NativeSelectOption value="medium">Medium</NativeSelectOption>
        <NativeSelectOption value="hard">Hard</NativeSelectOption>
      </NativeSelect>
    </label>
  );
  const moreFilters = (
    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <fieldset>
        <legend className="mb-1.5 text-[13px] font-semibold text-muted-foreground">Platform</legend>
        <div className="flex flex-wrap gap-1.5">
          {PLATFORMS.map(p => {
            const on = filters.platform.includes(p);
            return (
              <button
                key={p}
                type="button"
                aria-pressed={on}
                className={cn('inline-flex h-11 items-center gap-1.5 rounded-full border border-border-strong px-3.5 text-sm font-medium transition-colors hover:bg-raised', on && 'border-primary font-bold ring-1 ring-primary')}
                onClick={() => update({ platform: on ? filters.platform.filter(x => x !== p) : [...filters.platform, p] })}
              >
                {p}{meta?.platforms[p] ? <span className="text-muted-foreground tabular-nums">{meta.platforms[p].toLocaleString()}</span> : null}
              </button>
            );
          })}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-1.5 text-[13px] font-semibold text-muted-foreground">Rating range</legend>
        <div className="flex items-center gap-2">
          <NativeSelect className="min-w-0 flex-1" aria-label="Minimum rating" value={filters.rating_min} onChange={e => update({ rating_min: Number(e.target.value) })}>
            <NativeSelectOption value={0}>Min</NativeSelectOption>
            {RATINGS.map(r => <NativeSelectOption key={r} value={r}>{r}</NativeSelectOption>)}
          </NativeSelect>
          <span className="text-muted-foreground" aria-hidden="true">to</span>
          <NativeSelect className="min-w-0 flex-1" aria-label="Maximum rating" value={filters.rating_max} onChange={e => update({ rating_max: Number(e.target.value) })}>
            <NativeSelectOption value={0}>Max</NativeSelectOption>
            {RATINGS.map(r => <NativeSelectOption key={r} value={r}>{r}</NativeSelectOption>)}
          </NativeSelect>
        </div>
        <p className="mt-1.5 text-[13px] text-muted-foreground">Codeforces scale; other sites are placed on it.</p>
      </fieldset>
      <label className="grid gap-1.5">
        <span className="text-[13px] font-semibold text-muted-foreground">Sort</span>
        <NativeSelect value={filters.sort} onChange={e => update({ sort: e.target.value as Filters['sort'] })}>
          {SORTS.map(([id, label]) => <NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}
        </NativeSelect>
      </label>
      {meta?.sheets['striver-a2z'] ? (
        <label className="flex min-h-11 cursor-pointer items-center gap-3 self-end text-[15px]">
          <Checkbox checked={filters.sheet === 'striver-a2z'} onCheckedChange={v => update({ sheet: v === true ? 'striver-a2z' : '' })} />
          On the Striver A2Z sheet
        </label>
      ) : null}
    </div>
  );

  return (
    <Page wide>
      <PracticeNav />
      <Reveal>
        <PageHeader
          eyebrow={NAME.practice}
          title={NAME.problems}
          description={unlocked ? `${unlocked.toLocaleString()} external problems from LeetCode, CSES and Codeforces. They open on those sites and are not judged here. Socrat's own judged problems are on each skill's lesson page.` : 'Problems appear as you finish skills.'}
        />
      </Reveal>

      {/* Hero: the personalised recommendations. */}
      {recs ? (
        <Reveal index={1} className="mb-8 grid grid-cols-[minmax(0,1fr)] gap-3 sm:gap-4 lg:grid-cols-12 lg:gap-6">
          {top ? (
            <section className="doodle-host relative flex min-h-64 flex-col gap-4 overflow-hidden rounded-card bg-forest p-6 text-forest-foreground [--card-muted:color-mix(in_srgb,var(--forest-foreground),transparent_18%)] lg:col-span-6 lg:p-8" data-tone="hero" aria-labelledby="for-you-heading">
              <Illustration name="target" className="pointer-events-none absolute top-4 right-4 size-28 [--illo-line:#fff] lg:size-32" />
              <p id="for-you-heading" className="font-hand origin-left -rotate-2 text-[22px] text-white/90">picked for you</p>
              <h2 className="type-display-m max-w-[18ch]">{top.title}</h2>
              <p className="max-w-md text-[15px]">{top.reason}</p>
              <div className="flex flex-wrap gap-2"><Badge>{top.platform}</Badge><Level problem={top} /></div>
              <div className="mt-auto">
                <Button asChild variant="ink">
                  {top.url.startsWith('/') ? (
                    <Link href={top.url}>Open problem<ArrowCircle /></Link>
                  ) : (
                    <a href={top.url} target="_blank" rel="noopener noreferrer" onClick={() => api.post(`/library/problems/${top.id}/opened`).catch(() => undefined)}>
                      Open on {top.platform}<span className="sr-only">, opens in a new tab</span><ArrowCircle />
                    </a>
                  )}
                </Button>
              </div>
            </section>
          ) : (
            <section className="self-start rounded-card border p-6 lg:col-span-6" aria-labelledby="for-you-heading">
              <h2 id="for-you-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Recommended for you</h2>
              <p className="mt-2 text-[15px] text-muted-foreground">Finish your first lesson and recommendations start here.</p>
              <Button asChild variant="outline" className="mt-4"><Link href="/today">Go to {NAME.today}</Link></Button>
            </section>
          )}
          <div className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:col-span-6 lg:gap-6">
            {rest.slice(0, 2).map(p => (
              <div key={p.id} className="flex min-w-0 flex-col gap-3 paper rounded-card p-5">
                <ProblemName problem={p} className="text-base" />
                <p className="text-sm text-muted-foreground">{p.reason}</p>
                <div className="mt-auto flex flex-wrap items-center gap-2"><PlatformTag platform={p.platform} /><Level problem={p} /></div>
              </div>
            ))}
            <Link href="/sprint" className="group flex min-h-40 flex-col justify-between gap-4 rounded-card bg-cream p-5 text-cream-foreground shadow-[0_10px_24px_-18px_rgb(21_22_30/0.35)] transition-[transform,background-color] duration-200 hover:-translate-y-0.5 hover:-rotate-[0.4deg]">
              <span className="type-label">{NAME.sprint}</span>
              <span className="flex items-end justify-between gap-3">
                <span className="font-display text-lg leading-tight font-semibold tracking-[-0.02em]">3 problems, 45 minutes</span>
                <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </span>
            </Link>
            <div className="flex flex-col gap-3 rounded-card bg-raised p-5">
              <LevelCard level={recs.level} solved={recs.solved_external} />
              {!recs.codeforces ? <Link href="/settings#codeforces" className="text-sm font-semibold underline underline-offset-4">Link Codeforces for sharper picks</Link> : null}
            </div>
          </div>
        </Reveal>
      ) : null}

      {contests.length ? (
        <section className="mb-8 rounded-card border p-5" aria-labelledby="contests-heading">
          <h2 id="contests-heading" className="font-display text-lg font-semibold tracking-[-0.02em]">Upcoming rated rounds</h2>
          <ul className="mt-3 grid gap-2 text-[15px]">
            {contests.map(c => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2">
                <a href={c.url} target="_blank" rel="noopener noreferrer" className="font-semibold underline-offset-4 hover:underline">{c.name}<span className="sr-only">, opens on Codeforces</span></a>
                <span className="text-[13px] text-muted-foreground tabular-nums">
                  {new Date(c.start * 1000).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}, {Math.round(c.duration_minutes / 60 * 10) / 10} h
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Search, three visible filters, more filters. */}
      <section aria-labelledby="results-heading" className="min-w-0">
        <h2 id="results-heading" className="sr-only">{NAME.problems}</h2>
        <div className="grid grid-cols-[minmax(0,1fr)] gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              type="search"
              aria-label="Search problems"
              placeholder="Search by problem name"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="h-13 w-full rounded-control border border-border-strong bg-card pr-4 pl-12 text-base text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring"
            />
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="hidden min-w-56 flex-1 md:block">{conceptSelect}</div>
            <div className="hidden w-44 md:block">{difficultySelect}</div>
            <div role="tablist" aria-label="Status" className="inline-flex h-12 max-w-full min-w-0 items-center gap-1 overflow-x-auto rounded-full bg-raised p-1 text-muted-foreground">
              {STATUSES.map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={filters.status === id}
                  onClick={() => update({ status: id })}
                  className={cn('inline-flex h-full min-h-10 items-center gap-1.5 rounded-full border border-transparent px-3.5 text-sm font-medium whitespace-nowrap transition-colors', filters.status === id ? 'border-border bg-card font-bold text-foreground' : 'hover:text-foreground')}
                >
                  {id === 'bookmarked' ? <Star className="size-3.5" aria-hidden="true" /> : null}{label}
                </button>
              ))}
            </div>
            <Button variant="outline" className="hidden md:inline-flex" aria-expanded={more} aria-controls="more-filters" onClick={() => setMore(v => !v)}>
              <SlidersHorizontal data-icon="inline-start" /> {more ? 'Fewer filters' : 'More filters'}
            </Button>
            <Button variant="outline" className="md:hidden" aria-haspopup="dialog" onClick={() => setSheet(true)}>
              <SlidersHorizontal data-icon="inline-start" /> Filters{chips.length ? ` (${chips.length})` : ''}
            </Button>
          </div>
          {more ? <div id="more-filters" className="hidden rounded-card border p-5 md:block">{moreFilters}</div> : null}
          {chips.length ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-muted-foreground tabular-nums">{page ? `${page.total.toLocaleString()} results` : 'Filtering'}</span>
              {chips.map(chip => (
                <button key={chip.label} type="button" onClick={chip.clear} className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border-strong pr-2 pl-3 text-sm font-semibold hover:bg-raised" aria-label={`Remove filter ${chip.label}`}>
                  {chip.label} <X className="size-4" aria-hidden="true" />
                </button>
              ))}
              <button type="button" onClick={clearAll} className="min-h-9 px-1 text-sm font-semibold underline underline-offset-4">Clear all</button>
            </div>
          ) : null}
        </div>

        <Sheet open={sheet} onOpenChange={setSheet}>
          <SheetContent side="bottom" className="gap-0">
            <SheetHeader className="px-5 pt-4">
              <SheetTitle>Filters</SheetTitle>
              <SheetDescription>Filters apply as you change them.</SheetDescription>
            </SheetHeader>
            <div className="grid gap-5 px-5 py-4">
              {conceptSelect}
              {difficultySelect}
              {moreFilters}
            </div>
            <div className="sticky bottom-0 flex gap-3 border-t bg-card px-5 py-4">
              {chips.length ? <Button variant="outline" onClick={clearAll}>Clear all</Button> : null}
              <Button className="flex-1" onClick={() => setSheet(false)}>Show {page ? page.total.toLocaleString() : ''} problems</Button>
            </div>
          </SheetContent>
        </Sheet>

        <div className="mt-6 grid grid-cols-[minmax(0,1fr)] gap-4">
          {page ? <Pager total={page.total} offset={offset} setOffset={setOffset} /> : null}

          {/* Desktop: dense table. Phone: card rows. */}
          <div className={cn('hidden overflow-hidden paper rounded-card transition-opacity md:block', loading && 'opacity-90')} aria-busy={loading}>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-5">Problem</TableHead>
                  <TableHead>Difficulty</TableHead>
                  <TableHead className="hidden lg:table-cell">Skill</TableHead>
                  <TableHead className="pr-5 text-right">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {page?.items.map(p => (
                  <TableRow key={p.id} data-problem-row="">
                    <TableCell className="min-w-56 py-3 pl-5 whitespace-normal">
                      <div className="flex flex-wrap items-center gap-2">
                        <ProblemName problem={p} onOpened={() => replaceItem(p.id, { status: p.status ?? 'attempted' })} />
                        <PlatformTag platform={p.platform} />
                        {p.striver ? <Badge variant="secondary">A2Z</Badge> : null}
                      </div>
                      {p.companies ? <p className="mt-0.5 text-[13px] text-muted-foreground">Asked at {p.companies} companies</p> : null}
                    </TableCell>
                    <TableCell><Level problem={p} /></TableCell>
                    <TableCell className="hidden min-w-44 whitespace-normal lg:table-cell">
                      {p.concept ? (
                        <Link href={conceptHref(p.concept.id)} className="inline-flex items-center gap-2 text-[15px] underline-offset-4 hover:underline">
                          <StatusIcon status={statusFromBand(p.concept.band)} size={20} />
                          {p.concept.title}
                        </Link>
                      ) : null}
                    </TableCell>
                    <TableCell className="pr-5 text-right">
                      <StatusControl id={p.id} status={p.status} bookmarked={p.bookmarked} compact onChange={next => replaceItem(p.id, next)} />
                    </TableCell>
                  </TableRow>
                ))}
                {!page ? Array.from({ length: 8 }, (_, i) => (
                  <TableRow key={`s${i}`}><TableCell colSpan={4} className="px-5"><Skeleton className="h-7 w-full" /></TableCell></TableRow>
                )) : null}
              </TableBody>
            </Table>
          </div>
          <ul className={cn('grid gap-3 md:hidden', loading && 'opacity-90')} aria-busy={loading}>
            {page?.items.map(p => (
              <li key={p.id} data-problem-row="" className="grid gap-3 paper rounded-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <ProblemName problem={p} className="text-base" onOpened={() => replaceItem(p.id, { status: p.status ?? 'attempted' })} />
                  <StatusIcon status={p.status === 'solved' ? 'practised' : 'not_seen'} size={24} title={p.status === 'solved' ? 'Solved' : p.status === 'attempted' ? 'Attempted' : 'Not solved yet'} />
                </div>
                <div className="flex flex-wrap items-center gap-2"><PlatformTag platform={p.platform} /><Level problem={p} />{p.striver ? <Badge variant="secondary">A2Z</Badge> : null}</div>
                <div className="flex items-center justify-between gap-2">
                  {p.concept ? <Link href={conceptHref(p.concept.id)} className="text-sm font-semibold underline underline-offset-4">{p.concept.title}</Link> : <span />}
                  <StatusControl id={p.id} status={p.status} bookmarked={p.bookmarked} compact onChange={next => replaceItem(p.id, next)} />
                </div>
              </li>
            ))}
            {!page ? Array.from({ length: 4 }, (_, i) => <li key={i}><Skeleton className="h-32 w-full rounded-card" /></li>) : null}
          </ul>

          {page && !page.items.length ? (
            filters.status === 'bookmarked' && !chips.length ? (
              <EmptyState title="Your list is empty">Save a problem with its star to keep it here.</EmptyState>
            ) : chips.length || filters.status !== 'all' ? (
              <EmptyState title="No problems match" action={<Button variant="outline" onClick={() => { clearAll(); update({ status: 'all' }); }}>Clear filters</Button>}>
                Remove a filter or search for a different skill.
              </EmptyState>
            ) : (
              <EmptyState title="Nothing unlocked yet" action={<Button asChild variant="outline"><Link href="/plan">Go to {NAME.skills}</Link></Button>}>
                Problems appear as you finish skills.
              </EmptyState>
            )
          ) : null}

          {page ? <Pager total={page.total} offset={offset} setOffset={setOffset} /> : null}
          {error ? <ErrorNote message={error} retry={load} /> : null}
          <p className="text-[13px] text-muted-foreground">Names, ratings and tags only. Statements stay on the original sites. Mark problems solved here, or link Codeforces in {NAME.settings} to sync.</p>
        </div>
      </section>
    </Page>
  );
}
