'use client';

import { useEffect, useMemo, useState } from 'react';
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
import { PlanBuildingRun, WELCOME_KEY } from '@/components/socrat/plan-building';

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
  const { profile, loading, refresh } = useSession();
  const allowed = !loading; // the questions and placement come first; signing in happens after
  const router = useRouter();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [step, setStep] = useState<Step>('about');
  // Each step starts at the top, so the progress bar and Back are always in view.
  useEffect(() => { window.scrollTo({ top: 0 }); }, [step]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [restored, setRestored] = useState(false);
  // Back from signing in after placement: play the plan being built instead of a list.
  const [welcome, setWelcome] = useState(false);

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
    if (profile.enrollment && !moving) {
      let returning = false;
      // Cleared when the animation ends, not here: effects may run twice.
      try { returning = sessionStorage.getItem(WELCOME_KEY) === '1'; } catch { /* storage unavailable */ }
      if (returning && !profile.guest && profile.enrollment.status === 'active') { setWelcome(true); return; }
      if (!welcome) router.replace(profile.enrollment.status !== 'active' || profile.guest ? '/placement' : '/today');
      return;
    }
    setName(n => n || profile.display_name || '');
    if (profile.birth_year) setStep(s => (s === 'about' ? 'course' : s));
  }, [profile, router, welcome]);

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
      const savedStep = saved.step as Step;
      // Never skip the profile step for an incomplete profile.
      if ((profile?.birth_year || (saved.name && saved.birthYear)) && ORDER.includes(savedStep) && savedStep !== 'about' && (savedCourse || savedStep === 'course')) setStep(savedStep);
    } catch { /* start fresh */ }
  }, [courses, restored, profile?.birth_year]);
  useEffect(() => {
    if (!restored) return;
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ step, name, birthYear, course: course?.id, level, language, minutes, weekdays, targetDate, targetRole, targetRating, motivation }));
    } catch { /* per-viewer nicety only */ }
  }, [restored, step, name, birthYear, course, level, language, minutes, weekdays, targetDate, targetRole, targetRating, motivation]);

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
    if (!profile) { // a guest session holds the plan and placement until they sign in
      setBusy(true);
      setError('');
      try {
        await api.post('/auth/guest');
        await refresh();
      } catch (e) {
        setError(explain(e));
        setBusy(false);
        return;
      }
    }
    await submitPlan();
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
      setBusy(false);
    }
  }

  if (welcome) {
    return (
      <PlanBuildingRun
        onDone={() => {
          try { sessionStorage.removeItem(WELCOME_KEY); } catch { /* storage unavailable */ }
          router.replace('/today');
        }}
      />
    );
  }

  if (!allowed || !courses) return error ? <div className="mx-auto max-w-2xl p-6"><ErrorNote message={error} /></div> : <Loading variant="form" label="Loading setup" />;

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
            {!profile || profile.guest ? <p className="text-[15px] text-muted-foreground">Already have an account? <a href="/login" className="font-semibold underline underline-offset-4">Log in</a></p> : null}
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
            <Button size="lg" className="justify-self-start" disabled={busy || !level || !language} aria-busy={busy}>
              {busy ? 'Creating your plan' : 'Create my plan'}<ArrowCircle loading={busy} />
            </Button>
            {!level || !language ? <p className="text-sm text-muted-foreground">Choose a level and a language first.</p> : null}
          </form>
        ) : null}
      </div>

      {error ? <ErrorNote message={error} title={retryable(error) ? undefined : 'Check this'} /> : null}
    </div>
  );
}
