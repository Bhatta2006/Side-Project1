'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, BookOpen, Code2, Target, Trophy } from '@/components/icons';
import { ApiError, api, explain } from '@/lib/api';
import { useSession } from '@/lib/session';
import { LANGUAGE_LABEL, hours } from '@/lib/routes';
import type { Course, Language } from '@/lib/types';
import { ErrorNote, Loading } from '@/components/common';
import { Choice, Pill } from '@/components/choice';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Progress } from '@/components/ui/progress';
import { Soc } from '@/components/socrat/illustration';

const MINUTES = [15, 20, 30, 45, 60, 90, 120] as const;
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const ROLES = [
  ['internship', 'Internship'],
  ['new-grad', 'New grad'],
  ['mid-level', 'Mid-level'],
  ['senior', 'Senior'],
] as const;
type Step = 'about' | 'course' | 'level' | 'language' | 'schedule' | 'review';
const ORDER: Step[] = ['about', 'course', 'level', 'language', 'schedule', 'review'];
const COURSE_ICON: Record<string, typeof BookOpen> = { zero: BookOpen, dsa: Target, cp: Trophy };
const DRAFT_KEY = 'socrat:onboarding';
const MIN_AGE = 13;

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z" />
      <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6H1.3a12 12 0 0 0 0 10.8l4-3.1z" />
      <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z" />
    </svg>
  );
}

function detectTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

/** Each onboarding step is one of Soc's questions: he asks it from the margin. */
function Heading({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">quick question</p>
        <h1 className="type-display-l mt-1">{title}</h1>
        <p className="mt-3 text-base text-muted-foreground">{body}</p>
      </div>
      <Soc size={96} mood="curious" className="mt-2 hidden sm:block" />
    </div>
  );
}

/** One row on the review step, with an Edit link back to its step. */
function Summary({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }) {
  return (
    <div className="flex min-h-14 items-center justify-between gap-4 border-b py-3 last:border-0">
      <div className="min-w-0">
        <dt className="text-[13px] text-muted-foreground">{label}</dt>
        <dd className="font-semibold">{value}</dd>
      </div>
      <Button type="button" variant="link" size="sm" onClick={onEdit}>Edit<span className="sr-only"> {label.toLowerCase()}</span></Button>
    </div>
  );
}

/** Validation answers (age, missing details) are fixed in the form, not by retrying. */
const retryable = (message: string) => !/age|valid|details|already/i.test(message);

