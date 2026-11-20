'use client';

/**
 * Lesson 0: the only way into Socrat. A goal in the learner's words, a mode, a door (an everyday
 * scenario for this goal), an honest daily time budget, then a quick win, a snag and a reveal,
 * all before any account. Sign-in comes last and turns the draft into a course plan.
 * The server keeps the answer keys and grades every tap (`socrat/onboarding.py`).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from '@/components/icons';
import { api, explain } from '@/lib/api';
import { useSession } from '@/lib/session';
import { ErrorNote, Loading } from '@/components/common';
import { Choice } from '@/components/choice';
import { ArrowCircle, Button } from '@/components/ui/button';
import { FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { Soc } from '@/components/socrat/illustration';
import { Celebrate } from '@/components/socrat/celebrate';
import { PebbleFriend } from '@/components/socrat/pebble-friend';
import { dailyGoalName } from '@/lib/game';
import { cn } from '@/lib/utils';

type Mode = 'sprint' | 'builder' | 'explorer';
type Task = { prompt: string; scene: string; options: string[] };
type Draft = {
  id: string;
  subject: string;
  goal: string;
  doors: string[];
  mode: Mode | null;
  door: string | null;
  safety_notes: string[];
  calibration: 'pending' | 'ready' | 'none';
  win: Task | null;
  snag: Task | null;
  hint: string | null;
  reveal: { explain: string; concept: string; real_world: string } | null;
  progress: Record<string, { done: boolean; tries: number }>;
  request_id: string | null;
};
type Result = { correct: boolean; nudge: string; done: boolean; answer: number | null };
type Plan = {
  id: string;
  status: string;
  published: boolean;
  enroll: Record<string, unknown> | null;
  job: { state: string } | null;
  skeleton: { title: string; modules: { title: string; lessons: string[] }[] } | null;
  blueprint: { title: string; tagline: string; modules: { id: string; title: string; concepts: { id: string; title: string }[] }[] } | null;
  // When the learner can start (onboarding-handoff.md 3.3): their first lesson is written.
  start?: { state: 'waiting' | 'roadmap_ready' | 'first_lesson_ready' | 'first_lesson_failed'; concept: string | null; retry: boolean };
  // A later level Lesson 0 suggests once the course is published; only ever an offer.
  level_suggestion?: { level: string; start: string; reason: string } | null;
};
const SETTLED = new Set(['first_lesson_ready', 'first_lesson_failed']);
type Step = 'goal' | 'mode' | 'door' | 'time' | 'win' | 'snag' | 'reveal' | 'save' | 'plan';

const STEPS: Step[] = ['goal', 'mode', 'door', 'time', 'win', 'snag', 'reveal', 'save'];
const KEY = 'socrat:lesson0';
const MODES: { id: Mode; title: string; body: string }[] = [
  { id: 'sprint', title: 'Sprint', body: 'An exam or a deadline. Fast, high-yield, no detours.' },
  { id: 'builder', title: 'Builder', body: 'Make something real. Theory only when the project needs it.' },
  { id: 'explorer', title: 'Deep explorer', body: 'Understand the why. Slower, and it sticks.' },
];
const MINUTES = [
  { m: 10, label: '10 min', body: 'Tiny steps that still add up' },
  { m: 25, label: '25 min', body: 'One solid lesson a day' },
  { m: 60, label: '60 min', body: 'Room to go deep' },
];
const EXAMPLES = ['Build a REST API', 'Pass my DBMS exam', 'Understand stock investing', 'Play my first song on guitar'];

function Ask({ eyebrow, title, body, trio }: { eyebrow?: string; title: string; body?: string; trio?: boolean }) {
  return (
    <div className={cn('flex items-start justify-between gap-4', trio && 'max-sm:flex-col-reverse max-sm:gap-1')}>
      <div className="min-w-0">
        {eyebrow ? <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">{eyebrow}</p> : null}
        <h1 className="type-display-l mt-1 text-balance">{title}</h1>
        {body ? <p className="mt-3 text-base text-muted-foreground">{body}</p> : null}
      </div>
      <Soc size={88} mood="curious" className="nb-only mt-2 hidden sm:block" />
      {trio ? (
        <span aria-hidden="true" className="db-only relative mt-1 h-[92px] w-[132px] flex-none">
          <PebbleFriend kind="jade" size={52} className="db-bob absolute bottom-0 left-0 -rotate-6 [animation-delay:400ms]" />
          <PebbleFriend kind="ember" size={48} className="db-bob absolute right-0 bottom-1 rotate-6 [animation-delay:800ms]" />
          <PebbleFriend kind="soc" mood="happy" size={72} className="db-bob absolute top-0 left-[30px]" />
        </span>
      ) : (
        <PebbleFriend kind="soc" size={72} className="db-only db-bob mt-2 hidden sm:block" />
      )}
    </div>
  );
}

function detectTimezone() {
  try { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch { return 'UTC'; }
}

export default function Start() {
  const router = useRouter();
  const { profile, features, loading, refresh } = useSession();
  const [step, setStep] = useState<Step>('goal');
  const [text, setText] = useState('');
  const [draft, setDraft] = useState<Draft | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [minutes, setMinutes] = useState<number | null>(null);
  const [ownDoor, setOwnDoor] = useState('');
  const [picked, setPicked] = useState<number | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [note, setNote] = useState('');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [offer, setOffer] = useState<Plan | null>(null);
  const [birthYear, setBirthYear] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [restored, setRestored] = useState(false);
  const pending = useRef<Promise<Draft> | null>(null);
  const shownAt = useRef(0);
  const claiming = useRef(false);

  useEffect(() => { window.scrollTo({ top: 0 }); shownAt.current = performance.now(); }, [step]);

  // A reload, or the return from Google sign-in, picks up where the learner was.
  useEffect(() => {
    let saved: { id?: string; step?: Step; mode?: Mode; minutes?: number; text?: string } = {};
    try { saved = JSON.parse(sessionStorage.getItem(KEY) ?? '{}'); } catch { /* start fresh */ }
    if (!saved.id) { setRestored(true); return; }
    setText(saved.text ?? '');
    setMode(saved.mode ?? null);
    setMinutes(saved.minutes ?? null);
    api.get<Draft>(`/onboarding/${saved.id}`)
      .then(d => { setDraft(d); setStep(d.request_id ? 'plan' : saved.step ?? 'door'); })
      .catch(() => { try { sessionStorage.removeItem(KEY); } catch { /* ignore */ } })
      .finally(() => setRestored(true));
  }, []);
  useEffect(() => {
    if (!restored) return;
    try { sessionStorage.setItem(KEY, JSON.stringify({ id: draft?.id, step, mode, minutes, text })); } catch { /* per-viewer nicety */ }
  }, [restored, draft?.id, step, mode, minutes, text]);

  async function act<T>(work: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError('');
    try { return await work(); } catch (e) { setError(explain(e)); return undefined; } finally { setBusy(false); }
  }

  // Stage 1: reading the goal and writing the doors runs while the learner picks a mode.
  function submitGoal(event: React.FormEvent) {
    event.preventDefault();
    if (text.trim().length < 3) return;
    setError('');
    const call = api.post<Draft>('/onboarding', { text: text.trim() });
    pending.current = call;
    call.then(setDraft).catch(e => { setError(explain(e)); setStep('goal'); });
    setStep('mode');
  }

  async function chooseMode(m: Mode) {
    setMode(m);
    setStep('door');
    if (!draft && pending.current) await act(() => pending.current as Promise<Draft>);
  }

  // The calibration is written for the chosen door while the learner picks a time budget.
  function chooseDoor(door: string) {
    if (!draft || !mode || !door.trim()) return;
    setStep('time');
    pending.current = api.post<Draft>(`/onboarding/${draft.id}/choose`, { mode, door: door.trim() });
    pending.current.then(setDraft).catch(e => setError(explain(e)));
  }

  async function chooseTime(m: number) {
    setMinutes(m);
    const ready = draft?.calibration === 'pending' && pending.current ? await act(() => pending.current as Promise<Draft>) : draft;
    if (!ready) return;
    setStep(ready.calibration === 'ready' ? 'win' : 'save');
  }

  async function answer(stepName: 'win' | 'snag', choice: number | null) {
    if (!draft) return;
    const ms = Math.round(performance.now() - shownAt.current);
    const out = await act(() => api.post<Draft & { result: Result }>(`/onboarding/${draft.id}/answer`, { step: stepName, choice, ms, note: note.trim() }));
    shownAt.current = performance.now();
    if (!out) return;
    setDraft(out);
    setResult(out.result);
  }

  function next() {
    setResult(null);
    setPicked(null);
    setNote('');
    setStep(step === 'win' ? 'snag' : step === 'snag' ? 'reveal' : 'save');
  }

  async function hint() {
    if (!draft) return;
    const out = await act(() => api.post<Draft>(`/onboarding/${draft.id}/hint`, {}));
    if (out) setDraft(out);
  }

  const claim = useCallback(async () => {
    if (!draft || !minutes || claiming.current) return;
    claiming.current = true;
    setBusy(true);
    setError('');
    try {
      if (profile && !profile.birth_year) {
        await api.patch('/me', { birth_year: Number(birthYear), birthday_passed: true, timezone: detectTimezone() });
        await refresh();
      }
      const out = await api.post<{ draft: Draft; request: Plan }>(`/onboarding/${draft.id}/claim`, { minutes });
      setDraft(out.draft);
      setPlan(out.request);
      setStep('plan');
    } catch (e) {
      setError(explain(e));
    } finally {
      claiming.current = false;
      setBusy(false);
    }
  }, [draft, minutes, profile, birthYear, refresh]);

  // Back from sign-in with an age already on the account: save the course without asking again.
  useEffect(() => {
    if (step === 'save' && profile?.birth_year && draft && minutes && !error) void claim();
  }, [step, profile?.birth_year, draft, minutes, error, claim]);

  // The plan is written in the background; ask again until it can be started.
  useEffect(() => {
    if (step !== 'plan' || !draft?.request_id) return;
    let alive = true;
    const look = () => api.get<Plan>(`/learning-requests/${draft.request_id}`).then(p => { if (alive) setPlan(p); }).catch(() => undefined);
    void look();
    // Until the first lesson is written (or its writing failed), not just until the plan exists.
    const settled = !!plan?.start && SETTLED.has(plan.start.state);
    const timer = setInterval(() => { if (!settled) void look(); }, 2500);
    return () => { alive = false; clearInterval(timer); };
  }, [step, draft?.request_id, plan?.start?.state]);

  async function enrol(published: Plan, level?: string) {
    await api.post('/enrollments', level ? { ...published.enroll, level } : published.enroll);
    try { sessionStorage.removeItem(KEY); } catch { /* ignore */ }
    await refresh();
    router.push('/today');
  }

  async function begin() {
    if (!plan) return;
    await act(async () => {
      const published = await api.post<Plan>(`/learning-requests/${plan.id}/publish`, {});
      // A later start is only offered; the learner chooses (backlog 2.7).
      if (published.level_suggestion) setOffer(published);
      else await enrol(published);
    });
  }

  async function retryFirstLesson() {
    if (!plan?.start?.concept) return;
    await act(async () => {
      setPlan(await api.post<Plan>(`/learning-requests/${plan.id}/concepts/${plan.start!.concept}/regenerate`, {}));
    });
  }

  async function devSignIn() {
    await act(async () => {
      await api.post('/auth/dev-login', { subject: `learner-${Math.random().toString(36).slice(2, 8)}`, display_name: 'Learner' });
      await refresh();
    });
  }

  const thisYear = new Date().getFullYear();
  const years = useMemo(() => Array.from({ length: 90 }, (_, i) => thisYear - 13 - i), [thisYear]);

  if (loading || !restored) return <Loading variant="form" label="Loading" />;

  const position = Math.max(0, STEPS.indexOf(step === 'plan' ? 'save' : step));
  const back = { mode: 'goal', door: 'mode', time: 'door' }[step as string] as Step | undefined;
  const task = step === 'win' ? draft?.win : step === 'snag' ? draft?.snag : null;

  return (
    <div className="mx-auto w-full max-w-2xl px-4 pt-6 pb-32 sm:px-6 md:pt-10">
      <div className="mb-10 grid gap-3">
        <div className="flex min-h-11 items-center justify-between gap-4">
          {back ? <Button type="button" variant="ghost" size="sm" className="-ml-3" onClick={() => setStep(back)}><ArrowLeft data-icon="inline-start" /> Back</Button> : <span />}
          <p className="text-sm font-semibold text-muted-foreground">Lesson 0</p>
        </div>
        <Progress value={(100 * (position + 1)) / STEPS.length} aria-label={`Step ${position + 1} of ${STEPS.length}`} />
      </div>

      <div key={step} className="animate-in fade-in slide-in-from-bottom-2 duration-200">
        {step === 'goal' ? (
          <form onSubmit={submitGoal} className="grid gap-6">
            <Ask eyebrow="first question" trio title="What do you want to be able to actually do?" body="Any skill, in your own words. Messy is fine." />
            <Textarea autoFocus className="min-h-24 text-lg" maxLength={500} value={text} onChange={e => setText(e.target.value)} aria-label="What you want to be able to do" placeholder="For example: automate my boring Excel work" />
            <ul className="flex flex-wrap gap-2" aria-label="Examples">
              {EXAMPLES.map(x => <li key={x}><Button type="button" variant="outline" size="sm" onClick={() => setText(x)}>{x}</Button></li>)}
            </ul>
            <Button size="lg" className="justify-self-start" disabled={text.trim().length < 3}>Continue<ArrowCircle /></Button>
          </form>
        ) : null}

        {step === 'mode' ? (
          <div className="grid gap-6">
            <Ask title="What's your vibe right now?" body="This shapes the whole course. You can change it later." />
            <div className="grid gap-3">
              {MODES.map(m => (
                <Choice key={m.id} className="min-h-[72px]" selected={mode === m.id} aria-pressed={mode === m.id} onClick={() => void chooseMode(m.id)}>
                  <span className="choice-title block text-[17px] font-semibold">{m.title}</span>
                  <span className="block text-[15px] text-muted-foreground">{m.body}</span>
                </Choice>
              ))}
            </div>
          </div>
        ) : null}

        {step === 'door' ? (
          !draft ? <Loading variant="inline" label="Reading your goal" /> : (
            <div className="grid gap-6">
              <Ask title="Pick your door" body="We'll start from one of these everyday scenes. Pick the one that feels most like you." />
              <div className="grid gap-3 sm:grid-cols-2">
                {draft.doors.map(d => (
                  <Choice key={d} className="min-h-[72px]" selected={draft.door === d} aria-pressed={draft.door === d} onClick={() => chooseDoor(d)}>
                    <span className="choice-title block text-[17px] font-semibold">{d}</span>
                  </Choice>
                ))}
              </div>
              <form className="grid gap-2" onSubmit={e => { e.preventDefault(); chooseDoor(ownDoor); }}>
                <FieldLabel htmlFor="own-door">Or your own</FieldLabel>
                <div className="flex gap-2">
                  <Input id="own-door" maxLength={80} value={ownDoor} onChange={e => setOwnDoor(e.target.value)} placeholder="For example: my football team" />
                  <Button type="submit" variant="outline" disabled={ownDoor.trim().length < 2}>Use this</Button>
                </div>
              </form>
            </div>
          )
        ) : null}

        {step === 'time' ? (
          <div className="grid gap-6">
            <Ask title="On a tired, messy weekday, how many minutes can you really give this?" body="Be honest: lessons are cut to fit, so day two never feels like a wall." />
            <div className="grid gap-3 sm:grid-cols-3">
              {MINUTES.map(o => (
                <Choice key={o.m} className="min-h-[88px]" selected={minutes === o.m} aria-pressed={minutes === o.m} disabled={busy} onClick={() => void chooseTime(o.m)}>
                  <span className="db-only mb-0.5 block text-[12.5px] font-extrabold text-[var(--db-primary-lo)]">{dailyGoalName(o.m)}</span>
                  <span className="choice-title block text-lg font-semibold">{o.label}</span>
                  <span className="block text-[14px] text-muted-foreground">{o.body}</span>
                </Choice>
              ))}
            </div>
            {busy ? <Loading variant="inline" label="Setting up your first puzzle" /> : null}
          </div>
        ) : null}

        {(step === 'win' || step === 'snag') && task ? (
          <div className="grid gap-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">{step === 'win' ? 'warm up' : 'one step further'}</p>
                {/* A question, not a headline: up to three sentences must read at a glance. */}
                <h1 className="mt-2 text-xl leading-snug font-semibold text-balance">{task.prompt}</h1>
                {step === 'win' ? <p className="mt-2 text-sm text-muted-foreground">This helps Socrat pick where you start. Nothing here is graded.</p> : null}
              </div>
              <Soc size={72} mood="curious" className="mt-2 hidden sm:block" />
            </div>
            {task.scene ? <pre className="code-block whitespace-pre-wrap">{task.scene}</pre> : null}
            <div className="grid gap-3" role="radiogroup" aria-label="Your answer">
              {task.options.map((o, i) => {
                const settled = result?.done && result.answer !== null;
                const tone = settled && i === result.answer ? 'correct' : 'idle';
                return (
                  <Choice key={o} role="radio" aria-checked={picked === i} marker={String.fromCharCode(65 + i)} selected={picked === i} tone={tone} disabled={busy || !!result?.done} onClick={() => { setPicked(i); setResult(null); void answer(step, i); }}>
                    <span className="choice-title whitespace-pre-wrap">{o}</span>
                  </Choice>
                );
              })}
            </div>
            {result && !result.correct && result.nudge ? <p className="font-hand text-[22px] text-pen" role="status">{result.nudge}</p> : null}
            {result?.correct ? <p className="font-hand text-[22px] text-pen" role="status">{step === 'win' ? 'Exactly. Now a little further.' : 'You got it.'}</p> : null}
            {step === 'snag' && !result?.done ? (
              <div className="grid gap-3">
                {draft?.hint ? <p className="paper rounded-card p-4 text-[15px]">{draft.hint}</p> : null}
                <label className="grid gap-2 text-sm">
                  <span className="font-semibold">Explain your thinking <span className="font-normal text-muted-foreground">(optional, never graded)</span></span>
                  <Textarea className="min-h-16" maxLength={500} value={note} onChange={e => setNote(e.target.value)} />
                </label>
                <div className="flex flex-wrap gap-3">
                  {!draft?.hint ? <Button type="button" variant="outline" disabled={busy} onClick={() => void hint()}>Give me a hint</Button> : null}
                  <Button type="button" variant="ghost" disabled={busy} onClick={() => void answer('snag', null)}>I&apos;m stuck, show me</Button>
                </div>
              </div>
            ) : null}
            {result?.done || (step === 'snag' && draft?.reveal) ? <Button size="lg" className="justify-self-start" onClick={next}>Continue<ArrowCircle /></Button> : null}
          </div>
        ) : null}

        {step === 'reveal' && draft?.reveal ? (
          <div className="grid gap-6">
            <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">here&apos;s the trick</p>
            <p className="text-lg">{draft.reveal.explain}</p>
            <h1 className="type-display-l">You just used <span className="hl hl-draw">{draft.reveal.concept}</span></h1>
            <p className="text-base text-muted-foreground">{draft.reveal.real_world}</p>
            <Button size="lg" className="justify-self-start" onClick={() => setStep('save')}>Build my course from here<ArrowCircle /></Button>
          </div>
        ) : null}

        {step === 'save' ? (
          <div className="grid gap-6">
            <Ask
              title={draft?.calibration === 'none' ? 'Your course starts here' : 'Save your course'}
              body={draft?.calibration === 'none' ? 'The first puzzle could not be set up right now, so your first lesson will find where you start instead.' : 'Sign in so your plan and progress are kept. Your answers are already in.'}
            />
            {/* Shown here, not earlier: by now the draft holds the model's reading of the goal. */}
            {draft?.safety_notes.map(n => <p key={n} className="text-sm">{n}</p>)}
            {!profile ? (
              <div className="grid gap-3">
                {features?.oidc_login ? <Button asChild variant="outline" size="lg" className="w-full"><a href="/api/v1/auth/login">Continue with Google</a></Button> : null}
                {features?.dev_login ? <Button type="button" variant="outline" size="lg" className="w-full" onClick={() => void devSignIn()}>Continue as a test learner (development)</Button> : null}
                {features && !features.oidc_login && !features.dev_login ? <p className="text-[15px] text-muted-foreground">Sign-in is not configured on this server.</p> : null}
                <p className="text-[13px] text-muted-foreground">
                  By continuing you agree to the <a href="/terms" className="underline underline-offset-4">terms</a> and the <a href="/privacy" className="underline underline-offset-4">privacy policy</a>. You must be 13 or older.
                </p>
              </div>
            ) : !profile.birth_year ? (
              <form className="grid gap-4" onSubmit={e => { e.preventDefault(); void claim(); }}>
                <div className="grid gap-2">
                  <FieldLabel htmlFor="birth-year">Year you were born</FieldLabel>
                  <NativeSelect id="birth-year" className="w-full max-w-xs [&_select]:h-13" value={birthYear} onChange={e => setBirthYear(e.target.value)} required>
                    <NativeSelectOption value="" disabled>Choose a year</NativeSelectOption>
                    {years.map(y => <NativeSelectOption key={y} value={y}>{y}</NativeSelectOption>)}
                  </NativeSelect>
                  <p className="text-[13px] text-muted-foreground">Socrat is for learners aged 13 and over. Only the year is stored.</p>
                </div>
                <Button size="lg" className="justify-self-start" disabled={busy || !birthYear} aria-busy={busy}>Save my course<ArrowCircle loading={busy} /></Button>
              </form>
            ) : (
              <Loading variant="inline" label="Saving your course" />
            )}
          </div>
        ) : null}

        {step === 'plan' ? (
          <div className="grid gap-6">
            {plan?.blueprint && (!plan.start || plan.start.state === 'first_lesson_ready') ? <Celebrate kind="amber" emoji="map" sound="finish" className="-mb-4 justify-self-start" /> : null}
            <Ask title={plan?.blueprint?.title || plan?.skeleton?.title || 'Writing your course plan'} body={plan?.blueprint ? plan.blueprint.tagline : 'Module 1 first, the rest just before you reach it. This takes a minute.'} />
            {!plan?.blueprint ? <Loading variant="inline" label="Planning your course" /> : null}
            <ol className="grid gap-2">
              {(plan?.blueprint?.modules.map(m => ({ title: m.title, n: m.concepts.length })) ?? plan?.skeleton?.modules.map(m => ({ title: m.title, n: m.lessons.length })) ?? []).map((m, i) => (
                <li key={`${i}-${m.title}`} className="flex min-h-12 items-center justify-between gap-3 rounded-[4px] border bg-card px-4 py-3">
                  <span className="font-semibold">{m.title}</span>
                  <span className="text-[13px] text-muted-foreground">{m.n} lesson{m.n === 1 ? '' : 's'}</span>
                </li>
              ))}
            </ol>
            {plan?.job?.state === 'failed' ? <ErrorNote message="The plan could not be written. Try again in a moment." /> : null}
            {plan?.blueprint && plan.start?.state === 'roadmap_ready' ? (
              // Visible words, not placeholder bars: a live run waited 2-5 minutes here.
              <p role="status" className="flex items-center gap-3 rounded-[4px] border bg-card px-4 py-3 text-[15px]">
                <span aria-hidden className="size-2.5 shrink-0 animate-pulse rounded-full bg-primary" />
                Your first lesson is being written for you. It is usually ready in a few minutes; you can stay on this page.
              </p>
            ) : null}
            {plan?.start?.state === 'first_lesson_failed' ? (
              <div className="grid gap-3">
                <ErrorNote message="Your first lesson could not be written this time." />
                {plan.start.retry ? <Button variant="outline" className="justify-self-start" disabled={busy} onClick={() => void retryFirstLesson()}>Try again</Button> : null}
              </div>
            ) : null}
            {offer?.level_suggestion ? (
              <div className="grid gap-3 rounded-[4px] border bg-card p-4" role="group" aria-label="Where to start">
                <p className="text-sm">{offer.level_suggestion.reason}</p>
                <div className="flex flex-wrap gap-2">
                  <Button disabled={busy} onClick={() => void act(() => enrol(offer, offer.level_suggestion!.level))}>Start there</Button>
                  <Button variant="outline" disabled={busy} onClick={() => void act(() => enrol(offer))}>Start from the beginning</Button>
                </div>
              </div>
            ) : null}
            {/* Older servers send no ``start``: the plan alone is enough to begin, as before. */}
            {plan?.blueprint && !offer && (!plan.start || plan.start.state === 'first_lesson_ready') ? (
              <Button size="lg" className="justify-self-start" disabled={busy} aria-busy={busy} onClick={() => void begin()}>Start learning<ArrowCircle loading={busy} /></Button>
            ) : null}
          </div>
        ) : null}
      </div>

      {error ? <ErrorNote message={error} title={error && /age|valid/i.test(error) ? 'Check this' : undefined} /> : null}
      {error && step === 'save' ? <Button className="mt-3" variant="outline" onClick={() => { setError(''); void claim(); }}>Try again</Button> : null}
    </div>
  );
}
