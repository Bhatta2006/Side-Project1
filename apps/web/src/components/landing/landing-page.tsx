'use client';

import Link from 'next/link';
import { Fragment, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Menu, Plus, X } from '@/components/icons';
import { api } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import type { Course } from '@/lib/types';
import { Illustration, Soc, type IllustrationName } from '@/components/socrat/illustration';
import { LiveSoc } from '@/components/socrat/live-soc';
import { SocSprite, SocSpriteEager } from '@/components/socrat/soc-sprite';
import type { SocMood } from '@/components/socrat/soc';
import { StatusIcon } from '@/components/socrat/status';
import { Wordmark } from '@/components/socrat/wordmark';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Paper } from '@/components/ui/paper';
import { InView } from '@/components/motion';
import { Reveal } from '@/components/common';
import { WhySocrat } from '@/components/landing/why-socrat';
import { CommunityButton, CommunityCard } from '@/components/community-link';
import { InstallAppButton } from '@/components/install-app';
import { SocraticDemo } from '@/components/landing/socratic-demo';
import { FollowSoc } from '@/components/landing/follow-soc';
import { ProductFilm } from '@/components/landing/product-film';
import { AskColumns, FeatureCards, SourcesStrip } from '@/components/landing/motion-sections';
import { cn } from '@/lib/utils';


/** The hero's opening question. Each answer changes how Soc reacts and where the button goes. */
const GOALS: { id: string; label: string; mood: SocMood; say: string; cta: string; href: string }[] = [
  { id: 'zero', label: 'Learn to code from zero', mood: 'happy', say: 'Lovely. So what is a variable, really?', cta: 'Start from zero', href: '/start?course=zero' },
  { id: 'interview', label: 'Crack DSA interviews', mood: 'curious', say: 'Why does a hash map make it fast?', cta: 'Prep for interviews', href: '/start?course=dsa' },
  { id: 'competitive', label: 'Win coding contests', mood: 'proud', say: 'Can you prove it runs in time?', cta: 'Train for contests', href: '/start?course=cp' },
  { id: 'explore', label: 'Just looking around', mood: 'wink', say: 'Then watch a day with me, just below.', cta: 'See how it works', href: '#film' },
];

const PATHS = [
  { id: 'zero', name: 'Programming from Zero', title: 'Start from the very first line', description: 'Write your first programs in Python, C++ or Java and understand what each line does.', color: 'bg-[var(--book-blue)] text-white [--illo-line:#fff]', doodle: 'bulb' as IllustrationName },
  { id: 'interview', name: 'DSA for Interviews', title: 'The patterns behind interview questions', description: 'Learn why each technique works, then explain your choices and trade-offs out loud.', color: 'bg-[var(--book-red)] text-white [--illo-line:#fff]', doodle: 'plane' as IllustrationName },
  { id: 'competitive', name: 'Competitive Programming', title: 'Contest speed, on real understanding', description: 'Contest techniques, timed practice and upsolving, built on the foundations.', color: 'bg-[var(--book-yellow)] text-[#15161E]', doodle: 'ladder' as IllustrationName },
];

const FAQ = [
  ['Why not just use ChatGPT?', 'A chatbot will write the solution for you, and you learn little from pasting it. Socrat asks what you tried, raises help one step at a time after real attempts, blocks solution code until you have earned it, and checks what you can do on your own.'],
  ['Can I use it on my phone?', 'Yes. Lessons, concept checks, reviews and the tutor work on a phone, and you can install Socrat to your home screen. Writing code is best on a laptop or desktop.'],
  ['Can I start without knowing how to code?', 'Yes. Programming from Zero starts with your first program. You choose Python, C++ or Java, and a short placement check finds the right starting point.'],
  ['How is this different from a problem list?', 'A problem list gives you options. Socrat connects lessons, checks and practice into a plan built from your goal, your time and what you have shown you can do.'],
  ['Will the tutor give me the answer?', 'The tutor starts with a question or a small hint. Help gets more specific as you make real attempts. A full walkthrough is available after you have worked through the problem.'],
  ['What counts as proof?', 'Reading a lesson does not. Concept checks, judged code and reviews do, and help you received lowers how much a success counts.'],
  ['Where do the practice problems come from?', 'Socrat has its own judged problems and a curated index of LeetCode, CSES and Codeforces problems. External statements and submissions stay on those platforms.'],
];

