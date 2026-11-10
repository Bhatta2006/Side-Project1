'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { conceptHref } from '@/lib/routes';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { EmptyState } from '@/components/socrat/states';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * The course's own sections (GET /sections): what this subject needs beyond lessons and
 * practice (a vocabulary, a timeline, a repertoire), plus key ideas, mistakes, formulas and
 * sources built from every course's lessons. Each fills as the learner finishes lessons.
 */
interface Entry { values: string[]; url?: string }
interface Group { concept: string; title: string; entries: Entry[] }
interface Section {
  id: string;
  title: string;
  purpose: string;
  style: 'cards' | 'table' | 'timeline' | 'list';
  fields: string[];
  built_in: boolean;
  count: number;
  groups: Group[];
}
interface Overview { course: string; lessons_done: number; lessons_total: number; sections: Section[] }

function Value({ entry, index, formula }: { entry: Entry; index: number; formula: boolean }) {
  const text = entry.values[index];
  if (formula) return <code className="font-mono text-[15px] break-words">{text}</code>;
  if (index === 0 && entry.url) {
    return <a href={entry.url} target="_blank" rel="noreferrer" className="font-semibold underline underline-offset-4">{text}</a>;
  }
  return <>{text}</>;
}

function Entries({ section, group }: { section: Section; group: Group }) {
  const formula = section.id === 'formulas';
  if (section.style === 'table' && section.fields.length > 1) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[15px]">
          <thead>
            <tr className="border-b text-sm text-muted-foreground">
              {section.fields.map(f => <th key={f} scope="col" className="py-2 pr-4 font-medium">{f}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y">
            {group.entries.map((e, i) => (
              <tr key={i}>
                {section.fields.map((f, n) => (
                  <td key={f} className={`py-2 pr-4 align-top ${n === 0 ? 'font-semibold' : 'text-muted-foreground'}`}>
                    <Value entry={e} index={n} formula={false} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (section.style === 'timeline') {
    return (
      <ol className="grid gap-3 border-l border-border-strong pl-4">
        {group.entries.map((e, i) => (
          <li key={i} className="grid gap-0.5">
            <span className="text-sm font-semibold tabular-nums">{e.values[0]}</span>
            {e.values.slice(1).map((v, n) => (
              <span key={n} className={n === 0 ? 'text-[15px]' : 'text-[15px] text-muted-foreground'}>{v}</span>
            ))}
          </li>
        ))}
      </ol>
    );
  }
  if (section.style === 'cards') {
    return (
      <ul className="grid gap-3 sm:grid-cols-2">
        {group.entries.map((e, i) => (
          <li key={i} className="grid gap-1 rounded-xl border border-border-strong p-4">
            <span className="text-[17px] font-semibold">{e.values[0]}</span>
            {e.values.slice(1).map((v, n) => (
              <span key={n} className="text-[15px] text-muted-foreground">
                <span className="sr-only">{section.fields[n + 1]}: </span>{v}
              </span>
            ))}
          </li>
        ))}
      </ul>
    );
  }
  return (
    <ul className="grid list-disc gap-2 pl-5 text-[15px]">
      {group.entries.map((e, i) => (
        <li key={i}>
          <Value entry={e} index={0} formula={formula} />
          {e.values.slice(1).map((v, n) => <span key={n} className="text-muted-foreground">, {v}</span>)}
        </li>
      ))}
    </ul>
  );
}

export default function NotesPage() {
  const allowed = useGuard('active');
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<Overview>('/sections').then(setData).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!data && !error)) return <Loading label="Loading your notes" />;
  if (!data) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const section = data.sections.find(s => s.id === open) ?? data.sections[0];
  return (
    <Page narrow>
      <PageHeader
        title="Notes"
        description={`What you have collected in ${data.course}: ${data.lessons_done} of ${data.lessons_total} lessons finished. Each lesson you finish adds to these.`}
      />
      {section ? (
        <>
          <div className="mb-6 flex flex-wrap gap-1 rounded-2xl bg-raised p-1" role="group" aria-label="Sections">
            {data.sections.map(s => (
              <button
                key={s.id}
                type="button"
                aria-pressed={section.id === s.id}
                onClick={() => setOpen(s.id)}
                className={`min-h-10 rounded-full px-4 text-sm font-semibold ${section.id === s.id ? 'bg-card shadow-sm' : 'text-muted-foreground'}`}
              >
                {s.title}{s.count ? <span className="ml-1.5 font-normal tabular-nums text-muted-foreground">{s.count}</span> : null}
              </button>
            ))}
          </div>
          <p className="mb-4 max-w-[68ch] text-[15px] text-muted-foreground">{section.purpose}</p>
          {section.groups.length ? (
            <div className="grid gap-4">
              {section.groups.map(g => (
                <Card key={g.concept} className="grid gap-3 p-5 lg:p-6">
                  <h2 className="text-sm font-medium text-muted-foreground">
                    From <Link href={conceptHref(g.concept)} className="text-foreground underline-offset-4 hover:underline">{g.title}</Link>
                  </h2>
                  <Entries section={section} group={g} />
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState title={`Nothing in ${section.title} yet`} illustration={false}>
              <p>It fills as you finish lessons that add to it.</p>
            </EmptyState>
          )}
        </>
      ) : (
        <EmptyState title="Your notes start with your first lesson" action={<Button asChild><Link href="/today">Go to today</Link></Button>}>
          <p>Finish a lesson and its key ideas, mistakes to avoid and sources are kept here.</p>
        </EmptyState>
      )}
    </Page>
  );
}
