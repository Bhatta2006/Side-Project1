'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { ArrowLeft, Check, ChevronDown, Cloud, CloudOff, Loader2, Play, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { ApiError, api, explain } from '@/lib/api';
import { reportError } from '@/lib/report-error';
import { useGuard, useSession } from '@/lib/session';
import { LANGUAGE_LABEL, NAME, activityHref, conceptHref, formatStamp } from '@/lib/routes';
import type { Case, Language, ProblemView, Submission } from '@/lib/types';
import { cn } from '@/lib/utils';
import { useEditorPrefs } from '@/lib/editor-prefs';
import { readLocalDraft, writeLocalDraft } from '@/lib/local-drafts';
import { runInBrowser, warm, type RunnerStage } from '@/lib/runner';
import CodeEditor from '@/components/code-editor';
import { parseDiagnostics } from '@/components/code-editor/diagnostics';
import Markdown from '@/components/markdown';
import { Difficulty, ErrorNote, Loading } from '@/components/common';
import { AttentionIcon, LockedState } from '@/components/socrat/states';
import { useExamGuard, useSocMoment } from '@/components/socrat/soc-moment';
import { StatusIcon } from '@/components/socrat/status';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';

// The tutor panel opens on demand: load it after hydration so it stays out of first-load JS.
// Only the 'Visual' tab needs it, so it loads when that tab is opened.
const ConceptVisual = dynamic(() => import('@/components/socrat/concept-visual').then(m => m.ConceptVisual), { ssr: false });
const Assistant = dynamic(() => import('@/components/assistant'), { ssr: false });
// Per-test results appear only after a run, so they load then.
// The editor settings popover opens rarely; a same-size placeholder holds its place until it loads.
const EditorSettings = dynamic(() => import('@/components/editor-settings'), {
  ssr: false,
  loading: () => <span className="inline-block size-11" aria-hidden="true" />,
});
const CaseResults = dynamic(() => import('@/components/socrat/case-results'), { ssr: false });

type Tone = 'success' | 'info' | 'error' | 'warning';
const VERDICT: Record<string, { label: string; tone: Tone }> = {
  accepted: { label: 'Accepted', tone: 'success' },
  ran: { label: 'Ran', tone: 'info' },
  executed: { label: 'Ran', tone: 'info' },
  wrong_answer: { label: 'Wrong answer', tone: 'error' },
  compile_error: { label: 'Compilation error', tone: 'error' },
  runtime_error: { label: 'Runtime error', tone: 'error' },
  timeout: { label: 'Time limit exceeded', tone: 'warning' },
  output_limit: { label: 'Output limit exceeded', tone: 'warning' },
  memory_limit: { label: 'Memory limit exceeded', tone: 'warning' },
  system_error: { label: 'Runner error. This is not your code; try again', tone: 'warning' },
};
const STAGE_LABEL: Record<string, string> = {
  loading: 'Starting the runner in your browser',
  compiling: 'Compiling in your browser',
  running: 'Running your code in your browser',
};
const TONE_CLASS: Record<Tone, string> = {
  success: 'border-foreground',
  info: 'border-border-strong',
  error: 'border-attention',
  warning: 'border-attention',
};

/** Passed: a check in a cream circle. Anything else: the coral triangle. */
function CaseMark({ ok }: { ok: boolean }) {
  return ok
    ? <span className="grid size-6 flex-none place-items-center rounded-full bg-cream text-cream-foreground"><Check className="size-3.5" strokeWidth={2.5} aria-hidden="true" /></span>
    : <AttentionIcon size={22} />;
}

