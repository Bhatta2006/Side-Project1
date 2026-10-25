'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { BAND_LABEL, conceptHref } from '@/lib/routes';
import type { LearnerProfile } from '@/lib/types';

function spacing(scale: number) {
  if (scale >= 1.15) return 'You remember well, so reviews are spaced further apart.';
  if (scale <= 0.85) return 'Reviews come a little sooner, so ideas stick.';
  return 'Reviews follow the standard spacing.';
}

/** A1: what Socrat's learner model says, in words, so adaptation is never a black box. */
export function LearnerProfileCard() {
  const [profile, setProfile] = useState<LearnerProfile | null>(null);

  useEffect(() => {
    api.get<LearnerProfile>('/adaptive/profile').then(setProfile).catch(() => undefined);
  }, []);

  if (!profile) return null;
  const stuck = profile.concepts.filter(c => c.stuck);
  const rising = profile.concepts.filter(c => (c.trend ?? 0) >= 0.2).map(c => c.title);
  const leaning = profile.concepts.filter(c => c.hint_dependence >= 0.6 && c.attempts >= 3).map(c => c.title);
  return (
    <section className="paper rounded-card p-5 lg:p-6" aria-labelledby="model-heading">
      <h2 id="model-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">How Socrat sees you</h2>
      <p className="mt-1 text-sm text-muted-foreground">What your plan adapts to. Estimates from your evidence, not grades.</p>
      <dl className="mt-4 grid gap-3 text-[15px]">
        <div>
          <dt className="font-semibold">Practice level</dt>
          <dd className="text-muted-foreground">
            About {profile.level.rating}
            {profile.level.codeforces ? `, with your Codeforces rating of ${profile.level.codeforces}` : ''}
          </dd>
        </div>
        <div>
          <dt className="font-semibold">Study rhythm</dt>
          <dd className="text-muted-foreground">
            About {Math.round(profile.adherence * 100)}% of your planned time. Your finish date uses this.
          </dd>
        </div>
        <div>
          <dt className="font-semibold">Memory</dt>
          <dd className="text-muted-foreground">{spacing(profile.review_scale)}</dd>
        </div>
        {rising.length ? (
          <div>
            <dt className="font-semibold">Improving</dt>
            <dd className="text-muted-foreground">{rising.slice(0, 4).join(', ')}</dd>
          </div>
        ) : null}
        {leaning.length ? (
          <div>
            <dt className="font-semibold">Leaning on hints</dt>
            <dd className="text-muted-foreground">{leaning.slice(0, 4).join(', ')}</dd>
          </div>
        ) : null}
      </dl>
      {stuck.length ? (
        <div className="mt-4">
          <h3 className="type-label mb-2 text-muted-foreground">Where you&apos;re stuck</h3>
          <ul className="grid gap-2">
            {stuck.map(c => (
              <li key={c.concept} className="rounded-[16px] bg-raised p-3">
                <Link href={conceptHref(c.concept)} className="font-semibold underline-offset-4 hover:underline">{c.title}</Link>
                <span className="ml-2 text-[13px] text-muted-foreground">{BAND_LABEL[c.band]}</span>
                <p className="mt-1 text-[14px] text-muted-foreground">{c.stuck?.summary}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
