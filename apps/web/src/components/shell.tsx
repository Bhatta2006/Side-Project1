'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';
import { PageTransition, ScrollBar } from '@/components/motion';
import { ThemeToggle } from '@/components/theme-toggle';
import { useTheme } from 'next-themes';
import {
  ChartNoAxesColumn,
  Download,
  Flame,
  FlaskConical,
  House,
  LogOut,
  MessageCircle,
  MessageSquareWarning,
  Monitor,
  Moon,
  NotebookPen,
  PanelLeftClose,
  PanelLeftOpen,
  Route,
  Settings,
  Shapes,
  ShieldCheck,
  Sigma,
  SquareCode,
  Sparkles,
  Sun,
  type LucideIcon,
} from 'lucide-react';
import { api } from '@/lib/api';
import { COURSE_ROUTES, NAV, navFor, navItems, type NavKey } from '@/lib/routes';
import { useSession } from '@/lib/session';
import { practiceHref, useCourse } from '@/lib/course';
import { NavLabel } from '@/components/nav-label';
import { PLAN_NAME } from '@/lib/plans';
import { useInstall } from '@/lib/pwa';
import { useCommunityUrl } from '@/components/community-link';
import type { BillingStatus, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { CommandMenu } from '@/components/command-menu';
import { FeedbackButton, ReportProblem, openReportProblem } from '@/components/report-problem';
import { Tour } from '@/components/tour';
import { Wordmark } from '@/components/socrat/wordmark';
import { Soc } from '@/components/socrat/illustration';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const ICON: Record<NavKey, LucideIcon> = {
  today: House,
  skills: Route,
  practice: SquareCode,
  playground: Shapes,
  evidence: ChartNoAxesColumn,
  settings: Settings,
};
// Settings lives in the avatar menu on phones.
const MOBILE_KEYS = NAV.filter(item => item.key !== 'settings').map(item => item.key);

/** The studio's own icon in the Practice slot. */
const STUDIO_ICON: Record<string, LucideIcon> = { workbench: Sigma, lab: FlaskConical, reading: NotebookPen };
function iconFor(item: { key: NavKey }, studio?: string): LucideIcon {
  return (item.key === 'practice' && studio && STUDIO_ICON[studio]) || ICON[item.key];
}

function DevBanner() {
  const { features } = useSession();
  if (!features?.demo_mode && !features?.dev_login) return null;
  return (
    <div className="border-b bg-raised px-4 py-1.5 text-center text-[13px] text-muted-foreground">
      Local development build. Sign-in is simulated and code runs without a secure sandbox.
    </div>
  );
}

function ThemeItems() {
  const { theme, setTheme } = useTheme();
  return (
    <DropdownMenuRadioGroup value={theme ?? 'system'} onValueChange={setTheme}>
      <DropdownMenuRadioItem value="light"><Sun /> Light</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="dark"><Moon /> Dark</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="system"><Monitor /> System</DropdownMenuRadioItem>
    </DropdownMenuRadioGroup>
  );
}

function UserMenu() {
  const { profile, signOut } = useSession();
  const router = useRouter();
  const { state: installState, install } = useInstall();
  const community = useCommunityUrl();
  const name = profile?.display_name || 'Learner';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Account menu" data-tour="settings">
          <Avatar className="size-9">
            <AvatarFallback className="border-2 border-[var(--soc-outline)] bg-[var(--highlight)] text-[13px] font-semibold text-[#15161E]">{name.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="font-normal normal-case tracking-normal">
          <p className="text-[15px] font-semibold text-foreground">{name}</p>
          <p className="text-[13px] text-muted-foreground">Logged in</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild><Link href="/settings"><Settings /> Settings</Link></DropdownMenuItem>
        <DropdownMenuItem asChild><Link href="/pricing"><Sparkles /> Plans</Link></DropdownMenuItem>
        {profile?.admin ? <DropdownMenuItem asChild><Link href="/admin"><ShieldCheck /> Admin</Link></DropdownMenuItem> : null}
        <DropdownMenuItem onSelect={() => openReportProblem()}><MessageSquareWarning /> Report a problem</DropdownMenuItem>
        {community ? (
          <DropdownMenuItem asChild><a href={community} target="_blank" rel="noopener noreferrer"><MessageCircle /> WhatsApp community</a></DropdownMenuItem>
        ) : null}
        {installState === 'prompt' ? <DropdownMenuItem onSelect={() => { install(); }}><Download /> Install the app</DropdownMenuItem> : null}
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Theme</DropdownMenuLabel>
        <ThemeItems />
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={async () => { await signOut(); router.replace('/login'); }}>
          <LogOut /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Streak and today's minutes from the learner summary. Neutral: nothing about a streak is coloured. */
function Momentum() {
  const pathname = usePathname();
  const [today, setToday] = useState<Pick<Today, 'streak' | 'minutes'> | null>(null);
  useEffect(() => {
    api.get<{ streak: Today['streak'] | null; minutes: Today['minutes'] | null }>('/me/summary')
      .then(s => setToday(s.streak && s.minutes ? { streak: s.streak, minutes: s.minutes } : null))
      .catch(() => undefined);
  }, [pathname]);
  if (!today) return null;
  const percent = today.minutes.goal ? Math.min(100, (100 * today.minutes.done) / today.minutes.goal) : 0;
  const r = 13;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-1.5">
      {today.streak.current > 0 || today.streak.studied_today ? <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/progress"
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border-strong px-3 text-sm font-bold tabular-nums transition-colors hover:bg-raised"
            aria-label={`${today.streak.current} day streak${today.streak.studied_today ? ', studied today' : ''}`}
          >
            <Flame className="size-4" strokeWidth={1.75} aria-hidden="true" />
            {today.streak.current}
          </Link>
        </TooltipTrigger>
        <TooltipContent>
          {today.streak.studied_today ? 'Studied today' : 'Study today to keep your streak'}
          {today.streak.freezes ? `. ${today.streak.freezes} freeze${today.streak.freezes > 1 ? 's' : ''} banked` : ''}
        </TooltipContent>
      </Tooltip> : null}
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/today" className="hidden h-9 items-center gap-2 rounded-full border border-border-strong py-1 pr-3 pl-1 text-[13px] font-semibold tabular-nums transition-colors hover:bg-raised sm:inline-flex" aria-label={`${today.minutes.done} of ${today.minutes.goal} minutes studied today`}>
            <svg viewBox="0 0 32 32" className="size-7 -rotate-90" aria-hidden="true">
              <circle cx="16" cy="16" r={r} fill="none" stroke="var(--border)" strokeWidth="3.5" />
              <circle cx="16" cy="16" r={r} fill="none" stroke="var(--primary)" strokeWidth="3.5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - percent / 100)} />
            </svg>
            {today.minutes.done}/{today.minutes.goal} min
          </Link>
        </TooltipTrigger>
        <TooltipContent>Today&apos;s study goal</TooltipContent>
      </Tooltip>
    </div>
  );
}

/**
 * A page that belongs to another kind of course (company questions in a children's math
 * course, the problem library in a Kannada course) sends the learner to their own Practice.
 */
function useCourseRoutes(learning: boolean) {
  const pathname = usePathname();
  const router = useRouter();
  const { features, ready } = useCourse();
  useEffect(() => {
    if (!learning || !ready) return;
    const foreign = COURSE_ROUTES.find(r => (pathname === r.root || pathname.startsWith(`${r.root}/`)) && !features[r.needs]);
    if (foreign) router.replace(practiceHref(features));
  }, [learning, ready, pathname, features, router]);
}

/** Whether this week's assessment is waiting: shown as a dot on Evidence. */
function useAssessmentReady(learning: boolean) {
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    // Only an active learner has an assessment; elsewhere the call can only fail.
    if (!learning) return;
    api.get<{ current: { state: string } }>('/assessments')
      .then(r => setReady(r.current.state === 'available' || r.current.state === 'in_progress'))
      .catch(() => setReady(false));
  }, [pathname, learning]);
  return ready;
}

