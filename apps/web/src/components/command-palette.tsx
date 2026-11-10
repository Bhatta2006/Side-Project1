'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BookOpen, Building2, CalendarCheck, ChartNoAxesColumn, ExternalLink, House, NotebookPen, RotateCcw, Route, Settings, Shapes, Sparkles, SquareCode, Timer } from 'lucide-react';
import { api } from '@/lib/api';
import { NAME, conceptHref } from '@/lib/routes';
import type { CourseFeatures, DrillOverview, LibraryProblem } from '@/lib/types';
import { useCourse } from '@/lib/course';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';

// `needs`: shown only when the learner's course has it (company questions are DSA only).
const PAGES: { href: string; label: string; icon: typeof House; keywords: string; needs?: keyof CourseFeatures }[] = [
  { href: '/today', label: NAME.today, icon: House, keywords: 'home dashboard' },
  { href: '/plan', label: NAME.skills, icon: Route, keywords: 'plan roadmap modules schedule' },
  { href: '/library', label: NAME.problems, icon: SquareCode, keywords: 'practice library', needs: 'library' },
  { href: '/studio', label: NAME.practiceSets, icon: Sparkles, keywords: 'practice questions quiz drill', needs: 'drills' },
  { href: '/companies', label: NAME.companies, icon: Building2, keywords: 'interview bank', needs: 'companies' },
  { href: '/sprint', label: NAME.sprint, icon: Timer, keywords: 'timer clock', needs: 'library' },
  { href: '/playground', label: NAME.playground, icon: Shapes, keywords: 'visual explain' },
  { href: '/reviews', label: 'Reviews', icon: RotateCcw, keywords: 'review spaced recall snooze due' },
  { href: '/notes', label: 'Notes', icon: NotebookPen, keywords: 'notes key ideas mistakes formulas sources vocabulary timeline sections' },
  { href: '/progress', label: NAME.evidence, icon: ChartNoAxesColumn, keywords: 'progress mastery history' },
  { href: '/assessments', label: NAME.assessment, icon: CalendarCheck, keywords: 'assessments test exam' },
  { href: '/settings', label: NAME.settings, icon: Settings, keywords: 'account theme' },
];

interface Concept { id: string; title: string; module: string; locked: boolean }

/** The ⌘K dialog; loaded on first use so cmdk stays out of every page's bundle. */
export default function CommandPalette({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) {
  const router = useRouter();
  const { features } = useCourse();
  const library = features.library;
  const pages = PAGES.filter(p => !p.needs || features[p.needs]);
  const [query, setQuery] = useState('');
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [problems, setProblems] = useState<LibraryProblem[]>([]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setConcepts([]);
    if (library) {
      api.get<{ concepts: Concept[] }>('/library/meta').then(m => { if (active) setConcepts(m.concepts.filter(c => !c.locked)); }).catch(() => undefined);
    } else {
      // Courses without the library list their own topics.
      api.get<DrillOverview>('/drills').then(o => {
        if (active) setConcepts(o.concepts.filter(c => !c.locked).map(c => ({ id: c.concept, title: c.title, module: o.course, locked: false })));
      }).catch(() => undefined);
    }
    return () => { active = false; };
  }, [open, library]);
  useEffect(() => {
    if (!open || !library || query.trim().length < 2) { setProblems([]); return; }
    setProblems([]);
    let active = true;
    const timer = setTimeout(() => {
      api.get<{ items: LibraryProblem[] }>(`/library?q=${encodeURIComponent(query.trim())}&sort=popular&limit=6`)
        .then(r => { if (active) setProblems(r.items); })
        .catch(() => undefined);
    }, 200);
    return () => { active = false; clearTimeout(timer); };
  }, [open, query, library]);

  function go(href: string) {
    setOpen(false);
    setQuery('');
    if (href.startsWith('http')) window.open(href, '_blank', 'noopener,noreferrer');
    else router.push(href);
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen} title="Search Socrat" description={library ? "Jump to a page, lesson or problem" : "Jump to a page or lesson"}>
      <Command>
      <CommandInput placeholder={library ? "Search lessons, problems, pages…" : "Search lessons and pages…"} value={query} onValueChange={setQuery} />
      <CommandList>
        <CommandEmpty>No results. Try another word.</CommandEmpty>
        <CommandGroup heading="Pages">
          {pages.map(p => (
            <CommandItem key={p.href} value={`page ${p.label} ${p.keywords}`} onSelect={() => go(p.href)}>
              <p.icon /> {p.label}
            </CommandItem>
          ))}
        </CommandGroup>
        {problems.length ? (
          <>
            <CommandSeparator />
            <CommandGroup heading="Problems">
              {problems.map(p => (
                <CommandItem key={p.id} value={`problem ${p.title} ${query}`} onSelect={() => go(p.url)}>
                  <span className="truncate">{p.title}</span>
                  <span className="ml-auto flex flex-none items-center gap-1 text-[13px] text-muted-foreground">
                    {p.url.startsWith('http') ? <>Opens on {p.platform} <ExternalLink className="size-3.5!" aria-hidden="true" /></> : p.platform}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        ) : null}
        {concepts.length ? (
          <>
            <CommandSeparator />
            <CommandGroup heading="Skills">
              {concepts.map(c => (
                <CommandItem key={c.id} value={`lesson ${c.title} ${c.module}`} onSelect={() => go(conceptHref(c.id))}>
                  <BookOpen /> <span className="truncate">{c.title}</span>
                  <span className="ml-auto text-[13px] text-muted-foreground">{c.module}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        ) : null}
      </CommandList>
      </Command>
    </CommandDialog>
  );
}
