import { BadgeCheck, CheckCircle2, ShieldCheck } from 'lucide-react';
import type { PassportView } from '@/lib/types';
import { LANGUAGE_LABEL } from '@/lib/routes';
import { Wordmark } from '@/components/socrat/wordmark';

function Stat({ value, label, hint }: { value: number; label: string; hint?: string }) {
  return (
    <div className="rounded-[20px] border bg-card p-4">
      <p className="font-display text-4xl leading-none font-semibold tracking-[-0.04em] tabular-nums">{value}</p>
      <p className="mt-2 text-sm font-semibold">{label}</p>
      {hint ? <p className="mt-0.5 text-[13px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** The passport itself, shared by the public page and the owner's preview. No client state. */
export function PassportCard({ passport, headingLevel = 1 }: { passport: PassportView; headingLevel?: 1 | 2 }) {
  const Heading = headingLevel === 1 ? 'h1' : 'h2';
  const c = passport.counts;
  const generated = new Date(passport.generated_at * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  return (
    <article className="grid gap-6">
      <header data-tone="hero" className="grain relative overflow-hidden rounded-card bg-forest p-6 text-forest-foreground sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="type-label">Skill Passport</p>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-current px-3 py-1 text-[13px] font-semibold"><ShieldCheck className="size-4" aria-hidden="true" /> Verified by Socrat</span>
        </div>
        <Heading className="type-display-l mt-4 break-words">{passport.name}</Heading>
        <p className="mt-2 text-base">
          {passport.course ? `${passport.course}${passport.language ? ` in ${LANGUAGE_LABEL[passport.language]}` : ''}. ` : ''}Learning on Socrat since {passport.member_since}.
        </p>
      </header>

      <section aria-label="Verified results" className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat value={c.unaided_solves} label="Solved unaided" hint="Judged problems, no hints" />
        <Stat value={c.judged_solves} label="Judged solves" hint={c.assisted_solves ? `${c.assisted_solves} with tutor help` : 'All hidden tests passed'} />
        <Stat value={c.checks_passed} label="Checks passed" hint="Concept checks and reviews, unaided" />
        <Stat value={c.checkpoints} label="Checkpoints" hint={c.weekly_assessments ? `${c.weekly_assessments} weekly assessments` : 'Module test-outs'} />
      </section>

      <section aria-labelledby="mastered-heading" className="paper rounded-card p-5 lg:p-6">
        <h2 id="mastered-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Mastered</h2>
        <p className="mt-1 text-[15px] text-muted-foreground">Shown in checks and judged code, and still holding up in spaced reviews.</p>
        {passport.mastered.length ? (
          <ul className="mt-4 flex flex-wrap gap-2">
            {passport.mastered.map(s => (
              <li key={s.id} className="inline-flex min-h-10 items-center gap-2 rounded-full bg-primary px-4 text-[15px] font-semibold text-primary-foreground">
                <CheckCircle2 className="size-4" aria-hidden="true" />{s.title}
              </li>
            ))}
          </ul>
        ) : <p className="mt-4 text-[15px]">No skill has reached mastery yet. Mastery needs repeated, unaided evidence over time.</p>}
        {passport.practising.length ? (
          <>
            <h3 className="mt-6 text-[15px] font-semibold">Practising</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {passport.practising.map(s => (
                <li key={s.id} className="inline-flex min-h-9 items-center rounded-full border border-border-strong px-3.5 text-sm">{s.title}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      {passport.badges.length ? (
        <section aria-labelledby="badges-heading" className="paper rounded-card p-5 lg:p-6">
          <h2 id="badges-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Milestones</h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {passport.badges.map(b => (
              <li key={b.id} className="flex gap-3">
                <BadgeCheck className="mt-0.5 size-5 flex-none text-primary" aria-hidden="true" />
                <span><span className="font-semibold">{b.title}.</span> <span className="text-muted-foreground">{b.description}</span></span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="flex flex-wrap items-center justify-between gap-3 text-[13px] text-muted-foreground">
        <span>Computed from judged submissions and checks on {generated}. Reading a lesson never counts, and help received lowers what a result counts for.</span>
        <Wordmark size={22} />
      </footer>
    </article>
  );
}
