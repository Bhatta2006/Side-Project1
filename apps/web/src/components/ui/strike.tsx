"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { MARK_WIPE, useMarkInk } from "@/hooks/use-mark-ink"
import { useMergedRef } from "@/lib/ink/react"
import { strikeRecipe, type StrikeKind } from "@/lib/ink/recipes/strike-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

const FALLBACK: Record<MarkPen, string> = {
  ink: "decoration-ink",
  blue: "decoration-ink-you",
  red: "decoration-red",
  green: "decoration-green",
  pencil: "decoration-pencil-mark",
  marker: "decoration-marker",
  orange: "decoration-tangerine",
}

function Strike({
  kind = "single",
  tone = "red",
  weight = "regular",
  animate = false,
  show = true,
  delay,
  seed,
  asChild = false,
  className,
  children,
  ref,
  ...props
}: React.ComponentProps<"s"> & {
  kind?: StrikeKind
  tone?: MarkPen
  weight?: MarkWeight
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
  asChild?: boolean
}) {
  const { hostRef, hostProps, nodes } = useMarkInk({
    recipe: strikeRecipe,
    params: { kind, tone, weight },
    kind: "strike",
    seed,
    mode: kind === "cross" ? "box" : "lines",
    over: true,
    animate,
    show,
    delay,
  })
  const Comp = asChild ? Slot.Root : "s"
  return (
    <Comp
      data-slot="strike"
      data-kind={kind}
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn(
        "relative isolate decoration-1 data-[ink-ready]:no-underline data-[mark=off]:no-underline forced-colors:not-data-[mark=off]:line-through! not-focus-visible:outline-none forced-colors:not-focus-visible:outline-none!",
        FALLBACK[tone],
        animate && "no-underline noscript:line-through",
        animate && MARK_WIPE,
        className,
      )}
      {...props}
    >
      <Slot.Slottable>{children}</Slot.Slottable>
      {nodes}
    </Comp>
  )
}

export { Strike }
