'use client';

import dynamic from 'next/dynamic';
import { PenLine } from 'lucide-react';

export type Category = 'bug' | 'idea' | 'feedback' | 'content';

/** Opens the feedback dialog from anywhere (header button, menu, error page, settings). */
export function openReportProblem(category: Category = 'bug') {
  window.dispatchEvent(new CustomEvent('socrat:report', { detail: category }));
}

/** The Feedback and Invite dialogs load after first paint so they cost nothing on routes until opened. */
export const ReportProblem = dynamic(() => import('@/components/header-dialogs'), { ssr: false });

/** Sticky-note look shared by the header's Feedback and Invite buttons. */
export const NOTE = 'group inline-flex h-9 items-center gap-1.5 rounded-[10px_14px_9px_12px] border-2 border-[var(--soc-outline)] px-3 shadow-[2px_2px_0_var(--soc-outline)] transition-[transform,box-shadow] duration-200 ease-[var(--ease-soft)] hover:-translate-y-0.5 hover:rotate-0 hover:shadow-[3px_4px_0_var(--soc-outline)] active:translate-y-0 active:shadow-none';
export const BADGE = 'hidden rounded-full border border-current px-1.5 text-[10px] font-bold tracking-wide uppercase';

/** Always-visible header button for beta testers: a yellow sticky note in ink. */
export function FeedbackButton() {
  return (
    <button
      type="button"
      onClick={() => openReportProblem('feedback')}
      aria-label="Send feedback, ask for a feature or report a bug"
      className={`${NOTE} -rotate-2 bg-[var(--highlight)] text-[#15161E]`}
    >
      <PenLine className="size-4 transition-transform group-hover:-rotate-12" strokeWidth={2} aria-hidden="true" />
      <span className="font-hand text-[18px] leading-none">Feedback</span>
      <span className={`${BADGE} sm:inline`}>beta</span>
    </button>
  );
}
