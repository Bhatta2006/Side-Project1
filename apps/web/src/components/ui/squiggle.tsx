"use client"

import * as React from "react"

import { MARK_REVEAL, useMarkPhase } from "@/hooks/use-mark-ink"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { squiggleRecipe, type SquiggleKind } from "@/lib/ink/recipes/squiggle-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

function Squiggle({
  kind = "wavy",
  orientation = "horizontal",
  decorative = true,
  tone = "ink",
  weight = "regular",
  animate = false,
  show = true,
  delay,
  seed,
  className,
  style,
  ref,
  ...props
}: Omit<React.ComponentProps<"div">, "children"> & {
  kind?: SquiggleKind
  orientation?: "horizontal" | "vertical"
  decorative?: boolean
  tone?: MarkPen
  weight?: MarkWeight
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
}) {
  const { hostRef, hostProps, node } = useInk({ recipe: squiggleRecipe, params: { kind, orientation, tone, weight, animate }, kind: "squiggle", seed })
  const { phaseRef, phaseProps } = useMarkPhase({ animate, show })
  const ready = !!node && show
  return (
    <div
      data-slot="squiggle"
      data-kind={kind}
      data-orientation={orientation}
      role={decorative ? "none" : "separator"}
      aria-orientation={decorative ? undefined : orientation}
      ref={useMergedRef<HTMLElement>(hostRef, phaseRef, ref as React.Ref<HTMLElement> | undefined)}
      {...(ready ? hostProps : {})}
      {...phaseProps}
      style={{ ...(animate ? ({ "--ll-draw-delay": `${delay ?? 0}ms` } as React.CSSProperties) : undefined), ...style }}
      className={cn("relative isolate shrink-0 outline-none", orientation === "horizontal" ? "h-4 w-full" : "h-full min-h-8 w-4", animate && MARK_REVEAL, className)}
      {...props}
    >
      {ready ? node : null}
    </div>
  )
}

export { Squiggle }
