'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { Lightbulb, Play, SendHorizontal } from '@/components/icons';
import { api, explain, stream } from '@/lib/api';
import { runInBrowser, warm, type RunnerStage } from '@/lib/runner';
import { useLite } from '@/lib/lite';
import type { TryProblem } from '@/lib/types';
import CodeEditor from '@/components/code-editor';
import Markdown from '@/components/markdown';
import { Soc } from '@/components/socrat/illustration';
import { StatusIcon } from '@/components/socrat/status';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';

type Turn = { role: 'user' | 'assistant'; content: string };
type Outcome = { passed: number; total: number; failing: { input: string; expected: string; got: string; error: string; syntax: boolean } | null };

const CODE_KEY = 'socrat.try.code';
const STARTERS = ["I don't know where to start", 'My code is too slow', 'Why does my answer differ?'];

function clock(ms: number) {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function summary(o: Outcome | null) {
  if (!o) return '';
  let text = `${o.passed} of ${o.total} tests passed.`;
  if (o.failing) text += `\nFirst failing input:\n${o.failing.input}\nExpected:\n${o.failing.expected}\nGot:\n${o.failing.got}${o.failing.error ? `\nErrors:\n${o.failing.error.slice(0, 600)}` : ''}`;
  return text;
}

function stageLabel(stage: RunnerStage | null) {
  if (!stage) return 'Run tests';
  if (stage === 'loading') return 'Starting Python';
  return 'Running';
}

/** One real problem with Soc, before sign-up. Code runs in this browser; nothing is saved. */
export function TryTutor() {
  const { resolvedTheme } = useTheme();
  const { lite } = useLite();
  const [problem, setProblem] = useState<TryProblem | null>(null);
  const [failed, setFailed] = useState(false);
  const [code, setCode] = useState('');
  const [stage, setStage] = useState<RunnerStage | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [runError, setRunError] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [chatError, setChatError] = useState('');
  const [solvedIn, setSolvedIn] = useState<number | null>(null);
  const started = useRef<number | null>(null);
  const attempted = useRef(false);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<TryProblem>('/try').then(p => {
      setProblem(p);
      let saved = '';
      try { saved = localStorage.getItem(CODE_KEY) ?? ''; } catch { /* private window */ }
      setCode(saved || p.starter);
    }).catch(() => setFailed(true));
  }, []);

  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight }); }, [turns]);

  function edit(next: string) {
    setCode(next);
    started.current ??= Date.now();
    try { localStorage.setItem(CODE_KEY, next); } catch { /* per-viewer nicety only */ }
  }

  async function run() {
    if (!problem || stage) return;
    started.current ??= Date.now();
    setRunError('');
    setStage('loading');
    try {
      const results = await runInBrowser(
        { token: '', language: 'python', time_limit_ms: problem.time_limit_ms, expires_at: 0, tests: problem.tests.map(t => ({ index: t.index, input: t.input })) },
        code,
        setStage,
      );
      let passed = 0;
      let failing: Outcome['failing'] = null;
      for (const r of results) {
        const test = problem.tests.find(t => t.index === r.index)!;
        const ok = r.status === 'executed' && r.stdout.trim() === test.expected.trim();
        if (ok) passed += 1;
        else failing ??= { input: test.input.trim(), expected: test.expected.trim(), got: r.status === 'timeout' ? '(ran out of time)' : r.stdout.trim(), error: r.stderr, syntax: r.status === 'compile_error' };
      }
      setOutcome({ passed, total: results.length, failing });
      attempted.current = true;
      if (passed === results.length && solvedIn === null) setSolvedIn(Date.now() - (started.current ?? Date.now()));
    } catch (e) {
      setRunError(e instanceof Error ? e.message : 'The code runner could not start in this browser.');
    } finally {
      setStage(null);
    }
  }

  async function send(intent: 'chat' | 'hint', text = draft) {
    if (busy || !problem) return;
    const message = text.trim();
    const history = turns;
    setTurns([...history, { role: 'user', content: message || 'Give me a hint.' }, { role: 'assistant', content: '' }]);
    setDraft('');
    setBusy(true);
    setChatError('');
    let reply = '';
    const show = (value: string) => setTurns(t => [...t.slice(0, -1), { role: 'assistant', content: value }]);
    try {
      for await (const { event, data } of stream('/try/messages', {
        history, message, intent, code, result: summary(outcome), new_attempt: attempted.current,
      })) {
        if (event === 'delta') show((reply += String(data.text ?? '')));
        else if (event === 'replace' || event === 'done') show((reply = String(data.text ?? reply)));
      }
      attempted.current = false;
    } catch (e) {
      setTurns(history);
      setChatError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  if (failed) return null;
  const used = turns.filter(t => t.role === 'user').length;
  const outOfTurns = problem ? used >= problem.max_turns : false;
  const solved = outcome !== null && outcome.passed === outcome.total;

  return (
    <section id="try" aria-labelledby="try-title" className="mx-auto max-w-[1500px] scroll-mt-20 px-5 py-20 sm:px-8 lg:py-28 lg:pr-10 lg:pl-[128px]">
      <p className="font-hand origin-left -rotate-2 text-[24px] text-pen">no account needed, go on</p>
      <h2 id="try-title" className="type-display-l mt-4 max-w-[20ch]">Solve one problem with Soc, <span className="hl">right now</span></h2>
      <p className="type-body-l mt-4 max-w-2xl text-muted-foreground">Write Python, run the tests in your browser, and ask Soc when you get stuck. Watch what it does instead of giving you the answer.</p>

      <div className="mt-12 grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:gap-6">
        <div className="paper grid min-w-0 content-start gap-4 rounded-card p-4 sm:p-6">
          {!problem ? (
            <div className="grid min-h-[420px] place-items-center" role="status"><Spinner /><span className="sr-only">Loading the problem</span></div>
          ) : (
            <>
              <div>
                <h3 className="font-display text-2xl font-semibold tracking-[-0.04em]">{problem.title}</h3>
                <Markdown source={problem.statement} className="prose-compact mt-2 text-[15px]" />
                <p className="mt-2 text-[13px] text-muted-foreground">{problem.input_format}</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <figure><figcaption className="mb-1 text-[13px] font-semibold">Example input</figcaption><pre className="code-block text-[13px]!"><code>{problem.examples[0].input}</code></pre></figure>
                  <figure><figcaption className="mb-1 text-[13px] font-semibold">Expected output</figcaption><pre className="code-block text-[13px]!"><code>{problem.examples[0].output}</code></pre></figure>
                </div>
              </div>
              <div className="min-h-56 overflow-hidden rounded-[4px] border" onFocus={() => { if (!lite) void warm('python'); }}>
                <CodeEditor
                  language="python"
                  value={code}
                  onChange={edit}
                  onBlur={() => undefined}
                  fontSize={14}
                  theme={resolvedTheme === 'dark' ? 'dark' : 'light'}
                  ariaLabel="Python solution editor"
                  assistMode="learning"
                  onRun={run}
                />
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={run} disabled={Boolean(stage)} aria-busy={Boolean(stage)}>
                  {stage ? <Spinner data-icon="inline-start" /> : <Play data-icon="inline-start" />}{stageLabel(stage)}
                </Button>
                <span className="text-[13px] text-muted-foreground">Runs in your browser. The first run loads Python, about 10 seconds.</span>
              </div>
              <div aria-live="polite">
                {runError ? <p role="alert" className="rounded-[4px] border border-attention px-4 py-3 text-sm">{runError}</p> : null}
                {outcome ? (
                  <div className="rounded-[4px] border bg-background p-4">
                    <p className="flex items-center gap-2 font-display text-lg font-semibold tracking-[-0.03em]">
                      <StatusIcon status={solved ? 'practised' : 'needs_practice'} size={22} />
                      {outcome.passed} of {outcome.total} tests passed
                    </p>
                    {outcome.failing ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        {outcome.failing.syntax ? 'Python could not read your code. Check the line below.' : outcome.failing.error ? 'Your code raised an error on a test.' : outcome.failing.got === '(ran out of time)' ? 'Correct idea, perhaps, but too slow on a test.' : `Expected ${outcome.failing.expected.slice(0, 40)}, got ${outcome.failing.got.slice(0, 40) || 'nothing'}.`} Ask Soc about it.
                      </p>
                    ) : null}
                    {outcome.failing?.error ? (
                      <pre className="io-block mt-2 max-h-40 overflow-auto text-xs">{outcome.failing.error.trim().split('\n').slice(-6).join('\n')}</pre>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </>
          )}
        </div>

        <div className="paper flex min-h-[520px] min-w-0 flex-col overflow-hidden rounded-card lg:max-h-[760px]">
          <header className="flex items-center gap-3 border-b px-5 py-4">
            <button type="button" aria-label="Write to Soc" className="flex-none rounded-full" onClick={() => document.getElementById('try-message')?.focus()}>
              <Soc size={40} />
            </button>
            <div>
              <p className="font-semibold">Soc, your tutor</p>
              <p className="text-[13px] text-muted-foreground">Asks before it tells. Never writes the answer here.</p>
            </div>
          </header>
          <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
            {!turns.length ? (
              <div className="grid gap-2 text-[15px] text-muted-foreground">
                <p>Tell me what you tried, or pick a starting point. Hints get more specific as you keep working.</p>
                {STARTERS.map(s => (
                  <Button key={s} type="button" variant="outline" size="sm" className="h-auto min-h-11 justify-start rounded-[4px] py-2.5 text-left font-medium whitespace-normal" disabled={busy || !problem} onClick={() => send('chat', s)}>{s}</Button>
                ))}
              </div>
            ) : null}
            {turns.map((t, i) => t.role === 'user' ? (
              <div key={i} className="chat-bubble-user">{t.content}</div>
            ) : (
              <div key={i} className="chat-bubble-assistant">
                {t.content ? <Markdown source={t.content} language="python" className="prose-compact" /> : (
                  <span className="flex items-center gap-1 py-1" aria-label="Thinking">
                    {[0, 1, 2].map(n => <span key={n} className="size-1.5 animate-pulse-slow rounded-full bg-muted-foreground" style={{ animationDelay: `${n * 200}ms` }} />)}
                  </span>
                )}
              </div>
            ))}
            {solved ? (
              <div data-tone="hero" className="rounded-[4px] bg-forest p-5 text-forest-foreground">
                <p className="font-display text-xl font-semibold tracking-[-0.03em]">Solved{solvedIn !== null ? ` in ${clock(solvedIn)}` : ''}.</p>
                <p className="mt-1 text-sm">That is what Socrat feels like. Sign up to keep this as your first piece of evidence and get a plan built around your goal.</p>
                <Button asChild variant="ink" className="mt-4"><Link href="/login">Create my plan<ArrowCircle /></Link></Button>
              </div>
            ) : null}
          </div>
          {chatError ? <p role="alert" className="mx-4 mb-2 rounded-[4px] border border-attention px-3 py-2 text-sm">{chatError}</p> : null}
          {outOfTurns ? (
            <div className="border-t p-4 text-sm">
              <p>That is the end of the free preview.</p>
              <Button asChild size="sm" className="mt-3"><Link href="/login">Keep going with Soc<ArrowCircle /></Link></Button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 border-t px-4 pt-3">
                <Button type="button" variant="outline" size="sm" disabled={busy || !problem} onClick={() => send('hint', '')}><Lightbulb data-icon="inline-start" /> Give me a hint</Button>
                {problem ? <span className="ml-auto text-[13px] text-muted-foreground tabular-nums">{problem.max_turns - used} messages left</span> : null}
              </div>
              <form className="flex items-end gap-2 p-3" onSubmit={e => { e.preventDefault(); if (draft.trim()) send('chat'); }}>
                <label className="sr-only" htmlFor="try-message">Message Soc</label>
                <Textarea
                  id="try-message"
                  className="max-h-40 min-h-12 flex-1 resize-none py-2.5"
                  rows={2}
                  maxLength={1000}
                  value={draft}
                  placeholder="What did you try? Where does it break?"
                  onChange={e => setDraft(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (draft.trim()) send('chat'); } }}
                />
                <Button size="icon-lg" disabled={busy || !draft.trim() || !problem} aria-label="Send message"><SendHorizontal /></Button>
              </form>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
