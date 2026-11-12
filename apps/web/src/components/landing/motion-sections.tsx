'use client';

import Link from 'next/link';
import type { CSSProperties, ReactNode } from 'react';
import { Check } from '@/components/icons';
import { Soc } from '@/components/socrat/illustration';
import type { SocMood } from '@/components/socrat/soc';
import { InView } from '@/components/motion';
import { cn } from '@/lib/utils';

/*
 * The landing's moving sections, all CSS: columns of questions Soc answers with questions,
 * rows of the open resources he points to, and index cards whose small drawings loop while
 * Soc says what they show. Reduced motion stops every loop and leaves the drawings at rest.
 */

const v = (vars: Record<string, string | number>) => vars as CSSProperties;

/** A line from Soc: his face and a note in red pen. */
function SocSays({ mood = 'neutral', children, className }: { mood?: SocMood; children: ReactNode; className?: string }) {
  return (
    <p className={cn('flex items-center gap-2.5', className)}>
      <Soc size={34} mood={mood} className="flex-none" />
      <span className="font-hand text-[19px] leading-tight text-pen">{children}</span>
    </p>
  );
}

/* ----------------------------------------- Ask Soc ------------------------------------------- */

const ASKS: [string, string][] = [
  ['Why is my loop off by one?', 'What’s the last value i takes?'],
  ['Just tell me the answer to two-sum.', 'For each number, what are you really looking for?'],
  ['My recursion never stops.', 'Which call should return without calling again?'],
  ['Is O(n log n) fast enough here?', 'How big can n get in this problem?'],
  ['Why does my binary search hang?', 'What happens when lo and hi sit side by side?'],
  ['What is a pointer, really?', 'If a variable is a box, what is its address?'],
  ['Why is my DP answer too big?', 'What does dp[i] mean, in one sentence?'],
  ['Should I use a list or a set?', 'Do you need the order, or fast lookups?'],
  ['It passes the samples but fails.', 'What is the smallest input you haven’t tried?'],
  ['Python says NoneType. Why?', 'What does your function return on its last line?'],
  ['How do I start a graph problem?', 'What are the nodes, and what makes an edge?'],
  ['Is greedy right here?', 'Can you find a case where the best-looking step is wrong?'],
];

function AskCard({ ask, reply }: { ask: string; reply: string }) {
  return (
    <div className="paper grid gap-2.5 rounded-[4px] p-4">
      <p className="justify-self-end rounded-[14px_14px_4px_14px] bg-raised px-3.5 py-2 text-[15px]">{ask}</p>
      <div className="flex items-end gap-2">
        <Soc size={28} mood="curious" className="mb-0.5 flex-none" />
        <p className="rounded-[14px_14px_14px_4px] border bg-cream px-3.5 py-2 text-[15px] text-cream-foreground">{reply}</p>
      </div>
    </div>
  );
}

export function AskColumns() {
  const columns = [ASKS.slice(0, 4), ASKS.slice(4, 8), ASKS.slice(8, 12)];
  return (
    <section id="ask" data-soc="wink|Noticed? I answer with questions." data-soc-x="right" aria-labelledby="ask-title" className="below-fold mx-auto grid max-w-[1500px] scroll-mt-20 items-center gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:py-28 lg:pr-10 lg:pl-[128px]">
      <div>
        <h2 id="ask-title" className="type-display-l max-w-[14ch]">Ask anything. Get a better question back.</h2>
        <p className="type-body-l mt-6 max-w-[34rem] text-muted-foreground">
          Soc never pastes the answer. He asks the one question that gets you unstuck, and gives more help only after you try.
        </p>
        <SocSays mood="wink" className="mt-8">it’s annoying. it works.</SocSays>
      </div>
      <div aria-hidden="true" className="marquee-host relative h-[520px] overflow-hidden [mask-image:linear-gradient(transparent,#000_14%,#000_86%,transparent)]">
        <div className="grid h-full grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {columns.map((col, c) => (
            <div key={c} className={cn('min-w-0', c === 1 && 'hidden sm:block', c === 2 && 'hidden xl:block')}>
              <div className="marquee-y grid gap-4" data-dir={c === 1 ? 'down' : undefined} style={v({ '--dur': `${34 + c * 7}s` })}>
                {[...col, ...col].map(([ask, reply], i) => <AskCard key={i} ask={ask} reply={reply} />)}
              </div>
            </div>
          ))}
        </div>
      </div>
      <ul className="sr-only">
        {ASKS.map(([ask, reply]) => <li key={ask}>{ask} Soc asks: {reply}</li>)}
      </ul>
    </section>
  );
}

