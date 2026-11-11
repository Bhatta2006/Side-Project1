'use client';

import { cn } from '@/lib/utils';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api, explain, stream } from '@/lib/api';
import { useCourse } from '@/lib/course';
import type { ChatMessage, Proposal, ProposalsView } from '@/lib/types';
import { ProposalList } from '@/components/socrat/proposals';
import { ArrowLeft, BookOpen, Check, History, Lightbulb, SendHorizontal, SquarePen, ThumbsDown, ThumbsUp, X } from '@/components/icons';
import { prefersReducedMotion } from '@/lib/motion';
import { Soc } from '@/components/socrat/illustration';
import Markdown from './markdown';
import { Button } from '@/components/ui/button';
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

interface ChatSummary { id: string; title: string; messages: number; updated_at: number; current: boolean }
interface SocContext { sections: { title: string; text: string }[]; teaching: string; history_turns: number }
type View = 'chat' | 'history' | 'context';

/** Soc is thinking: a pencil scribble that keeps drawing itself, with what Soc is doing in hand. */
function Thinking({ label }: { label?: string }) {
  return (
    <span className="flex items-center gap-2 py-1" role="status">
      <svg viewBox="0 0 64 20" className="soc-scribble h-5 w-14 flex-none text-pen" aria-hidden="true">
        <path d="M2 12c5-9 9 7 14-1s8-7 12 1 8 6 12-2 8-6 12 1 6 4 10-1" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
      <span className="font-hand text-[19px] leading-none text-muted-foreground">{label ? `${label.toLowerCase()}…` : 'thinking…'}</span>
    </span>
  );
}