export default function Problem() {
  const allowed = useGuard('signed-in');
  const { profile, features } = useSession();
  const { resolvedTheme } = useTheme();
  const params = useParams<{ id: string }>();
  const problemId = params.id;
  const [language, setLanguage] = useState<Language | null>(null);
  const [problem, setProblem] = useState<ProblemView | null>(null);
  const [source, setSource] = useState('');
  const [runtimes, setRuntimes] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<Submission | null>(null);
  const [pending, setPending] = useState<'run' | 'submit' | null>(null);
  const [stage, setStage] = useState<RunnerStage | null>(null);
  const [customInput, setCustomInput] = useState('');
  const [useCustom, setUseCustom] = useState(false);
  const [saved, setSaved] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [error, setError] = useState('');
  // Opened from a weekly exam (?assessment=<id>): no tutor, no copy and paste, and the way
  // back after a submission leads to the exam, not to Today.
  const [examId, setExamId] = useState<string | null>(null);
  // Opened from a transfer check (?check=/transfer/...): the same rules, and the way back is the check.
  const [checkBack, setCheckBack] = useState<string | null>(null);
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const id = query.get('assessment');
    setExamId(id && /^[A-Za-z0-9-]{8,64}$/.test(id) ? id : null);
    const back = query.get('check');
    setCheckBack(back && /^\/transfer\/[a-z0-9/-]{1,160}$/.test(back) ? back : null);
  }, []);
  const proving = Boolean(examId || checkBack);
  const examGuard = useExamGuard(proving);
  const soc = useSocMoment();
  const attempted = useRef(false);
  const canExecuteRef = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef({ source: '', language: null as Language | null });
  latest.current = { source, language };

  const lang = language ?? profile?.enrollment?.language ?? 'python';

  const load = useCallback(() => {
    setError('');
    api
      .get<ProblemView>(`/problems/${problemId}?language=${lang}`)
      .then(p => {
        setProblem(p);
        // Edits that never reached the server (offline, closed tab) win over the server copy.
        const local = readLocalDraft(problemId, lang);
        if (local && !local.synced && local.source !== (p.draft ?? p.starter)) {
          setSource(local.source);
          latest.current = { source: local.source, language: lang };
          setSaved('unsaved');
          saveTimer.current = setTimeout(() => saveDraftRef.current(), 300);
        } else {
          setSource(p.draft ?? p.starter);
          setSaved('saved');
        }
      })
      .catch(e => setError(explain(e)));
  }, [problemId, lang]);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  useEffect(() => { if (allowed) void warm(lang); }, [allowed, lang]);
  useEffect(() => {
    if (!allowed) return;
    api.get<{ languages: Record<string, boolean> }>('/runtimes').then(r => setRuntimes(r.languages)).catch(() => undefined);
  }, [allowed]);

  const saveDraft = useCallback(async () => {
    const { source: text, language: l } = latest.current;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaved('saving');
    try {
      await api.put(`/problems/${problemId}/draft`, { source: text, language: l ?? lang });
      writeLocalDraft(problemId, l ?? lang, text, true);
      setSaved('saved');
    } catch {
      setSaved('unsaved');
    }
  }, [problemId, lang]);
  const saveDraftRef = useRef(saveDraft);
  saveDraftRef.current = saveDraft;

  const [prefs, setPrefs] = useEditorPrefs();
  const workspace = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLElement>(null);
  // The results sit below the editor; bring them into view when a run finishes.
  useEffect(() => {
    if (result?.status === 'done') resultsRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [result?.id, result?.status]);

  /** Drag (or arrow keys) on the divider resizes the statement and editor panes. */
  function startResize(event: React.PointerEvent<HTMLDivElement>) {
    const box = workspace.current?.getBoundingClientRect();
    if (!box) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const move = (e: PointerEvent) => setPrefs({ split: (e.clientX - box.left) / box.width });
    const stop = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', stop); };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
  }

  function resetToStarter() {
    if (!problem) return;
    setSource(problem.starter);
    // Save now, not after the typing debounce: the blur that opened this dialog may have
    // just saved the old code, and a quick reload must not bring it back.
    latest.current = { ...latest.current, source: problem.starter };
    void saveDraft();
    toast('Code reset to the starter template.');
  }

  function onChange(next: string) {
    setSource(next);
    setSaved('unsaved');
    writeLocalDraft(problemId, lang, next, false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(saveDraft, 1500);
  }
  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current); }, []);

  async function execute(mode: 'run' | 'submit') {
    if (pending) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setPending(mode);
    setError('');
    setResult(null);
    try {
      const body: Record<string, unknown> = { source, language: lang };
      if (mode === 'run' && useCustom) body.custom_input = customInput;
      let job = await api.post<Submission>(`/problems/${problemId}/${mode}`, body);
      setSaved('saved');
      writeLocalDraft(problemId, lang, source, true);
      attempted.current = true;
      if (job.browser) {
        const cases = await runInBrowser(job.browser, source, setStage);
        job = await api.post<Submission>(`/submissions/${job.id}/browser-result`, { token: job.browser.token, cases });
      }
      const started = Date.now();
      while (job.status !== 'done' && Date.now() - started < 90_000) {
        await new Promise(r => setTimeout(r, job.status === 'queued' ? 600 : 400));
        job = await api.get<Submission>(`/submissions/${job.id}`);
        setResult(job);
      }
      setResult(job);
      if (job.status !== 'done') setError('The runner is taking longer than usual. Your submission is saved; check back in a moment.');
      if (mode === 'submit' && job.verdict === 'accepted') {
        setProblem(p => (p ? { ...p, solved: true } : p));
        soc.show('celebrate');
      }
      if (job.status === 'done') {
        setProblem(p => p && { ...p, history: [{ id: job.id, mode: job.mode, verdict: job.verdict, status: job.status, passed: job.passed, total: job.total, at: job.created_at }, ...p.history].slice(0, 10) });
      }
    } catch (e) {
      // Runner failures in the browser (not API refusals) are ours to fix.
      if (!(e instanceof ApiError)) reportError('runner', e);
      setError(explain(e));
    } finally {
      setPending(null);
      setStage(null);
    }
  }

  const diagnostics = useMemo(() => {
    if (!result?.cases?.length) return [];
    const text = result.cases.map(c => c.stderr ?? '').filter(Boolean).join('\n');
    return parseDiagnostics(text);
  }, [result]);

  if (!allowed || (!problem && !error)) return <Loading variant="workspace" label="Loading the problem" />;
  if (!problem) return <div className="mx-auto max-w-3xl p-6"><ErrorNote message={error} retry={load} /></div>;

  const runtimeKnown = Object.keys(runtimes).length > 0;
  const runtimeReady = !runtimeKnown || runtimes[lang];
  const canExecute = Boolean(features?.code_execution) && runtimeReady && !problem.locked;
  canExecuteRef.current = canExecute && !pending;
  const verdict = result?.status === 'done'
    ? (result.verdict === 'compile_error' && lang === 'python' ? { label: 'Syntax error', tone: 'error' as Tone } : VERDICT[result.verdict] ?? { label: result.verdict, tone: 'info' as Tone })
    : null;

  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 pt-4 pb-40 sm:px-6 md:pb-10 lg:px-10">
      {examGuard}
      {soc.element}
      {proving ? (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-[16px] border border-border-strong px-4 py-2.5 text-[15px]">
          <span className="font-semibold">{examId ? 'Weekly exam coding task' : 'Transfer check'}. No tutor, no copy and paste.</span>
          <Button asChild size="sm" variant="outline"><Link href={examId ? '/assessments' : checkBack ?? '/plan'}>{examId ? 'Back to the exam' : 'Back to the check'}</Link></Button>
        </div>
      ) : null}
      <header className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 border-b pb-4">
        <Link href={examId ? '/assessments' : conceptHref(problem.concept.id)} transitionTypes={['nav-back']} aria-label={examId ? 'Back to the exam' : `Back to ${problem.concept.title}`} className="grid size-11 flex-none place-items-center rounded-full border border-border-strong transition-colors hover:bg-raised">
          <ArrowLeft className="size-5" strokeWidth={1.5} aria-hidden="true" />
        </Link>
        <h1 id="problem-title" className="min-w-0 flex-1 basis-40 font-display sm:truncate text-2xl font-semibold tracking-[-0.03em]">{problem.title}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Difficulty level={problem.difficulty} />
          <Badge asChild><Link href={conceptHref(problem.concept.id)}>{problem.concept.title}</Link></Badge>
          {problem.solved ? <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold"><StatusIcon status="practised" size={20} /> Solved</span> : null}
        </div>
        <div className="hidden items-center gap-2 lg:flex">
          <Button variant="run" disabled={!canExecute || Boolean(pending)} aria-busy={pending === 'run'} onClick={() => execute('run')}>
            {pending === 'run' ? <Loader2 className="animate-spin" /> : <Play />} Run tests
          </Button>
          <Button disabled={!canExecute || Boolean(pending)} aria-busy={pending === 'submit'} onClick={() => execute('submit')}>
            Submit solution<ArrowCircle loading={pending === 'submit'} />
          </Button>
        </div>
      </header>
      <div
        ref={workspace}
        className="workspace"
        style={{ '--split-a': `${prefs.split}fr`, '--split-b': `${1 - prefs.split}fr` } as React.CSSProperties}
      >
        <Card className="min-w-0 gap-0 py-0 lg:sticky lg:top-20 lg:self-start" aria-label="Problem statement">
          <Tabs defaultValue="description" className="gap-0">
            <div className="border-b px-4 pt-2">
              <TabsList variant="line" className="h-12">
                <TabsTrigger value="description">Description</TabsTrigger>
                <TabsTrigger value="attempts">Attempts{problem.history.length ? ` (${problem.history.length})` : ''}</TabsTrigger>
                <TabsTrigger value="visual">Visual</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="description" className="max-h-none overflow-y-auto p-5 lg:max-h-[calc(100dvh-13rem)]">
              {problem.locked ? (
                <LockedState title={`Locked until ${problem.locked.module}`} href={activityHref(problem.locked.gate)} className="mb-5">
                  Pass the {problem.locked.module} checkpoint to run and submit this problem.
                </LockedState>
              ) : null}
              <Markdown source={problem.statement} language={lang} className="prose-compact" />
              <h2 className="mt-6 mb-1 font-display text-base font-bold">Input</h2>
              <Markdown source={problem.input_format} className="prose-compact" />
              <h2 className="mt-4 mb-1 font-display text-base font-bold">Output</h2>
              <Markdown source={problem.output_format} className="prose-compact" />
              {problem.constraints.length ? (
                <>
                  <h2 className="mt-4 mb-1 font-display text-base font-bold">Constraints</h2>
                  <ul className="list-disc pl-5 text-sm text-muted-foreground">{problem.constraints.map(c => <li key={c} className="font-mono text-[13px]">{c}</li>)}</ul>
                </>
              ) : null}
              {problem.examples.map((ex, i) => (
                <div key={i} className="mt-5">
                  <h2 className="mb-2 font-display text-base font-bold">Example {i + 1}</h2>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div><p className="mb-1 text-xs text-muted-foreground">Input</p><pre className="io-block">{ex.input}</pre></div>
                    <div><p className="mb-1 text-xs text-muted-foreground">Output</p><pre className="io-block">{ex.output}</pre></div>
                  </div>
                  {ex.explanation ? <p className="mt-2 text-sm text-muted-foreground">{ex.explanation}</p> : null}
                </div>
              ))}
            </TabsContent>
            <TabsContent value="visual" className="p-5">
              <p className="mb-3 text-[15px] text-muted-foreground">A visual of {problem.concept.title}, the idea behind this problem. It does not solve it.</p>
              <ConceptVisual concept={problem.concept.id} title={problem.concept.title} problem={problem.id} />
            </TabsContent>
            <TabsContent value="attempts" className="p-5">
              {problem.history.length ? (
                <ul className="grid divide-y text-[15px]">
                  {problem.history.map(h => {
                    const v = VERDICT[h.verdict];
                    return (
                      <li key={h.id} className="flex min-h-12 items-center justify-between gap-2 py-2.5">
                        <span className="flex items-center gap-2.5">
                          <CaseMark ok={h.verdict === 'accepted' || h.verdict === 'ran' || h.verdict === 'executed'} />
                          <span className="font-semibold">{v?.label ?? h.status}</span>
                          <span className="text-muted-foreground">{h.mode === 'submit' ? 'Submitted' : 'Ran'}</span>
                        </span>
                        <span className="text-[13px] text-muted-foreground tabular-nums">{h.passed} of {h.total}. {formatStamp(h.at)}</span>
                      </li>
                    );
                  })}
                </ul>
              ) : <p className="text-[15px] text-muted-foreground">No attempts yet. Run your tests to check your code on the examples.</p>}
            </TabsContent>
          </Tabs>
        </Card>

        <section className="relative grid min-w-0 gap-3" aria-label="Code workspace">
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize statement and editor"
            aria-valuemin={25}
            aria-valuemax={65}
            aria-valuenow={Math.round(prefs.split * 100)}
            tabIndex={0}
            onPointerDown={startResize}
            onKeyDown={e => {
              if (e.key === 'ArrowLeft') { e.preventDefault(); setPrefs({ split: prefs.split - 0.02 }); }
              if (e.key === 'ArrowRight') { e.preventDefault(); setPrefs({ split: prefs.split + 0.02 }); }
            }}
            className="group absolute inset-y-0 -left-3 z-10 hidden w-2 cursor-col-resize touch-none items-center justify-center rounded-full lg:flex"
          >
            <span className="h-12 w-1 rounded-full bg-border-strong transition-colors group-hover:bg-primary group-focus-visible:bg-primary" />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="flex items-center gap-2 text-sm">
              <span className="sr-only">Language</span>
              <NativeSelect
                size="sm"
                value={lang}
                onChange={async e => { if (saved !== 'saved') await saveDraft(); setResult(null); setLanguage(e.target.value as Language); }}
              >
                {(['python', 'cpp', 'java'] as const).map(l => (
                  <NativeSelectOption key={l} value={l}>{LANGUAGE_LABEL[l]}{runtimeKnown && !runtimes[l] ? ' (runner offline)' : ''}</NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <span className="ml-auto flex items-center gap-1.5 text-[13px] text-muted-foreground" aria-live="polite">
              {saved === 'saving' ? <Loader2 className="size-3.5 animate-spin" /> : saved === 'saved' ? <Cloud className="size-3.5" /> : <CloudOff className="size-3.5" />}
              {saved === 'saving' ? 'Saving' : saved === 'saved' ? 'Draft saved' : 'Unsaved changes'}
            </span>
            <div className="flex items-center gap-1">
              <EditorSettings prefs={prefs} setPrefs={setPrefs} />
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label="Reset starter code"><RotateCcw /></Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Reset starter code</AlertDialogTitle>
                    <AlertDialogDescription>Your current {LANGUAGE_LABEL[lang]} code is replaced. Past submissions stay in your history.</AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Keep my code</AlertDialogCancel>
                    <AlertDialogAction variant="attention" onClick={resetToStarter}>Reset code</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
          <CodeEditor
            key={lang}
            language={lang}
            value={source}
            onChange={onChange}
            onBlur={() => { if (saved === 'unsaved') saveDraft(); }}
            fontSize={prefs.fontSize}
            tabSize={prefs.tabSize}
            theme={resolvedTheme === 'dark' ? 'dark' : 'light'}
            diagnostics={diagnostics}
            ariaLabel={`${LANGUAGE_LABEL[lang]} solution editor`}
            assistMode="learning"
            onRun={() => { if (canExecuteRef.current) execute('run'); }}
            onSubmit={() => { if (canExecuteRef.current) execute('submit'); }}
          />
          <p id="editor-keyboard-help" className="sr-only">Press Escape, then Tab, to move focus out of the editor.</p>

          <details className="group rounded-[16px] border" open={useCustom} onToggle={e => setUseCustom((e.currentTarget as HTMLDetailsElement).open)}>
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 text-[15px] font-semibold [&::-webkit-details-marker]:hidden">
              Custom input {useCustom ? <span className="text-[13px] font-medium text-muted-foreground">Used when you run tests</span> : null}
              <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden="true" />
            </summary>
            <div className="px-3 pb-3">
              <Textarea className="font-mono text-sm" rows={4} value={customInput} onChange={e => setCustomInput(e.target.value)} maxLength={20000} aria-label="Custom input" />
            </div>
          </details>
          <div className={cn('sticky bottom-[calc(72px+env(safe-area-inset-bottom))] z-20 -mx-4 flex flex-wrap items-center gap-2 border-t bg-background px-4 py-3 sm:mx-0 sm:rounded-[20px] sm:border md:bottom-4 lg:static lg:border-0 lg:bg-transparent lg:p-0', !proving && 'pr-[84px] sm:pr-[84px] lg:pr-0')}>
            {/* Desktop runs and submits from the header; these are the phone and tablet copies. */}
            <Button variant="run" className="flex-1 sm:flex-none lg:hidden" disabled={!canExecute || Boolean(pending)} aria-busy={pending === 'run'} onClick={() => execute('run')}>
              {pending === 'run' ? <Loader2 className="animate-spin" /> : <Play />} Run tests
            </Button>
            <Button className="flex-1 sm:flex-none lg:hidden" disabled={!canExecute || Boolean(pending)} aria-busy={pending === 'submit'} onClick={() => execute('submit')}>
              Submit solution<ArrowCircle loading={pending === 'submit'} />
            </Button>
          </div>
          {problem.locked ? <p className="text-sm text-muted-foreground">Run and submit unlock after the {problem.locked.module} checkpoint.</p> : null}
          {!features?.code_execution ? (
            <p className="rounded-[16px] border px-4 py-3 text-[15px]">Code execution is turned off on this server. Your drafts still save, and Soc can review your code.</p>
          ) : !runtimeReady ? (
            <div className="flex items-start gap-3 rounded-[16px] border border-attention px-4 py-3 text-[15px]"><AttentionIcon /> <span>{LANGUAGE_LABEL[lang]} needs Socrat's server runner, which is offline right now. Python and C++ run in your browser; switch language to run your code.</span></div>
          ) : null}
          <p className="hidden text-[13px] text-muted-foreground sm:block">
            <kbd className="rounded-md border border-border-strong px-1.5 font-sans">Ctrl Enter</kbd> runs tests. <kbd className="rounded-md border border-border-strong px-1.5 font-sans">Ctrl Shift Enter</kbd> submits.
          </p>
          {features?.execution_backend === 'local_process' ? (
            <p className="text-[13px] text-muted-foreground">Local development runner. Not secure for untrusted code.</p>
          ) : null}

          <div aria-live="polite">
            {pending && result?.status !== 'done' ? (
              <p className="flex items-center gap-2 rounded-[16px] border px-4 py-3 text-[15px] text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> {stage?.startsWith('downloading:') ? `Downloading the C++ compiler to your browser (once): ${stage.split(':')[1]}%` : STAGE_LABEL[stage ?? ''] ?? (result?.status === 'running' ? 'Running your code' : 'Waiting for a runner')}
              </p>
            ) : null}
            {verdict && result ? (
              <section ref={resultsRef} className={cn('grid scroll-mb-24 gap-3 paper rounded-card p-4 animate-in fade-in duration-200 lg:p-5', TONE_CLASS[verdict.tone])} aria-label="Results">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="font-display text-xl font-semibold tracking-[-0.03em]">
                    {result.total && result.verdict !== 'ran' && result.verdict !== 'compile_error' ? `${result.passed} of ${result.total} tests passed` : verdict.label}
                  </h2>
                  <span className="text-[13px] font-semibold text-muted-foreground">{result.mode === 'submit' ? 'Submission' : 'Test run'}: {verdict.label}</span>
                </div>
                {result.verdict === 'compile_error' || result.verdict === 'runtime_error' ? (
                  <div className="flex items-start gap-3 rounded-[16px] border border-attention p-3">
                    <AttentionIcon />
                    <pre className="io-block min-w-0 flex-1 bg-transparent! p-0!">{result.cases.find(c => c.stderr)?.stderr || verdict.label}</pre>
                  </div>
                ) : null}
                {result.mode === 'submit' && result.verdict === 'accepted' ? (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-[15px]">
                      {result.assistance >= 5 ? 'Solved with the full walkthrough. Try writing it again from memory tomorrow.' : result.assistance ? 'Solved. Hints count for a little less, and that is fine while you are learning.' : 'Solved without help. Nice work.'}
                    </p>
                    {proving
                      ? <Button asChild><Link href={examId ? '/assessments' : checkBack ?? '/plan'}>{examId ? 'Back to the exam' : 'Back to the check'}<ArrowCircle /></Link></Button>
                      : <Button asChild><Link href="/today">Continue to {NAME.today}</Link></Button>}
                  </div>
                ) : null}
                <div className="grid gap-2">
                  <CaseResults cases={result.cases} />
                </div>
              </section>
            ) : null}
          </div>
          {error ? <ErrorNote message={error} /> : null}
        </section>
      </div>
      {proving ? null : <Assistant
        scope={`problem:${problem.id}`}
        title="Ask Soc"
        language={lang}
        context={() => ({ code: latest.current.source, newAttempt: attempted.current })}
        onSent={() => { attempted.current = false; }}
      />}
    </div>
  );
}
