'use client';

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { ArrowLeft, ArrowRight } from '@/components/icons';
import Markdown from '@/components/markdown';
import { Button } from '@/components/ui/button';
import { isCheckPage, minutes, splitPages } from '@/lib/pages';
import { cn } from '@/lib/utils';

const VIEW_KEY = 'socrat:lesson-view';

function readView(): 'pages' | 'scroll' {
  try {
    return window.localStorage.getItem(VIEW_KEY) === 'scroll' ? 'scroll' : 'pages';
  } catch {
    return 'pages';
  }
}

function saveView(view: 'pages' | 'scroll') {
  try {
    window.localStorage.setItem(VIEW_KEY, view);
  } catch {
    /* private window: the choice lasts for this visit only */
  }
}

export type ExtraPage = { key: string; title: string; node: ReactNode };

/**
 * The lesson one page at a time: one `## ` section per page, then any visuals or tasks as
 * pages of their own, then the recap. Page sizes were chosen for this learner when the lesson
 * was written. "Show the whole lesson" keeps the single scroll for anyone who prefers it.
 */
export function LessonPages({ id, source, language, extra = [], recap, onPage, tool }: {
  id: string;
  source: string;
  language?: string;
  extra?: ExtraPage[];
  recap: ReactNode;
  /** Told the page the reader has reached (1-based), each time it changes. */
  onPage?: (page: number) => void;
  /** Shown under a reading page (0-based index, its title): "show me this part". */
  tool?: (index: number, title: string) => ReactNode;
}) {
  const reading = useMemo(() => splitPages(source), [source]);
  const total = reading.length + extra.length + 1;
  const [view, setView] = useState<'pages' | 'scroll'>('pages');
  const [index, setIndex] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const top = useRef<HTMLDivElement>(null);
  const moved = useRef(false);

  useEffect(() => setView(readView()), []);
  useEffect(() => { setIndex(0); moved.current = false; }, [id]);

  const reached = useRef(onPage);
  reached.current = onPage;
  useEffect(() => {
    if (moved.current) reached.current?.(index + 1);
  }, [index]);

  useEffect(() => {
    if (!moved.current) return;
    heading.current?.focus({ preventScroll: true });
    top.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }, [index]);

  useEffect(() => {
    if (view !== 'pages') return;
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) return;
      if (el?.closest('[role="dialog"]')) return;
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  function go(step: number) {
    moved.current = true;
    setIndex(i => Math.max(0, Math.min(total - 1, i + step)));
  }

  function switchView(next: 'pages' | 'scroll') {
    setView(next);
    saveView(next);
  }

  const toggle = (
    <button
      type="button"
      className="text-sm font-medium text-muted-foreground underline underline-offset-4 hover:text-foreground"
      onClick={() => switchView(view === 'pages' ? 'scroll' : 'pages')}
    >
      {view === 'pages' ? 'Show the whole lesson on one page' : 'Read one page at a time'}
    </button>
  );

  if (view === 'scroll' || total <= 2) {
    return (
      <div className="max-w-[68ch]">
        {total > 2 ? <div className="mb-4 flex justify-end">{toggle}</div> : null}
        <div id="step-lesson"><Markdown source={source} language={language} rich /></div>
        {extra.map(p => <div key={p.key} className="mt-8">{p.node}</div>)}
        <div className="mt-10">{recap}</div>
      </div>
    );
  }

  const onReading = index < reading.length;
  const onExtra = !onReading && index < reading.length + extra.length;
  const page = onReading ? reading[index] : null;
  const title = page ? page.title : onExtra ? extra[index - reading.length].title : 'Recap';
  const label = page && isCheckPage(page) ? 'Check' : `Page ${index + 1} of ${total}`;

  return (
    <div ref={top} className="max-w-[68ch] scroll-mt-24">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <ol className="flex items-center gap-1.5" aria-label="Lesson pages">
          {Array.from({ length: total }, (_, i) => (
            <li key={i}>
              <button
                type="button"
                aria-label={`Page ${i + 1} of ${total}`}
                aria-current={i === index ? 'step' : undefined}
                onClick={() => { moved.current = true; setIndex(i); }}
                className="grid h-6 place-items-center px-0.5"
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    'block h-2 rounded-full transition-[width,background-color]',
                    i === index ? 'w-6 bg-primary' : i < index ? 'w-2 bg-foreground/45' : 'w-2 bg-border-strong',
                  )}
                />
              </button>
            </li>
          ))}
        </ol>
        <span className="text-[13px] text-muted-foreground">About {minutes(reading)} min</span>
      </div>

      <section aria-labelledby="lesson-page-title" id="step-lesson">
        <p className="mb-1 text-[13px] font-medium text-muted-foreground">{label}</p>
        {title ? (
          <h2 id="lesson-page-title" ref={heading} tabIndex={-1} className="mb-4 font-display text-2xl font-semibold tracking-[-0.03em] outline-none">
            {title}
          </h2>
        ) : <h2 id="lesson-page-title" ref={heading} tabIndex={-1} className="sr-only">Lesson</h2>}
        {page ? <Markdown source={page.body} language={language} rich /> : onExtra ? extra[index - reading.length].node : recap}
        {page && tool && !isCheckPage(page) ? <div className="mt-6">{tool(index, page.title)}</div> : null}
      </section>

      <div className="mt-8 flex items-center justify-between gap-3 border-t pt-5">
        <Button variant="outline" onClick={() => go(-1)} disabled={index === 0}>
          <ArrowLeft className="size-4" aria-hidden="true" /> Back
        </Button>
        {index < total - 1 ? (
          <Button onClick={() => go(1)}>
            {index === total - 2 ? 'Recap' : 'Next'} <ArrowRight className="size-4" aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      <div className="mt-4">{toggle}</div>
    </div>
  );
}
