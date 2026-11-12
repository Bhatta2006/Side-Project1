"use client"

import * as React from "react"

import { Paper, type PaperProps } from "@/components/ui/paper"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { cardRuleRecipe, type CardRuleStyle } from "@/lib/ink/recipes/card-ink"
import { cn } from "@/lib/utils"

/** Socrat card tones from before Looseleaf, each mapped onto a paper stock. */
type CardTone = "surface" | "hero" | "violet" | "lilac" | "cream" | "raised" | "outlined"
const TONE_STOCK: Record<CardTone, NonNullable<PaperProps["stock"]>> = {
  surface: "card",
  hero: "sticky-yellow",
  violet: "sticky-blue",
  lilac: "sticky-blue",
  cream: "sticky-yellow",
  raised: "slip",
  outlined: "paper",
}

type CardProps = Omit<PaperProps, "size"> & {
  tone?: CardTone | null
  /** "sm" tightens the padding; a pair is the sheet size Paper draws an edge at. */
  size?: PaperProps["size"] | "default" | "sm"
}

function Card({ className, stock, rules = "none", tone, size, ...props }: CardProps) {
  const compact = size === "sm"
  const paperSize = Array.isArray(size) ? (size as PaperProps["size"]) : undefined
  return (
    <Paper
      data-slot="card"
      data-tone={tone ?? "surface"}
      data-size={compact ? "sm" : "default"}
      stock={stock ?? TONE_STOCK[tone ?? "surface"]}
      rules={rules}
      size={paperSize}
      className={cn("group/card flex flex-col text-card-foreground", compact ? "gap-4 py-4 [--card-spacing:16px] [&>[data-slot^=card-]]:px-4" : "gap-6 py-6 [--card-spacing:24px] lg:[--card-spacing:28px]", className)}
      {...props}
    />
  )
}

type RuleProps = {
  rule?: CardRuleStyle
}

const hasClass = (className: string | undefined, name: string) => !!className && className.split(/\s+/).includes(name)

function useDivider(edge: "top" | "bottom", drawn: boolean, rule: CardRuleStyle, ref: React.Ref<HTMLElement> | undefined) {
  const { hostRef, hostProps, node } = useInk({ recipe: cardRuleRecipe, params: { edge, style: rule }, kind: "rule" })
  const merged = useMergedRef<HTMLElement>(drawn ? hostRef : undefined, ref)
  return { ref: merged, hostProps: drawn && node ? hostProps : {}, node: drawn ? node : null }
}

function CardHeader({ className, rule = "pencil", ref, children, ...props }: React.ComponentProps<"div"> & RuleProps) {
  const d = useDivider("bottom", hasClass(className, "border-b"), rule, ref as React.Ref<HTMLElement> | undefined)
  return (
    <div
      data-slot="card-header"
      ref={d.ref as React.Ref<HTMLDivElement>}
      {...d.hostProps}
      className={cn(
        "@container/card-header relative isolate grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:border-transparent [.border-b]:pb-6",
        className
      )}
      {...props}
    >
      {d.node}
      {children}
    </div>
  )
}

function CardTitle({ className, as: Tag = "div", ...props }: React.ComponentProps<"div"> & { as?: "h2" | "h3" | "div" }) {
  return <Tag data-slot="card-title" className={cn("font-script text-[1.7rem] leading-none font-semibold", className)} {...props} />
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-description" className={cn("text-sm text-muted-foreground", className)} {...props} />
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-action" className={cn("col-start-2 row-span-2 row-start-1 self-start justify-self-end", className)} {...props} />
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn("px-6", className)} {...props} />
}

function CardFooter({ className, rule = "pencil", ref, children, ...props }: React.ComponentProps<"div"> & RuleProps) {
  const d = useDivider("top", hasClass(className, "border-t"), rule, ref as React.Ref<HTMLElement> | undefined)
  return (
    <div
      data-slot="card-footer"
      ref={d.ref as React.Ref<HTMLDivElement>}
      {...d.hostProps}
      className={cn("relative isolate flex items-center px-6 [.border-t]:border-transparent [.border-t]:pt-6", className)}
      {...props}
    >
      {d.node}
      {children}
    </div>
  )
}

export { Card, CardHeader, CardFooter, CardTitle, CardAction, CardDescription, CardContent }
export type { CardProps, CardTone }
