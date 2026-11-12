import Link from 'next/link';
import { Check, Minus } from '@/components/icons';
import { ArrowCircle, Button } from '@/components/ui/button';

/**
 * The first question every learner asks: why not just use a chatbot? Each Socrat claim here
 * is a rule the server enforces (help ladder, leak guard, evidence weighting), not a promise.
 */
const ROWS = [
  {
    moment: 'You are stuck',
    chatbot: 'Writes the full solution the moment you ask.',
    socrat: 'Asks what you tried first. Help rises one step at a time, and only after real attempts.',
  },
  {
    moment: 'Code in the reply',
    chatbot: 'Hands you code to paste.',
    socrat: 'A leak guard on the server stops solution code until you have earned the walkthrough.',
  },
  {
    moment: 'Did you learn it?',
    chatbot: 'No way to tell.',
    socrat: 'Judged tests, concept checks and spaced reviews. Help you received lowers what a solve counts for.',
  },
  {
    moment: 'Next session',
    chatbot: 'Starts from a blank chat.',
    socrat: 'Knows your plan, the skills you have shown and the mistakes you keep making.',
  },
  {
    moment: 'What you can show',
    chatbot: 'A chat log.',
    socrat: 'A Skill Passport with verified evidence you can share with recruiters.',
  },
];

export function WhySocrat({ skills, problems }: { skills: number; problems: number }) {
  const facts: [string, string][] = [
    ['6', 'levels of help, enforced on the server'],
    [skills ? String(skills) : '100+', 'skills, each with its own checks'],
    [problems ? String(problems) : '100+', 'judged problems with hidden tests'],
  ];
  return (
    <section id="why" aria-labelledby="why-title" className="mx-auto max-w-[1500px] scroll-mt-20 px-5 py-20 sm:px-8 lg:py-28 lg:pr-10 lg:pl-[128px]">
      <div>
        <p className="font-hand origin-left -rotate-2 text-[24px] text-pen">the AI tutor that won&apos;t do your homework</p>
        <h2 id="why-title" className="type-display-l mt-4 max-w-[18ch]">Why not just <span className="hl">ask ChatGPT?</span></h2>
        <p className="type-body-l mt-4 max-w-2xl text-muted-foreground">
          A chatbot is built to answer. Socrat is built so that next time, <em>you</em> can, and so you can prove it.
        </p>

        <div className="paper mt-10 overflow-hidden rounded-card text-foreground">
          <div className="hidden grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)_minmax(0,1.3fr)] gap-6 border-b px-6 py-4 text-[13px] font-semibold text-muted-foreground md:grid">
            <span>When</span>
            <span>A general chatbot</span>
            <span className="text-brand">Socrat</span>
          </div>
          <ul>
            {ROWS.map(row => (
              <li key={row.moment} className="grid gap-3 border-b px-5 py-5 last:border-b-0 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)_minmax(0,1.3fr)] md:gap-6 md:px-6">
                <p className="font-display text-lg font-semibold tracking-[-0.03em]">{row.moment}</p>
                <p className="flex gap-2.5 text-[15px] text-muted-foreground">
                  <Minus className="mt-0.5 size-4.5 flex-none" aria-hidden="true" />
                  <span><span className="sr-only">A general chatbot: </span>{row.chatbot}</span>
                </p>
                <p className="flex gap-2.5 text-[15px] font-medium">
                  <span className="mt-0.5 grid size-5 flex-none place-items-center rounded-full bg-primary text-primary-foreground" aria-hidden="true"><Check className="size-3" strokeWidth={3} /></span>
                  <span><span className="sr-only">Socrat: </span>{row.socrat}</span>
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <dl className="grid grid-cols-3 gap-4 sm:gap-8">
            {facts.map(([value, label]) => (
              <div key={label}>
                <dt className="sr-only">{label}</dt>
                <dd className="font-display text-4xl leading-none font-semibold tracking-[-0.05em] tabular-nums sm:text-6xl">{value}</dd>
                <dd className="mt-2 max-w-[18ch] text-[13px] text-muted-foreground sm:text-sm">{label}</dd>
              </div>
            ))}
          </dl>
          <Button asChild variant="ink" size="lg"><a href="#try">See it on a real problem<ArrowCircle /></a></Button>
        </div>
      </div>
      <p className="mt-6 text-[13px] text-muted-foreground">
        Learning-outcome results from the beta cohort will be published here. <Link href="/login" className="underline underline-offset-4">Join the beta</Link> to be part of them.
      </p>
    </section>
  );
}
