"use client"

import * as React from "react"

import { Arrow } from "@/components/ui/arrow"
import { Handwritten } from "@/components/ui/handwritten"
import { useMarkPhase } from "@/hooks/use-mark-ink"
import { useMergedRef } from "@/lib/ink/react"
import type { ArrowCurve, ArrowDirection, ArrowHead } from "@/lib/ink/recipes/arrow-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

const LAYOUT: Record<ArrowDirection, string> = {
  right: "flex-row items-center",
  left: "flex-row-reverse items-center",
  down: "flex-col items-center",
  up: "flex-col-reverse items-center",
  "down-right": "flex-row items-start",
  "down-left": "flex-row-reverse items-start",
  "up-right": "flex-row items-end",
  "up-left": "flex-row-reverse items-end",
}

function Callout({
  direction = "left",
  curve = "curved",
  head = "v",
  tone = "blue",
  weight = "regular",
  bend = "up",
  arrow = true,
  arrowClassName,
  animate = false,
  show = true,
  delay,
  seed,
  className,
  children,
  ref,
  ...props
}: React.ComponentProps<"span"> & {
  direction?: ArrowDirection
  curve?: ArrowCurve
  head?: ArrowHead
  tone?: MarkPen
  weight?: MarkWeight
  bend?: "up" | "down"
  arrow?: boolean
  arrowClassName?: string
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
}) {
  const { phaseRef, phaseProps } = useMarkPhase({ animate, show })
  const arrowEl = arrow ? (
    <Arrow
      aria-hidden
      direction={direction}
      curve={curve}
      head={head}
      tone={tone}
      weight={weight}
      bend={bend}
      animate={animate}
      show={show}
      delay={(delay ?? 0) + 250}
      seed={seed === undefined ? undefined : `${seed}:arrow`}
      className={cn("h-10 w-14", arrowClassName)}
    />
  ) : null
  const vertical = direction === "up" || direction === "down"
  return (
    <span
      data-slot="callout"
      role="note"
      ref={useMergedRef<HTMLElement>(phaseRef, ref as React.Ref<HTMLElement> | undefined)}
      {...phaseProps}
      className={cn(
        "group/callout inline-flex gap-1.5 data-[mark=off]:hidden",
        LAYOUT[direction],
        vertical && "gap-0.5",
        className,
      )}
      {...props}
    >
      <Handwritten
        as="span"
        seed={seed}
        data-slot="callout-text"
        style={animate && delay ? ({ transitionDelay: `${delay}ms` } as React.CSSProperties) : undefined}
        className={cn(
          "max-w-[16ch] font-script text-[22px] leading-[1.05] text-ink-you",
          animate && "transition-opacity duration-(--ll-dur-sheet) ease-out group-data-[mark=idle]/callout:opacity-0",
          vertical && "max-w-[22ch] text-center",
        )}
      >
        {children}
      </Handwritten>
      {arrowEl}
    </span>
  )
}

export { Callout }
