"use client"

import * as React from "react"

import { MARK_REVEAL, useMarkPhase } from "@/hooks/use-mark-ink"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { quoteRecipe } from "@/lib/ink/recipes/quote-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

const SIZE = { sm: 24, md: 32, lg: 46 } as const
const PADDING = { sm: "ps-10 pe-8 py-1", md: "ps-[3.25rem] pe-10 py-1.5", lg: "ps-[4.75rem] pe-14 py-2" } as const

function Quote({ className, ...props }: React.ComponentProps<"figure">) {
  return <figure data-slot="quote" className={cn("m-0 grid w-fit max-w-full content-start gap-2.5 self-start justify-self-start", className)} {...props} />
}

function QuoteText({
  size = "md",
  tone = "marker",
  weight = "regular",
  rule = false,
  animate = false,
  show = true,
  delay,
  seed,
  className,
  style,
  children,
  ref,
  ...props
}: React.ComponentProps<"blockquote"> & {
  size?: keyof typeof SIZE
  tone?: MarkPen
  weight?: MarkWeight
  rule?: boolean
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
}) {
  const { hostRef, hostProps, node } = useInk({ recipe: quoteRecipe, params: { tone, weight, size: SIZE[size], rule, animate }, kind: "quote", seed })
  const { phaseRef, phaseProps } = useMarkPhase({ animate, show })
  const ready = !!node && show
  return (
    <blockquote
      data-slot="quote-text"
      ref={useMergedRef<HTMLElement>(hostRef, phaseRef, ref as React.Ref<HTMLElement> | undefined)}
      {...(ready ? hostProps : {})}
      {...phaseProps}
      style={{ ...(animate ? ({ "--ll-draw-delay": `${delay ?? 0}ms` } as React.CSSProperties) : undefined), ...style }}
      className={cn(
        "relative isolate m-0 outline-none font-script text-[26px] leading-[1.3] text-foreground",
        PADDING[size],
        !node && show && !animate && "before:absolute before:start-0 before:top-0 before:font-script before:text-5xl before:text-marker before:content-['\\201C']",
        "forced-colors:before:absolute forced-colors:before:start-0 forced-colors:before:top-0 forced-colors:before:font-script forced-colors:before:text-5xl forced-colors:before:content-['\\201C']",
        animate && MARK_REVEAL,
        className,
      )}
      {...props}
    >
      {ready ? node : null}
      {children}
    </blockquote>
  )
}

function QuoteAttribution({ className, ...props }: React.ComponentProps<"figcaption">) {
  return (
    <figcaption
      data-slot="quote-attribution"
      className={cn("ps-[3.25rem] font-hand text-sm text-muted-foreground before:content-['—_']", className)}
      {...props}
    />
  )
}

export { Quote, QuoteText, QuoteAttribution }
