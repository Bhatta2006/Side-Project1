'use client';

import { Moon, Sun } from '@/components/icons';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { prefersReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';

/** Light/dark switch. The icons swap with CSS only; the page crossfades via the View Transition API when available. */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const toggle = () => {
    const next = resolvedTheme === 'dark' ? 'light' : 'dark';
    const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown };
    if (doc.startViewTransition && !prefersReducedMotion()) doc.startViewTransition(() => setTheme(next));
    else setTheme(next);
  };
  return (
    <Button variant="ghost" size="icon" className={cn('relative', className)} onClick={toggle} aria-label="Switch between light and dark theme" suppressHydrationWarning>
      <Sun className="absolute size-5 rotate-0 scale-100 transition-transform duration-300 ease-[var(--ease-soft)] dark:-rotate-90 dark:scale-0" aria-hidden="true" />
      <Moon className="absolute size-5 rotate-90 scale-0 transition-transform duration-300 ease-[var(--ease-soft)] dark:rotate-0 dark:scale-100" aria-hidden="true" />
    </Button>
  );
}
