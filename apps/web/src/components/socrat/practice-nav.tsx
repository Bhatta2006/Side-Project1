'use client';

import Link from 'next/link';
import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { PRACTICE_SEGMENTS } from '@/lib/routes';
import { useCourse } from '@/lib/course';
import { cn } from '@/lib/utils';

/**
 * Problems | Company questions | Company sprint | Focus sprint, as far as the course has them
 * (company questions are DSA only). Real route links, so URLs and back work.
 */
export function PracticeNav({ className }: { className?: string }) {
  const pathname = usePathname();
  const nav = useRef<HTMLElement>(null);
  const { features } = useCourse();
  const segments = PRACTICE_SEGMENTS.filter(segment => features[segment.needs]);
  // On a narrow screen the tab row scrolls; keep the current tab in view.
  useEffect(() => {
    nav.current?.querySelector('[aria-current="page"]')?.scrollIntoView({ block: 'nearest', inline: 'center' });
  }, [pathname]);
  if (segments.length < 2) return null;
  return (
    <nav ref={nav} data-tour="practice-nav" aria-label="Practice" className={cn('no-scrollbar mb-6 max-w-full overflow-x-auto', className)}>
      <ul className="inline-flex h-12 items-center gap-1 rounded-full bg-raised p-1">
        {segments.map(segment => {
          const active = pathname === segment.href || pathname.startsWith(`${segment.href}/`);
          return (
            <li key={segment.href} className="h-full">
              <Link
                href={segment.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-flex h-full min-h-10 items-center rounded-full border border-transparent px-4 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground',
                  active && 'border-border bg-card font-bold text-foreground',
                )}
              >
                {segment.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
