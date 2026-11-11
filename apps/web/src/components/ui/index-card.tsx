"use client"

import * as React from "react"

import { Paper, type PaperProps } from "@/components/ui/paper"
import { usePaperDecor } from "@/hooks/use-paper-object"
import type { Accent } from "@/lib/ink/paper/props"
import { indexCardRecipe } from "@/lib/ink/recipes/index-card-ink"
import { cn } from "@/lib/utils"

type IndexCardProps = Omit<PaperProps, "stock" | "rules"> & {
  hole?: boolean
  flag?: Accent | false
  stack?: 0 | 1 | 2 | 3
}

function IndexCard({ className, children, ref, hole = false, flag = false, stack = 0, as = "div", seed, tilt, size, style, ...props }: IndexCardProps) {
  const o = usePaperDecor({
    recipe: indexCardRecipe,
    params: { hole, flag: flag || "none", stack },
    kind: "index-card",
    ref,
    seed,
    tilt,
    tiltMax: 0.5 * 0.45,
    size,
    enabled: hole || !!flag || stack > 0,
  })
  return (
    <Paper
      data-slot="index-card"
      as={as}
      stock="index-card"
      rules="index"
      size={size}
      {...o.paper}
      {...props}
      className={cn(o.paper.className, "flex min-h-56 w-full max-w-md flex-col px-5 pb-[25px] text-[17px] leading-[30px] rtl:[&>[data-slot=paper-rules]]:-scale-x-100", className)}
      style={{ ...o.paper.style, ...style }}
    >
      {o.decor}
      {children}
    </Paper>
  )
}

function IndexCardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="index-card-header" className={cn("flex h-[49px] shrink-0 items-end justify-between gap-3 pb-1.5", className)} {...props} />
}

function IndexCardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="index-card-title" className={cn("min-w-0 truncate pe-[0.2em] -me-[0.2em] pb-[0.2em] -mb-[0.2em] font-script text-[1.65rem] leading-none font-bold", className)} {...props} />
}

function IndexCardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="index-card-content" className={cn("flex-1", className)} {...props} />
}

function IndexCardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="index-card-footer" className={cn("mt-auto flex items-center justify-between gap-3 text-sm leading-[30px] text-muted-foreground", className)} {...props} />
}

export { IndexCard, IndexCardHeader, IndexCardTitle, IndexCardContent, IndexCardFooter }
export type { IndexCardProps }
