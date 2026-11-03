'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Check, Download, LogOut } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useReducedMotion } from '@/lib/motion';
import { useGuard, useSession } from '@/lib/session';
import { LANGUAGE_LABEL, NAME, hours } from '@/lib/routes';
import type { BillingStatus, Course, Language, Profile } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { Pill } from '@/components/choice';
import { TOUR_EVENT } from '@/components/tour';
import CodeforcesLink from '@/components/codeforces-link';
import { SuccessLine } from '@/components/socrat/states';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Switch } from '@/components/ui/switch';
import { useInstall } from '@/lib/pwa';
import { CommunityButton, useCommunityUrl } from '@/components/community-link';
import { LanguagePicker } from '@/components/language-picker';
import { DataUsePicker } from '@/components/data-use';
import { InstallAppButton } from '@/components/install-app';
import { Soc } from '@/components/socrat/illustration';

const MINUTES = [15, 20, 30, 45, 60, 90, 120];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const THEMES = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'system', label: 'System' },
] as const;

function Section({ id, title, description, children, className }: { id: string; title: string; description?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section aria-labelledby={id} className={cn('paper rounded-card p-5 lg:p-6', className)}>
      <h2 id={id} className="font-display text-xl font-semibold tracking-[-0.035em]"><span className="bg-[linear-gradient(transparent_62%,color-mix(in_srgb,var(--highlight)_70%,transparent)_62%)] px-0.5">{title}</span></h2>
      {description ? <p className="mt-1 text-[15px] text-muted-foreground">{description}</p> : null}
      <div className="mt-5">{children}</div>
    </section>
  );
}

const NAV = [
  { id: 'appearance', label: 'Appearance' },
  { id: 'schedule', label: 'Profile and schedule' },
  { id: 'connections', label: 'Plan and connections' },
  { id: 'account', label: 'Data and account' },
] as const;

/** Which section is in view, so the nav can say where you are. */
function useActiveSection() {
  const [active, setActive] = useState<string>(NAV[0].id);
  useEffect(() => {
    const seen = new Map<string, boolean>();
    const observer = new IntersectionObserver(entries => {
      for (const e of entries) seen.set(e.target.id, e.isIntersecting);
      const first = NAV.find(n => seen.get(n.id));
      if (first) setActive(first.id);
    }, { rootMargin: '-96px 0px -55% 0px' });
    for (const n of NAV) { const el = document.getElementById(n.id); if (el) observer.observe(el); }
    return () => observer.disconnect();
  }, []);
  return [active, setActive] as const;
}

