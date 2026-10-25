'use client';

import { useEffect, useState } from 'react';
import { notFound } from 'next/navigation';
import { Activity, Gauge, MessageSquare, ThumbsUp, Users } from 'lucide-react';
import { ApiError, api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { ErrorNote, Loading, Page, PageHeader, StatCard } from '@/components/common';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ReviewQueue } from '@/components/review-queue';
import { AdminUsers } from '@/components/admin-users';
import { useSession } from '@/lib/session';

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

interface ErrorItem { id: string; source: 'server' | 'browser' | 'learner'; message: string; route: string; count: number; first_at: number; last_at: number; request_id?: string; stack: string; reporter: string | null }

const SOURCE_LABEL = { server: 'Server', browser: 'Browser', learner: 'Learner report' } as const;

/** Open errors and learner reports, newest first; resolving hides one until it happens again. */
function Errors({ items, onResolve }: { items: ErrorItem[] | null; onResolve: (id: string) => void }) {
  if (!items) return null;
  return (
    <Card className="mt-6 gap-0 overflow-hidden pb-0">
      <CardHeader className="pb-3">
        <CardTitle>Errors and reports</CardTitle>
        <CardDescription>Server exceptions, browser crashes and "Report a problem" messages, grouped. A resolved error reopens if it happens again.</CardDescription>
      </CardHeader>
      {items.length ? (
        <ul className="grid divide-y border-t">
          {items.map(e => (
            <li key={e.id} className="grid gap-1.5 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-semibold">{SOURCE_LABEL[e.source]}{e.count > 1 ? ` · ${e.count} times` : ''}</span>
                <span className="text-xs text-muted-foreground">{e.route || 'no page'} · last {new Date(e.last_at * 1000).toLocaleString()}</span>
              </div>
              <p className="break-words">{e.message}</p>
              {e.stack ? (
                <details className="text-xs"><summary className="cursor-pointer text-muted-foreground">Stack{e.request_id ? ` (request ${e.request_id})` : ''}</summary><pre className="io-block mt-2 max-h-60 overflow-auto whitespace-pre-wrap">{e.stack}</pre></details>
              ) : null}
              <div><Button size="sm" variant="outline" onClick={() => onResolve(e.id)}>Mark resolved</Button></div>
            </li>
          ))}
        </ul>
      ) : <CardContent className="pb-6 text-sm text-muted-foreground">No open errors.</CardContent>}
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
    <Card className="mt-6 gap-0 overflow-hidden pb-0">
      <CardHeader className="pb-3">
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

export default function Admin() {
  const allowed = useGuard('signed-in');
  const { profile } = useSession();
  const [data, setData] = useState<Overview | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState('');
  const [costs, setCosts] = useState<AICosts | null>(null);
  const [errorItems, setErrorItems] = useState<ErrorItem[] | null>(null);
  const resolve = (id: string) => {
    api.post(`/admin/errors/${id}/resolve`, {}).then(() => setErrorItems(items => items?.filter(e => e.id !== id) ?? null)).catch(e => setError(explain(e)));
  };

  useEffect(() => {
    if (!allowed || !profile?.admin) return;
    api.get<Overview>('/admin/overview')
      .then(setData)
      .catch(e => (e instanceof ApiError && e.status === 403 ? setForbidden(true) : setError(explain(e))));
    api.get<AICosts>('/admin/ai-costs').then(setCosts).catch(() => undefined);
    api.get<{ items: ErrorItem[] }>('/admin/errors').then(r => setErrorItems(r.items)).catch(() => undefined);
  }, [allowed, profile?.admin]);

  // Not on the allow-list: the page does not exist, as far as they can tell.
  if (forbidden || (profile && !profile.admin)) notFound();
  if (!allowed || (!data && !error)) return <Loading variant="list" />;
  if (!data) return <Page><ErrorNote message={error} /></Page>;

  const e = data.engagement;
  return (
    <Page wide>
      <PageHeader eyebrow={<span className="inline-flex rounded-full border border-border-strong px-2.5 py-0.5 normal-case tracking-normal">Admin</span>} title="How learners are doing" description="Computed from learning data. No third-party tracking." />

      <Tabs defaultValue="metrics" className="gap-6">
        <TabsList>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="users">Users and plans</TabsTrigger>
          <TabsTrigger value="review">Review queue</TabsTrigger>
        </TabsList>
        <TabsContent value="users"><AdminUsers /></TabsContent>
        <TabsContent value="review"><ReviewQueue /></TabsContent>
        <TabsContent value="metrics">

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={<Gauge />} label="Activation (lesson + check within 24 h)" value={pct(data.activation.rate)} hint={`${data.activation.activated} of ${data.activation.signups} sign-ups`} />
        <StatCard icon={<Users />} label="Weekly active learners" value={e.weekly_active.toLocaleString()} hint={`${e.minutes_per_active_day} min per active day`} />
        <StatCard icon={<MessageSquare />} label="Tutor messages, last 7 days" value={e.tutor_messages_7d.toLocaleString()} hint={`${e.tutor_messages_per_active} per active learner`} />
        <StatCard icon={<ThumbsUp />} label="Tutor reply ratings" value={`${e.tutor_ratings.up} / ${e.tutor_ratings.down}`} hint="helpful / not helpful" />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card>
          <CardHeader><CardTitle>Activation funnel</CardTitle><CardDescription>Learners reaching each step, share of all sign-ups</CardDescription></CardHeader>
          <CardContent><Funnel steps={data.funnel} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="size-4" /> Retention</CardTitle><CardDescription>Studied on day N after sign-up</CardDescription></CardHeader>
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

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3"><CardTitle>Checkpoints</CardTitle><CardDescription>Hardest first; a very low pass rate may mean missing teaching</CardDescription></CardHeader>
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
          ) : <CardContent className="pb-6 text-sm text-muted-foreground">No checkpoint attempts yet.</CardContent>}
        </Card>
        <Card className="gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3"><CardTitle>Questions to review</CardTitle><CardDescription>At least 20 answers and nearly everyone right, or nearly everyone wrong</CardDescription></CardHeader>
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
          ) : <CardContent className="pb-6 text-sm text-muted-foreground">Nothing flagged yet — items need 20+ answers to judge.</CardContent>}
        </Card>
      </div>

      <Errors items={errorItems} onResolve={resolve} />
      <Costs costs={costs} />

      <Card className="mt-6 gap-0 overflow-hidden pb-0">
        <CardHeader className="pb-3">
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
        ) : <CardContent className="pb-6 text-sm text-muted-foreground">No visits measured yet. Browsers report when a tab is hidden or closed.</CardContent>}
      </Card>

      {data.unhelpful_resources.length ? (
        <Card className="mt-6 gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3"><CardTitle>Resources learners found unhelpful</CardTitle></CardHeader>
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
        </TabsContent>
      </Tabs>
    </Page>
  );
}
