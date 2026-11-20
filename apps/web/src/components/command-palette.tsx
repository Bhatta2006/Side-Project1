'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BookOpen, CalendarCheck, ChartNoAxesColumn, House, NotebookPen, RotateCcw, Route, Settings, Shapes, Sparkles } from '@/components/icons';
import { api } from '@/lib/api';
import { NAME, conceptHref } from '@/lib/routes';
import type { CourseFeatures, DrillOverview } from '@/lib/types';
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

// `needs`: shown only when the learner's course has it.
const PAGES: { href: string; label: string; icon: typeof House; keywords: string; needs?: keyof CourseFeatures }[] = [
  { href: '/today', label: NAME.today, icon: House, keywords: 'home dashboard' },
  { href: '/plan', label: NAME.skills, icon: Route, keywords: 'plan roadmap modules schedule' },
  { href: '/courses', label: 'Courses', icon: BookOpen, keywords: 'my courses library catalog community shared switch' },
  { href: '/studio', label: NAME.practiceSets, icon: Sparkles, keywords: 'practice questions quiz drill', needs: 'drills' },
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
  const pages = PAGES.filter(p => !p.needs || features[p.needs]);
  const [query, setQuery] = useState('');
  const [concepts, setConcepts] = useState<Concept[]>([]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setConcepts([]);
    // The learner's own course lists its topics.
    api.get<DrillOverview>('/drills').then(o => {
      if (active) setConcepts(o.concepts.filter(c => !c.locked).map(c => ({ id: c.concept, title: c.title, module: o.course, locked: false })));
    }).catch(() => undefined);
    return () => { active = false; };
  }, [open]);
  function go(href: string) {
    setOpen(false);
    setQuery('');
    if (href.startsWith('http')) window.open(href, '_blank', 'noopener,noreferrer');
    else router.push(href);
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen} title="Search Socrat" description="Jump to a page or lesson">
      <Command>
      <CommandInput placeholder="Search lessons and pages…" value={query} onValueChange={setQuery} />
      <CommandList>
        <CommandEmpty>No results. Try another word.</CommandEmpty>
        <CommandGroup heading="Pages">
          {pages.map(p => (
            <CommandItem key={p.href} value={`page ${p.label} ${p.keywords}`} onSelect={() => go(p.href)}>
              <p.icon /> {p.label}
            </CommandItem>
          ))}
        </CommandGroup>
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