function SectionNav({ active, onPick }: { active: string; onPick: (id: string) => void }) {
  return (
    <nav aria-label="Settings sections" className="sticky top-16 z-10 -mx-4 border-b bg-background/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6 lg:top-24 lg:mx-0 lg:self-start lg:border-0 lg:bg-transparent lg:p-0 lg:backdrop-blur-none">
      <ul className="no-scrollbar flex gap-1 overflow-x-auto lg:grid lg:overflow-visible">
        {NAV.map(n => (
          <li key={n.id} className="flex-none">
            <a
              href={`#${n.id}`}
              aria-current={active === n.id ? 'location' : undefined}
              onClick={() => onPick(n.id)}
              className={cn('flex min-h-10 items-center rounded-full px-4 text-[15px] font-medium whitespace-nowrap text-muted-foreground transition-colors hover:bg-raised hover:text-foreground lg:rounded-[14px]', active === n.id && 'bg-raised font-bold text-foreground')}
            >
              {n.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Current plan, what is left of it this period, and cancelling. */
function PlanSection() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [error, setError] = useState('');
  const load = () => api.get<BillingStatus>('/billing/status').then(setStatus).catch(() => undefined);
  useEffect(() => { void load(); }, []);
  if (!status?.enabled) return null;
  const paid = status.plan !== 'free';
  const left = (k: 'chat' | 'playground') => {
    const u = status.usage[k];
    return u.limit ? `${Math.max(0, u.limit - u.used)} of ${u.limit} left ${u.window === 'week' ? 'this week' : 'today'}` : 'locked on this plan';
  };
  async function cancel() {
    setError('');
    try { await api.post('/billing/cancel'); await load(); } catch (e) { setError(explain(e)); }
  }
  return (
    <Section id="plan-heading" title="Plan" description={<>You are on <strong className="capitalize">{status.plan}</strong>.</>}>
      <ul className="grid gap-1 text-[15px] text-muted-foreground">
        <li>Soc messages: {left('chat')}</li>
        <li>Playground: {left('playground')}</li>
        {paid && status.renews_at ? <li>{status.cancel_at_period_end ? 'Ends' : 'Renews'} on {new Date(status.renews_at * 1000).toLocaleDateString()}</li> : null}
      </ul>
      {error ? <ErrorNote message={error} className="mt-3" /> : null}
      <div className="mt-4 flex flex-wrap gap-3">
        <Button asChild variant="outline"><a href="/pricing">{paid ? 'Change plan' : 'See plans'}</a></Button>
        {paid && !status.cancel_at_period_end ? <Button variant="outline" onClick={() => void cancel()}>Cancel renewal</Button> : null}
      </div>
    </Section>
  );
}

/** Install to the home screen and the beta community; hidden when neither applies. */
function AppSection() {
  const { state } = useInstall();
  const community = useCommunityUrl();
  const installable = state === 'prompt' || state === 'ios';
  if (!installable && !community) return null;
  return (
    <Section id="app-heading" title="App and community" description="Install Socrat on your phone for lessons, checks, reviews and Soc on the go. Writing code works best on a laptop.">
      <div className="flex flex-wrap gap-3">
        <InstallAppButton />
        <CommunityButton />
      </div>
    </Section>
  );
}

/** A small flat preview of each theme: canvas, card, a brand bar. */
function ThemePreview({ id }: { id: 'light' | 'dark' | 'system' }) {
  const swatch = (bg: string, card: string, text: string) => (
    <span className="flex h-16 flex-1 flex-col gap-1.5 p-2" style={{ background: bg }}>
      <span className="h-2 w-10 rounded-full" style={{ background: text }} />
      <span className="flex-1 rounded-md p-1.5" style={{ background: card }}><span className="block h-2 w-8 rounded-full bg-[#2340E8]" /></span>
    </span>
  );
  const light = swatch('#F6F5F0', '#FFFFFF', '#15161E');
  const dark = swatch('#121318', '#1A1B21', '#ECEBE5');
  return <span className="flex w-full overflow-hidden rounded-[14px] border" aria-hidden="true">{id === 'light' ? light : id === 'dark' ? dark : <>{light}{dark}</>}</span>;
}

function Appearance() {
  const { theme, setTheme } = useTheme();
  const motion = useReducedMotion();
  const { profile, refresh } = useSession();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return (
    <Section id="appearance-heading" title="Appearance" description="System follows your device.">
      <div className="grid gap-6 lg:grid-cols-2 lg:gap-10">
        <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Theme">
          {THEMES.map(t => {
            const active = mounted && (theme ?? 'system') === t.id;
            return (
              <button
                key={t.id}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(t.id)}
                className={cn('grid content-start gap-2 rounded-[20px] border border-border-strong p-2 pb-3 text-left transition-colors hover:bg-raised', active && 'border-primary ring-1 ring-primary')}
              >
                <ThemePreview id={t.id} />
                <span className="flex items-center gap-1.5 px-1 text-[15px] font-medium">
                  {active ? <Check className="size-4 text-brand" aria-hidden="true" /> : null}
                  <span className={cn(active && 'font-bold')}>{t.label}</span>
                </span>
              </button>
            );
          })}
        </div>
        <div className="grid content-start divide-y">
          <LanguagePicker />
          <div className="flex items-start justify-between gap-4 py-5">
            <div>
              <label htmlFor="reduce-motion" className="font-semibold">Reduce motion</label>
              <p id="reduce-motion-help" className="text-sm text-muted-foreground">
                Turns off fades, slides and visual playback in this browser. {motion.reduced && !motion.setting ? 'Your device already asks for less motion.' : ''}
              </p>
            </div>
            <Switch id="reduce-motion" checked={motion.setting} onCheckedChange={motion.set} aria-describedby="reduce-motion-help" />
          </div>
          <DataUsePicker />
          <div className="flex items-start justify-between gap-4 py-5">
            <div>
              <label htmlFor="reminders" className="font-semibold">Study reminders</label>
              <p id="reminders-help" className="text-sm text-muted-foreground">
                {profile?.can_remind === false
                  ? 'Reminders are sent by email, and this account has no email address.'
                  : 'One email in the early evening on a study day when you have not started yet. It stops after three you do not act on.'}
              </p>
            </div>
            <Switch
              id="reminders"
              checked={!!profile?.reminders}
              disabled={profile?.can_remind === false}
              onCheckedChange={async on => { await api.patch('/me', { reminders: on }); await refresh(); }}
              aria-describedby="reminders-help"
            />
          </div>
          {profile?.enrollment?.status === 'active' ? (
            <div className="flex items-center justify-between gap-4 pt-5">
              <div>
                <p className="font-semibold">Tour of Socrat</p>
                <p className="text-sm text-muted-foreground">A one-minute walk through each section.</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => window.dispatchEvent(new CustomEvent(TOUR_EVENT))}>Replay tour</Button>
            </div>
          ) : null}
        </div>
      </div>
    </Section>
  );
}

export default function Settings() {
  const allowed = useGuard('enrolled');
  const { profile, refresh, signOut } = useSession();
  const router = useRouter();
  const [course, setCourse] = useState<Course | null>(null);
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<Language>('python');
  const [minutes, setMinutes] = useState(30);
  const [weekdays, setWeekdays] = useState<number[]>([]);
  const [targetDate, setTargetDate] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState<'idle' | 'busy' | 'done'>('idle');
  const [confirmDelete, setConfirmDelete] = useState('');
  const [section, setSection] = useActiveSection();

  useEffect(() => {
    if (!profile?.enrollment) return;
    const e = profile.enrollment;
    setName(profile.display_name ?? '');
    setLanguage(e.language);
    setMinutes(e.minutes_per_day);
    setWeekdays(e.weekdays);
    setTargetDate(String(e.goal.target_date ?? ''));
    api.get<{ items: Course[] }>('/courses').then(r => setCourse(r.items.find(c => c.id === e.course) ?? null)).catch(() => undefined);
  }, [profile]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setStatus('');
    try {
      if (name.trim() && name.trim() !== profile?.display_name) await api.patch('/me', { display_name: name.trim() });
      await api.patch<Profile>('/enrollments/current', {
        language,
        minutes_per_day: minutes,
        weekdays,
        ...(targetDate ? { target_date: targetDate } : { clear_target_date: true }),
      });
      await refresh();
      setStatus(`Saved. Your plan was updated at ${new Date().toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}.`);
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  async function exportData() {
    setExporting('busy');
    setError('');
    try {
      const data = await api.get<unknown>('/me/export');
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `socrat-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setExporting('done');
    } catch (e) {
      setError(explain(e));
      setExporting('idle');
    }
  }

  async function deleteAccount() {
    setBusy(true);
    try {
      await api.del('/me');
      await signOut().catch(() => undefined);
      await refresh();
      router.replace('/');
    } catch (e) {
      setError(explain(e));
      setBusy(false);
    }
  }

  if (!allowed || !profile?.enrollment) return <Loading variant="form" label="Loading settings" />;
  const toggleDay = (i: number) => setWeekdays(w => (w.includes(i) ? (w.length > 1 ? w.filter(x => x !== i) : w) : [...w, i].sort()));

  return (
    <Page>
      <PageHeader eyebrow="make it yours" title={NAME.settings} description="Changes to your schedule update your plan straight away." actions={<Soc size={88} mood="wink" className="hidden sm:block" />} />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10">
        <SectionNav active={section} onPick={setSection} />
        <div className="grid min-w-0 gap-10">
        <div id="appearance" className="scroll-mt-32"><Appearance /></div>

        <form id="schedule" onSubmit={save} data-tour="settings-schedule" className="scroll-mt-32">
          <Section id="schedule-heading" title="Profile and schedule" description="How Socrat addresses you and how much time you have.">
            <div className="grid gap-6">
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                <Field>
                  <FieldLabel htmlFor="settings-name">Name</FieldLabel>
                  <Input id="settings-name" value={name} onChange={e => setName(e.target.value)} maxLength={80} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="settings-language">Language</FieldLabel>
                  <NativeSelect id="settings-language" className="w-full [&_select]:h-13" value={language} onChange={e => setLanguage(e.target.value as Language)}>
                    {(course?.languages ?? [language]).map(l => <NativeSelectOption key={l} value={l}>{LANGUAGE_LABEL[l]}</NativeSelectOption>)}
                  </NativeSelect>
                </Field>
                <Field>
                  <FieldLabel htmlFor="settings-target">Target date</FieldLabel>
                  <Input id="settings-target" type="date" value={targetDate} onChange={e => setTargetDate(e.target.value)} aria-describedby="settings-target-help" />
                  <FieldDescription id="settings-target-help">Leave empty for no deadline.</FieldDescription>
                </Field>
              </div>
              <div className="grid gap-6 lg:grid-cols-2 lg:gap-10">
              <fieldset>
                <legend className="mb-2 text-[15px] font-semibold">Time per study day</legend>
                <div className="flex flex-wrap gap-2">
                  {MINUTES.map(m => <Pill key={m} pressed={minutes === m} onClick={() => setMinutes(m)}>{hours(m)}</Pill>)}
                </div>
              </fieldset>
              <fieldset>
                <legend className="mb-2 text-[15px] font-semibold">Study days</legend>
                <div className="flex flex-wrap gap-2">
                  {DAYS.map((d, i) => <Pill key={d} pressed={weekdays.includes(i)} onClick={() => toggleDay(i)}>{d}</Pill>)}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{hours(minutes)} on {weekdays.length} day{weekdays.length === 1 ? '' : 's'} is {hours(minutes * weekdays.length)} a week.</p>
              </fieldset>
              </div>
              <div className="flex flex-wrap items-center gap-4 border-t pt-5">
                <Button disabled={busy} aria-busy={busy}>{busy ? 'Saving' : 'Save changes'}</Button>
                {status ? <SuccessLine>{status}</SuccessLine> : null}
              </div>
            </div>
          </Section>
        </form>

        <div id="connections" className="scroll-mt-32 grid items-start gap-4 lg:grid-cols-2 lg:gap-6">
          <PlanSection />
          <CodeforcesLink />
          <AppSection />
        </div>

        <div id="account" className="scroll-mt-32 grid items-start gap-4 lg:grid-cols-2 lg:gap-6">
        <Section id="data-heading" title="Your data" description={<>Download everything Socrat stores about you: profile, enrollments, results, code submissions and tutor conversations. How we use it: <a href="/privacy" className="underline underline-offset-4">privacy policy</a> · <a href="/terms" className="underline underline-offset-4">terms</a>.</>}>
          <div className="flex flex-wrap items-center gap-4">
            <Button variant="outline" onClick={exportData} disabled={exporting === 'busy'} aria-busy={exporting === 'busy'}>
              <Download data-icon="inline-start" /> {exporting === 'busy' ? 'Preparing your export' : 'Download my data'}
            </Button>
            {exporting === 'done' ? <SuccessLine>Downloaded.</SuccessLine> : null}
          </div>
        </Section>

        <Section id="account-heading" title="Account">
          <Button variant="outline" onClick={async () => { await signOut(); router.replace('/login'); }}><LogOut data-icon="inline-start" /> Log out</Button>
        </Section>

          <div className="lg:col-span-2">
        <Section id="danger-heading" title="Danger zone" description="Permanently removes your account, progress, code and conversations." className="border-attention">
          <AlertDialog onOpenChange={open => { if (!open) setConfirmDelete(''); }}>
            <AlertDialogTrigger asChild><Button variant="destructive">Delete account</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete your account</AlertDialogTitle>
                <AlertDialogDescription>This permanently removes your learning data. Export it first if you want a copy. Type <strong className="text-foreground">delete</strong> to confirm.</AlertDialogDescription>
              </AlertDialogHeader>
              <Input value={confirmDelete} onChange={e => setConfirmDelete(e.target.value)} autoComplete="off" aria-label="Type delete to confirm" />
              <AlertDialogFooter>
                <AlertDialogCancel>Keep my account</AlertDialogCancel>
                <AlertDialogAction variant="attention" disabled={busy || confirmDelete.trim().toLowerCase() !== 'delete'} onClick={deleteAccount}>
                  Delete permanently
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </Section>
          </div>
        </div>
        {error ? <ErrorNote message={error} /> : null}
        </div>
      </div>
    </Page>
  );
}
