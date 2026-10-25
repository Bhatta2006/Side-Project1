'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, MoreHorizontal, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { ApiError, api, explain, stream } from '@/lib/api';
import { useGuard } from '@/lib/session';
import type { VisualArtifact } from '@/lib/explainer';
import { cn } from '@/lib/utils';
import { Loading, Page } from '@/components/common';
import { ErrorState, SuccessLine } from '@/components/socrat/states';
import { StatusIcon } from '@/components/socrat/status';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';

const VisualExplainer = dynamic(() => import('@/components/visual-explainer'), { ssr: false, loading: () => <Skeleton className="h-[560px] w-full rounded-card" /> });
type Level = VisualArtifact['level'];
interface Suggestion { id: string; title: string; reason: string }
interface Saved { id: string; title: string; created_at: number }

const LEVELS: [Level, string][] = [['simple', 'Simple'], ['standard', 'Standard'], ['deep', 'Go deep']];
// The real phases the generator reports. Repairing appears only when it happens.
const PHASES = [
  ['generating', 'Building the visual'],
  ['checking', 'Checking that it runs'],
  ['reviewing', 'Reviewing it'],
  ['repairing', 'Repairing it'],
] as const;
// Errors where retrying cannot help right now.
const NO_RETRY = new Set(['upgrade_required', 'playground_day_limit', 'playground_daily_limit', 'playground_unavailable', 'playground_sandbox_unavailable']);