/* ----------------------------------------- Sources ------------------------------------------- */

// Resources Socrat links learners to (content/sources/registry.yaml, link-only and open-licence
// entries). Names only, in our own lettering: no logos, nothing that reads as a partnership.
const SOURCES_A = ['cp-algorithms', 'USACO Guide', 'CSES Problem Set', 'Competitive Programmer’s Handbook', 'freeCodeCamp', 'Tech Interview Handbook', 'Exercism', 'Think C++', 'Python for Everybody', 'CS50', 'MIT OpenCourseWare', 'OpenStax', 'Automate the Boring Stuff', 'The Odin Project'];
const SOURCES_B = ['cppreference', 'Python documentation', 'VisuAlgo', 'Python Tutor', 'Khan Academy', 'LeetCode', 'Codeforces', 'AtCoder', 'Kattis', 'HackerRank', 'NeetCode', 'Errichto', 'WilliamFiset', 'Developer Roadmap'];
const TAB = ['bg-[var(--book-yellow)] text-[#15161E]', 'bg-card', 'bg-[color-mix(in_srgb,var(--book-blue)_16%,var(--card))]', 'bg-card', 'bg-[color-mix(in_srgb,var(--book-red)_14%,var(--card))]'];

function SourceRow({ names, dir, dur }: { names: string[]; dir?: 'right'; dur: number }) {
  return (
    <div className="overflow-hidden">
      <div className="marquee-x flex w-max gap-3 py-1.5" data-dir={dir} style={v({ '--dur': `${dur}s` })}>
        {[...names, ...names].map((name, i) => (
          <span key={i} className={cn('flex-none rounded-[4px] border border-border-strong px-4 py-2.5 text-[17px] whitespace-nowrap shadow-[2px_2px_0_var(--border-strong)]', TAB[i % TAB.length], i % 3 === 1 ? '-rotate-1' : i % 3 === 2 ? 'rotate-1' : '')}>
            {name}
          </span>
        ))}
      </div>
    </div>
  );
}

export function SourcesStrip() {
  return (
    <section id="sources" data-soc="happy|Want more? I send you here." data-soc-x="left" aria-labelledby="sources-title" className="below-fold scroll-mt-20 py-20 lg:py-28">
      <div className="mx-auto max-w-[1500px] px-5 sm:px-8 lg:pr-10 lg:pl-[128px]">
        <h2 id="sources-title" className="type-display-l max-w-[20ch]">Soc writes every lesson. For more, he points to the best of the open web.</h2>
        <p className="type-body-l mt-5 max-w-[40rem] text-muted-foreground">
          Practice problems, references and visualisers from the places programmers already trust. Statements and submissions stay on their sites.{' '}
          <Link href="/attribution" className="underline underline-offset-4">See every source</Link>
        </p>
      </div>
      <div aria-hidden="true" className="marquee-host mt-12 grid gap-3 [mask-image:linear-gradient(90deg,transparent,#000_8%,#000_92%,transparent)]">
        <SourceRow names={SOURCES_A} dur={58} />
        <SourceRow names={SOURCES_B} dir="right" dur={64} />
      </div>
      <p className="sr-only">Resources include {[...SOURCES_A, ...SOURCES_B].join(', ')}.</p>
    </section>
  );
}

/* ------------------------------------------ Cards -------------------------------------------- */

function HintLadder() {
  return (
    <div className="grid gap-3">
      <div className="loop-ladder flex gap-1.5">
        {[0, 1, 2, 3, 4, 5].map(i => <span key={i} className="h-2.5 flex-1 rounded-full bg-border-strong" style={v({ '--i': i })} />)}
      </div>
      <div className="flex justify-between text-[12px] text-muted-foreground"><span>a question</span><span>a nudge</span><span>the idea</span><span>the answer</span></div>
    </div>
  );
}

function Tests() {
  return (
    <div className="flex items-center gap-2">
      {[0, 1, 2, 3, 4].map(i => (
        <span key={i} className="grid size-9 place-items-center rounded-[6px] bg-[color-mix(in_srgb,var(--proof)_22%,transparent)]">
          <span className="loop-tick grid size-9 place-items-center rounded-[6px] bg-proof text-[var(--proof-foreground)]" style={v({ '--i': i })}><Check className="size-4" strokeWidth={3} /></span>
        </span>
      ))}
      <span className="ml-1 font-mono text-[12px] text-muted-foreground">hidden tests</span>
    </div>
  );
}