// The tutor panel loads after first paint so it never counts against every route's JS budget.
const Assistant = dynamic(() => import('@/components/assistant'), { ssr: false });
const COLLAPSE_KEY = 'socrat:sidebar-collapsed';
const ownTutor = (path: string) => path === '/today' || path === '/plan' || path.startsWith('/learn/') || /^\/problems\/[^/]+$/.test(path);
/** Checks and tests are proof of what the learner knows on their own: no tutor on these. */
const examRoute = (path: string) => path.startsWith('/quiz/') || path.startsWith('/transfer/') || path === '/assessments';

/** Current plan with the next step up: Free and Plus can upgrade, Pro manages. Hidden while billing is off. */
function PlanCard({ collapsed }: { collapsed: boolean }) {
  const pathname = usePathname();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  useEffect(() => {
    api.get<BillingStatus>('/billing/status').then(setStatus).catch(() => setStatus(null));
  }, [pathname]); // re-read after checkout or cancelling
  if (!status?.enabled) return null;
  const { plan } = status;
  const top = plan === 'pro';
  const free = plan === 'free';
  const label = top ? 'Manage plan' : free ? 'Become a Founding Member' : 'Upgrade to Pro';
  const href = top ? '/settings#plan-heading' : '/pricing';
  const hint = status.cancel_at_period_end && status.renews_at ? `Ends ${new Date(status.renews_at * 1000).toLocaleDateString()}` : free ? `every topic and daily Soc for ₹${status.prices.plus.month.INR / 100}/month` : 'Every topic unlocked · company questions on Pro';
  return (
    <div className="px-3 pb-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href={href} aria-label={`${PLAN_NAME[plan]} plan. ${label}`} className={cn('flex h-11 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-card hover:text-foreground', !collapsed && 'lg:hidden')}>
            <Sparkles className="size-[22px]" strokeWidth={1.6} aria-hidden="true" />
          </Link>
        </TooltipTrigger>
        <TooltipContent side="right">{PLAN_NAME[plan]} plan · {label}</TooltipContent>
      </Tooltip>
      <section aria-label="Your plan" className={cn('hidden rounded-2xl border px-3 py-2.5', free ? 'border-proof-stroke bg-proof text-proof-foreground' : 'border-border-strong bg-card', !collapsed && 'lg:block')}>
        <p className="text-sm font-semibold">{free ? "You're on Free" : `${PLAN_NAME[plan]} plan`}</p>
        <p className={cn('mt-0.5 text-xs leading-snug', free ? 'text-proof-foreground/75' : 'text-muted-foreground')}>
          {free && !status.cancel_at_period_end ? <span className="font-semibold text-proof-foreground">Founding price: </span> : null}{hint}
        </p>
        <Button asChild size="xs" variant={top ? 'outline' : free ? 'ink' : 'default'} className="mt-2 w-full"><Link href={href}>{label}</Link></Button>
      </section>
    </div>
  );
}