const STEPS: { title: string; status: 'read' | 'practised' | 'mastered'; label: string; text: string; doodle: IllustrationName; note: string }[] = [
  { title: 'Read', status: 'read', label: 'Read', text: 'Short lessons with worked traces, edge cases and self-checks. Reading alone never counts as mastery.', doodle: 'welcome', note: 'the easy part' },
  { title: 'Check', status: 'practised', label: 'Check passed', text: 'Reading opens the check. Pass it to show what you learned; a missed check brings support and a fresh try.', doodle: 'bulb', note: 'the aha part' },
  { title: 'Prove', status: 'mastered', label: 'Mastered', text: 'Checkpoints and spaced reviews confirm what holds up over time, as the questions get harder.', doodle: 'target', note: 'the part that counts' },
];

/** Words that rise in one after another (`.word-rise` on the parent); `from` continues the count. */
function Words({ text, from = 0 }: { text: string; from?: number }) {
  // The space sits between the spans: inside an inline-block it would collapse.
  return <>{text.split(' ').map((w, i) => <Fragment key={i}>{i ? ' ' : ''}<span style={{ '--i': from + i } as React.CSSProperties}>{w}</span></Fragment>)}</>;
}

/** A hand-drawn arrow in red pen. */
function PenArrow({ className, d = 'M6 6c10 18 14 34 10 56', head = 'M6 50l10 12 8-14' }: { className?: string; d?: string; head?: string }) {
  return (
    <svg viewBox="0 0 40 70" className={cn('text-pen', className)} fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} /><path d={head} />
    </svg>
  );
}

/** A notebook section: heading with an optional handwritten aside. */
function SectionHead({ id, title, children, note }: { id: string; title: React.ReactNode; children?: React.ReactNode; note?: string }) {
  return (
    <div className="max-w-3xl">
      <h2 id={id} className="type-display-l">{title}</h2>
      {children ? <p className="type-body-l mt-4 max-w-2xl text-muted-foreground">{children}</p> : null}
      {note ? <p className="font-hand mt-3 -rotate-2 text-[24px] text-pen">{note}</p> : null}
    </div>
  );
}

