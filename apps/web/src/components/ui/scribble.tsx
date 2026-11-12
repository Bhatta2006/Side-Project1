"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { MARK_WIPE, useMarkInk } from "@/hooks/use-mark-ink"
import { useMergedRef } from "@/lib/ink/react"
import { scribbleRecipe } from "@/lib/ink/recipes/scribble-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

function Scribble({
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
  tone?: MarkPen
  weight?: MarkWeight
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
  asChild?: boolean
}) {
  const { hostRef, hostProps, nodes } = useMarkInk({
    recipe: scribbleRecipe,
    params: { tone, weight },
    kind: "scribble",
    seed,
    over: true,
    animate,
    show,
    delay,
  })
  const Comp = asChild ? Slot.Root : "span"
  return (
    <Comp
      data-slot="scribble"
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn(
        "relative isolate line-through decoration-2 decoration-ink data-[ink-ready]:no-underline data-[mark=off]:no-underline forced-colors:not-data-[mark=off]:line-through! not-focus-visible:outline-none forced-colors:not-focus-visible:outline-none!",
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

export { Scribble }
