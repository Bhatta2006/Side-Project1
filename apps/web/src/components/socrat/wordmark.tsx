import { cn } from '@/lib/utils';

/** The mark: an eight-spoke asterisk in royal blue, as on the waitlist page. Minimum 16 px. */
export function Mark({ size = 24, className }: { size?: number; className?: string }) {
  const px = Math.max(16, size);
  return (
    <svg viewBox="0 0 24 24" width={px} height={px} aria-hidden="true" focusable="false" className={cn('mark flex-none text-primary', className)}>
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
        <path d="M12 2.5v19M2.5 12h19M5.3 5.3l13.4 13.4M18.7 5.3 5.3 18.7" />
      </g>
    </svg>
  );
}

/** Wordmark: "Socrat®" in the display face with the asterisk after it. Compact shows the asterisk alone. */
export function Wordmark({ className, compact = false, size = 26 }: { className?: string; compact?: boolean; size?: number }) {
  if (compact) {
    return (
      <span className={cn('inline-flex items-center', className)}>
        <Mark size={size} />
        <span className="sr-only">Socrat</span>
      </span>
    );
  }
  return (
    <span className={cn('inline-flex items-center gap-2', className)} style={{ fontSize: size }}>
      <span className="font-display leading-none font-medium tracking-[-0.045em]">Socrat<sup className="ml-px align-super text-[0.42em] font-normal tracking-normal">®</sup></span>
      <Mark size={size * 0.9} className="transition-transform duration-500 ease-[var(--ease-soft)] [a:hover_&]:rotate-45" />
    </span>
  );
}
