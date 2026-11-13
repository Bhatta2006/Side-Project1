import type { Metadata } from 'next';
import Link from 'next/link';
import { CONTRIBUTORS, UPDATED } from '@/lib/changelog';
import { LEGAL } from '@/lib/legal';

export const metadata: Metadata = {
  title: 'Change log',
  description: 'The learners whose bug reports and feature requests were fixed or built.',
};

const day = (iso: string) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });

/** Public: everyone whose reports shipped, with a count and their one major report. */
export default function ChangelogPage() {
  const people = [...CONTRIBUTORS].sort((a, b) => b.reports - a.reports || a.name.localeCompare(b.name));
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pt-8 pb-24 sm:px-6">
      <header className="mb-8 border-b pb-6">
        <p className="type-label mb-3 text-muted-foreground">Last updated <time dateTime={UPDATED}>{day(UPDATED)}</time></p>
        <h1 className="type-display-l">Change log</h1>
        <p className="mt-4 text-base text-pretty text-muted-foreground">
          The learners who reported a bug or asked for a feature that we then fixed or built. Thank you.
        </p>
      </header>

      <ul className="grid gap-px overflow-hidden rounded-[4px] border bg-border">
        {people.map(person => (
          <li key={person.name} className="grid gap-1.5 bg-card p-4 sm:p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h2 className="min-w-0 text-base font-semibold [overflow-wrap:anywhere]">{person.name}</h2>
              <p className="flex-none text-[15px] tabular-nums">{person.reports} {person.reports === 1 ? 'report' : 'reports'} solved</p>
            </div>
            <p className="text-[15px] leading-relaxed text-pretty text-muted-foreground">
              <span className="type-label mr-2">Major</span>{person.major}
            </p>
          </li>
        ))}
      </ul>

      <aside className="mt-12 border-t pt-6 text-[15px] text-muted-foreground">
        Found a bug or want something added? Use the Feedback button in the app, or write to{' '}
        <a href={`mailto:${LEGAL.contact}`} className="font-medium text-foreground underline underline-offset-4">{LEGAL.contact}</a>. If we ship it, your name goes here.{' '}
        <Link href="/" className="font-medium text-foreground underline underline-offset-4">Back to the home page</Link>
      </aside>
    </div>
  );
}
