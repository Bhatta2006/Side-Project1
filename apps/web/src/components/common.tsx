'use client';

import Link from 'next/link';
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { ArrowLeft } from '@/components/icons';
import { cn } from '@/lib/utils';
import type { Band } from '@/lib/types';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/socrat/states';
import { StatusLabel, statusFromBand } from '@/components/socrat/status';

/** Page container: standard 1152 px, wide 1440 px, narrow 768 px. Padding 16 / 24 / 40. */
export function Page({ children, wide = false, narrow = false, className }: { children: ReactNode; wide?: boolean; narrow?: boolean; className?: string }) {
  return (
    <div className={cn('mx-auto w-full px-4 pt-6 pb-32 sm:px-6 md:pt-8 lg:px-10 lg:pb-16', wide ? 'max-w-[1440px]' : narrow ? 'max-w-3xl' : 'max-w-6xl', className)}>
      {children}
    </div>
  );
}

/** Optional 11 px eyebrow, a display-l title, one muted line. */
export function PageHeader({ eyebrow, title, description, actions, className }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <header className={cn('mb-8 flex flex-wrap items-end justify-between gap-4 lg:mb-10', className)}>
      <div className="min-w-0 max-w-3xl">
        {eyebrow ? <p className="font-hand mb-2 origin-left -rotate-2 text-[22px] text-pen">{eyebrow}</p> : null}
        <h1 className="type-display-l">{title}</h1>
        {description ? <p className="mt-3 text-base text-muted-foreground text-pretty">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** Small section heading inside a page, in the display face. */
export function SectionTitle({ id, children, className, as: Tag = 'h2' }: { id?: string; children: ReactNode; className?: string; as?: 'h2' | 'h3' }) {
  return <Tag id={id} className={cn('font-display text-2xl font-semibold tracking-[-0.03em]', className)}>{children}</Tag>;
}

/** Content-shaped placeholder; perceived as faster than a spinner. */
type LoadingVariant = 'page' | 'inline' | 'article' | 'workspace' | 'list' | 'quiz' | 'form' | 'blank';

function HeaderSkeleton() {
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-12 w-96 max-w-full" />
      <Skeleton className="h-4 w-[28rem] max-w-full" />
    </div>
  );
}

/** Lines of text of varied length, like a paragraph. */
function Lines({ count, className }: { count: number; className?: string }) {
  return (
    <div className={cn('grid gap-3', className)}>
      {Array.from({ length: count }, (_, i) => <Skeleton key={i} className="h-4 rounded-full" style={{ width: `${[96, 88, 92, 70, 84, 60][i % 6]}%` }} />)}
    </div>
  );
}

/**
 * Page-shaped placeholders: each variant mirrors its page's layout so content lands where
 * the skeleton was (no layout shift) and the wait feels shorter.
 */
export function Loading({ label = 'Loading', variant = 'page' }: { label?: string; variant?: LoadingVariant }) {
  if (variant === 'inline') {
    return (
      <div className="grid gap-2 p-4" role="status" aria-label={label}>
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-11 w-full" />)}
      </div>
    );
  }
  if (variant === 'blank') {
    // Public pages that usually redirect: a skeleton would flash a layout that never appears.
    return <div className="min-h-[60dvh]" role="status" aria-label={label}><span className="sr-only">{label}</span></div>;
  }
  const body = {
    page: (
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-6">
        <div className="grid gap-4 lg:gap-6">
          <Skeleton className="h-64 w-full rounded-card" />
          <div className="grid grid-cols-2 gap-3 lg:gap-6"><Skeleton className="h-36 rounded-card" /><Skeleton className="h-36 rounded-card" /></div>
          <Skeleton className="h-28 w-full rounded-card" />
        </div>
        <div className="grid content-start gap-4 lg:gap-6">
          <Skeleton className="h-40 w-full rounded-card" />
          <Skeleton className="h-28 w-full rounded-card" />
        </div>
      </div>
    ),
    article: (
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid content-start gap-6">
          <Skeleton className="h-40 w-full rounded-card" />
          <Lines count={5} />
          <Skeleton className="h-36 w-full rounded-[4px]" />
          <Lines count={4} />
        </div>
        <Skeleton className="hidden h-64 w-full rounded-card lg:block" />
      </div>
    ),
    workspace: (
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div className="grid content-start gap-5">
          <Lines count={4} />
          <Skeleton className="h-24 w-full rounded-[4px]" />
          <Lines count={3} />
        </div>
        <Skeleton className="h-[420px] w-full rounded-card" />
      </div>
    ),
    list: (
      <div className="grid gap-4">
        <div className="flex flex-wrap gap-2">
          <Skeleton className="h-13 w-80 max-w-full rounded-control" />
          {[0, 1, 2].map(i => <Skeleton key={i} className="h-11 w-32 rounded-full" />)}
        </div>
        <div className="grid gap-2">
          {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-14 w-full" />)}
        </div>
      </div>
    ),
    quiz: (
      <div className="mx-auto grid w-full max-w-2xl gap-5">
        <Skeleton className="h-1.5 w-full rounded-full" />
        <Lines count={2} />
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full rounded-[4px]" />)}
      </div>
    ),
    form: (
      <div className="mx-auto grid w-full max-w-3xl gap-4">
        {[0, 1, 2].map(i => (
          <div key={i} className="grid gap-3 rounded-card border p-6">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-13 w-full rounded-control" />
            <Skeleton className="h-13 w-2/3 rounded-control" />
          </div>
        ))}
      </div>
    ),
  }[variant];
  return (
    <Page>
      <div role="status" aria-label={label} className="grid animate-reveal gap-8" style={{ '--reveal-delay': '150ms' } as CSSProperties}>
        <span className="sr-only">{label}</span>
        <HeaderSkeleton />
        {body}
      </div>
    </Page>
  );
}

/** Kept for existing call sites: the shared inline error with a retry. */
export function ErrorNote({ message, retry, className, title }: { message: string; retry?: () => void; className?: string; title?: string }) {
  return <ErrorState message={message} retry={retry} className={className} title={title} />;
}

/** Progress ring: 4 px round-capped stroke, track in the hairline colour, the real value in the centre. */
export function Ring({ value, label, size = 64, stroke = 4, className, ariaLabel }: { value: number; label: ReactNode; size?: number; stroke?: number; className?: string; tone?: string; ariaLabel?: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setDrawn(true)); // start empty, then draw
    return () => cancelAnimationFrame(frame);
  }, []);
  return (
    <div className={cn('relative grid flex-none place-items-center', className)} style={{ width: size, height: size }} role="img" aria-label={ariaLabel ?? `${Math.round(clamped)} percent`}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--ring-track, var(--border))" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--ring-value, var(--primary))"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={drawn ? circumference * (1 - clamped / 100) : circumference}
          className="transition-[stroke-dashoffset] duration-[320ms] ease-[var(--ease-soft)]"
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-sm font-bold tabular-nums">{label}</span>
    </div>
  );
}

