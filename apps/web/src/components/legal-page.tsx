import Link from 'next/link';
import type { ReactNode } from 'react';
import { LEGAL } from '@/lib/legal';

/** Long-form legal text: one readable column, headings with anchors, related links. */
export function LegalPage({ title, summary, children }: { title: string; summary: ReactNode; children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pt-8 pb-24 sm:px-6">
      <header className="mb-8 border-b pb-6">
        <p className="type-label mb-3 text-muted-foreground">Last updated {LEGAL.updated}</p>
        <h1 className="type-display-l">{title}</h1>
        <div className="mt-4 text-base text-muted-foreground text-pretty">{summary}</div>
      </header>
      <div className="legal grid gap-8 text-[15px] leading-7 [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-bold [&_h2]:tracking-[-0.02em] [&_h2]:text-foreground [&_li]:mt-1.5 [&_section]:grid [&_section]:gap-3 [&_ul]:list-disc [&_ul]:pl-5 [&_a]:font-medium [&_a]:underline [&_a]:underline-offset-4">
        {children}
      </div>
      <nav aria-label="Legal" className="mt-12 flex flex-wrap gap-6 border-t pt-6 text-sm text-muted-foreground">
        <Link href="/privacy">Privacy policy</Link>
        <Link href="/terms">Terms of service</Link>
        <Link href="/refunds">Refunds and cancellation</Link>
        <Link href="/attribution">Attribution</Link>
        <a href={`mailto:${LEGAL.contact}`}>{LEGAL.contact}</a>
      </nav>
    </div>
  );
}