export default function Start() {
  const { profile, features, loading, refresh } = useSession();
  const allowed = !loading; // the questions come first; signing in happens at the end
  const router = useRouter();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [step, setStep] = useState<Step>('about');
  // Each step starts at the top, so the progress bar and Back are always in view.
  useEffect(() => { window.scrollTo({ top: 0 }); }, [step]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [restored, setRestored] = useState(false);
  // Set once a signed-out learner heads to sign in: on return the plan is created from the saved answers.
  const [pending, setPending] = useState(false);
  const finishing = useRef(false);

  const [name, setName] = useState('');
  const [birthYear, setBirthYear] = useState('');
  const [birthdayPassed, setBirthdayPassed] = useState(true);
  const [course, setCourse] = useState<Course | null>(null);
  const [level, setLevel] = useState('');
  const [language, setLanguage] = useState<Language | ''>('');
  const [minutes, setMinutes] = useState<number>(30);
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4]);
  const [targetDate, setTargetDate] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [targetRating, setTargetRating] = useState('');
  const [motivation, setMotivation] = useState('');

  const [runtimes, setRuntimes] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.get<{ items: Course[] }>('/courses').then(r => setCourses(r.items)).catch(e => setError(explain(e)));
    api.get<{ languages: Record<string, boolean> }>('/runtimes').then(r => setRuntimes(r.languages)).catch(() => undefined);
  }, []);
  useEffect(() => {
    if (!profile) return;
    // A finished course may start the next one (the API refuses unless the course is done).
    const moving = new URLSearchParams(window.location.search).get('next') === '1';
    if (profile.enrollment && !moving) { router.replace(profile.enrollment.status === 'placement' ? '/placement' : '/today'); return; }
    setName(n => n || profile.display_name || '');
    if (profile.birth_year) setStep(s => (s === 'about' ? 'course' : s));
  }, [profile, router]);

  // Choices survive moving between steps and a reload within this browser session.
  useEffect(() => {
    if (!courses || restored) return;
    setRestored(true);
    try {
      const saved = JSON.parse(sessionStorage.getItem(DRAFT_KEY) ?? 'null') as Record<string, unknown> | null;
      if (!saved) {
        const wanted = courses.find(c => c.id === new URLSearchParams(window.location.search).get('course'));
        if (wanted) { setCourse(wanted); if (wanted.languages.length === 1) setLanguage(wanted.languages[0]); }
        return;
      }
      const savedCourse = courses.find(c => c.id === saved.course) ?? null;
      if (typeof saved.name === 'string' && saved.name) setName(saved.name);
      if (typeof saved.birthYear === 'string') setBirthYear(saved.birthYear);
      setCourse(savedCourse);
      if (savedCourse && typeof saved.level === 'string') setLevel(saved.level);
      if (savedCourse && typeof saved.language === 'string') setLanguage(saved.language as Language);
      if (typeof saved.minutes === 'number') setMinutes(saved.minutes);
      if (Array.isArray(saved.weekdays) && saved.weekdays.length) setWeekdays(saved.weekdays as number[]);
      if (typeof saved.targetDate === 'string') setTargetDate(saved.targetDate);
      if (typeof saved.targetRole === 'string') setTargetRole(saved.targetRole);
      if (typeof saved.targetRating === 'string') setTargetRating(saved.targetRating);
      if (typeof saved.motivation === 'string') setMotivation(saved.motivation);
      if (saved.pending === true) setPending(true);
      const savedStep = saved.step as Step;
      // Never skip the profile step for an incomplete profile.
      if ((profile?.birth_year || (saved.name && saved.birthYear)) && ORDER.includes(savedStep) && savedStep !== 'about' && (savedCourse || savedStep === 'course')) setStep(savedStep);
    } catch { /* start fresh */ }
  }, [courses, restored, profile?.birth_year]);
  useEffect(() => {
    if (!restored) return;
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ step, name, birthYear, course: course?.id, level, language, minutes, weekdays, targetDate, targetRole, targetRating, motivation, pending }));
    } catch { /* per-viewer nicety only */ }
  }, [restored, step, name, birthYear, course, level, language, minutes, weekdays, targetDate, targetRole, targetRating, motivation, pending]);

  const thisYear = new Date().getFullYear();
  const years = useMemo(() => Array.from({ length: 90 }, (_, i) => thisYear - 13 - i), [thisYear]);
  const borderline = Number(birthYear) === thisYear - 13;

  async function saveAbout(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    if (thisYear - Number(birthYear) < MIN_AGE || (borderline && !birthdayPassed)) {
      setError(explain(new ApiError(422, 'minimum_age')));
      return;
    }
    if (!profile) { // saved with the plan once they sign in
      setStep(course ? 'level' : 'course');
      return;
    }
    setBusy(true);
    try {
      await api.patch('/me', {
        display_name: name.trim() || undefined,
        birth_year: Number(birthYear),
        birthday_passed: borderline ? birthdayPassed : true,
        timezone: detectTimezone(),
      });
      await refresh();
      setStep('course');
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  async function enroll(event: React.FormEvent) {
    event.preventDefault();
    if (!profile) { setPending(true); return; } // show the sign-in options
    await submitPlan();
  }

  async function devSignIn() {
    setError('');
    try {
      const subject = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 64) || 'learner';
      await api.post('/auth/dev-login', { subject, display_name: name.trim() });
      await refresh();
    } catch (e) {
      setError(explain(e));
    }
  }

  async function submitPlan() {
    if (!course || !language || !level) return;
    setBusy(true);
    setError('');
    try {
      if (!profile?.birth_year) {
        await api.patch('/me', { display_name: name.trim() || undefined, birth_year: Number(birthYear), birthday_passed: borderline ? birthdayPassed : true, timezone: detectTimezone() });
      }
      const body: Record<string, unknown> = { course: course.id, language, level, minutes_per_day: minutes, weekdays };
      if (targetDate) body.target_date = targetDate;
      if (targetRole) body.target_role = targetRole;
      if (targetRating) body.target_rating = Number(targetRating);
      if (motivation.trim()) body.motivation = motivation.trim();
      const result = await api.post<{ status: string }>('/enrollments', body);
      try { sessionStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ }
      await refresh();
      router.replace(result.status === 'placement' ? '/placement' : '/today');
    } catch (e) {
      setError(explain(e));
      setPending(false);
      setBusy(false);
    }
  }

  // Back from signing in with a finished set of answers: create the plan without asking again.
  useEffect(() => {
    if (!restored || !pending || !profile || finishing.current || !course || !language || !level) return;
    if (!profile.birth_year && !birthYear) return;
    finishing.current = true;
    void submitPlan();
  });

  if (!allowed || !courses) return error ? <div className="mx-auto max-w-2xl p-6"><ErrorNote message={error} /></div> : <Loading variant="form" label="Loading setup" />;

  // Sign in first: the plan, the placement check and every answer are kept from the start.
  if (!profile) {
    return (
      <div className="mx-auto grid w-full max-w-md gap-8 px-4 pt-12 pb-32 sm:px-6 md:pt-20">
        <div className="grid justify-items-start gap-3">
          <Soc size={112} mood="curious" />
          <p className="font-hand origin-left -rotate-2 text-[22px] text-pen">before we start</p>
          <h1 className="type-display-l">Make your <span className="hl hl-draw">Socrat</span> account</h1>
          <p className="text-base text-muted-foreground">A few questions and a short placement check follow. Signing in first means none of it is lost.</p>
        </div>
        <div className="grid gap-3">
          {features?.oidc_login ? (
            <Button asChild size="lg" className="w-full"><a href="/api/v1/auth/login"><GoogleMark /> Continue with Google</a></Button>
          ) : null}
          {features?.dev_login ? (
            <Button type="button" variant="outline" size="lg" className="w-full" onClick={() => void devSignIn()}>Continue as a simulated learner (development)</Button>
          ) : null}
          {features && !features.oidc_login && !features.dev_login ? <p className="text-[15px] text-muted-foreground">Sign-in is not configured on this server.</p> : null}
        </div>
        <p className="text-[13px] text-muted-foreground">
          By continuing you agree to the <a href="/terms" className="underline underline-offset-4">terms of service</a> and the <a href="/privacy" className="underline underline-offset-4">privacy policy</a>. You must be 13 or older.
        </p>
        {error ? <ErrorNote message={error} /> : null}
      </div>
    );
  }

  const position = ORDER.indexOf(step);
  const back = position > (profile?.birth_year ? 1 : 0) ? () => setStep(ORDER[position - 1]) : undefined;
  const toggleDay = (i: number) => setWeekdays(w => (w.includes(i) ? (w.length > 1 ? w.filter(x => x !== i) : w) : [...w, i].sort()));
  const weekly = minutes * weekdays.length;

  return (
    <div className="mx-auto w-full max-w-2xl px-4 pt-6 pb-32 sm:px-6 md:pt-10">
      <div className="mb-10 grid gap-3">
        <div className="flex min-h-11 items-center justify-between gap-4">
          {back ? <Button type="button" variant="ghost" size="sm" className="-ml-3" onClick={back}><ArrowLeft data-icon="inline-start" /> Back</Button> : <span />}
          <p className="text-sm font-semibold text-muted-foreground tabular-nums">Step {position + 1} of {ORDER.length}</p>
        </div>
        <Progress value={(100 * (position + 1)) / ORDER.length} aria-label={`Step ${position + 1} of ${ORDER.length}`} />
      </div>

      <div key={step} className="animate-in fade-in slide-in-from-bottom-2 duration-200">
        {step === 'about' ? (
          <form onSubmit={saveAbout} className="grid gap-6">
            <Heading title="Let us set you up" body="Two quick details, then you choose what to learn." />
            <Field>
              <FieldLabel htmlFor="about-name">What should we call you?</FieldLabel>
              <Input id="about-name" className="max-w-md" value={name} onChange={e => setName(e.target.value)} maxLength={80} required />
            </Field>
            <Field>
              <FieldLabel htmlFor="about-year">Year you were born</FieldLabel>
              <NativeSelect id="about-year" className="w-full max-w-xs [&_select]:h-13" value={birthYear} onChange={e => setBirthYear(e.target.value)} required>
                <NativeSelectOption value="" disabled>Choose a year</NativeSelectOption>
                {years.map(y => <NativeSelectOption key={y} value={y}>{y}</NativeSelectOption>)}
              </NativeSelect>
              <FieldDescription>Socrat is for learners aged 13 and over. Only the year is stored.</FieldDescription>
            </Field>
            {borderline ? (
              <label className="flex min-h-11 items-center gap-3 text-[15px]">
                <Checkbox checked={birthdayPassed} onCheckedChange={v => setBirthdayPassed(v === true)} />
                I have already had my birthday this year
              </label>
            ) : null}
            <Button size="lg" className="justify-self-start" disabled={busy || !birthYear || !name.trim()} aria-busy={busy}>Continue<ArrowCircle loading={busy} /></Button>
          </form>
        ) : null}

        {step === 'course' ? (
          <div className="grid gap-6">
            <Heading title="What do you want to learn?" body="You can switch later. Foundations from other courses are added when you need them." />
            <div className="grid gap-3">
              {courses.map(c => {
                const Icon = COURSE_ICON[c.id] ?? Code2;
                return (
                  <Choice
                    key={c.id}
                    icon={<Icon />}
                    className="min-h-[72px]"
                    selected={course?.id === c.id}
                    aria-pressed={course?.id === c.id}
                    onClick={() => { setCourse(c); if (course?.id !== c.id) { setLevel(''); setLanguage(c.languages.length === 1 ? c.languages[0] : ''); } setStep('level'); }}
                  >
                    <span className="choice-title block text-[17px] font-semibold">{c.title}</span>
                    <span className="block text-[15px] text-muted-foreground">{c.tagline}</span>
                    <span className="mt-1 block text-[13px] text-muted-foreground">{c.concept_count} skills, {c.problem_count} judged problems</span>
                  </Choice>
                );
              })}
            </div>
          </div>
        ) : null}

        {step === 'level' && course ? (
          <div className="grid gap-6">
            <Heading title="How much do you already know?" body="If you pick a higher level, a short adaptive check confirms it, so nothing important gets skipped." />
            <div className="grid gap-3">
              {course.levels.map((l, i) => (
                <Choice key={l.id} marker={i + 1} className="min-h-[72px]" selected={level === l.id} aria-pressed={level === l.id} onClick={() => { setLevel(l.id); setStep('language'); }}>
                  <span className="choice-title block text-[17px] font-semibold">{l.label}</span>
                  <span className="block text-[15px] text-muted-foreground">{l.description}</span>
                </Choice>
              ))}
            </div>
          </div>
        ) : null}

        {step === 'language' && course ? (
          <div className="grid gap-6">
            <Heading title="Which language?" body="Lessons, examples, checks and your code editor all follow this choice. Not sure? Python reads closest to plain English." />
            <div className="grid gap-3 sm:grid-cols-3">
              {course.languages.map(l => {
                // Don't sell a language whose code can't run yet (D-7).
                const offline = Object.keys(runtimes).length > 0 && !runtimes[l];
                return (
                  <Choice key={l} disabled={offline} selected={language === l} aria-pressed={language === l} className="min-h-[72px] items-center justify-center disabled:opacity-60" onClick={() => { setLanguage(l); setStep('schedule'); }}>
                    <span className="block">
                      <span className="choice-title block text-center text-lg font-semibold">{LANGUAGE_LABEL[l]}</span>
                      {offline ? (
                        <span className="block text-center text-sm text-muted-foreground">Coming soon: code can't run yet</span>
                      ) : l === 'python' ? (
                        <span aria-hidden="true" className="mt-0.5 block text-center text-[13px] text-muted-foreground">Easiest to start with</span>
                      ) : null}
                    </span>
                  </Choice>
                );
              })}
            </div>
          </div>
        ) : null}

        {step === 'schedule' && course ? (
          <form onSubmit={e => { e.preventDefault(); setStep('review'); }} className="grid gap-8">
            <Heading title="When can you study?" body="Your plan fits into this time. Missed days never pile up; the plan moves forward instead." />
            <fieldset>
              <legend className="mb-3 text-[15px] font-semibold">Time per study day</legend>
              <div className="flex flex-wrap gap-2">
                {MINUTES.map(m => <Pill key={m} pressed={minutes === m} onClick={() => setMinutes(m)}>{hours(m)}</Pill>)}
              </div>
            </fieldset>
            <fieldset>
              <legend className="mb-3 text-[15px] font-semibold">Study days</legend>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((d, i) => <Pill key={d} pressed={weekdays.includes(i)} onClick={() => toggleDay(i)}>{d}</Pill>)}
              </div>
            </fieldset>
            <div className="rounded-card bg-raised p-5" role="status">
              <p className="type-display-m tabular-nums">{hours(weekly)} a week</p>
              <p className="mt-1 text-[15px] text-muted-foreground">{hours(minutes)} on {weekdays.length} day{weekdays.length === 1 ? '' : 's'} is {hours(weekly)} a week.</p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="target-date">Target date <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
                <Input id="target-date" type="date" value={targetDate} min={new Date().toISOString().slice(0, 10)} onChange={e => setTargetDate(e.target.value)} />
              </Field>
              {course.id === 'dsa' ? (
                <Field>
                  <FieldLabel htmlFor="target-role">Interviewing for <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
                  <NativeSelect id="target-role" className="w-full [&_select]:h-13" value={targetRole} onChange={e => setTargetRole(e.target.value)}>
                    <NativeSelectOption value="">No specific role</NativeSelectOption>
                    {ROLES.map(([id, label]) => <NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}
                  </NativeSelect>
                </Field>
              ) : null}
              {course.id === 'cp' ? (
                <Field>
                  <FieldLabel htmlFor="target-rating">Target rating <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
                  <Input id="target-rating" type="number" min={0} max={4000} step={50} value={targetRating} onChange={e => setTargetRating(e.target.value)} />
                </Field>
              ) : null}
            </div>
            <Field>
              <FieldLabel htmlFor="motivation">Why are you learning this? <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
              <Input id="motivation" value={motivation} onChange={e => setMotivation(e.target.value)} maxLength={280} aria-describedby="motivation-help" />
              <FieldDescription id="motivation-help">Your tutor keeps this in mind.</FieldDescription>
            </Field>
            <Button size="lg" className="justify-self-start">Continue<ArrowCircle /></Button>
          </form>
        ) : null}

        {step === 'review' && course ? (
          <form onSubmit={enroll} className="grid gap-8">
            <Heading title="Check your choices" body="Your plan is built from these. You can change study time later in Settings." />
            <dl className="paper rounded-card px-5">
              <Summary label="Course" value={course.title} onEdit={() => setStep('course')} />
              <Summary label="Starting level" value={course.levels.find(l => l.id === level)?.label ?? 'Not chosen'} onEdit={() => setStep('level')} />
              <Summary label="Language" value={language ? LANGUAGE_LABEL[language] : 'Not chosen'} onEdit={() => setStep('language')} />
              <Summary label="Study time" value={`${hours(minutes)} on ${weekdays.map(i => DAYS[i]).join(', ')}`} onEdit={() => setStep('schedule')} />
              {targetDate ? <Summary label="Target date" value={new Date(`${targetDate}T00:00:00`).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })} onEdit={() => setStep('schedule')} /> : null}
            </dl>
            {!profile && pending ? (
              <div className="paper grid gap-4 rounded-card p-5" role="region" aria-label="Sign in to save your plan">
                <div>
                  <h2 className="font-display text-xl font-bold tracking-[-0.02em]">Save your plan</h2>
                  <p className="mt-1 text-[15px] text-muted-foreground">Sign in so your plan and progress are kept. Your answers are already filled in.</p>
                </div>
                {features?.oidc_login ? (
                  <Button asChild variant="outline" size="lg" className="w-full"><a href="/api/v1/auth/login"><GoogleMark /> Continue with Google</a></Button>
                ) : null}
                {features?.dev_login ? (
                  <Button type="button" variant="outline" size="lg" className="w-full" onClick={() => void devSignIn()}>Continue as {name.trim() || 'a simulated learner'} (development)</Button>
                ) : null}
                {features && !features.oidc_login && !features.dev_login ? <p className="text-[15px] text-muted-foreground">Sign-in is not configured on this server.</p> : null}
                <p className="text-[13px] text-muted-foreground">
                  By continuing you agree to the <a href="/terms" className="underline underline-offset-4">terms of service</a> and the <a href="/privacy" className="underline underline-offset-4">privacy policy</a>. You must be 13 or older.
                </p>
              </div>
            ) : (
              <Button size="lg" className="justify-self-start" disabled={busy || !level || !language} aria-busy={busy}>
                {busy ? 'Creating your plan' : profile ? 'Create my plan' : 'Save my plan'}<ArrowCircle loading={busy} />
              </Button>
            )}
            {!level || !language ? <p className="text-sm text-muted-foreground">Choose a level and a language first.</p> : null}
          </form>
        ) : null}
      </div>

      {error ? <ErrorNote message={error} title={retryable(error) ? undefined : 'Check this'} /> : null}
    </div>
  );
}
