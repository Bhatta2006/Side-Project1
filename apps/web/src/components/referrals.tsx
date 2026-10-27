'use client';

import { Sparkles } from 'lucide-react';
import { BADGE, NOTE } from '@/components/report-problem';

/** Sits beside the feedback note: a blue sticky note that opens the invite ladder. */
export function ReferButton() {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event('socrat:refer'))}
      aria-label="Invite friends and earn free Founding Member and Pro"
      className={`${NOTE} rotate-2 bg-primary text-primary-foreground`}
    >
      <Sparkles className="size-4 transition-transform group-hover:-rotate-12" strokeWidth={2} aria-hidden="true" />
      <span className="hidden font-hand text-[18px] leading-none sm:inline">Invite</span>
      <span className={`${BADGE} md:inline`}>free pro</span>
    </button>
  );
}
