'use client';

import type { ComponentProps, ReactNode } from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StatusIcon } from '@/components/socrat/status';

type Tone = 'idle' | 'correct' | 'wrong';

/**
 * A large selectable card. Use `role="radio"` + `aria-checked` for answers, or
 * `aria-pressed` for setup choices. Selected: an inked card with an offset shadow and a yellow marker.
 * Checked answers show shape plus colour: a check in a cream circle, or a coral triangle.
 */
export function Choice({
  selected = false,
  tone = 'idle',
  marker,
  icon,
  children,
  className,
  note,
  ...rest
}: ComponentProps<'button'> & { selected?: boolean; tone?: Tone; marker?: ReactNode; icon?: ReactNode; note?: ReactNode }) {
  const props = rest;
  return (
    <button
      type="button"
      data-selected={selected || undefined}
      data-tone={tone}
      className={cn(
        'group/choice flex min-h-14 w-full items-start gap-3 rounded-[20px] border border-border-strong bg-card p-4 text-left transition-[transform,box-shadow,border-color] duration-200 ease-[var(--ease-soft)] outline-none',
        'hover:border-foreground/40',
        // Selected: an inked card with an offset shadow, like a book pulled from Soc's stack.
        'data-[selected]:-translate-x-0.5 data-[selected]:-translate-y-0.5 data-[selected]:border-2 data-[selected]:border-[var(--soc-outline)] data-[selected]:shadow-[4px_4px_0_var(--soc-outline)] dark:data-[selected]:border-foreground dark:data-[selected]:shadow-[4px_4px_0_var(--foreground)] data-[selected]:[&_.choice-title]:font-semibold',
        'disabled:cursor-default disabled:hover:bg-card',
        tone === 'correct' && 'border-foreground ring-1 ring-foreground hover:bg-card',
        tone === 'wrong' && 'border-attention ring-1 ring-attention hover:bg-card',
        className,
      )}
      {...props}
    >
      {marker !== undefined ? (
        <span
          className={cn(
            'grid size-8 flex-none place-items-center rounded-full border border-dashed border-border-strong text-[13px] font-bold text-muted-foreground transition-colors',
            'group-data-[selected]/choice:border-solid group-data-[selected]/choice:border-[var(--soc-outline)] group-data-[selected]/choice:bg-[var(--highlight)] group-data-[selected]/choice:text-[#15161E]',
            tone === 'correct' && 'border-solid border-transparent! bg-[var(--highlight)]! text-[#15161E]!',
            tone === 'wrong' && 'border-none! bg-transparent!',
          )}
          aria-hidden="true"
        >
          {tone === 'correct' ? <Check className="size-4" /> : tone === 'wrong' ? <StatusIcon status="needs_practice" size={28} /> : marker}
        </span>
      ) : null}
      {icon ? <span className="grid size-10 flex-none place-items-center rounded-full bg-raised text-foreground transition-colors group-data-[selected]/choice:bg-[var(--highlight)] group-data-[selected]/choice:text-[#15161E] [&_svg]:size-5 [&_svg]:stroke-[1.5]">{icon}</span> : null}
      <span className="min-w-0 flex-1 self-center">{children}</span>
      {note ? <span className="flex-none self-center text-[13px] font-bold">{note}</span> : null}
      {selected && marker === undefined ? <Check className="mt-0.5 size-5 flex-none text-brand" aria-hidden="true" /> : null}
    </button>
  );
}

/** Pill toggle used for minutes and weekdays: selected is an ink pill with a check. */
export function Pill({ pressed, className, children, ...props }: ComponentProps<'button'> & { pressed: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      className={cn(
        'inline-flex h-11 items-center gap-1.5 rounded-full border border-border-strong bg-card px-4 text-[15px] font-medium transition-colors hover:border-foreground/40',
        'aria-pressed:border-ink aria-pressed:bg-ink aria-pressed:text-ink-foreground',
        'outline-none',
        className,
      )}
      {...props}
    >
      {pressed ? <Check className="size-4" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
