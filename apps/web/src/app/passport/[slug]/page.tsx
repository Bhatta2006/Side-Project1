import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { PassportView } from '@/lib/types';
import { PassportCard } from '@/components/passport-view';
import { ArrowCircle, Button } from '@/components/ui/button';

const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';

async function load(slug: string): Promise<PassportView | null> {
  if (!/^[A-Za-z0-9_-]{8,24}$/.test(slug)) return null;
  const response = await fetch(`${API}/api/v1/passport/${slug}`, { cache: 'no-store' }).catch(() => null);
  if (!response?.ok) return null;
  return response.json();
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const passport = await load((await params).slug);
  if (!passport) return { title: 'Skill Passport' };
  const c = passport.counts;
  const n = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`;
  const description = `${n(c.unaided_solves, 'problem')} solved unaided, ${n(passport.mastered.length, 'skill')} mastered, ${n(c.checks_passed, 'check')} passed. Verified by Socrat.`;
  return {
    title: `${passport.name}'s Skill Passport`,
    description,
    openGraph: { title: `${passport.name}'s Skill Passport`, description, type: 'profile', siteName: 'Socrat' },
    twitter: { card: 'summary', title: `${passport.name}'s Skill Passport`, description },
  };
}

export default async function Passport({ params }: { params: Promise<{ slug: string }> }) {
  const passport = await load((await params).slug);
  if (!passport) notFound();
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:py-12">
      <PassportCard passport={passport} />
      <aside className="mt-10 flex flex-col items-start gap-4 rounded-card bg-raised p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-display text-xl font-semibold tracking-[-0.03em]">Learn it. Then prove it.</p>
          <p className="mt-1 text-[15px] text-muted-foreground">Socrat’s tutor asks before it tells, so every result here is the learner’s own.</p>
        </div>
        <Button asChild><Link href="/">Build your own passport<ArrowCircle /></Link></Button>
      </aside>
    </div>
  );
}