function when(seconds: number) {
  return new Date(seconds * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const LEVEL_TEXT = ['Asking what you tried', 'Guiding question', 'Conceptual nudge', 'Approach', 'Partial plan', 'Full walkthrough'];
const STARTERS: Record<string, string[]> = {
  general: ['What should I focus on this week?', 'Pick 3 problems for me', 'Where am I weakest right now?'],
  plan: ['Help me build my plan', 'I have interviews coming up', "I'm stuck. What should change?"],
  concept: ['Explain this with a real example', 'When would I use this?', 'Give me a problem to practise this'],
};
// Courses without code (a language, drawing, finance): no problem library to pick from.
const STARTERS_NO_CODE: Record<string, string[]> = {
  general: ['What should I focus on this week?', 'Quiz me on what I learned', 'Where am I weakest right now?'],
  plan: ['Help me build my plan', 'I have a deadline coming up', "I'm stuck. What should change?"],
  concept: ['Explain this with a real example', 'When would I use this?', 'Ask me a question to practise this'],
};

export default function Assistant({ scope, title, language, context, onSent, openSignal = 0, launcher: showLauncher = true }: Props) {
  const problem = scope.startsWith('problem:');
  // Problem picks and the practice library exist only in the programming courses.
  const coding = useCourse().features.library;
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
  const [view, setView] = useState<View>('chat');
  const [chats, setChats] = useState<ChatSummary[] | null>(null);
  const [socContext, setSocContext] = useState<SocContext | null>(null);
  // An archived chat being read; it can be continued, not written to.
  const [archived, setArchived] = useState<{ id: string; messages: ChatMessage[] } | null>(null);
  // How many characters of the streaming reply are on screen; null when nothing is typing.
  const [typed, setTyped] = useState<number | null>(null);
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
  useEffect(() => { setLoaded(false); setMessages([]); setLadder({}); setView('chat'); setArchived(null); }, [scope]);
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

  // Type the reply out smoothly, however the server chunks it; catch up faster when far behind.
  useEffect(() => {
    if (typed === null) return;
    const last = messages[messages.length - 1];
    const length = last?.role === 'assistant' ? last.content.length : 0;
    if (typed >= length) { if (!busy) setTyped(null); return; }
    const frame = requestAnimationFrame(() => setTyped(t => (t === null ? null : Math.min(length, t + Math.max(2, Math.ceil((length - t) / 12))))));
    return () => cancelAnimationFrame(frame);
  }, [typed, messages, busy]);

  function showHistory() {
    setView('history'); setChats(null); setError('');
    api.get<{ items: ChatSummary[] }>(`/assistant/chats?scope=${encodeURIComponent(scope)}`)
      .then(r => setChats(r.items))
      .catch(e => { setChats([]); setError(explain(e)); });
  }
  function showContext() {
    setView('context'); setSocContext(null); setError('');
    api.get<SocContext>(`/assistant/context?scope=${encodeURIComponent(scope)}`)
      .then(setSocContext)
      .catch(e => setError(explain(e)));
  }
  async function newChat() {
    if (busy) return;
    setError('');
    try {
      await api.post('/assistant/chats', { scope });
      // Reloading picks up the carried-over hint ladder on a problem.
      setMessages([]); setArchived(null); setView('chat'); setLoaded(false);
      requestAnimationFrame(() => input.current?.focus());
    } catch (e) { setError(explain(e)); }
  }
  async function openChat(chat: ChatSummary) {
    setError('');
    if (chat.current) { setArchived(null); setView('chat'); return; }
    try {
      const t = await api.get<{ messages: ChatMessage[] }>(`/assistant/chats/${chat.id}`);
      setArchived({ id: chat.id, messages: t.messages }); setView('chat');
    } catch (e) { setError(explain(e)); }
  }
  async function continueChat() {
    if (!archived) return;
    try {
      await api.post(`/assistant/chats/${archived.id}/resume`, {});
      setArchived(null); setLoaded(false);
    } catch (e) { setError(explain(e)); }
  }
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
    setView('chat'); setArchived(null);
    if (!prefersReducedMotion()) setTyped(0);
    let reply = '';
    let proposed = false;
    let finished = false;
    const update = (content: string, level?: number, id?: string) =>
      setMessages(m => [...m.slice(0, -1), { role: 'assistant', content, level, id }]);
    try {
      for await (const { event, data } of stream('/assistant/messages', {
        scope, message, intent, code: extra.code, new_attempt: extra.newAttempt,
      })) {
        if (event === 'move') setActivity([String(data.label)]);
        else if (event === 'tool') {
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
      setTyped(null);
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
        <div className="flex flex-none items-center">
          <Button variant="ghost" size="icon-sm" onClick={() => void newChat()} disabled={busy || (!messages.length && !archived)} aria-label="New chat" title="New chat"><SquarePen /></Button>
          <Button variant="ghost" size="icon-sm" onClick={() => (view === 'history' ? setView('chat') : showHistory())} aria-pressed={view === 'history'} aria-label="Chat history" title="Chat history"><History /></Button>
          <Button variant="ghost" size="icon-sm" onClick={() => (view === 'context' ? setView('chat') : showContext())} aria-pressed={view === 'context'} aria-label="What Soc knows" title="What Soc knows"><BookOpen /></Button>
          <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close tutor"><X /></Button>
        </div>
      </header>
      {view === 'history' ? (
        <div className="chat-page flex-1 overflow-y-auto px-4 py-4">
          <button type="button" onClick={() => setView('chat')} className="mb-3 inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold"><ArrowLeft className="size-4" /> Back to chat</button>
          <h3 className="font-hand mb-2 text-[24px] leading-none text-pen">your chats</h3>
          {chats === null ? <Thinking label="Finding your chats" /> : !chats.length ? (
            <p className="text-[15px] text-muted-foreground">No chats here yet. Ask Soc something and it shows up here.</p>
          ) : (
            <ul className="grid gap-2">
              {chats.map(chat => (
                <li key={chat.id}>
                  <button type="button" onClick={() => void openChat(chat)} className="flex min-h-14 w-full items-center justify-between gap-3 rounded-[14px_18px_12px_16px] border-2 border-border-strong bg-card px-3 py-2 text-left transition-[transform,box-shadow] hover:-translate-y-0.5 hover:border-[var(--soc-outline)] hover:shadow-[3px_3px_0_var(--soc-outline)]">
                    <span className="min-w-0">
                      <span className="block truncate font-semibold">{chat.title}</span>
                      <span className="block text-[13px] text-muted-foreground">{when(chat.updated_at)} · {chat.messages} messages</span>
                    </span>
                    {chat.current ? <span className="font-hand flex-none text-[17px] text-pen">current</span> : null}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <Button type="button" variant="outline" size="sm" className="mt-4" disabled={busy || (!messages.length && !archived)} onClick={() => void newChat()}><SquarePen data-icon="inline-start" /> Start a new chat</Button>
        </div>
      ) : view === 'context' ? (
        <div className="chat-page flex-1 overflow-y-auto px-4 py-4">
          <button type="button" onClick={() => setView('chat')} className="mb-3 inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold"><ArrowLeft className="size-4" /> Back to chat</button>
          <h3 className="font-hand text-[24px] leading-none text-pen">what soc knows</h3>
          <p className="mt-1 mb-3 text-[13px] text-muted-foreground">Soc reads this before every reply, plus the last {socContext?.history_turns ?? 12} messages of this chat{problem ? ' and the code in your editor' : ''}. Nothing else.</p>
          {!socContext ? <Thinking label="Opening the notebook" /> : (
            <div className="grid gap-2">
              <div className="rounded-[14px_18px_12px_16px] border-2 border-dashed border-border-strong bg-card px-3 py-2 text-sm">
                <p className="font-semibold">How Soc is teaching this chat</p>
                <p className="text-muted-foreground">{socContext.teaching}</p>
              </div>
              {socContext.sections.map(section => (
                <details key={section.title} className="group rounded-[14px_18px_12px_16px] border border-border-strong bg-card px-3 py-2 text-sm">
                  <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between font-semibold [&::-webkit-details-marker]:hidden">{section.title}<span className="text-muted-foreground transition-transform group-open:rotate-90" aria-hidden="true">›</span></summary>
                  <p className="mt-1 whitespace-pre-wrap text-muted-foreground">{section.text}</p>
                </details>
              ))}
            </div>
          )}
        </div>
      ) : archived ? (
        <div className="chat-page flex-1 space-y-3 overflow-y-auto px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-[14px_18px_12px_16px] border-2 border-dashed border-border-strong bg-card px-3 py-2 text-sm">
            <span>An earlier chat (read-only)</span>
            <span className="flex gap-1">
              <Button type="button" size="sm" variant="ghost" onClick={() => setArchived(null)}>Back</Button>
              <Button type="button" size="sm" onClick={() => void continueChat()}>Continue this chat</Button>
            </span>
          </div>
          {archived.messages.map((m, i) => m.role === 'user'
            ? <div key={i} className="chat-bubble-user">{m.content}</div>
            : <div key={i} className="flex items-end gap-2"><Soc size={28} className="mb-1" /><div className="chat-bubble-assistant min-w-0 flex-1"><Markdown source={m.content} language={language} className="prose-compact" /></div></div>)}
        </div>
      ) : null}
      {/* The conversation is written on a ruled page with a red margin. */}
      <div ref={scroller} hidden={view !== 'chat' || Boolean(archived)} className="chat-page flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {!messages.length ? (
          <div className="text-[15px] text-muted-foreground">
            <div className="mb-3 flex items-end gap-3">
              <Soc size={84} mood="curious" />
              <p className="font-hand pb-2 text-[22px] leading-tight text-pen">{problem ? 'show me what you tried.' : 'hi! ask me anything.'}</p>
            </div>
            {problem
              ? 'Tell me what you tried and where it breaks. Hints get more specific as you keep working. Run your code or explain your thinking to unlock the next level.'
              : scope === 'general'
                ? coding
                  ? 'I know your plan, your progress and the whole practice library. Ask what to study, which problems to do next, or anything you are stuck on.'
                  : 'I know your plan and your progress. Ask what to study next, to quiz you, or about anything you are stuck on.'
                : scope === 'plan'
                  ? "Let's shape your roadmap together. I'll ask a few questions, then suggest changes you can accept or skip. Nothing changes without your yes."
                  : 'Ask about this lesson, an idea that feels fuzzy, or what to focus on next.'}
            {!problem ? (
              <div className="mt-4 grid gap-2">
                {(coding ? STARTERS : STARTERS_NO_CODE)[scope === 'general' || scope === 'plan' ? scope : 'concept'].map(s => (
                  <Button key={s} type="button" variant="outline" size="sm" className="h-auto min-h-11 justify-start rounded-[4px] py-2.5 text-left font-medium whitespace-normal" disabled={busy || !loaded} onClick={() => send('chat', s)}>
                    {s}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        {messages.map((m, i) => {
          const typing = typed !== null && i === messages.length - 1 && m.role === 'assistant';
          const content = typing ? m.content.slice(0, typed) : m.content;
          return m.role === 'user' ? (
            <div key={i} className="chat-bubble-user">{m.content}</div>
          ) : (
            <div key={i} className="flex items-end gap-2">
            <Soc size={28} mood={busy && i === messages.length - 1 ? 'thinking' : m.rating === 1 ? 'happy' : 'neutral'} className="mb-1" />
            <div className="chat-bubble-assistant min-w-0 flex-1">
              {/* Finished steps get a tick; the step in progress is the scribble below. */}
              {busy && i === messages.length - 1 && activity.length > 1 && !content ? (
                <ul className="mb-1 grid gap-1 text-xs text-muted-foreground" aria-label="What the tutor checked">
                  {activity.slice(0, -1).map(a => (
                    <li key={a} className="flex items-center gap-2"><Check className="size-3" />{a}</li>
                  ))}
                </ul>
              ) : null}
              {content ? (
                <>
                {/* While typing, a pen-stroke caret trails the last word. */}
                <Markdown source={typing ? `${content}▍` : content} language={language} className="prose-compact" />
                {m.id && !typing && !(busy && i === messages.length - 1) ? (
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
              ) : <Thinking label={activity[activity.length - 1]} />}
            </div>
            </div>
          );
        })}
        {proposals.length && !busy ? (
          <div aria-label="Plan changes Soc suggested">
            <ProposalList compact proposals={proposals} onDecided={v => setProposals(v.pending.filter(p => p.source === 'tutor'))} />
          </div>
        ) : null}
      </div>
      {error ? <p role="alert" className="mx-4 mb-2 rounded-[4px] border border-attention px-3 py-2 text-sm">{error}</p> : null}
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