function Reviews() {
  const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const due = [1, 4, 6];
  return (
    <div className="flex gap-1.5">
      {days.map((d, i) => (
        <span key={i} className="grid h-14 flex-1 place-items-center rounded-[4px] border bg-card text-[12px] text-muted-foreground">
          {d}
          {due.includes(i) ? <span className="loop-check grid size-5 place-items-center rounded-full bg-primary text-primary-foreground" style={v({ '--i': due.indexOf(i) })}><Check className="size-3" strokeWidth={3} /></span> : <span className="size-5" />}
        </span>
      ))}
    </div>
  );
}

function Replan() {
  return (
    <div className="grid grid-cols-3 gap-1.5 text-[12px] text-muted-foreground">
      {['Tue', 'Wed', 'Thu'].map(d => <span key={d} className="text-center">{d}</span>)}
      <span className="col-span-1 rounded-[4px] border border-dashed px-2 py-3 text-center">missed</span>
      <span className="rounded-[4px] border bg-card px-2 py-3" />
      <span className="rounded-[4px] border bg-card px-2 py-3" />
      <span className="loop-slide col-start-1 row-start-2 rounded-[4px] bg-[var(--book-yellow)] px-2 py-3 text-center font-medium text-[#15161E]">Loops</span>
    </div>
  );
}

function Editor() {
  const line = 'for i, x in enumerate(nums):';
  return (
    <pre className="rounded-[4px] bg-[var(--code-bg)] px-4 py-3 font-mono text-[13px] leading-[22px] text-[var(--code-fg)]">
      <div className="text-[color-mix(in_srgb,var(--code-fg)_55%,transparent)]">seen = {'{}'}</div>
      <div className="flex"><span className="loop-type inline-block overflow-hidden whitespace-pre" style={v({ '--chars': line.length })}>{line}</span><span className="film-caret" /></div>
    </pre>
  );
}

const CARDS: { title: string; text: string; art: ReactNode; soc: string; mood: SocMood; wide?: boolean }[] = [
  { title: 'Asks before it tells', text: 'Help comes in six steps, each only after a real attempt. The full answer is the last one.', art: <HintLadder />, soc: 'answers come last. on purpose.', mood: 'wink', wide: true },
  { title: 'Judged, not guessed', text: 'Your code runs against hidden tests in Python, C++ or Java.', art: <Tests />, soc: 'the tests decide. not me.', mood: 'proud' },
  { title: 'Remembers for you', text: 'Spaced reviews bring a skill back just before you would forget it.', art: <Reviews />, soc: 'I’ll bring it back on time.', mood: 'happy' },
  { title: 'Plans around your week', text: 'Miss a day and the plan moves forward. Nothing piles up.', art: <Replan />, soc: 'missed a day? no stress.', mood: 'sleepy' },
  { title: 'A real editor', text: 'Write, run and debug in the browser, with judged problems from day one.', art: <Editor />, soc: 'type it. run it. own it.', mood: 'thinking', wide: true },
];

export function FeatureCards() {
  return (
    <section id="features" data-soc="proud|All of this is me, working for you." data-soc-x="left" aria-labelledby="features-title" className="below-fold mx-auto max-w-[1500px] scroll-mt-20 px-5 py-20 sm:px-8 lg:py-28 lg:pr-10 lg:pl-[128px]">
      <h2 id="features-title" className="type-display-l max-w-[18ch]">A tutor, a judge and a planner in one notebook.</h2>
      <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4 lg:gap-6">
        {CARDS.map((card, i) => (
          <InView key={card.title} index={i} className={cn('flex', card.wide && 'lg:col-span-2')}>
            <article className="paper flex w-full flex-col gap-5 rounded-[4px] p-6 lg:p-7">
              <div aria-hidden="true" className="min-h-[88px] content-center">{card.art}</div>
              <div>
                <h3 className="text-[22px] font-medium tracking-[-0.02em]">{card.title}</h3>
                <p className="mt-2 text-[15px] text-muted-foreground">{card.text}</p>
              </div>
              <SocSays mood={card.mood} className="mt-auto">{card.soc}</SocSays>
            </article>
          </InView>
        ))}
      </div>
    </section>
  );
}
