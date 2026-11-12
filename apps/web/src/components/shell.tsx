'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { PageTransition, ScrollBar } from '@/components/motion';
import {
  ChartNoAxesColumn,
  Download,
  Flame,
  FlaskConical,
  House,
  LogOut,
  MessageCircle,
  MessageSquareWarning,
  NotebookPen,
  Route,
  Search,
  Settings,
  Shapes,
  ShieldCheck,
  Sigma,
  SquareCode,
  Sparkles,
  type LucideIcon,
} from '@/components/icons';
import { api } from '@/lib/api';
import { NAV, navFor, navItems, type NavKey } from '@/lib/routes';
import { useSession } from '@/lib/session';
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Kbd } from '@/components/ui/kbd';
import { Paper } from '@/components/ui/paper';
import { Tally } from '@/components/ui/tally';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { InkTiles } from '@/lib/ink/react';

const SHEET_TILES = ['fibre', 'relief', 'cloud'] as const;

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

function UserMenu() {
  const { profile, signOut } = useSession();
  const router = useRouter();
  const { state: installState, install } = useInstall();
  const community = useCommunityUrl();
  const name = profile?.display_name || 'Learner';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" aria-label="Account menu" data-tour="settings" className="grid size-10 place-items-center rounded-full">
          <Avatar className="size-9">
            <AvatarFallback name={name} />
          </Avatar>
        </button>
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
          <Button asChild variant="ghost" size="sm" className="tabular-nums">
            <Link href="/progress" aria-label={`${today.streak.current} day streak${today.streak.studied_today ? ', studied today' : ''}`}>
              {today.streak.current >= 2 && today.streak.current <= 10
                ? <Tally count={today.streak.current} size="sm" tone="red" seed="streak" />
                : <Flame strokeWidth={1.75} aria-hidden="true" />}
              {today.streak.current}
            </Link>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {today.streak.studied_today ? 'Studied today' : 'Study today to keep your streak'}
          {today.streak.freezes ? `. ${today.streak.freezes} freeze${today.streak.freezes > 1 ? 's' : ''} banked` : ''}
        </TooltipContent>
      </Tooltip> : null}
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/today" className="hidden h-9 items-center gap-1.5 px-2 text-[15px] font-bold whitespace-nowrap tabular-nums text-ink md:inline-flex" aria-label={`${today.minutes.done} of ${today.minutes.goal} minutes studied today`}>
            <svg viewBox="0 0 32 32" className="size-7 -rotate-90" aria-hidden="true">
              <circle cx="16" cy="16" r={r} fill="none" stroke="var(--ll-line-soft)" strokeWidth="3" />
              <circle cx="16" cy="16" r={r} fill="none" stroke="var(--ll-marker)" strokeWidth="3.5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - percent / 100)} />
            </svg>
            {today.minutes.done}/{today.minutes.goal} min
          </Link>
        </TooltipTrigger>
        <TooltipContent>Today&apos;s study goal</TooltipContent>
      </Tooltip>
    </div>
  );
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
// The sticker catalogue is large and the shell shows one rocket, so it loads on its own.
const Sticker = dynamic(() => import('@/components/ui/sticker').then(m => m.Sticker), { ssr: false });
const ReportThanks = dynamic(() => import('@/components/report-thanks').then(m => m.ReportThanks), { ssr: false });
const COLLAPSE_KEY = 'socrat:sidebar-collapsed';
const ownTutor = (path: string) => path === '/today' || path === '/plan' || path.startsWith('/learn/') || /^\/problems\/[^/]+$/.test(path);
/** Checks and tests are proof of what the learner knows on their own: no tutor on these. */
const examRoute = (path: string) => path.startsWith('/quiz/') || path.startsWith('/transfer/') || path === '/assessments';

/** Current plan with the next step up: Free and Plus can upgrade, Pro manages. Hidden while billing is off. */
function PlanCard() {
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
    <SidebarGroup className="px-4 group-data-[collapsible=icon]:hidden">
      <Paper as="section" aria-label="Your plan" stock={free ? 'sticky-yellow' : 'index-card'} tilt={-1.2} tape="top" seed="plan-card" className="relative px-3 pt-4 pb-3">
        {free ? <Sticker name="rocket" size={46} rotate={12} seed="plan-rocket" className="absolute -top-5 right-1" /> : null}
        <p className="font-script text-xl leading-none">{free ? "You're on Free" : `${PLAN_NAME[plan]} plan`}</p>
        <p className="mt-1.5 text-sm leading-snug text-ink-soft">
          {free && !status.cancel_at_period_end ? <span className="font-bold text-ink">Founding price: </span> : null}{hint}
        </p>
        <Button asChild size="sm" variant={top ? 'outline' : 'default'} className="mt-3 h-auto min-h-8 w-full py-1.5 text-center whitespace-normal"><Link href={href}>{label}</Link></Button>
      </Paper>
    </SidebarGroup>
  );
}

