import { BadgeCheck, CheckCircle2, ShieldCheck } from '@/components/icons';
import type { PassportView } from '@/lib/types';
import { LANGUAGE_LABEL } from '@/lib/routes';
import { Wordmark } from '@/components/socrat/wordmark';

function Stat({ value, label, hint }: { value: number; label: string; hint: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-1 bg-card p-4">
      <dt className="order-2 text-sm leading-snug font-semibold">{label}</dt>
      <dd className="order-1 font-display text-3xl leading-none font-semibold tracking-[-0.04em] tabular-nums">{value}</dd>
      <dd className="order-3 text-[13px] leading-snug text-muted-foreground">{hint}</dd>
    </div>
  );
}

/** The passport itself, shared by the public page and the owner's preview. No client state. */
export function PassportCard({ passport, headingLevel = 1 }: { passport: PassportView; headingLevel?: 1 | 2 }) {
  const Heading = headingLevel === 1 ? 'h1' : 'h2';
  const c = passport.counts;
  const generated = new Date(passport.generated_at * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  return (
    <article className="grid min-w-0 gap-5 sm:gap-6">
      <header data-tone="hero" className="rounded-card bg-forest p-5 text-forest-foreground sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <p className="type-label">Skill Passport</p>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-current px-3 py-1 text-[13px] font-semibold whitespace-nowrap"><ShieldCheck className="size-4 flex-none" aria-hidden="true" /> Verified by Socrat</span>
        </div>
        <Heading className="type-display-l mt-4 [overflow-wrap:anywhere]">{passport.name}</Heading>
        <p className="mt-2 text-base">
          {passport.course ? `${passport.course}${passport.language ? ` in ${LANGUAGE_LABEL[passport.language]}` : ''}. ` : ''}Learning on Socrat since {passport.member_since}.
        </p>
      </header>

      {/* Six cells, so the grid is full at two columns and at three: no stray card on any screen. */}
      <section aria-label="Verified results">
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-[4px] border bg-border sm:grid-cols-3">
          <Stat value={c.unaided_solves} label="Solved unaided" hint="No hints used" />
          <Stat value={c.judged_solves} label="Judged solves" hint={c.assisted_solves ? `${c.assisted_solves} with tutor help` : 'All hidden tests passed'} />
          <Stat value={c.checks_passed} label="Checks passed" hint="Checks and reviews" />
          <Stat value={c.transfer_verified} label="Transfer verified" hint="On an unseen problem" />
          <Stat value={c.checkpoints} label="Checkpoints" hint={c.weekly_assessments ? `${c.weekly_assessments} weekly assessments` : 'Module test-outs'} />
          <Stat value={c.longest_streak} label="Longest streak" hint="Days in a row" />
        </dl>
      </section>

      <section aria-labelledby="mastered-heading" className="paper rounded-card p-5 lg:p-6">
        <h2 id="mastered-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Mastered</h2>
        <p className="mt-1 text-[15px] text-muted-foreground">Shown in checks and judged code, and still holding up in spaced reviews.</p>
        {passport.mastered.length ? (
          <ul className="mt-4 flex flex-wrap gap-2">
            {passport.mastered.map(s => (
              <li key={s.id} className="inline-flex min-h-10 max-w-full flex-wrap items-center gap-x-2 gap-y-1 rounded-[20px] bg-primary px-4 py-1.5 text-[15px] font-semibold text-primary-foreground">
                <CheckCircle2 className="size-4 flex-none" aria-hidden="true" /><span className="min-w-0 [overflow-wrap:anywhere]">{s.title}</span>
                {s.transfer_verified ? <span className="rounded-full bg-primary-foreground/20 px-2 text-[12px]">Verified on a new problem</span> : null}
              </li>
            ))}
          </ul>
        ) : <p className="mt-4 text-[15px]">No skill has reached mastery yet. Mastery needs repeated, unaided evidence over time.</p>}
        {passport.practising.length ? (
          <>
            <h3 className="mt-6 text-[15px] font-semibold">Practising</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {passport.practising.map(s => (
                <li key={s.id} className="inline-flex min-h-9 max-w-full items-center rounded-[18px] border border-border-strong px-3.5 py-1 text-sm [overflow-wrap:anywhere]">{s.title}</li>
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
                <span className="min-w-0"><span className="font-semibold">{b.title}.</span> <span className="text-muted-foreground">{b.description}</span></span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="flex flex-wrap items-center justify-between gap-3 text-[13px] text-muted-foreground">
        <span className="min-w-0 basis-64 grow">Computed from judged submissions and checks on {generated}. Reading a lesson never counts, and help received lowers what a result counts for.</span>
        <Wordmark size={22} />
      </footer>
    </article>
  );
}