export function LandingPage() {
  const { profile, loading } = useSession();
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [menu, setMenu] = useState(false);
  const [goal, setGoal] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && profile) router.replace(destination(profile, 'active') ?? '/today');
  }, [loading, profile, router]);

  useEffect(() => {
    let active = true;
    api.get<{ items: Course[] }>('/courses').then(r => { if (active) setCourses(r.items); }).catch(() => undefined);
    return () => { active = false; };
  }, []);

  const links = [['#how', 'How it works'], ['#tutor', 'The tutor'], ['#film', 'See it'], ['#paths', 'Paths'], ['/pricing', 'Pricing'], ['#faq', 'FAQ']] as const;
  const chosen = GOALS.find(g => g.id === goal) ?? null;
  const skills = courses.reduce((sum, c) => sum + c.concept_count, 0);
  const problems = courses.reduce((sum, c) => sum + c.problem_count, 0);

  return (
    <div className="landing ll-desk min-h-dvh text-foreground">
      {/* Dozens of small Socs wearing a few faces: each face is drawn once, and only the hero's is in the HTML. */}
      <SocSprite>
      <header
        className="landing-nav fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-4"
        onKeyDown={event => { if (event.key === 'Escape' && menu) { setMenu(false); event.currentTarget.querySelector<HTMLButtonElement>('[data-menu-button]')?.focus(); } }}
      >
        <Paper stock="slip" tilt={false} seed="landing-header" className="relative mx-auto flex h-16 max-w-[1500px] items-center justify-between gap-4 px-4 sm:px-6">
          <Link href="/" aria-label="Socrat home" className="rounded-full"><Wordmark /></Link>
          <nav aria-label="Site" className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 lg:flex">
            {links.map(([href, label]) => <a key={href} href={href} className="rounded-[3px] px-3 py-1.5 text-[17px] text-ink transition-colors hover:bg-hi-select">{label}</a>)}
          </nav>
          <div className="flex items-center gap-1 sm:gap-3">
            <Button asChild variant="outline" className="hidden sm:inline-flex"><Link href="/login">Log in</Link></Button>
            <Button asChild className="max-sm:h-10 max-sm:px-4 max-sm:[&_[data-slot=arrow]]:hidden"><Link href="/start">Get started<ArrowCircle /></Link></Button>
            <Button data-menu-button variant="ghost" size="icon" className="lg:hidden" aria-label={menu ? 'Close navigation' : 'Open navigation'} aria-expanded={menu} aria-controls={menu ? 'landing-mobile-nav' : undefined} onClick={() => setMenu(!menu)}>
              {menu ? <X /> : <Menu />}
            </Button>
          </div>
        </Paper>
        {menu ? (
          <nav id="landing-mobile-nav" aria-label="Mobile site" className="paper mx-auto mt-2 grid max-w-[1500px] rounded-card px-4 py-2 lg:hidden">
            {links.map(([href, label]) => <a key={href} href={href} onClick={() => setMenu(false)} className="flex min-h-12 items-center text-[17px] font-medium">{label}</a>)}
            <Link href="/login" className="flex min-h-12 items-center text-[17px] font-medium">Log in</Link>
            <InstallAppButton variant="ghost" className="-ml-3 justify-start text-[17px]" />
          </nav>
        ) : null}
      </header>

      <main>
        {/* Hero: Soc introduces himself, then asks the first question. The answer changes his reaction. */}
        <section id="hero" aria-labelledby="hero-title" className="relative min-h-[100svh] overflow-hidden [--margin-x:20px] sm:[--margin-x:40px] lg:[--margin-x:88px]">
          <div className="mx-auto grid min-h-[100svh] max-w-[1500px] items-center gap-10 pt-28 pr-5 pb-24 pl-10 sm:pr-8 sm:pl-16 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:pr-10 lg:pl-[128px]">
            <div>
              <p className="word-rise max-w-[30ch] text-[22px] leading-[1.3] tracking-[-0.03em] text-muted-foreground sm:text-[28px] lg:text-[32px]">
                <Words text="Hey there, I'm Soc," /><br /><Words text="the tutor who answers your questions with questions." from={4} />
              </p>
              {/* The heading is the largest paint: no fade-in on it (LCP). */}
              <h1 id="hero-title" className="mt-8 max-w-[19ch] text-[34px] leading-[1.12] font-medium tracking-[-0.045em] sm:text-[44px] lg:text-[52px]">
                Quick question before we start: <span className="hl hl-draw">what do you want to be able to do?</span>
              </h1>
              <Reveal index={1}>
                <div role="radiogroup" aria-label="Your goal" className="mt-9 flex max-w-[44rem] flex-wrap gap-2.5">
                  {GOALS.map(g => {
                    const on = goal === g.id;
                    return (
                      <button
                        key={g.id}
                        type="button"
                        role="radio"
                        aria-checked={on}
                        onClick={() => setGoal(on ? null : g.id)}
                        className={cn(
                          'min-h-11 rounded-full border px-5 text-[16px] tracking-[-0.01em] transition-[background-color,color,border-color,transform] duration-200 ease-[var(--ease-soft)] active:scale-[0.97]',
                          on ? 'border-ink bg-ink text-ink-foreground' : 'border-border-strong bg-card hover:-translate-y-0.5 hover:border-foreground/40',
                        )}
                      >
                        {g.label}
                      </button>
                    );
                  })}
                  <Button asChild size="lg" className="lg:h-11">
                    <Link href={chosen?.href ?? '/start'}>{chosen?.cta ?? 'Get started'}<ArrowCircle /></Link>
                  </Button>
                </div>
                <p className="mt-4 text-[14px] text-muted-foreground">Free while in beta. The first problem needs no sign-up.</p>
              </Reveal>
            </div>
            <div className="relative mx-auto w-full max-w-[300px] sm:max-w-[360px] lg:mr-0 lg:max-w-[420px]">
              <SocSpriteEager><LiveSoc mood={chosen?.mood ?? 'worried'} say={chosen?.say ?? null} /></SocSpriteEager>
            </div>
          </div>
          <Illustration name="bulb" className="drift pointer-events-none absolute top-28 right-[38%] hidden size-16 opacity-70 lg:block" />
          <Illustration name="plane" className="drift-slow pointer-events-none absolute bottom-24 left-[44%] hidden size-20 opacity-70 lg:block" />
          <a href="#film" className="absolute right-6 bottom-6 hidden items-end gap-2 sm:flex lg:right-12 lg:bottom-8">
            <span className="font-hand -rotate-3 text-[26px] text-pen">scroll down, I&apos;ll follow you</span>
            <PenArrow className="h-12 w-7" />
          </a>
        </section>

        {/* A day with Soc, as a short film: it replaces the live demo, so it costs nothing to show. */}
        <section id="film" data-soc="hide" aria-labelledby="film-title" className="mx-auto max-w-[1500px] scroll-mt-20 px-5 pt-6 pb-20 sm:px-8 lg:pr-10 lg:pb-28 lg:pl-[128px]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <h2 id="film-title" className="type-display-l max-w-[16ch]">Watch a day with Soc.</h2>
            <p className="font-hand -rotate-2 text-[24px] text-pen">40 seconds. no sign-up.</p>
          </div>
          <InView className="mt-10">
            <ProductFilm className="mx-auto max-w-[1080px] rotate-[-0.4deg]" />
          </InView>
        </section>

        {/* The problem, stated plainly, beside a replay of Soc teaching. */}
        <section id="statement" data-soc="thinking|Finding answers is easy. Knowing why?" data-soc-x="left" aria-labelledby="statement-title" className="mx-auto grid max-w-[1500px] scroll-mt-20 grid-cols-1 items-center gap-14 px-5 py-20 sm:px-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:py-32 lg:pr-10 lg:pl-[128px]">
          <div>
            <h2 id="statement-title" className="text-[44px] leading-[0.98] font-semibold tracking-[-0.055em] sm:text-[64px] lg:text-[84px]">
              More tutorials won&apos;t fix that. <span className="hl">Proving what you can do</span> will.
            </h2>
            <p className="type-body-l mt-8 max-w-[36rem] text-muted-foreground">Finding information is easy now. The hard part is knowing what to learn, what to practise, and whether you actually learned it.</p>
          </div>
          <div id="tutor" className="scroll-mt-28">
            <SocraticDemo className="mx-auto w-full max-w-[540px] lg:mr-0" />
          </div>
        </section>

        {/* Questions answered with questions, drifting past in columns. */}
        <AskColumns />

        {/* How it works: three pages of a notebook. */}
        <section id="how" data-soc="happy|Read, check, prove. In that order." data-soc-x="right" aria-labelledby="how-title" className="below-fold mx-auto max-w-[1500px] scroll-mt-20 px-5 py-20 sm:px-8 lg:py-28 lg:pr-10 lg:pl-[128px]">
          <SectionHead id="how-title" title={<>Read. Check. <span className="hl">Prove.</span></>} note="reading about it is not knowing it">
            Every skill separates reading a lesson, passing its check and proving it again after a gap.
          </SectionHead>
          <div className="mt-14 grid gap-5 md:grid-cols-3 lg:gap-8">
            {STEPS.map((step, i) => (
              <InView key={step.title} index={i} className="doodle-host paper group relative flex flex-col rounded-card p-6 transition-transform duration-300 ease-[var(--ease-soft)] hover:-translate-y-1 lg:p-8">
                <div className="contents">
                  <div className="flex items-start justify-between">
                    <span className="font-hand text-[44px] leading-none text-pen">{i + 1}.</span>
                    <Illustration name={step.doodle} className="-mt-2 -mr-2 size-28" />
                  </div>
                  <h3 className="type-display-m mt-2">{step.title}</h3>
                  <p className="mt-3 text-[16px] text-muted-foreground">{step.text}</p>
                  <div className="mt-auto flex items-center gap-2.5 pt-6 text-[14px] font-medium">
                    <StatusIcon status={step.status} size={24} />
                    <span>{step.label}</span>
                    <span className="font-hand ml-auto text-[20px] font-normal text-pen opacity-0 transition-opacity duration-300 group-hover:opacity-100">{step.note}</span>
                  </div>
                </div>
              </InView>
            ))}
          </div>
        </section>

        {/* The main question learners ask: why not a chatbot. */}
        <div data-soc="worried|A chatbot would just give you the answer…">
          <WhySocrat skills={skills} problems={problems} />
        </div>


        {/* What Soc does, as index cards with small looping drawings and a word from him on each. */}
        <FeatureCards />

        {/* Where he sends you for more: the open resources, drifting past. */}
        <SourcesStrip />

        {/* Learning paths: three books from Soc's stack. */}
        <section id="paths" data-soc="happy|Pick a book. Any book." data-soc-x="right" aria-labelledby="paths-title" className="below-fold mx-auto max-w-[1500px] scroll-mt-20 px-5 py-20 sm:px-8 lg:py-28 lg:pr-10 lg:pl-[128px]">
          <SectionHead id="paths-title" title="Three ways in" note="each one is a book from Soc's stack ↓" />
          <div className="mt-12 grid gap-6 md:grid-cols-3 lg:gap-8">
            {PATHS.map((path, i) => {
              const course = courses.find(c => c.id === path.id || c.title === path.name);
              return (
                <InView key={path.id} index={i} className="doodle-host group">
                  <Link
                    href={`/start?course=${path.id}`}
                    aria-label={`Get started with ${path.name}`}
                    className={cn('relative flex min-h-[22rem] flex-col gap-3 overflow-hidden rounded-[4px] border-2 border-[var(--soc-outline)] p-6 shadow-[6px_6px_0_var(--soc-outline)] transition-[transform,box-shadow] duration-300 ease-[var(--ease-soft)] group-hover:-translate-x-0.5 group-hover:-translate-y-1 group-hover:shadow-[9px_10px_0_var(--soc-outline)] lg:p-8', path.color)}
                  >
                    <span aria-hidden="true" className="absolute inset-y-0 left-5 w-px bg-current opacity-25" />
                    <p className="type-label pl-4 opacity-85">{course?.title ?? path.name}</p>
                    <h3 className="pl-4 font-display text-[30px] leading-[1.04] font-semibold tracking-[-0.045em]">{path.title}</h3>
                    <p className="pl-4 text-[16px] opacity-90">{path.description}</p>
                    {course ? <p className="path-count pl-4 text-[14px] font-medium">{course.concept_count} skills · {course.problem_count} judged problems</p> : null}
                    <div className="mt-auto flex items-end justify-between pl-4">
                      <span className="inline-flex h-11 items-center gap-2 rounded-full bg-card px-5 text-[15px] font-medium text-foreground">Get started<ArrowCircle /></span>
                      <Illustration name={path.doodle} className="-mr-3 -mb-3 size-28" />
                    </div>
                  </Link>
                </InView>
              );
            })}
          </div>
        </section>

        {/* FAQ: questions in the margin, answers on the line. */}
        <section id="faq" data-soc="curious|Ask me anything. I will ask back." data-soc-x="right" aria-labelledby="faq-title" className="below-fold mx-auto grid max-w-[1500px] scroll-mt-20 gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1fr_1.5fr] lg:py-28 lg:pr-10 lg:pl-[128px]">
          <div>
            <h2 id="faq-title" className="type-display-l">Questions?</h2>
            <p className="font-hand mt-3 -rotate-2 text-[24px] text-pen">of course there are questions. it&apos;s Socrat.</p>
            <Illustration name="empty" className="mt-8 hidden size-48 lg:block" />
          </div>
          <div className="grid">
            {FAQ.map(([question, answer]) => (
              <details key={question} className="landing-question group border-b border-border-strong">
                <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-4 py-4 text-[19px] font-medium tracking-[-0.02em] [&::-webkit-details-marker]:hidden">
                  {question}
                  <Plus className="size-5 flex-none transition-transform duration-300 ease-[var(--ease-soft)] group-open:rotate-45" aria-hidden="true" />
                </summary>
                <p className="max-w-[60ch] pb-6 text-[16px] text-muted-foreground">{answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Beta community */}
        <div className="below-fold mx-auto max-w-[1500px] px-5 pb-8 sm:px-8 lg:pr-10 lg:pl-[128px]"><CommunityCard /></div>

        {/* Final call to action: Soc, happy, on his books. */}
        <section data-soc="hide" aria-labelledby="cta-title" className="below-fold mx-auto max-w-[1500px] px-5 pb-20 sm:px-8 lg:pr-10 lg:pb-28 lg:pl-[128px]">
          <InView className="paper relative grid items-center gap-8 overflow-hidden rounded-[4px] p-8 sm:p-10 lg:grid-cols-[1fr_auto] lg:p-14">
            <div>
              <h2 id="cta-title" className="type-display-l max-w-[18ch]">Start where you are. <span className="hl">Soc will ask the first question.</span></h2>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg"><Link href="/login">Get started<ArrowCircle /></Link></Button>
                <InstallAppButton variant="outline" size="lg" />
              </div>
            </div>
            <div className="mx-auto w-[220px] lg:mr-6">
              <LiveSoc mood="happy" bubbleSide="left" />
            </div>
          </InView>
        </section>
      </main>

      <footer className="border-t border-border-strong">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-6 px-5 py-10 sm:px-8 lg:pr-10 lg:pl-[128px]">
          <Wordmark size={22} />
          <nav aria-label="Footer" className="flex flex-wrap gap-6 text-[15px] text-muted-foreground">
            <a href="#how" className="hover:text-foreground">How it works</a>
            <a href="#tutor" className="hover:text-foreground">The tutor</a>
            <a href="#paths" className="hover:text-foreground">Paths</a>
            <Link href="/pricing" className="hover:text-foreground">Pricing</Link>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
            <Link href="/login" className="hover:text-foreground">Log in</Link>
            <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
            <Link href="/refunds" className="hover:text-foreground">Refunds</Link>
            <Link href="/terms" className="hover:text-foreground">Terms</Link>
            <Link href="/changelog" className="hover:text-foreground">Change log</Link>
            <Link href="/attribution" className="hover:text-foreground">Attribution</Link>
          </nav>
          <CommunityButton variant="ghost" size="sm" label="WhatsApp community" />
          <p className="text-[13px] text-muted-foreground">© {new Date().getFullYear()} Socrat</p>
        </div>
      </footer>

      <FollowSoc heroId="hero" />
      </SocSprite>
    </div>
  );
}
