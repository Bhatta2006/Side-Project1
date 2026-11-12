"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { MARK_WIPE, useMarkInk } from "@/hooks/use-mark-ink"
import { useMergedRef } from "@/lib/ink/react"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { underlineRecipe, type UnderlineKind } from "@/lib/ink/recipes/underline-ink"
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

function Underline({
  kind = "single",
  tone = "ink",
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
}: React.ComponentProps<"span"> & {
  kind?: UnderlineKind
  tone?: MarkPen
  weight?: MarkWeight
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
  asChild?: boolean
}) {
  const { hostRef, hostProps, nodes } = useMarkInk({
    recipe: underlineRecipe,
    params: { kind, tone, weight },
    kind: "underline",
    seed,
    animate,
    show,
    delay,
  })
  const Comp = asChild ? Slot.Root : "span"
  return (
    <Comp
      data-slot="underline"
      data-kind={kind}
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn(
        "relative isolate underline decoration-1 underline-offset-[0.2em] data-[ink-ready]:no-underline data-[mark=off]:no-underline forced-colors:not-data-[mark=off]:underline! not-focus-visible:outline-none forced-colors:not-focus-visible:outline-none!",
        FALLBACK[tone],
        animate && "no-underline noscript:underline",
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

export { Underline }
