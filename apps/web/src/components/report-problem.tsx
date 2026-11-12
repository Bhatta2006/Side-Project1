'use client';

import dynamic from 'next/dynamic';
import { PenLine } from '@/components/icons';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export type Category = 'bug' | 'idea' | 'feedback' | 'content';

/** Opens the feedback dialog from anywhere (header button, menu, error page, settings). */
export function openReportProblem(category: Category = 'bug') {
  window.dispatchEvent(new CustomEvent('socrat:report', { detail: category }));
}

/** The dialog loads after first paint so it costs nothing on routes until it is opened. */
export const ReportProblem = dynamic(() => import('@/components/feedback-dialog'), { ssr: false });

/** Always-visible header button for beta testers: a drawn ghost button with a beta tag. */
export function FeedbackButton() {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={() => openReportProblem('feedback')}
      aria-label="Send feedback, ask for a feature or report a bug"
    >
      <PenLine aria-hidden="true" />
      <span className="max-sm:sr-only">Feedback</span>
      <Badge variant="outline" className="hidden sm:inline-flex">beta</Badge>
    </Button>
  );
}