function savedDate(seconds: number) {
  return new Date(seconds * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function SavedList({ saved, busy, onOpen }: { saved: Saved[]; busy: boolean; onOpen: (id: string) => void }) {
  if (!saved.length) return <p className="text-[15px] text-muted-foreground">Visuals you generate are saved here.</p>;
  return (
    <div className="grid gap-3">
      <ul className="grid gap-2">
        {saved.map(item => (
          <li key={item.id}>
            <button type="button" disabled={busy} onClick={() => onOpen(item.id)} aria-label={`Open ${item.title}`} className="flex min-h-14 w-full items-center justify-between gap-3 rounded-[16px] bg-raised px-4 py-3 text-left transition-colors hover:bg-[color-mix(in_srgb,var(--raised),var(--foreground)_6%)] disabled:opacity-50">
              <span className="min-w-0">
                <span className="block truncate font-semibold">{item.title}</span>
                <span className="block text-[13px] text-muted-foreground">{savedDate(item.created_at)}</span>
              </span>
              <span className="text-sm font-semibold underline underline-offset-4" aria-hidden="true">Open</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="text-[13px] text-muted-foreground">Only you can see saved visuals.</p>
    </div>
  );
}

/** Generated text arrives hard-wrapped and indented; rebuild real paragraphs so it reflows. */
function Transcript({ text, className }: { text: string; className?: string }) {
  const paragraphs = text.split(/\n\s*\n/).map(p => p.replace(/\s*\n\s*/g, ' ').trim()).filter(Boolean);
  return <div className={cn('grid gap-3 leading-7', className)}>{paragraphs.map((p, i) => <p key={i}>{p}</p>)}</div>;
}

export default function PlaygroundPage() {
  const allowed = useGuard('active');
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [prompt, setPrompt] = useState('');
  const [level, setLevel] = useState<Level>('standard');
  const [artifact, setArtifact] = useState<VisualArtifact | null>(null);
  const [previewVersion, setPreviewVersion] = useState(0);
  const [fromSaved, setFromSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState('generating');
  const [seen, setSeen] = useState<string[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [failure, setFailure] = useState<{ code: string; message: string } | null>(null);
  const [notice, setNotice] = useState('');
  const [reportOpen, setReportOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [reporting, setReporting] = useState(false);
  const [panel, setPanel] = useState<'explanation' | 'saved'>('explanation');
  const [panelOpen, setPanelOpen] = useState(true);
  const [mac, setMac] = useState(false);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const cancelReport = useRef<HTMLButtonElement>(null);
  const explanation = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    setMac(/Mac|iPhone|iPad/.test(navigator.platform));
    setPanelOpen(window.matchMedia('(min-width: 1280px)').matches);
  }, []);
  useEffect(() => {
    if (!allowed) return;
    let active = true;
    const params = new URLSearchParams(window.location.search);
    const concept = params.get('concept');
    const sample = params.get('prompt'); // a lesson code sample, prefilled but never run for the learner
    if (sample) setPrompt(p => p || sample.slice(0, 4000));
    Promise.all([
      api.get<{ suggestions: Suggestion[]; concepts?: { id: string; title: string }[] }>('/playground'),
      api.get<{ items: Saved[] }>('/playground/artifacts'),
    ]).then(([overview, history]) => {
      if (!active) return;
      setSuggestions(overview.suggestions);
      setSaved(history.items);
      // A lesson link passes its skill as a request topic only, never as a preset lesson.
      const title = concept ? overview.concepts?.find(c => c.id === concept)?.title : undefined;
      if (title) setPrompt(p => p || title);
    }).catch(e => { if (active) setFailure({ code: '', message: explain(e) }); });
    return () => { active = false; };
  }, [allowed]);
  useEffect(() => {
    if (artifact) { resultHeading.current?.focus({ preventScroll: true }); resultHeading.current?.scrollIntoView({ block: 'start' }); }
  }, [artifact]);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    setElapsed(0);
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  const abort = useRef<AbortController | null>(null);
  const generate = useCallback(async (request: string, depth: Level) => {
    abort.current = new AbortController();
    setBusy(true); setArtifact(null); setFailure(null); setNotice(''); setPhase('generating'); setSeen(['generating']); setFromSaved(false);
    setPrompt(request); setLevel(depth);
    try {
      let complete = false;
      for await (const event of stream('/playground/generate', { prompt: request.trim(), level: depth, request_id: crypto.randomUUID() }, abort.current.signal)) {
        if (event.event === 'progress') {
          const next = String(event.data.phase);
          setPhase(next);
          setSeen(list => (list.includes(next) ? list : [...list, next]));
        } else if (event.event === 'error') throw new ApiError(502, String(event.data.code));
        else if (event.event === 'ready') {
          const result = event.data.artifact as unknown as VisualArtifact;
          setArtifact(result);
          setSaved(rows => [{ id: result.id, title: result.title, created_at: result.created_at }, ...rows.filter(row => row.id !== result.id)].slice(0, 20));
          complete = true;
        }
      }
      if (!complete) throw new Error('Generation ended before the visual was ready');
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') setNotice('Cancelled. Your question is still here.');
      else setFailure({ code: e instanceof ApiError ? e.code : '', message: explain(e) });
    } finally { setBusy(false); }
  }, []);

  async function openSaved(id: string) {
    setFailure(null); setNotice('');
    try {
      const result = await api.get<VisualArtifact>(`/playground/artifacts/${id}`);
      setPreviewVersion(value => value + 1); setArtifact(result); setPrompt(result.request); setLevel(result.level); setFromSaved(true);
    } catch (e) { setFailure({ code: e instanceof ApiError ? e.code : '', message: explain(e) }); }
  }
  async function report() {
    if (!artifact) return;
    setReporting(true);
    try {
      await api.post(`/playground/artifacts/${artifact.id}/report`, { reason: reason.trim() });
      setSaved(rows => rows.filter(row => row.id !== artifact.id)); setArtifact(null); setReportOpen(false); setReason('');
      setNotice('Reported. This visual was removed from your saved visuals.');
    } catch (e) { setFailure({ code: e instanceof ApiError ? e.code : '', message: explain(e) }); }
    finally { setReporting(false); }
  }
  function startOver(keep: boolean) {
    setArtifact(null); setFailure(null); setNotice('');
    if (!keep) setPrompt('');
    requestAnimationFrame(() => input.current?.focus());
  }
  function readExplanation() {
    setPanel('explanation'); setPanelOpen(true);
    if (explanation.current) explanation.current.open = true;
    document.getElementById('explanation-panel')?.scrollIntoView({ block: 'start' });
  }

  if (!allowed || (!suggestions && !failure)) return <Loading label="Loading the playground" />;
  const weak = (suggestions ?? []).filter(s => !s.reason.startsWith('Explore the next topic'));
  const canGenerate = prompt.trim().length >= 5 && !busy;
  const validation = failure?.code === 'playground_generation_invalid';
  const retryable = failure && failure.code && !NO_RETRY.has(failure.code);

  // Result: the request bar, a dominant canvas and the explanation panel.
  if (artifact) {
    return (
      <Page wide>
        <h1 className="sr-only">Playground</h1>
        <div className="sticky top-16 z-20 -mx-4 mb-5 flex flex-wrap items-center gap-2 border-b bg-background px-4 py-3 sm:-mx-6 sm:px-6 lg:-mx-10 lg:px-10">
          <p data-testid="request-bar" className="line-clamp-2 min-w-0 flex-1 basis-60 rounded-full border border-border-strong px-4 py-2 text-[15px] sm:line-clamp-1" title={artifact.request}>
            <span className="sr-only">Your question: </span>{artifact.request}
          </p>
          <Button variant="outline" size="sm" onClick={() => startOver(true)}>Edit request</Button>
          <Button variant="outline" size="sm" onClick={() => startOver(false)}>New question</Button>
          <Button variant="outline" size="sm" disabled={busy} onClick={() => void generate(artifact.request, 'simple')} title="Creates a new, simpler visual">Explain more simply</Button>
          <Button variant="outline" size="sm" disabled={busy} onClick={() => void generate(artifact.request, 'deep')} title="Creates a new, deeper visual">Go deeper</Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="ghost" size="icon-sm" aria-label="More actions"><MoreHorizontal /></Button></DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => { setReportOpen(true); setReason(''); }}>Report an issue</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <p className="basis-full text-[13px] text-muted-foreground">Explain more simply and Go deeper each create a new visual from the same question.</p>
        </div>

        <div className={cn('grid gap-6', panelOpen && 'xl:grid-cols-[minmax(0,1fr)_360px]')}>
          <section aria-labelledby="visual-heading" className="grid min-w-0 content-start gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 flex-wrap items-center gap-3">
                <h2 id="visual-heading" ref={resultHeading} tabIndex={-1} className="type-display-m scroll-mt-40">{artifact.title}</h2>
                <Badge>AI-generated</Badge>
              </div>
              <Button variant="ghost" size="sm" className="hidden lg:inline-flex" onClick={() => setPanelOpen(v => !v)} aria-expanded={panelOpen} aria-controls="explanation-panel">
                {panelOpen ? <PanelRightClose data-icon="inline-start" /> : <PanelRightOpen data-icon="inline-start" />} {panelOpen ? 'Hide panel' : 'Explanation and saved'}
              </Button>
            </div>
            <VisualExplainer
              key={`${artifact.id}:${previewVersion}`}
              artifact={artifact}
              onExplain={readExplanation}
              onReport={() => { setReportOpen(true); setReason(''); }}
              onBack={fromSaved ? () => { setPanel('saved'); setPanelOpen(true); setArtifact(null); } : undefined}
            />
          </section>

          {/* Desktop panel: Explanation and Saved. Phones get accordions. */}
          <aside id="explanation-panel" className={cn('hidden content-start gap-3 lg:grid', !panelOpen && 'lg:hidden')} aria-label="Explanation and saved visuals">
            <div className="inline-flex h-12 w-fit items-center gap-1 rounded-full bg-raised p-1" role="tablist" aria-label="Panel">
              {(['explanation', 'saved'] as const).map(id => (
                <button key={id} type="button" role="tab" aria-selected={panel === id} onClick={() => setPanel(id)} className={cn('inline-flex h-full items-center rounded-full border border-transparent px-4 text-sm font-medium text-muted-foreground', panel === id && 'border-border bg-card font-bold text-foreground')}>
                  {id === 'explanation' ? 'Explanation' : `Saved (${saved.length})`}
                </button>
              ))}
            </div>
            <div className="rounded-card border bg-card p-5" role="tabpanel">
              {panel === 'explanation' ? (
                <>
                  <h3 className="mb-2 font-display text-lg font-bold tracking-[-0.02em]">Explanation</h3>
                  <Transcript text={artifact.transcript} className="text-[15px]" />
                  <p className="mt-4 text-[13px] text-muted-foreground">Exploring does not count as practice or mastery.</p>
                </>
              ) : <SavedList saved={saved} busy={busy} onOpen={id => void openSaved(id)} />}
            </div>
          </aside>
          <div className="grid gap-3 lg:hidden">
            <details ref={explanation} className="group rounded-card border bg-card">
              <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 px-5 font-semibold [&::-webkit-details-marker]:hidden">Explanation <ChevronDown className="size-5 transition-transform group-open:rotate-180" aria-hidden="true" /></summary>
              <Transcript text={artifact.transcript} className="px-5 pb-5 text-[15px]" />
            </details>
            <details className="group rounded-card border bg-card">
              <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 px-5 font-semibold [&::-webkit-details-marker]:hidden">Saved ({saved.length}) <ChevronDown className="size-5 transition-transform group-open:rotate-180" aria-hidden="true" /></summary>
              <div className="px-5 pb-5"><SavedList saved={saved} busy={busy} onOpen={id => void openSaved(id)} /></div>
            </details>
          </div>
        </div>
        <ReportDialog open={reportOpen} setOpen={setReportOpen} reason={reason} setReason={setReason} reporting={reporting} onSend={() => void report()} cancelRef={cancelReport} />
      </Page>
    );
  }

  // Generating: the real phases, an elapsed counter, no fake progress.
  if (busy) {
    const visible = PHASES.filter(([id]) => id !== 'repairing' || seen.includes('repairing'));
    const order = visible.map(([id]) => id as string);
    const at = order.indexOf(phase);
    return (
      <Page wide>
        <h1 className="sr-only">Playground</h1>
        <p className="mb-5 line-clamp-2 rounded-full border border-border-strong px-4 py-2 text-[15px]"><span className="sr-only">Your question: </span>{prompt}</p>
        <section className="grid min-h-[max(420px,60dvh)] place-items-center rounded-card border bg-card p-8" aria-labelledby="generating-heading">
          <div className="w-full max-w-md">
            <h2 id="generating-heading" className="type-display-m">Building your visual</h2>
            <ol className="mt-6 grid gap-4" aria-label="Generation steps">
              {visible.map(([id, label], i) => {
                const state = i < at ? 'done' : i === at ? 'active' : 'pending';
                return (
                  <li key={id} className="flex items-center gap-3">
                    {state === 'done' ? (
                      <span className="grid size-7 place-items-center rounded-full bg-primary text-primary-foreground" aria-hidden="true"><svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg></span>
                    ) : state === 'active' ? (
                      <svg viewBox="0 0 24 24" className="size-7 animate-spin [animation-duration:2.4s]" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="var(--border)" strokeWidth="2.5" /><path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="var(--primary)" strokeWidth="2.5" strokeLinecap="round" /></svg>
                    ) : <StatusIcon status="not_seen" size={28} />}
                    <span className={cn('text-[17px]', state === 'active' ? 'font-bold' : state === 'pending' ? 'text-muted-foreground' : '')}>{label}</span>
                    <span className="ml-auto text-[13px] text-muted-foreground">{state === 'done' ? 'Done' : state === 'active' ? 'In progress' : ''}</span>
                  </li>
                );
              })}
            </ol>
            <p className="sr-only" role="status" aria-live="polite">{visible.find(([id]) => id === phase)?.[1] ?? 'Building the visual'}</p>
            <p className="mt-6 text-[15px] text-muted-foreground tabular-nums">This usually takes a minute or two. {elapsed}s so far.</p>
            <Button variant="outline" className="mt-4" onClick={() => abort.current?.abort()}>Cancel</Button>
          </div>
        </section>
      </Page>
    );
  }

  // Compose (first use, new question, edit) and generation errors, with the request kept.
  return (
    <Page wide>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-10">
        <div className="min-w-0">
          <h1 className="type-display-l">Ask about a concept.</h1>
          <p className="mt-3 max-w-2xl text-base text-muted-foreground">Socrat builds an interactive explanation from your question. Add your own values if you want to test them.</p>

          {failure ? (
            <ErrorState
              className="mt-6"
              title={validation ? 'The visual did not pass its checks.' : 'The visual could not be generated.'}
              message={failure.message}
              actions={
                <>
                  {failure.code === 'upgrade_required' || failure.code === 'playground_day_limit' ? <Button asChild size="sm"><Link href="/pricing">See plans</Link></Button> : null}
                  {retryable ? <Button size="sm" onClick={() => void generate(prompt, level)} disabled={!canGenerate}>Try again</Button> : null}
                  {validation ? <Button size="sm" variant="outline" onClick={() => void generate(prompt, 'simple')} disabled={!canGenerate}>Simplify the request</Button> : null}
                  {retryable ? <Button size="sm" variant="outline" onClick={() => input.current?.focus()}>Edit request</Button> : null}
                </>
              }
            />
          ) : null}
          {notice ? <SuccessLine className="mt-6">{notice}</SuccessLine> : null}

          <div className="mt-6 grid gap-4 rounded-card border bg-card p-5 lg:p-6">
            <label htmlFor="visual-request" className="font-semibold">Your question</label>
            <Textarea
              ref={input}
              id="visual-request"
              value={prompt}
              maxLength={4000}
              rows={3}
              className="min-h-28"
              aria-describedby="visual-request-help"
              placeholder="For example: how does binary search narrow the range? Let me change the target."
              onChange={event => setPrompt(event.target.value)}
              onKeyDown={event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && canGenerate) { event.preventDefault(); void generate(prompt, level); } }}
            />
            <p id="visual-request-help" className="text-[13px] text-muted-foreground tabular-nums">{prompt.length} of 4000 characters. Press {mac ? '⌘ + Enter' : 'Ctrl + Enter'} to generate.</p>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="inline-flex h-12 items-center gap-1 rounded-full bg-raised p-1" role="radiogroup" aria-label="Explanation depth">
                {LEVELS.map(([id, label]) => (
                  <button key={id} type="button" role="radio" aria-checked={level === id} onClick={() => setLevel(id)} className={cn('inline-flex h-full min-h-10 items-center rounded-full border border-transparent px-4 text-sm font-medium text-muted-foreground', level === id && 'border-border bg-card font-bold text-foreground')}>
                    {label}
                  </button>
                ))}
              </div>
              <Button size="lg" disabled={!canGenerate} onClick={() => void generate(prompt, level)}>Generate<ArrowCircle /></Button>
            </div>
            {prompt.trim().length < 5 ? <p className="text-[13px] text-muted-foreground">Write at least a few words to generate.</p> : null}
          </div>

          {weak.length ? (
            <section className="mt-6" aria-labelledby="review-heading">
              <h2 id="review-heading" className="type-label mb-3 text-muted-foreground">From your review list</h2>
              <div className="flex flex-wrap gap-2">
                {weak.map(item => (
                  <button key={item.id} type="button" title={item.reason} onClick={() => { setPrompt(item.title); input.current?.focus(); }} className="inline-flex h-11 items-center rounded-full border border-border-strong px-4 text-[15px] font-semibold transition-colors hover:bg-raised">
                    {item.title}
                  </button>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <aside className="grid content-start gap-4" aria-label="About the playground">
          <div className="rounded-card bg-raised p-5 text-[15px]">
            Generated visuals can contain mistakes. Compare them with your lesson. Exploring does not count as practice or mastery.
          </div>
          <section className="rounded-card border bg-card p-5" aria-labelledby="recent-heading">
            <h2 id="recent-heading" className="mb-3 font-display text-lg font-bold tracking-[-0.02em]">Recent visuals</h2>
            <SavedList saved={saved.slice(0, 3)} busy={busy} onOpen={id => void openSaved(id)} />
            {saved.length > 3 ? (
              <details className="group mt-3">
                <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 text-sm font-semibold underline underline-offset-4 [&::-webkit-details-marker]:hidden">All saved visuals ({saved.length})</summary>
                <div className="mt-2"><SavedList saved={saved.slice(3)} busy={busy} onOpen={id => void openSaved(id)} /></div>
              </details>
            ) : null}
          </section>
        </aside>
      </div>
      <ReportDialog open={reportOpen} setOpen={setReportOpen} reason={reason} setReason={setReason} reporting={reporting} onSend={() => void report()} cancelRef={cancelReport} />
    </Page>
  );
}

function ReportDialog({ open, setOpen, reason, setReason, reporting, onSend, cancelRef }: {
  open: boolean; setOpen: (open: boolean) => void; reason: string; setReason: (value: string) => void; reporting: boolean; onSend: () => void; cancelRef: React.RefObject<HTMLButtonElement | null>;
}) {
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent onOpenAutoFocus={event => { event.preventDefault(); cancelRef.current?.focus(); }}>
        <DialogHeader>
          <DialogTitle>Report this visual</DialogTitle>
          <DialogDescription>Reporting removes this visual from your saved visuals. Tell us what was wrong or did not work.</DialogDescription>
        </DialogHeader>
        <label htmlFor="visual-report" className="font-semibold">What went wrong?</label>
        <Textarea id="visual-report" value={reason} onChange={event => setReason(event.target.value)} maxLength={1000} rows={4} aria-describedby="visual-report-help" />
        <p id="visual-report-help" className="-mt-3 text-[13px] text-muted-foreground">At least a few words.</p>
        <DialogFooter>
          <Button ref={cancelRef} variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button disabled={reporting || reason.trim().length < 5} aria-busy={reporting} onClick={onSend}>{reporting ? 'Reporting' : 'Send report'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
