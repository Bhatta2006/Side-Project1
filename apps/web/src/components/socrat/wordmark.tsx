import { cn } from '@/lib/utils';

/**
 * The mark: Soc as a pebble, a dark stone with two white eyes and a little sheen. Drawn as plain SVG
 * (not the ink engine) so it stays crisp down to 16 px and keeps its stone colour in any theme.
 */
export function Mark({ size = 24, className }: { size?: number; className?: string }) {
  const px = Math.max(16, size);
  return (
    <svg viewBox="0 0 24 24" width={px} height={px} aria-hidden="true" focusable="false" className={cn('mark flex-none -rotate-6', className)}>
      <path d="M12 3.6C17.6 3.4 21.6 7.4 21.4 12.8C21.2 18 17.2 21.2 11.8 21C6.6 20.8 2.6 17.6 2.7 12.6C2.8 7.4 6.6 3.8 12 3.6Z" fill="#26211d" />
      <path d="M5.8 9.4Q7 6.6 10 5.8" fill="none" stroke="#fff" strokeOpacity="0.35" strokeWidth="1.3" strokeLinecap="round" />
      <ellipse cx="9.7" cy="12.2" rx="1.45" ry="2" fill="#fff" />
      <ellipse cx="14.5" cy="12.2" rx="1.45" ry="2" fill="#fff" />
    </svg>
  );
}

/** Wordmark: "Socrat®" in the display face with the pebble after it. Compact shows the pebble alone. */
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
      <Mark size={size * 0.9} className="transition-transform duration-500 ease-[var(--ease-soft)] [a:hover_&]:rotate-6" />
    </span>
  );
}