/** Desktop: a pad of paper hung from a binder clip, collapsible to an icon rail. Phones get the bottom bar. */
function AppSidebar({ active, ready }: { active: NavKey | null; ready: boolean }) {
  const { profile } = useSession();
  const [mac, setMac] = useState(false);
  useEffect(() => setMac(/Mac|iPhone|iPad/.test(navigator.platform)), []);
  return (
    <Sidebar variant="inset" collapsible="icon" seed="socrat-sidebar">
      <SidebarHeader className="px-4 pt-3 pb-1 group-data-[collapsible=icon]:px-2">
        <Link href="/today" aria-label="Socrat, Today" className="inline-flex items-center">
          <span className="group-data-[collapsible=icon]:hidden"><Wordmark /></span>
          <span className="hidden group-data-[collapsible=icon]:inline"><Wordmark compact size={22} /></span>
        </Link>
      </SidebarHeader>
      <SidebarContent className="overflow-x-hidden">
        <SidebarGroup>
          <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden">Notebook</SidebarGroupLabel>
          <SidebarGroupContent>
            <nav aria-label="Main">
              <SidebarMenu>
                {navItems(profile?.enrollment?.shape).map(item => {
                  const Icon = iconFor(item, profile?.enrollment?.shape?.studio);
                  const current = active === item.key;
                  return (
                    <SidebarMenuItem key={item.key}>
                      <SidebarMenuButton asChild isActive={current} tooltip={item.label} size="lg" className="text-[17px]">
                        <Link href={item.href} data-tour={item.key} aria-current={current ? 'page' : undefined}>
                          <Icon strokeWidth={1.75} aria-hidden="true" />
                          <span className="group-data-[collapsible=icon]:hidden">{item.label}</span>
                        </Link>
                      </SidebarMenuButton>
                      {ready && item.key === 'evidence' ? (
                        <SidebarMenuBadge><span className="size-2.5 rounded-full bg-hi ring-2 ring-ink" /><span className="sr-only">: weekly assessment available</span></SidebarMenuBadge>
                      ) : null}
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </nav>
          </SidebarGroupContent>
        </SidebarGroup>
        <div className="mt-auto" />
        <PlanCard />
        <SidebarGroup className="group-data-[collapsible=icon]:hidden">
          <div className="flex items-end gap-2 px-1">
            <Soc size={44} mood="wink" />
            <p className="font-script pb-1 text-xl leading-tight text-red">one question at a time</p>
          </div>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          {profile?.admin ? (
            <SidebarMenuItem>
              <SidebarMenuButton asChild tooltip="Admin"><Link href="/admin"><ShieldCheck aria-hidden="true" /><span className="group-data-[collapsible=icon]:hidden">Admin</span></Link></SidebarMenuButton>
            </SidebarMenuItem>
          ) : null}
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Search" onClick={() => window.dispatchEvent(new CustomEvent('socrat:search'))}>
              <Search aria-hidden="true" />
              <span className="flex-1 group-data-[collapsible=icon]:hidden">Search</span>
              <Kbd className="group-data-[collapsible=icon]:hidden">{mac ? '⌘K' : 'Ctrl K'}</Kbd>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

/** Phone: five destinations on a paper strip. 64 px plus the safe area; the current one is highlighted. */
function MobileNav({ active, ready }: { active: NavKey | null; ready: boolean }) {
  const { profile } = useSession();
  const mobile = navItems(profile?.enrollment?.shape).filter(item => MOBILE_KEYS.includes(item.key));
  return (
    <nav aria-label="Main" className="ll-paper ll-stock-slip fixed inset-x-0 bottom-0 z-40 border-t border-line pb-[env(safe-area-inset-bottom)] md:hidden">
      <ul className="grid h-[68px] grid-cols-5">
        {mobile.map(item => {
          const Icon = iconFor(item, profile?.enrollment?.shape?.studio);
          const current = active === item.key;
          return (
            <li key={item.key}>
              <Link
                href={item.href}
                data-tour={item.key}
                aria-current={current ? 'page' : undefined}
                className={cn('relative grid h-full min-w-0 content-center justify-items-center gap-0.5 px-0.5 text-[12px] leading-tight text-ink-muted', current && 'font-bold text-ink')}
              >
                <span className={cn('grid h-7 w-12 place-items-center rounded-[3px] transition-colors', current && 'bg-hi-select')}>
                  <Icon className="size-5" strokeWidth={1.75} aria-hidden="true" />
                </span>
                <span className="max-w-full truncate">{item.label}</span>
                {ready && item.key === 'evidence' ? <span className="absolute top-2 right-[calc(50%-22px)] size-2.5 rounded-full bg-hi ring-2 ring-ink"><span className="sr-only">: weekly assessment available</span></span> : null}
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
    <div className="ll-desk min-h-dvh">
      <a href="#main" className="skip-link">Skip to content</a>
      <DevBanner />
      {ownChrome ? null : (
        <header className="sticky top-0 z-40 px-3 pt-3">
          <Paper stock="slip" tilt={false} seed="marketing-header" className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
            <Link href={profile ? '/today' : '/'} aria-label="Socrat home"><Wordmark /></Link>
            <nav className="flex items-center gap-2" aria-label="Site">
              {profile ? <FeedbackButton /> : null}
              {profile ? (
                ['/start', '/placement'].includes(pathname) ? null : <Button asChild size="sm"><Link href="/today">Open app</Link></Button>
              ) : (
                <>
                  <Button asChild variant="ghost" size="sm"><Link href="/login">Log in</Link></Button>
                  <Button asChild size="sm"><Link href="/start">Get started</Link></Button>
                </>
              )}
            </nav>
          </Paper>
        </header>
      )}
      <main id="main" tabIndex={-1} className="outline-none"><PageTransition>{children}</PageTransition></main>
      {profile ? <><ReportProblem /><ReportThanks /></> : null}
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const { profile } = useSession();
  const pathname = usePathname();
  const learning = Boolean(profile?.enrollment && profile.enrollment.status === 'active');
  const [open, setOpen] = useState(true);
  useEffect(() => {
    // Tablets start on the icon rail so the page keeps its width; a saved choice wins.
    let saved: string | null = null;
    try { saved = localStorage.getItem(COLLAPSE_KEY); } catch { /* per-viewer nicety only */ }
    setOpen(saved === null ? window.matchMedia('(min-width: 1024px)').matches : saved !== 'true');
  }, []);
  const ready = useAssessmentReady(learning);

  if (!learning) return <MarketingShell>{children}</MarketingShell>;

  const active = navFor(pathname);
  const onOpenChange = (value: boolean) => {
    setOpen(value);
    try { localStorage.setItem(COLLAPSE_KEY, String(!value)); } catch { /* per-viewer nicety only */ }
  };
  return (
    <SidebarProvider open={open} onOpenChange={onOpenChange} className="ll-desk" style={{ '--sidebar-width': '17rem', '--sidebar-width-icon': '3.5rem' } as CSSProperties}>
      <a href="#main" className="skip-link">Skip to content</a>
      {pathname.startsWith('/learn') ? null : <ScrollBar />}
      <AppSidebar active={active} ready={ready} />
      <SidebarInset id="main" tabIndex={-1} className="min-w-0 pb-24 outline-none max-md:before:block md:pb-0">
        <InkTiles tiles={SHEET_TILES} />
        <DevBanner />
        <header style={{ viewTransitionName: 'app-header' }} className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-line-soft bg-paper/95 px-4 backdrop-blur-[2px] lg:px-8">
          <SidebarTrigger className="hidden md:inline-flex" />
          <Link href="/today" className="md:hidden" aria-label="Socrat, Today"><Wordmark size={24} /></Link>
          <div className="min-w-0 flex-1"><CommandMenu /></div>
          <div className="ml-auto flex items-center gap-1 sm:gap-1.5">
            <span className="hidden lg:contents"><FeedbackButton /></span>
            <span className="hidden sm:contents"><Momentum /></span>
            <UserMenu />
          </div>
        </header>
        <div className="min-w-0 flex-1 overflow-x-clip"><PageTransition>{children}</PageTransition></div>
      </SidebarInset>
      <MobileNav active={active} ready={ready} />
      <Tour />
      <ReportProblem />
      {/* Soc is one tap away everywhere; pages with their own tutor (lesson, problem, plan, today) mount a scoped one. */}
      {ownTutor(pathname) || examRoute(pathname) ? null : <Assistant scope="general" title="Ask Soc" />}
      <ReportThanks />
    </SidebarProvider>
  );
}
