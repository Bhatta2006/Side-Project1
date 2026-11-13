'use client';

import { createContext, useContext, useState, type ComponentProps, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

/*
 * Plain building blocks for the admin page. The learner-facing Card, Table and Tabs each draw a
 * sheet of textured paper with inked edges, which is the look of the product but a lot of paint
 * for a page that is mostly tables. These have the same names and props, so the admin screens
 * read the same, and render as flat boxes and ordinary tables: one border, no texture, no ink.
 */

export function Card({ className, ...props }: ComponentProps<'section'>) {
  return <section className={cn('flex flex-col gap-4 rounded-[6px] border bg-card py-4', className)} {...props} />;
}

export function CardHeader({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('grid gap-1 px-4', className)} {...props} />;
}

export function CardTitle({ className, ...props }: ComponentProps<'h2'>) {
  return <h2 className={cn('text-base leading-snug font-semibold', className)} {...props} />;
}

export function CardDescription({ className, ...props }: ComponentProps<'p'>) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />;
}

export function CardContent({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('px-4', className)} {...props} />;
}

/** One number with its label: a flat cell, several of them in a `StatRow`. */
export function StatCard({ label, value, hint, className }: { icon?: ReactNode; label: ReactNode; value: ReactNode; hint?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex min-w-0 flex-col gap-0.5 bg-card p-4', className)}>
      <p className="text-xl leading-tight font-semibold tabular-nums">{value}</p>
      <p className="text-sm font-medium">{label}</p>
      {hint ? <p className="text-[13px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** Stat cells side by side, divided by hairlines; always full rows of two or four. */
export function StatRow({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('grid grid-cols-2 gap-px overflow-hidden rounded-[6px] border bg-border xl:grid-cols-4', className)} {...props} />;
}

export function Table({ className, ...props }: ComponentProps<'table'>) {
  return (
    <div className="w-full overflow-x-auto border-t">
      <table className={cn('w-full border-collapse text-sm', className)} {...props} />
    </div>
  );
}

export function TableHeader(props: ComponentProps<'thead'>) {
  return <thead {...props} />;
}

export function TableBody({ className, ...props }: ComponentProps<'tbody'>) {
  return <tbody className={cn('[&_tr:last-child]:border-0', className)} {...props} />;
}

export function TableRow({ className, ...props }: ComponentProps<'tr'>) {
  return <tr className={cn('border-b', className)} {...props} />;
}

export function TableHead({ className, ...props }: ComponentProps<'th'>) {
  return <th className={cn('px-3 py-2 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground', className)} {...props} />;
}

export function TableCell({ className, ...props }: ComponentProps<'td'>) {
  return <td className={cn('px-3 py-2 align-top', className)} {...props} />;
}

const TabsContext = createContext<{ value: string; set: (value: string) => void }>({ value: '', set: () => undefined });

/** Tabs that mount only the open panel, so a closed tab costs no requests and no rendering. */
export function Tabs({ defaultValue, className, children }: { defaultValue: string; className?: string; children: ReactNode }) {
  const [value, set] = useState(defaultValue);
  return <TabsContext.Provider value={{ value, set }}><div className={cn('grid gap-6', className)}>{children}</div></TabsContext.Provider>;
}

export function TabsList({ className, ...props }: ComponentProps<'div'>) {
  return <div role="tablist" className={cn('flex gap-1 overflow-x-auto border-b', className)} {...props} />;
}

export function TabsTrigger({ value, className, children }: { value: string; className?: string; children: ReactNode }) {
  const tabs = useContext(TabsContext);
  const on = tabs.value === value;
  return (
    <button
      type="button"
      role="tab"
      id={`admin-tab-${value}`}
      aria-selected={on}
      aria-controls={`admin-panel-${value}`}
      onClick={() => tabs.set(value)}
      className={cn('-mb-px min-h-11 flex-none border-b-2 px-3 text-[15px] whitespace-nowrap', on ? 'border-foreground font-semibold' : 'border-transparent text-muted-foreground hover:text-foreground', className)}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, className, children }: { value: string; className?: string; children: ReactNode }) {
  const tabs = useContext(TabsContext);
  if (tabs.value !== value) return null;
  return <div role="tabpanel" id={`admin-panel-${value}`} aria-labelledby={`admin-tab-${value}`} className={cn('min-w-0', className)}>{children}</div>;
}

/** A text field in the admin's plain style. */
export const field = 'h-10 w-full rounded-[6px] border border-border-strong bg-card px-3 text-sm';

export const when = (seconds: number) => new Date(seconds * 1000).toLocaleString();
export const day = (seconds: number) => new Date(seconds * 1000).toLocaleDateString();
