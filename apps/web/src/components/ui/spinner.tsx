"use client"

import * as React from "react"

import { mascotProps } from "@/lib/ink/art/mascots"
import { drawMascot } from "@/lib/ink/art/mascot-draw"
import { memo } from "@/lib/ink/art-draw"
import { useDensity, useEnsureInkDefs, useInkSeed, useInkTier } from "@/lib/ink/react"
import { spinnerMark, type SpinnerVariant } from "@/lib/ink/recipes/spinner-ink"
import { cn } from "@/lib/utils"

function sizeFromClass(className?: string): number | undefined {
  if (!className) return undefined
  const m = /(?:^|\s)size-(?:(\d+(?:\.\d+)?)|\[(\d+(?:\.\d+)?)px\])(?=\s|$)/.exec(className)
  if (!m) return undefined
  return m[2] ? Number(m[2]) : Number(m[1]) * 4
}

const scribble =
  "[&_[data-part=reveal]]:[stroke-dasharray:.42_.58] [&_[data-part=reveal]]:animate-[ll-draw_calc(var(--ll-dur-draw)*2)_linear_infinite] " +
  "motion-reduce:[&_[data-part=reveal]]:animate-none motion-reduce:[&_[data-part=reveal]]:[stroke-dasharray:none] " +
  "[[data-motion=reduced]_&]:[&_[data-part=reveal]]:animate-none [[data-motion=reduced]_&]:[&_[data-part=reveal]]:[stroke-dasharray:none]"

const FLIP =
  "@keyframes ll-write-1{0%,33.2%{opacity:1}33.3%,100%{opacity:0}}" +
  "@keyframes ll-write-2{0%,33.2%{opacity:0}33.3%,66.5%{opacity:1}66.6%,100%{opacity:0}}" +
  "@keyframes ll-write-3{0%,66.5%{opacity:0}66.6%,100%{opacity:1}}" +
  "[data-slot=spinner][data-variant=write] [data-frame]{opacity:0}[data-slot=spinner][data-variant=write] [data-frame='3']{opacity:1}" +
  "[data-slot=spinner][data-variant=write] [data-frame='1']{animation:ll-write-1 var(--ll-write-lap) linear infinite}" +
  "[data-slot=spinner][data-variant=write] [data-frame='2']{animation:ll-write-2 var(--ll-write-lap) linear infinite}" +
  "[data-slot=spinner][data-variant=write] [data-frame='3']{animation:ll-write-3 var(--ll-write-lap) linear infinite}" +
  "@media (prefers-reduced-motion:reduce){[data-slot=spinner][data-variant=write] [data-frame]{animation:none!important}}" +
  "[data-motion=reduced] [data-slot=spinner][data-variant=write] [data-frame]{animation:none!important}" +
  "[data-motion=reduced] [data-slot=spinner][data-variant=write] [data-frame='1'],[data-motion=reduced] [data-slot=spinner][data-variant=write] [data-frame='2']{opacity:0}"

const WRITE_FRAMES = ["write-1", "write-2", "write-3"] as const

function StubbyFrames({ px, seed }: { px: number; seed: string }) {
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, "")
  const frames = React.useMemo(
    () =>
      WRITE_FRAMES.map((id) => memo(`spinner|${id}|${px}|${seed}|${uid}`, () => drawMascot(mascotProps.frames[id], px, seed, { idPrefix: `ll-${uid}${id.replace("-", "")}` }))),
    [px, seed, uid]
  )
  const { w, h } = frames[0]
  return (
    <span className="relative block" style={{ width: w, height: h }}>
      {frames.map((f, i) => (
        <svg
          key={WRITE_FRAMES[i]}
          data-ink="mascot"
          data-frame={i + 1}
          aria-hidden="true"
          focusable="false"
          viewBox={`0 0 ${f.w} ${f.h}`}
          width={f.w}
          height={f.h}
          className="ll-drop-sticker pointer-events-none absolute inset-0 overflow-visible"
          dangerouslySetInnerHTML={{ __html: f.svg }}
        />
      ))}
    </span>
  )
}

function Spinner({
  className,
  variant = "scribble",
  size,
  seed,
  children,
  style,
  ...props
}: Omit<React.ComponentProps<"span">, "children"> & {
  variant?: SpinnerVariant
  size?: number
  seed?: string | number
  children?: never
}) {
  useEnsureInkDefs()
  const tier = useInkTier()
  const calm = useDensity() === "calm"
  const id = useInkSeed(seed)
  const asked = size ?? sizeFromClass(className)
  const px = Math.max(8, Math.round(asked !== undefined && Number.isFinite(asked) ? asked : variant === "write" ? 64 : 16))
  const mark = React.useMemo(
    () =>
      variant === "write"
        ? null
        : variant === "loops"
          ? spinnerMark(id, px, { shape: "loops", w: px * 4, h: px, tier, calm })
          : spinnerMark(id, px, { tier, calm }),
    [id, px, variant, tier, calm]
  )
  return (
    <span
      role="status"
      aria-label="Loading"
      data-slot="spinner"
      data-variant={variant}
      style={{ "--ll-write-lap": "calc(var(--ll-dur-boil) * 2.25)", ...style } as React.CSSProperties}
      className={cn(
        variant === "scribble" ? "inline-flex size-4 shrink-0 items-center justify-center" : "inline-flex shrink-0 items-center justify-center",
        scribble,
        className
      )}
      {...props}
    >
      {variant === "write" ? (
        <>
          <style href="ll-spinner" precedence="low">
            {FLIP}
          </style>
          <StubbyFrames px={px} seed={id} />
        </>
      ) : mark ? (
        <svg
          data-ink="doodle"
          aria-hidden="true"
          focusable="false"
          viewBox={`${-mark.pad} ${-mark.pad} ${mark.w + 2 * mark.pad} ${mark.h + 2 * mark.pad}`}
          width={variant === "loops" ? mark.w + 2 * mark.pad : undefined}
          height={variant === "loops" ? mark.h + 2 * mark.pad : undefined}
          className={cn("pointer-events-none overflow-visible", variant === "scribble" ? "size-full" : "shrink-0")}
          dangerouslySetInnerHTML={{ __html: mark.svg }}
        />
      ) : null}
    </span>
  )
}

export { Spinner }
