"use client"

import * as React from "react"

import type { ArtDef } from "@/lib/ink/art/types"
import { drawSkeleton, memo } from "@/lib/ink/art-draw"
import { useEnsureInkDefs, useInkSeed } from "@/lib/ink/react"
import { cn } from "@/lib/utils"

export type AsteriskMark = "asterisk" | "star" | "dagger" | "double-dagger"

const MARKS: Record<AsteriskMark, ArtDef> = {
  asterisk: {
    kind: "icon",
    grid: 24,
    parts: [
      ["s", "M12.3 3.6 L11.7 20.4", 1.3],
      ["s", "M4.4 7.9 L19.6 16.3", 1.3],
      ["s", "M19.1 7.5 L5.2 16.6", 1.3],
    ],
    small: [
      ["s", "M12.4 3 L11.6 21", 1.1],
      ["s", "M3.5 7.4 L20.3 16.8", 1.1],
      ["s", "M20 7 L4.4 17", 1.1],
    ],
  },
  star: {
    kind: "icon",
    grid: 24,
    parts: [["s", "M12.2 3.1 L14.8 9.3 L21.3 9.9 L16.4 14.3 L17.9 20.7 L12.1 17.3 L6.3 20.8 L7.7 14.3 L2.8 9.8 L9.4 9.3 L12.5 3.9", 1.15]],
    small: [["s", "M12.2 2.6 L15 9 L21.6 9.7 L16.7 14.2 L18.2 21 L12.1 17.5 L5.9 21.1 L7.4 14.2 L2.4 9.6 L9.2 9 L12.6 3.4", 1.05]],
  },
  dagger: {
    kind: "icon",
    grid: 24,
    parts: [
      ["s", "M12.1 2.9 L11.8 21.3", 1.3],
      ["s", "M7.7 8.3 L16.4 7.8", 1.3],
    ],
    small: [
      ["s", "M12.2 2.4 L11.8 21.8", 1.15],
      ["s", "M6.9 8.4 L17.2 7.9", 1.15],
    ],
  },
  "double-dagger": {
    kind: "icon",
    grid: 24,
    parts: [
      ["s", "M12.1 2.9 L11.8 21.3", 1.3],
      ["s", "M7.7 7.6 L16.4 7.2", 1.3],
      ["s", "M8.1 13.9 L15.9 14.3", 1.3],
    ],
    small: [
      ["s", "M12.2 2.4 L11.8 21.8", 1.15],
      ["s", "M6.9 7.6 L17.2 7.1", 1.15],
      ["s", "M7.4 14.2 L16.8 14.6", 1.15],
    ],
  },
}

const TONES = { red: "text-red", ink: "text-ink", blue: "text-ink-you", pencil: "text-pencil-text" } as const

function Asterisk({
  mark = "asterisk",
  tone = "red",
  label,
  href,
  seed,
  className,
  children,
  ...props
}: Omit<React.ComponentProps<"span">, "ref"> & {
  mark?: AsteriskMark
  tone?: keyof typeof TONES
  label?: string
  href?: string
  seed?: string | number
}) {
  useEnsureInkDefs()
  const s = useInkSeed(seed)
  const def = MARKS[mark] ?? MARKS.asterisk
  const res = memo(`asterisk|${mark}|${s}`, () => drawSkeleton(def, 16, `${s}|${mark}`, { tone: "ui", kind: "icon" }))
  const glyph = (
    <svg
      data-ink="icon"
      aria-hidden="true"
      focusable="false"
      viewBox={`0 0 ${res.w} ${res.h}`}
      className={cn("pointer-events-none inline-block size-[0.8em] shrink-0 overflow-visible align-[0.4em]", TONES[tone])}
      dangerouslySetInnerHTML={{ __html: res.svg }}
    />
  )
  if (href) {
    return (
      <span data-slot="asterisk" data-mark={mark} className={cn("inline", className)} {...props}>
        {children}
        <a href={href} aria-label={label ?? "footnote"} className="relative after:absolute after:-inset-1.5 [&>svg]:transition-transform [&>svg]:duration-(--ll-dur-hover) hover:[&>svg]:scale-125">
          {glyph}
        </a>
      </span>
    )
  }
  const named = label ? ({ role: "img", "aria-label": label } as const) : ({ "aria-hidden": true } as const)
  return (
    <span data-slot="asterisk" data-mark={mark} className={cn("inline", className)} {...props}>
      {children}
      <span {...named}>{glyph}</span>
    </span>
  )
}

export { Asterisk }