/** Desktop: 248 px sidebar, collapsible to a 72 px rail. Tablet: rail only. */
function Sidebar({ active, collapsed, onToggle, ready }: { active: NavKey | null; collapsed: boolean; onToggle: () => void; ready: boolean }) {
  const { profile } = useSession();
  const course = useCourse();
  const [mac, setMac] = useState(false);
  useEffect(() => setMac(/Mac|iPhone|iPad/.test(navigator.platform)), []);
  return (
    <aside
      className={cn(
        // The sidebar is the notebook's margin: same paper, edged by the red margin line.
        'sticky top-0 hidden h-dvh flex-none flex-col border-r-[1.5px] border-r-margin-line bg-sidebar md:flex',
        'w-[72px]',
        !collapsed && 'lg:w-[248px]',
      )}
      data-collapsed={collapsed}
    >
      <div className={cn('flex h-16 items-center px-[24px]', !collapsed && 'lg:px-6')}>
        <Link href="/today" aria-label="Socrat, Today" className="rounded-full">
          <span className={cn('hidden', !collapsed && 'lg:inline')}><Wordmark /></span>
          <span className={cn(!collapsed && 'lg:hidden')}><Wordmark compact size={24} /></span>
        </Link>
      </div>
      <nav aria-label="Main" className="flex-1 px-3 pt-2">
        <ul className="grid gap-1">
          {navItems(profile?.enrollment?.shape, course.features).map(item => {
            const Icon = iconFor(item, profile?.enrollment?.shape?.studio);
            const current = active === item.key;
            const flagged = ready && item.key === 'evidence';
            const link = (
              <Link
                href={item.href}
                data-tour={item.key}
                aria-current={current ? 'page' : undefined}
                className={cn(
                  'relative isolate flex h-11 items-center gap-3 rounded-full px-3 text-[15px] tracking-[-0.01em] transition-colors',
                  current ? 'font-medium text-ink-foreground' : 'text-muted-foreground hover:bg-card hover:text-foreground',
                )}
              >
                {current ? <span className="absolute inset-0 -z-10 rounded-full bg-ink animate-in fade-in duration-200" /> : null}
                <Icon className={cn('size-[22px] flex-none')} strokeWidth={1.6} aria-hidden="true" />
                <span className={cn('sr-only', !collapsed && 'lg:not-sr-only')}><NavLabel item={item} /></span>
                {flagged ? (
                  <span className={cn('absolute top-2.5 left-8 size-2.5 rounded-full bg-[var(--highlight)] ring-2 ring-[var(--soc-outline)]', !collapsed && 'lg:static lg:ml-auto')}>
                    <span className="sr-only">: weekly assessment available</span>
                  </span>
                ) : null}
              </Link>
            );
            return (
              <li key={item.key}>
                <Tooltip>
                  <TooltipTrigger asChild>{link}</TooltipTrigger>
                  <TooltipContent side="right" className={cn(!collapsed && 'lg:hidden')}><NavLabel item={item} /></TooltipContent>
                </Tooltip>
              </li>
            );
          })}
        </ul>
      </nav>
      <PlanCard collapsed={collapsed} />
      <div className={cn('mx-3 mb-2 hidden items-end gap-2 rounded-[18px] border border-dashed border-border-strong p-3', !collapsed && 'lg:flex')}>
        <Soc size={44} mood="wink" />
        <p className="font-hand pb-1 text-[18px] leading-tight text-pen">one question at a time</p>
      </div>
      <div className="grid gap-1 border-t px-3 py-3">
        {profile?.admin ? (
          <Link href="/admin" aria-label="Admin" className="flex h-11 items-center gap-3 rounded-full px-3 text-[15px] text-muted-foreground transition-colors hover:bg-card hover:text-foreground">
            <ShieldCheck className="size-6 flex-none" strokeWidth={1.5} aria-hidden="true" />
            <span className={cn('hidden', !collapsed && 'lg:inline')}>Admin</span>
          </Link>
        ) : null}
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent('socrat:search'))}
          className="flex h-11 items-center gap-3 rounded-full px-3 text-[15px] text-muted-foreground transition-colors hover:bg-card hover:text-foreground"
          aria-label="Search Socrat"
        >
          <svg viewBox="0 0 24 24" className="size-6 flex-none" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <span className={cn('hidden flex-1 text-left', !collapsed && 'lg:inline')}>Search</span>
          <kbd className={cn('hidden rounded-md border border-border-strong px-1.5 font-sans text-xs', !collapsed && 'lg:inline')}>{mac ? '⌘K' : 'Ctrl K'}</kbd>
        </button>
        <button
          type="button"
          onClick={onToggle}
          className="hidden h-11 items-center gap-3 rounded-full px-3 text-[15px] text-muted-foreground transition-colors hover:bg-card hover:text-foreground lg:flex"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? <PanelLeftOpen className="size-6" strokeWidth={1.5} aria-hidden="true" /> : <PanelLeftClose className="size-6" strokeWidth={1.5} aria-hidden="true" />}
          <span className={cn('hidden', !collapsed && 'lg:inline')}>Collapse</span>
        </button>
      </div>
    </aside>
  );
}

