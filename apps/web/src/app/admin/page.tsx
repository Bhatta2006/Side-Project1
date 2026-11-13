'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { notFound } from 'next/navigation';
import { ApiError, api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { ErrorNote, Loading, Page } from '@/components/common';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, StatCard, StatRow, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/admin/ui';
import { Button } from '@/components/ui/button';
import { useSession } from '@/lib/session';

// Every tab is loaded when it is opened, not with the page.
const AdminUsers = dynamic(() => import('@/components/admin-users').then(m => m.AdminUsers), { ssr: false });
const FailedGenerations = dynamic(() => import('@/components/admin/generations').then(m => m.FailedGenerations), { ssr: false });
const Broadcast = dynamic(() => import('@/components/admin/broadcast').then(m => m.Broadcast), { ssr: false });
const ReviewQueue = dynamic(() => import('@/components/review-queue').then(m => m.ReviewQueue), { ssr: false });
const CourseBuilder = dynamic(() => import('@/components/course-builder').then(m => m.CourseBuilder), { ssr: false });
const StyleLab = dynamic(() => import('@/components/style-lab').then(m => m.StyleLab), { ssr: false });

interface Overview {
  funnel: { step: string; learners: number; share: number }[];
  activation: { activated: number; signups: number; rate: number };
  retention: { day: number; eligible: number; retained: number; rate: number | null }[];
  engagement: {
    weekly_active: number;
    minutes_per_active_day: number;
    tutor_messages_7d: number;
    tutor_messages_per_active: number;
    tutor_ratings: { up: number; down: number };
  };
  gates: { module: string; learners: number; pass_rate: number; attempts_per_learner: number }[];
  flagged_items: { concept: string; item: string; answers: number; correct_rate: number; issue: string }[];
  unhelpful_resources: { concept: string; url: string; opens: number; helpful: number; unhelpful: number }[];
  vitals: {
    days: number;
    budgets: { LCP: number; INP: number; CLS: number };
    pages: ({ route: string; samples: number } & Partial<Record<'LCP' | 'INP' | 'CLS', { p75: number; ok: boolean }>>)[];
  };
}

interface AICosts {
  enabled: boolean;
  today_usd: number;
  month_usd: number;
  daily_budget_usd: number;
  monthly_budget_usd: number;
  user_daily_budget_usd: number;
  learners_this_month: number;
  per_learner_usd: number;
  by_feature: Record<string, { calls: number; cost_usd: number; tokens: number }>;
  prices: { input_per_mtok: number; output_per_mtok: number };
}

interface Person { id: string; name: string; email: string | null }

interface ErrorItem {
  id: string;
  source: 'server' | 'browser' | 'learner';
  category: string | null;
  message: string;
  route: string;
  count: number;
  first_at: number;
  last_at: number;
  request_id?: string;
  stack: string;
  reporter: Person | null;
  resolved_at: number | null;
  resolved_by: Person | null;
  thanks_seen_at: number | null;
}

interface ReportLog {
  reporters: { reporter: Person; reported: number; solved: number; open: number; last_reported_at: number }[];
  totals: { reporters: number; reported: number; solved: number; open: number };
}

const SOURCE_LABEL = { server: 'Server', browser: 'Browser', learner: 'Learner report' } as const;
const CATEGORY_LABEL: Record<string, string> = { bug: 'Bug', content: 'Content', idea: 'Idea', feedback: 'Feedback', other: 'Other' };
const stamp = (t: number) => new Date(t * 1000).toLocaleString();
const who = (p: Person) => (p.email ? `${p.name} · ${p.email}` : p.name);

/** Errors and learner reports: open ones to fix, resolved ones as a record of who fixed what. */
function Errors({ open, resolved, onResolve, onShowResolved }: {
  open: ErrorItem[] | null;
  resolved: ErrorItem[] | null;
  onResolve: (id: string) => void;
  onShowResolved: () => void;
}) {
  const [tab, setTab] = useState<'open' | 'resolved'>('open');
  if (!open) return null;
  const items = tab === 'open' ? open : resolved;
  return (
    <Card className="pb-0">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Errors and reports</CardTitle>
            <CardDescription>Server exceptions, browser crashes and learner reports. A resolved error reopens if it happens again; a resolved learner report thanks its reporter.</CardDescription>
          </div>
          <div className="inline-flex gap-1" role="group" aria-label="Which reports">
            <Button size="sm" variant={tab === 'open' ? 'default' : 'outline'} aria-pressed={tab === 'open'} onClick={() => setTab('open')}>Open ({open.length})</Button>
            <Button size="sm" variant={tab === 'resolved' ? 'default' : 'outline'} aria-pressed={tab === 'resolved'} onClick={() => { setTab('resolved'); onShowResolved(); }}>Resolved</Button>
          </div>
        </div>
      </CardHeader>
      {!items ? <CardContent className="pb-4 text-sm text-muted-foreground">Loading…</CardContent> : items.length ? (
        <ul className="grid divide-y border-t">
          {items.map(e => (
            <li key={e.id} className="grid gap-1.5 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-semibold">
                  {SOURCE_LABEL[e.source]}{e.category ? ` · ${CATEGORY_LABEL[e.category] ?? e.category}` : ''}{e.count > 1 ? ` · ${e.count} times` : ''}
                </span>
                <span className="text-xs text-muted-foreground">{e.route || 'no page'} · {e.source === 'learner' ? `sent ${stamp(e.first_at)}` : `last ${stamp(e.last_at)}`}</span>
              </div>
              {e.reporter ? <p className="text-[13px]"><span className="text-muted-foreground">Reported by </span><span className="font-semibold">{who(e.reporter)}</span></p> : null}
              <p className="break-words">{e.message}</p>
              {e.stack ? (
                <details className="text-xs"><summary className="cursor-pointer text-muted-foreground">Stack{e.request_id ? ` (request ${e.request_id})` : ''}</summary><pre className="io-block mt-2 max-h-60 overflow-auto whitespace-pre-wrap">{e.stack}</pre></details>
              ) : null}
              {tab === 'open' ? (
                <div><Button size="sm" variant="outline" onClick={() => onResolve(e.id)}>{e.reporter ? 'Mark resolved and thank them' : 'Mark resolved'}</Button></div>
              ) : (
                <p className="text-[13px] text-muted-foreground">
                  Resolved{e.resolved_at ? ` ${stamp(e.resolved_at)}` : ''}{e.resolved_by ? ` by ${e.resolved_by.name}` : ''}
                  {e.reporter ? (e.thanks_seen_at ? ` · they saw the thank-you ${stamp(e.thanks_seen_at)}` : ' · thank-you not seen yet') : ''}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : <CardContent className="pb-4 text-sm text-muted-foreground">{tab === 'open' ? 'No open errors.' : 'Nothing resolved yet.'}</CardContent>}
    </Card>
  );
}

/** Who reports problems, and how many of their reports were solved. */
function ReportersLog({ log }: { log: ReportLog | null }) {
  if (!log) return null;
  const t = log.totals;
  return (
    <Card className="pb-0">
      <CardHeader>
        <CardTitle>Reporters</CardTitle>
        <CardDescription>{t.reported} learner reports from {t.reporters} {t.reporters === 1 ? 'person' : 'people'}: {t.solved} solved, {t.open} open.</CardDescription>
      </CardHeader>
      {log.reporters.length ? (
        <Table>
          <TableHeader><TableRow><TableHead className="pl-4">Learner</TableHead><TableHead className="text-right">Reported</TableHead><TableHead className="text-right">Solved</TableHead><TableHead className="text-right">Open</TableHead><TableHead className="pr-4 text-right">Last report</TableHead></TableRow></TableHeader>
          <TableBody>
            {log.reporters.map(r => (
              <TableRow key={r.reporter.id}>
                <TableCell className="pl-4 whitespace-normal"><span className="font-semibold">{r.reporter.name}</span>{r.reporter.email ? <span className="block text-xs text-muted-foreground">{r.reporter.email}</span> : null}</TableCell>
                <TableCell className="text-right tabular-nums">{r.reported}</TableCell>
                <TableCell className="text-right tabular-nums">{r.solved}</TableCell>
                <TableCell className="text-right tabular-nums">{r.open}</TableCell>
                <TableCell className="pr-4 text-right text-xs text-muted-foreground">{new Date(r.last_reported_at * 1000).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : <CardContent className="pb-4 text-sm text-muted-foreground">No learner reports yet.</CardContent>}
    </Card>
  );
}

const usd = (v: number) => `$${v < 10 ? v.toFixed(2) : Math.round(v).toLocaleString()}`;

/** Spend against the LLM budgets, estimated from token counts and the configured prices. */
function Costs({ costs }: { costs: AICosts | null }) {
  if (!costs) return null;
  const share = (spent: number, budget: number) => (budget ? Math.min(1, spent / budget) : 0);
  const rows = [
    { label: 'Today', spent: costs.today_usd, budget: costs.daily_budget_usd },
    { label: 'This month', spent: costs.month_usd, budget: costs.monthly_budget_usd },
  ];
  return (
    <Card className="pb-0">
      <CardHeader>
        <CardTitle>AI spend</CardTitle>
        <CardDescription>
          {costs.enabled ? 'AI is on.' : 'AI is switched off (SOCRAT_AI_ENABLED=false); learners get curated hints.'} Estimated from tokens at ${costs.prices.input_per_mtok} in / ${costs.prices.output_per_mtok} out per million. Each learner may spend {usd(costs.user_daily_budget_usd)} a day.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 pb-4">
        {rows.map(r => (
          <div key={r.label} className="grid grid-cols-[110px_minmax(0,1fr)_150px] items-center gap-3 text-sm">
            <span className="text-muted-foreground">{r.label}</span>
            <span className="relative h-3 rounded-full bg-muted" role="img" aria-label={`${r.label}: ${usd(r.spent)} of ${r.budget ? usd(r.budget) : 'no cap'}`}>
              <span className={`absolute inset-y-0 left-0 rounded-full ${share(r.spent, r.budget) >= 0.8 ? 'bg-attention' : 'bg-primary'}`} style={{ width: `${Math.max(1, 100 * share(r.spent, r.budget))}%` }} />
            </span>
            <span className="text-right tabular-nums">{usd(r.spent)} of {r.budget ? usd(r.budget) : 'no cap'}</span>
          </div>
        ))}
        <p className="text-sm text-muted-foreground">
          {costs.learners_this_month} learners used AI this month, {usd(costs.per_learner_usd)} each on average.
        </p>
      </CardContent>
      {Object.keys(costs.by_feature).length ? (
        <Table>
          <TableHeader><TableRow><TableHead className="pl-4">Feature</TableHead><TableHead className="text-right">Calls</TableHead><TableHead className="text-right">Tokens</TableHead><TableHead className="pr-4 text-right">Cost this month</TableHead></TableRow></TableHeader>
          <TableBody>
            {Object.entries(costs.by_feature).map(([feature, f]) => (
              <TableRow key={feature}>
                <TableCell className="pl-4 capitalize">{feature}</TableCell>
                <TableCell className="text-right tabular-nums">{f.calls.toLocaleString()}</TableCell>
                <TableCell className="text-right tabular-nums">{f.tokens.toLocaleString()}</TableCell>
                <TableCell className="pr-4 text-right tabular-nums">{usd(f.cost_usd)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </Card>
  );
}

/** p75 against the budget, with a word as well as a colour. */
function Vital({ value, unit }: { value?: { p75: number; ok: boolean }; unit: string }) {
  if (!value) return <span className="text-muted-foreground">—</span>;
  return (
    <span className={value.ok ? 'text-foreground' : 'font-semibold text-attention'}>
      <span className="tabular-nums">{value.p75.toLocaleString()}{unit}</span>{' '}
      <span className="text-xs">{value.ok ? 'good' : 'over'}</span>
    </span>
  );
}

const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`);

/** Single-series horizontal bars: magnitude by length, every value labelled, no legend needed. */
function Funnel({ steps }: { steps: Overview['funnel'] }) {
  const max = Math.max(1, ...steps.map(s => s.learners));
  return (
    <ol className="grid gap-2.5" aria-label="Activation funnel">
      {steps.map(s => (
        <li key={s.step} className="group grid grid-cols-[180px_minmax(0,1fr)_96px] items-center gap-3 text-sm" title={`${s.step}: ${s.learners} learners (${pct(s.share)} of sign-ups)`}>
          <span className="truncate text-muted-foreground">{s.step}</span>
          <span className="relative h-5">
            <span
              className="absolute inset-y-0 left-0 rounded-r-[4px] bg-primary transition-opacity group-hover:opacity-80"
              style={{ width: `${Math.max(1, (100 * s.learners) / max)}%` }}
            />
          </span>
          <span className="text-right tabular-nums">
            <span className="font-medium">{s.learners.toLocaleString()}</span>{' '}
            <span className="text-xs text-muted-foreground">{pct(s.share)}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Product metrics, AI spend and page speed. Loads its own data when the tab opens. */
function Metrics() {
  const [data, setData] = useState<Overview | null>(null);
  const [costs, setCosts] = useState<AICosts | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Overview>('/admin/overview').then(setData).catch(e => setError(explain(e)));
    api.get<AICosts>('/admin/ai-costs').then(setCosts).catch(() => undefined);
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const e = data.engagement;
  return (
    <div className="grid gap-6">
      <StatRow>
        <StatCard label="Activation (lesson + check within 24 h)" value={pct(data.activation.rate)} hint={`${data.activation.activated} of ${data.activation.signups} sign-ups`} />
        <StatCard label="Weekly active learners" value={e.weekly_active.toLocaleString()} hint={`${e.minutes_per_active_day} min per active day`} />
        <StatCard label="Tutor messages, last 7 days" value={e.tutor_messages_7d.toLocaleString()} hint={`${e.tutor_messages_per_active} per active learner`} />
        <StatCard label="Tutor reply ratings" value={`${e.tutor_ratings.up} / ${e.tutor_ratings.down}`} hint="helpful / not helpful" />
      </StatRow>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Card>
          <CardHeader><CardTitle>Activation funnel</CardTitle><CardDescription>Learners reaching each step, share of all sign-ups</CardDescription></CardHeader>
          <CardContent><Funnel steps={data.funnel} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Retention</CardTitle><CardDescription>Studied on day N after sign-up</CardDescription></CardHeader>
          <CardContent className="grid grid-cols-3 gap-3">
            {data.retention.map(r => (
              <div key={r.day} className="rounded-lg border p-3 text-center">
                <p className="text-xs text-muted-foreground">D{r.day}</p>
                <p className="text-2xl font-semibold tabular-nums">{pct(r.rate)}</p>
                <p className="text-[11px] text-muted-foreground">{r.retained}/{r.eligible}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="pb-0">
          <CardHeader><CardTitle>Checkpoints</CardTitle><CardDescription>Hardest first; a very low pass rate may mean missing teaching</CardDescription></CardHeader>
          {data.gates.length ? (
            <Table>
              <TableHeader><TableRow><TableHead className="pl-4">Module</TableHead><TableHead className="text-right">Learners</TableHead><TableHead className="text-right">Pass rate</TableHead><TableHead className="pr-4 text-right">Attempts each</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.gates.map(g => (
                  <TableRow key={g.module}>
                    <TableCell className="pl-4">{g.module}</TableCell>
                    <TableCell className="text-right tabular-nums">{g.learners}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(g.pass_rate)}</TableCell>
                    <TableCell className="pr-4 text-right tabular-nums">{g.attempts_per_learner}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <CardContent className="pb-4 text-sm text-muted-foreground">No checkpoint attempts yet.</CardContent>}
        </Card>
        <Card className="pb-0">
          <CardHeader><CardTitle>Questions to review</CardTitle><CardDescription>At least 20 answers and nearly everyone right, or nearly everyone wrong</CardDescription></CardHeader>
          {data.flagged_items.length ? (
            <Table>
              <TableHeader><TableRow><TableHead className="pl-4">Concept · item</TableHead><TableHead className="text-right">Answers</TableHead><TableHead className="text-right">Correct</TableHead><TableHead className="pr-4">Issue</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.flagged_items.map(i => (
                  <TableRow key={`${i.concept}-${i.item}`}>
                    <TableCell className="pl-4 whitespace-normal">{i.concept} · <span className="font-mono text-xs">{i.item}</span></TableCell>
                    <TableCell className="text-right tabular-nums">{i.answers}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(i.correct_rate)}</TableCell>
                    <TableCell className="pr-4">{i.issue}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <CardContent className="pb-4 text-sm text-muted-foreground">Nothing flagged yet — items need 20+ answers to judge.</CardContent>}
        </Card>
      </div>


      <Card className="pb-0">
        <CardHeader>
          <CardTitle>Page speed</CardTitle>
          <CardDescription>
            Real visits, last {data.vitals.days} days, 75th percentile. Budgets: LCP ≤ {data.vitals.budgets.LCP / 1000} s, INP ≤ {data.vitals.budgets.INP} ms, CLS ≤ {data.vitals.budgets.CLS}.
          </CardDescription>
        </CardHeader>
        {data.vitals.pages.length ? (
          <Table>
            <TableHeader><TableRow><TableHead className="pl-4">Page</TableHead><TableHead className="text-right">Samples</TableHead><TableHead className="text-right">LCP</TableHead><TableHead className="text-right">INP</TableHead><TableHead className="pr-4 text-right">CLS</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.vitals.pages.map(v => (
                <TableRow key={v.route}>
                  <TableCell className="pl-4 font-mono text-xs">{v.route}</TableCell>
                  <TableCell className="text-right tabular-nums">{v.samples}</TableCell>
                  <TableCell className="text-right"><Vital value={v.LCP} unit=" ms" /></TableCell>
                  <TableCell className="text-right"><Vital value={v.INP} unit=" ms" /></TableCell>
                  <TableCell className="pr-4 text-right"><Vital value={v.CLS} unit="" /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <CardContent className="pb-4 text-sm text-muted-foreground">No visits measured yet. Browsers report when a tab is hidden or closed.</CardContent>}
      </Card>

      {data.unhelpful_resources.length ? (
        <Card className="pb-0">
          <CardHeader><CardTitle>Resources learners found unhelpful</CardTitle></CardHeader>
          <Table>
            <TableHeader><TableRow><TableHead className="pl-4">Concept</TableHead><TableHead>Link</TableHead><TableHead className="text-right">Opens</TableHead><TableHead className="pr-4 text-right">Helpful / not</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.unhelpful_resources.map(r => (
                <TableRow key={`${r.concept}-${r.url}`}>
                  <TableCell className="pl-4">{r.concept}</TableCell>
                  <TableCell className="max-w-80 truncate"><a href={r.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4 hover:underline">{r.url}</a></TableCell>
                  <TableCell className="text-right tabular-nums">{r.opens}</TableCell>
                  <TableCell className="pr-4 text-right tabular-nums">{r.helpful} / {r.unhelpful}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
      <Costs costs={costs} />
    </div>
  );
}

/** Errors, learner reports and failed generations: what needs fixing. */
function Problems() {
  const [error, setError] = useState('');
  const [errorItems, setErrorItems] = useState<ErrorItem[] | null>(null);
  const [resolvedItems, setResolvedItems] = useState<ErrorItem[] | null>(null);
  const [reportLog, setReportLog] = useState<ReportLog | null>(null);
  const loadResolved = () => { api.get<{ items: ErrorItem[] }>('/admin/errors?status=resolved').then(r => setResolvedItems(r.items)).catch(() => undefined); };
  const loadLog = () => { api.get<ReportLog>('/admin/reports/log').then(setReportLog).catch(() => undefined); };
  const resolve = (id: string) => {
    api.post(`/admin/errors/${id}/resolve`, {})
      .then(() => { setErrorItems(items => items?.filter(e => e.id !== id) ?? null); setResolvedItems(null); loadLog(); })
      .catch(e => setError(explain(e)));
  };

  useEffect(() => {
    api.get<{ items: ErrorItem[] }>('/admin/errors').then(r => setErrorItems(r.items)).catch(e => setError(explain(e)));
    api.get<ReportLog>('/admin/reports/log').then(setReportLog).catch(() => undefined);
  }, []);

  return (
    <div className="grid gap-6">
      {error ? <ErrorNote message={error} /> : null}
      <FailedGenerations />
      <Errors open={errorItems} resolved={resolvedItems} onResolve={resolve} onShowResolved={loadResolved} />
      <ReportersLog log={reportLog} />
    </div>
  );
}

export default function Admin() {
  const allowed = useGuard('signed-in');
  const { profile } = useSession();

  // Not on the allow-list: the page does not exist, as far as they can tell.
  if (profile && !profile.admin) notFound();
  if (!allowed || !profile) return <Loading variant="list" />;

  return (
    <Page wide>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-[-0.02em]">Admin</h1>
        <p className="mt-1 text-sm text-muted-foreground">Accounts, problems, messages and metrics. Every change you make here is recorded in the audit log.</p>
      </header>

      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">Accounts</TabsTrigger>
          <TabsTrigger value="problems">Problems</TabsTrigger>
          <TabsTrigger value="messages">Messages</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="review">Review queue</TabsTrigger>
          <TabsTrigger value="courses">Courses</TabsTrigger>
          <TabsTrigger value="styles">Learning styles</TabsTrigger>
        </TabsList>
        <TabsContent value="users"><AdminUsers /></TabsContent>
        <TabsContent value="problems"><Problems /></TabsContent>
        <TabsContent value="messages"><Broadcast /></TabsContent>
        <TabsContent value="metrics"><Metrics /></TabsContent>
        <TabsContent value="review"><ReviewQueue /></TabsContent>
        <TabsContent value="courses"><CourseBuilder /></TabsContent>
        <TabsContent value="styles"><StyleLab /></TabsContent>
      </Tabs>
    </Page>
  );
}
