'use client';

import { cn } from '@/lib/utils';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api, explain, stream } from '@/lib/api';
import type { ChatMessage, Proposal, ProposalsView } from '@/lib/types';
import { ProposalList } from '@/components/socrat/proposals';
import { Check, Lightbulb, SendHorizontal, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { Soc } from '@/components/socrat/illustration';
import Markdown from './markdown';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';

interface Ladder {
  ceiling?: number;
  turns_at_ceiling?: number;
  revealed?: boolean;
}

interface Props {
  scope: string;
  title: string;
  language?: string;
  /** Problem pages supply the current code and whether a Run/Submit happened since the last message. */
  context?: () => { code: string; newAttempt: boolean };
  onSent?: () => void;
  /** Opens the panel from outside (e.g. a "Get a hint" button). Increment to trigger. */
  openSignal?: number;
  /** Hide the floating launcher, or show it on phones only, when the page has its own "Ask Soc" control. */
  launcher?: boolean | 'phone';
}

const LEVEL_TEXT = ['Asking what you tried', 'Guiding question', 'Conceptual nudge', 'Approach', 'Partial plan', 'Full walkthrough'];
const STARTERS: Record<string, string[]> = {
  general: ['What should I focus on this week?', 'Pick 3 problems for me', 'Where am I weakest right now?'],
  plan: ['Help me build my plan', 'I have interviews coming up', "I'm stuck. What should change?"],
  concept: ['Explain this with a real example', 'When would I use this?', 'Give me a problem to practise this'],
};

export default function Assistant({ scope, title, language, context, onSent, openSignal = 0, launcher: showLauncher = true }: Props) {
  const problem = scope.startsWith('problem:');
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ladder, setLadder] = useState<Ladder>({});
  const [loaded, setLoaded] = useState(false);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirmReveal, setConfirmReveal] = useState(false);
  // Whether the server would show the full solution now, and what is left if not.
  const [reveal, setReveal] = useState<{ ok: boolean; needs: string } | null>(null);
  const [activity, setActivity] = useState<string[]>([]);
  // Plan changes Soc proposed in chat; they apply only when the learner accepts them here.
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);
  const opener = useRef<HTMLElement | null>(null);

  // Keyboard users land in the message box on open and back on whatever opened it on close
  // (the floating launcher, or a page's own "Ask Soc" button).
  useEffect(() => {
    if (open) {
      if (document.activeElement instanceof HTMLElement && document.activeElement !== document.body) opener.current = document.activeElement;
      input.current?.focus();
    } else if (wasOpen.current) {
      const back = opener.current && opener.current.isConnected && opener.current.offsetParent !== null ? opener.current : launcher.current;
      back?.focus();
    }
    wasOpen.current = open;
  }, [open]);

  useEffect(() => { if (openSignal) setOpen(true); }, [openSignal]);
  useEffect(() => { setLoaded(false); setMessages([]); setLadder({}); }, [scope]);
  const refreshReveal = useCallback(() => {
    if (!problem) return;
    api
      .get<{ reveal: { ok: boolean; needs: string } | null }>(`/assistant/thread?scope=${encodeURIComponent(scope)}`)
      .then(t => setReveal(t.reveal))
      .catch(() => undefined);
  }, [problem, scope]);
  useEffect(() => {
    if (!open) return;
    // Submits made on the page since the panel last opened can unlock the solution.
    if (loaded) { refreshReveal(); return; }
    api
      .get<{ messages: ChatMessage[]; ladder: Ladder; reveal: { ok: boolean; needs: string } | null }>(`/assistant/thread?scope=${encodeURIComponent(scope)}`)
      .then(t => { setMessages(t.messages); setLadder(t.ladder ?? {}); setReveal(t.reveal); setLoaded(true); })
      .catch(e => setError(explain(e)));
  }, [open, loaded, scope, refreshReveal]);
  useEffect(() => {
    if (!open || problem) return;
    loadProposals();
  }, [open, problem]);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages, open, proposals]);

  function loadProposals() {
    api
      .get<ProposalsView>('/adaptive/proposals')
      .then(v => setProposals(v.pending.filter(p => p.source === 'tutor')))
      .catch(() => setProposals([]));
  }
  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  async function send(intent: 'chat' | 'hint' | 'reveal_confirmed', text = draft) {
    if (busy) return;
    const message = text.trim();
    if (intent === 'chat' && !message) return;
    setBusy(true);
    setError('');
    setConfirmReveal(false);
    const extra = context?.() ?? { code: '', newAttempt: false };
    const shown = message || (intent === 'hint' ? "I'd like a hint." : 'Please walk me through the full solution.');
    setMessages(m => [...m, { role: 'user', content: shown }, { role: 'assistant', content: '' }]);
    setDraft('');
    setActivity([]);
    let reply = '';
    let proposed = false;
    let finished = false;
    const update = (content: string, level?: number, id?: string) =>
      setMessages(m => [...m.slice(0, -1), { role: 'assistant', content, level, id }]);
    try {
      for await (const { event, data } of stream('/assistant/messages', {
        scope, message, intent, code: extra.code, new_attempt: extra.newAttempt,
      })) {
        if (event === 'tool') {
          if (String(data.name).startsWith('propose_')) proposed = true;
          setActivity(a => (a.includes(String(data.label)) ? a : [...a, String(data.label)]));
        }
        else if (event === 'delta') { reply += String(data.text ?? ''); update(reply); }
        else if (event === 'replace') { reply = String(data.text ?? ''); update(reply); }
        else if (event === 'done') {
          finished = true;
          reply = String(data.text ?? reply);
          update(reply, Number(data.level), data.message_id ? String(data.message_id) : undefined);
          if (problem) {
            const level = Number(data.level);
            setLadder(l => ({ ...l, ceiling: Math.max(l.ceiling ?? 0, Math.min(level, 4)), revealed: l.revealed || level >= 5 }));
          }
        }
      }
      if (!finished) throw new ApiError(0, 'request_failed');
      if (proposed) loadProposals();
      refreshReveal();
      onSent?.();
    } catch (e) {
      setMessages(m => m.slice(0, -2));
      setDraft(message);
      setError(explain(e));
    } finally {
      setBusy(false);
      setActivity([]);
    }
  }

  async function rate(id: string, rating: number) {
    setMessages(list => list.map(m => (m.id === id ? { ...m, rating: rating || null } : m)));
    await api.post(`/assistant/messages/${id}/rating`, { rating }).catch(() => undefined);
  }

  if (!open) {
    if (!showLauncher) return null;
    // 56 px, 16 px above the phone bottom nav; bottom right on desktop.
    return (
      <div className={`fixed right-4 bottom-[calc(80px+env(safe-area-inset-bottom))] z-40 md:bottom-6 lg:right-8 lg:bottom-8 ${showLauncher === 'phone' ? 'lg:hidden' : ''}`}>
        <button
          type="button"
          ref={launcher}
          onClick={() => setOpen(true)}
          aria-haspopup="dialog"
          aria-label="Ask Soc, your tutor"
          data-tour="tutor"
          className="group/soc flex h-14 items-center gap-3 rounded-full bg-card p-1 shadow-floating ring-1 ring-border transition-transform duration-200 ease-[var(--ease-soft)] active:scale-[0.98] lg:pr-5"
        >
          <Soc size={48} mood="wink" />
          <span className="hidden text-[15px] font-semibold lg:inline">Ask Soc</span>
        </button>
      </div>
    );
  }

  const level = ladder.revealed ? 5 : ladder.ceiling ?? 0;
  return (
    <section
      className={cn(
        'fixed inset-x-0 bottom-0 z-[60] flex h-[calc(100dvh-4rem)] flex-col overflow-hidden rounded-t-card border bg-card pb-[env(safe-area-inset-bottom)] text-card-foreground shadow-floating animate-in fade-in slide-in-from-bottom-2 sm:inset-x-auto sm:bottom-6 sm:h-[min(680px,calc(100dvh-6rem))] sm:w-[420px] sm:rounded-card sm:pb-0',
        // On a problem the test results sit bottom-right, so the tutor opens over the statement instead.
        problem ? 'sm:left-6 lg:left-[17rem]' : 'sm:right-6',
      )}
      role="dialog"
      aria-label={title}
      onKeyDown={e => { if (e.key === 'Escape') { e.stopPropagation(); setOpen(false); } }}
    >
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <Soc size={44} mood={busy ? 'thinking' : 'neutral'} />
          <div className="min-w-0">
            <h2 className="font-display text-lg font-semibold tracking-[-0.02em]">{title}</h2>
            {problem ? (
              <div className="mt-1 flex items-center gap-2">
                <div className="flex gap-0.5" aria-hidden="true">
                  {[0, 1, 2, 3, 4, 5].map(n => <span key={n} className={`h-1.5 w-3 rounded-full ${n <= level ? 'bg-primary' : 'bg-raised'}`} />)}
                </div>
                <p className="text-xs text-muted-foreground">{LEVEL_TEXT[level]}</p>
              </div>
            ) : <p className="text-[13px] text-muted-foreground">Asks before it tells. Knows your plan.</p>}
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close tutor"><X /></Button>
      </header>
      {/* The conversation is written on a ruled page with a red margin. */}
      <div ref={scroller} className="chat-page flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {!messages.length ? (
          <div className="text-[15px] text-muted-foreground">
            <div className="mb-3 flex items-end gap-3">
              <Soc size={84} mood="curious" />
              <p className="font-hand pb-2 text-[22px] leading-tight text-pen">{problem ? 'show me what you tried.' : 'hi! ask me anything.'}</p>
            </div>
            {problem
              ? 'Tell me what you tried and where it breaks. Hints get more specific as you keep working. Run your code or explain your thinking to unlock the next level.'
              : scope === 'general'
                ? 'I know your plan, your progress and the whole practice library. Ask what to study, which problems to do next, or anything you are stuck on.'
                : scope === 'plan'
                  ? "Let's shape your roadmap together. I'll ask a few questions, then suggest changes you can accept or skip. Nothing changes without your yes."
                  : 'Ask about this lesson, an idea that feels fuzzy, or what to focus on next.'}
            {!problem ? (
              <div className="mt-4 grid gap-2">
                {STARTERS[scope === 'general' || scope === 'plan' ? scope : 'concept'].map(s => (
                  <Button key={s} type="button" variant="outline" size="sm" className="h-auto min-h-11 justify-start rounded-[16px] py-2.5 text-left font-medium whitespace-normal" disabled={busy || !loaded} onClick={() => send('chat', s)}>
                    {s}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="chat-bubble-user">{m.content}</div>
          ) : (
            <div key={i} className="flex items-end gap-2">
            <Soc size={28} mood={busy && i === messages.length - 1 ? 'thinking' : m.rating === 1 ? 'happy' : 'neutral'} className="mb-1" />
            <div className="chat-bubble-assistant min-w-0 flex-1">
              {busy && i === messages.length - 1 && activity.length ? (
                <ul className="mb-2 grid gap-1 text-xs text-muted-foreground" aria-label="What the tutor is checking">
                  {activity.map((a, j) => (
                    <li key={a} className="flex items-center gap-2">
                      {j === activity.length - 1 && !m.content ? <Spinner className="size-3" /> : <Check className="size-3" />}
                      {a}
                    </li>
                  ))}
                </ul>
              ) : null}
              {m.content ? (
                <>
                <Markdown source={m.content} language={language} className="prose-compact" />
                {m.id && !(busy && i === messages.length - 1) ? (
                  <div className="mt-1.5 flex justify-end gap-0.5">
                    {([1, -1] as const).map(value => {
                      const on = m.rating === value;
                      const Icon = value === 1 ? ThumbsUp : ThumbsDown;
                      return (
                        <button
                          key={value}
                          type="button"
                          aria-pressed={on}
                          aria-label={value === 1 ? 'Helpful reply' : 'Not helpful'}
                          className={`grid size-8 place-items-center rounded-full transition-colors hover:bg-card ${on ? 'text-brand' : 'text-muted-foreground'}`}
                          onClick={() => rate(m.id!, on ? 0 : value)}
                        >
                          <Icon className={`size-3.5 ${on ? 'fill-current' : ''}`} />
                        </button>
                      );
                    })}
                  </div>
                ) : null}
                </>
              ) : activity.length && busy && i === messages.length - 1 ? null : (
                <span className="flex items-center gap-1 py-1" aria-label="Thinking">
                  {[0, 1, 2].map(n => <span key={n} className="size-1.5 animate-pulse-slow rounded-full bg-muted-foreground" style={{ animationDelay: `${n * 200}ms` }} />)}
                </span>
              )}
            </div>
            </div>
          ),
        )}
        {proposals.length && !busy ? (
          <div aria-label="Plan changes Soc suggested">
            <ProposalList compact proposals={proposals} onDecided={v => setProposals(v.pending.filter(p => p.source === 'tutor'))} />
          </div>
        ) : null}
      </div>
      {error ? <p role="alert" className="mx-4 mb-2 rounded-[16px] border border-attention px-3 py-2 text-sm">{error}</p> : null}
      {problem ? (
        <div className="flex flex-wrap items-center gap-2 border-t px-4 pt-3">
          <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => send('hint')}><Lightbulb data-icon="inline-start" /> Give me a hint</Button>
          {confirmReveal ? (
            <span className="flex flex-wrap items-center gap-2 text-xs">
              Show the full solution? It counts as heavy help.
              <Button type="button" size="sm" variant="destructive" disabled={busy} onClick={() => send('reveal_confirmed', '')}>Yes, show it</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => setConfirmReveal(false)}>Keep trying</Button>
            </span>
          ) : reveal && !reveal.ok && !ladder.revealed ? (
            <span className="text-xs text-muted-foreground">Full solution unlocks after you {reveal.needs}.</span>
          ) : level >= 3 ? ( // the walkthrough is offered only once real help has been given
            <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={() => setConfirmReveal(true)}>Show solution</Button>
          ) : null}
        </div>
      ) : null}
      <form className="flex items-end gap-2 border-t p-3" onSubmit={e => { e.preventDefault(); send('chat'); }}>
        <label className="sr-only" htmlFor={`assistant-${scope}`}>Message</label>
        <Textarea
          id={`assistant-${scope}`}
          ref={input}
          className="max-h-40 min-h-12 flex-1 resize-none py-2.5"
          rows={2}
          maxLength={4000}
          value={draft}
          placeholder={problem ? 'What did you try? Where does it break?' : 'Ask a question…'}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send('chat'); } }}
        />
        <Button size="icon-lg" disabled={busy || !draft.trim()} aria-label="Send message"><SendHorizontal /></Button>
      </form>
    </section>
  );
}
