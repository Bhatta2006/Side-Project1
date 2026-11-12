"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { MARK_REVEAL, useMarkInk } from "@/hooks/use-mark-ink"
import { useMergedRef } from "@/lib/ink/react"
import { circledRecipe, type CircledShape } from "@/lib/ink/recipes/circled-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

function Circled({
  shape = "circle",
  tone = "ink",
  weight = "regular",
  bleed,
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
  shape?: CircledShape
  tone?: MarkPen
  weight?: MarkWeight
  bleed?: number
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
  asChild?: boolean
}) {
  const { hostRef, hostProps, nodes } = useMarkInk({
    recipe: circledRecipe,
    params: { shape, tone, weight, bleed },
    kind: "circled",
    seed,
    mode: "box",
    over: true,
    animate,
    show,
    delay,
  })
  const Comp = asChild ? Slot.Root : "span"
  return (
    <Comp
      data-slot="circled"
      data-shape={shape}
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn(
        "relative isolate outline-1 outline-offset-2 outline-pencil-mark data-[ink-ready]:not-focus-visible:outline-none data-[mark=off]:outline-none",
        animate && "outline-none noscript:outline-1",
        animate && MARK_REVEAL,
        className,
      )}
      {...props}
    >
      <Slot.Slottable>{children}</Slot.Slottable>
      {nodes}
    </Comp>
  )
}

export { Circled }