/** A number shown as-is in tabular figures (no count-up animation). */
export function NumberTicker({ value, className }: { value: number; className?: string }) {
  return <span className={cn('tabular-nums', className)}>{value.toLocaleString()}</span>;
}

/** A mastery band as a status shape with its label. */
export function BandBadge({ band, className, reviewDue = false }: { band: Band; className?: string; reviewDue?: boolean }) {
  return <StatusLabel status={statusFromBand(band, reviewDue)} size={18} muted className={cn('text-[13px]', className)} />;
}

export function BackLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} transitionTypes={['nav-back']} className={cn('mb-5 inline-flex min-h-11 items-center gap-2 rounded-full text-[15px] font-semibold text-muted-foreground transition-colors hover:text-foreground', className)}>
      <ArrowLeft className="size-4" aria-hidden="true" /> {children}
    </Link>
  );
}

/** Difficulty as an outlined chip with a 1–3 bar glyph, so the level never relies on colour. */
export function Difficulty({ level, className }: { level: string; className?: string }) {
  const bars = level === 'hard' ? 3 : level === 'medium' ? 2 : 1;
  return (
    <span className={cn('inline-flex h-7 items-center gap-1.5 rounded-full border border-border-strong px-2.5 text-[13px] font-semibold capitalize [[data-tone=hero]_&]:border-current [[data-tone=lilac]_&]:border-current', className)}>
      <svg viewBox="0 0 12 12" className="size-3" aria-hidden="true">
        {[0, 1, 2].map(i => <rect key={i} x={i * 4.2} y={8 - i * 3} width="3" height={4 + i * 3} rx="1" fill="currentColor" opacity={i < bars ? 1 : 0.25} />)}
      </svg>
      {level}
    </span>
  );
}

/** Supporting number: number first, noun second, a one-line definition below. */
export function StatCard({ icon, label, value, hint, className }: { icon?: ReactNode; label: ReactNode; value: ReactNode; hint?: ReactNode; className?: string }) {
  return (
    <div data-slot="card" className={cn('paper flex flex-col gap-2 rounded-card p-5 transition-transform duration-200 hover:-translate-y-0.5 lg:p-6', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="type-display-m tabular-nums">{value}</div>
        {icon ? <span className="flex-none text-muted-foreground [&_svg]:size-6">{icon}</span> : null}
      </div>
      <p className="font-semibold">{label}</p>
      {hint ? <p className="text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** Fade with an 8 px rise for page sections; staggered by index. CSS only. */
export function Reveal({ children, index = 0, className }: { children: ReactNode; index?: number; className?: string }) {
  return (
    <div className={cn('animate-reveal', className)} style={{ '--reveal-delay': `${Math.min(index, 6) * 40}ms` } as CSSProperties}>
      {children}
    </div>
  );
}