/** Phone: five destinations. 64 px plus the safe area; active item has a brand pill behind its icon. */
function MobileNav({ active, ready }: { active: NavKey | null; ready: boolean }) {
  const { profile } = useSession();
  const course = useCourse();
  const mobile = navItems(profile?.enrollment?.shape, course.features).filter(item => MOBILE_KEYS.includes(item.key));
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 border-t bg-card pb-[env(safe-area-inset-bottom)] md:hidden">
      <ul className="grid h-16 grid-cols-5">
        {mobile.map(item => {
          const Icon = iconFor(item, profile?.enrollment?.shape?.studio);
          const current = active === item.key;
          return (
            <li key={item.key}>
              <Link
                href={item.href}
                data-tour={item.key}
                aria-current={current ? 'page' : undefined}
                className={cn('relative grid h-full content-center justify-items-center gap-1 text-xs font-medium text-muted-foreground', current && 'font-bold text-foreground')}
              >
                <span className={cn('relative isolate grid h-8 w-14 place-items-center rounded-full transition-colors', current && 'text-ink-foreground')}>
                  {current ? <span className="absolute inset-0 -z-10 rounded-full bg-ink animate-in fade-in zoom-in-90 duration-200" /> : null}
                  <Icon className="size-6" strokeWidth={1.5} aria-hidden="true" />
                </span>
                <NavLabel item={item} />
                {ready && item.key === 'evidence' ? <span className="absolute top-2 right-[calc(50%-22px)] size-2.5 rounded-full bg-[var(--highlight)] ring-2 ring-[var(--soc-outline)]"><span className="sr-only">: weekly assessment available</span></span> : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function MarketingShell({ children }: { children: ReactNode }) {
  const { profile } = useSession();
  const pathname = usePathname();
  const ownChrome = pathname === '/' || pathname === '/login';
  return (
    <>
      <a href="#main" className="skip-link">Skip to content</a>
      <DevBanner />
      {ownChrome ? null : (
        <header className="sticky top-0 z-40 border-b bg-[color-mix(in_srgb,var(--background)_88%,transparent)] backdrop-blur-md">
          <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
            <Link href={profile ? '/today' : '/'} aria-label="Socrat home" className="rounded-full"><Wordmark /></Link>
            <nav className="flex items-center gap-2" aria-label="Site">
              {profile ? <FeedbackButton /> : null}
              <ThemeToggle />
              {profile ? (
                ['/start', '/placement'].includes(pathname) ? null : <Button asChild size="sm"><Link href="/today">Open app</Link></Button>
              ) : (
                <>
                  <Button asChild variant="link" size="sm"><Link href="/login">Log in</Link></Button>
                  <Button asChild size="sm"><Link href="/start">Get started</Link></Button>
                </>
              )}
            </nav>
          </div>
        </header>
      )}
      <main id="main" tabIndex={-1} className="outline-none"><PageTransition>{children}</PageTransition></main>
      {profile ? <ReportProblem /> : null}
    </>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const { profile } = useSession();
  const pathname = usePathname();
  const learning = Boolean(profile?.enrollment && profile.enrollment.status === 'active');
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    try { setCollapsed(localStorage.getItem(COLLAPSE_KEY) === 'true'); } catch { /* default expanded */ }
  }, []);
  const ready = useAssessmentReady(learning);
  useCourseRoutes(learning);

  if (!learning) return <MarketingShell>{children}</MarketingShell>;

  const active = navFor(pathname);
  const toggle = () => setCollapsed(value => {
    try { localStorage.setItem(COLLAPSE_KEY, String(!value)); } catch { /* per-viewer nicety only */ }
    return !value;
  });
  return (
    <div className="flex min-h-dvh">
      <a href="#main" className="skip-link">Skip to content</a>
      {pathname.startsWith('/learn') ? null : <ScrollBar />}
      <Sidebar active={active} collapsed={collapsed} onToggle={toggle} ready={ready} />
      <div className="flex min-w-0 flex-1 flex-col">
        <DevBanner />
        <header style={{ viewTransitionName: 'app-header' }} className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b bg-[color-mix(in_srgb,var(--background)_88%,transparent)] px-4 backdrop-blur-md lg:px-10">
          <Link href="/today" className="rounded-full md:hidden" aria-label="Socrat, Today"><Wordmark size={26} /></Link>
          <div className="min-w-0 flex-1"><CommandMenu /></div>
          <div className="ml-auto flex items-center gap-1.5">
            <FeedbackButton />
            <Momentum />
            <ThemeToggle />
            <UserMenu />
          </div>
        </header>
        <main id="main" tabIndex={-1} className="min-w-0 flex-1 pb-24 outline-none md:pb-0"><PageTransition>{children}</PageTransition></main>
      </div>
      <MobileNav active={active} ready={ready} />
      <Tour />
      <ReportProblem />
      {/* Soc is one tap away everywhere; pages with their own tutor (lesson, problem, plan, today) mount a scoped one. */}
      {ownTutor(pathname) || examRoute(pathname) ? null : <Assistant scope="general" title="Ask Soc" />}
    </div>
  );
}
