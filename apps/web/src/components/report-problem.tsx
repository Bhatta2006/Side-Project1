'use client';

import dynamic from 'next/dynamic';
import { PenLine } from 'lucide-react';

export type Category = 'bug' | 'idea' | 'feedback' | 'content';

/** Opens the feedback dialog from anywhere (header button, menu, error page, settings). */
export function openReportProblem(category: Category = 'bug') {
  window.dispatchEvent(new CustomEvent('socrat:report', { detail: category }));
}

/** The dialog loads after first paint so it costs nothing on routes until it is opened. */
export const ReportProblem = dynamic(() => import('@/components/feedback-dialog'), { ssr: false });

/** Always-visible header button for beta testers: a yellow sticky note in ink. */
export function FeedbackButton() {
  return (
    <button
      type="button"
      onClick={() => openReportProblem('feedback')}
      aria-label="Send feedback, ask for a feature or report a bug"
      className="group inline-flex h-9 -rotate-2 items-center gap-1.5 rounded-[10px_14px_9px_12px] border-2 border-[var(--soc-outline)] bg-[var(--highlight)] px-3 text-[#15161E] shadow-[2px_2px_0_var(--soc-outline)] transition-[transform,box-shadow] duration-200 ease-[var(--ease-soft)] hover:-translate-y-0.5 hover:rotate-0 hover:shadow-[3px_4px_0_var(--soc-outline)] active:translate-y-0 active:shadow-none"
    >
      <PenLine className="size-4 transition-transform group-hover:-rotate-12" strokeWidth={2} aria-hidden="true" />
      <span className="font-hand text-[18px] leading-none max-sm:sr-only">Feedback</span>
      <span className="hidden rounded-full border border-[#15161E] px-1.5 text-[10px] font-bold tracking-wide uppercase sm:inline">beta</span>
    </button>
  );
}
