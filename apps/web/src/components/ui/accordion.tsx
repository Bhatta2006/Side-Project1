"use client"

import * as React from "react"
import { Accordion as AccordionPrimitive } from "radix-ui"

import { Icon } from "@/components/ui/icon"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { accordionRuleRecipe, accordionTriggerRecipe } from "@/lib/ink/recipes/accordion-ink"
import { MARGIN_BRACKET_DRAW, marginBracketRecipe, type MarginBracketParams } from "@/lib/ink/recipes/margin-bracket-ink"
import { markTouched } from "@/lib/ink/recipes/draw-on-ink"
import { cn } from "@/lib/utils"

type BracketKind = MarginBracketParams["kind"] | false
const BracketContext = React.createContext<BracketKind>("curly")

const FOLD = `@keyframes ll-accordion-down { from { height: 0; clip-path: inset(0); } to { height: var(--radix-accordion-content-height); clip-path: inset(0); } }
@keyframes ll-accordion-up { from { height: var(--radix-accordion-content-height); clip-path: inset(0); } to { height: 0; clip-path: inset(0); } }`

const SWIPE = "hover:[&>svg_[data-part=swipe]]:animate-[ll-wipe_var(--ll-dur-sheet)_var(--ll-ease-out)_both]"

function Rule() {
  const { hostRef, hostProps, node } = useInk({ recipe: accordionRuleRecipe, params: {}, kind: "rule", still: true })
  return (
    <span
      data-slot="accordion-rule"
      aria-hidden="true"
      ref={hostRef}
      {...(node ? hostProps : {})}
      className="pointer-events-none absolute inset-x-0 bottom-0 block h-2 forced-colors:hidden"
    >
      {node}
    </span>
  )
}

function Bracket({ kind }: { kind: Exclude<BracketKind, false> }) {
  const { hostRef, hostProps, node } = useInk({ recipe: marginBracketRecipe, params: { kind }, kind: "bracket", still: true })
  return (
    <span
      data-slot="accordion-bracket"
      aria-hidden="true"
      ref={hostRef}
      {...(node ? hostProps : {})}
      className={cn("pointer-events-none absolute inset-y-0 start-0 block w-3.5 forced-colors:hidden", MARGIN_BRACKET_DRAW)}
    >
      {node}
    </span>
  )
}

function Accordion({
  bracket = "curly",
  onClickCapture,
  ...props
}: React.ComponentProps<typeof AccordionPrimitive.Root> & {
  bracket?: BracketKind
}) {
  return (
    <BracketContext.Provider value={bracket}>
      <style href="ll-accordion" precedence="low">
        {FOLD}
      </style>
      <AccordionPrimitive.Root
        data-slot="accordion"
        onClickCapture={(e) => {
          markTouched(e)
          onClickCapture?.(e)
        }}
        {...props}
      />
    </BracketContext.Provider>
  )
}

function AccordionItem({ className, children, ...props }: React.ComponentProps<typeof AccordionPrimitive.Item>) {
  return (
    <AccordionPrimitive.Item
      data-slot="accordion-item"
      className={cn("group/accordion-item relative pb-2 last:[&>[data-slot=accordion-rule]]:hidden", className)}
      {...props}
    >
      {children}
      <Rule />
    </AccordionPrimitive.Item>
  )
}

function AccordionTrigger({
  className,
  children,
  seed,
  ref,
  ...props
}: React.ComponentProps<typeof AccordionPrimitive.Trigger> & {
  seed?: string | number
}) {
  const { hostRef, hostProps, node } = useInk({ recipe: accordionTriggerRecipe, params: { disabled: !!props.disabled }, kind: "row", seed, still: true })
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger
        data-slot="accordion-trigger"
        ref={useMergedRef<HTMLButtonElement>(hostRef, ref)}
        {...hostProps}
        className={cn(
          "group/accordion-trigger relative isolate -mx-2 flex flex-1 items-start justify-between gap-4 px-2 py-3.5 text-start font-hand text-base font-bold transition-[color] disabled:pointer-events-none disabled:text-pencil-text compact:py-2.5 calm:py-2 calm:text-[15px]",
          "[&_svg:not(.absolute):not([class*='size-'])]:size-4 [&[data-state=open]>[data-chevron]]:rotate-180",
          SWIPE,
          className
        )}
        {...props}
      >
        {node}
        {children}
        <Icon name="chevron-down" data-chevron="" size={16} className="pointer-events-none mt-1 shrink-0 transition-transform duration-(--ll-dur-sheet) ease-settle" />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  )
}

const OUTER_PADDING = /^(?:[^\s:]+:)*!?-?(?:p|py|pt|pb)-/

function splitContentClass(className?: string) {
  const outer: string[] = []
  const inner: string[] = []
  for (const token of (className ?? "").split(/\s+/)) {
    if (!token) continue
    ;(OUTER_PADDING.test(token) ? outer : inner).push(token)
  }
  return { outer: outer.join(" "), inner: inner.join(" ") }
}

function AccordionContent({ className, children, ...props }: React.ComponentProps<typeof AccordionPrimitive.Content>) {
  const bracket = React.useContext(BracketContext)
  const split = splitContentClass(className)
  return (
    <AccordionPrimitive.Content
      data-slot="accordion-content"
      className="group/accordion-content text-sm data-[state=closed]:animate-[ll-accordion-up_var(--ll-dur-sheet)_var(--ll-ease-out)] data-[state=open]:animate-[ll-accordion-down_var(--ll-dur-sheet)_var(--ll-ease-out)]"
      {...props}
    >
      <div className={cn("pt-0 pb-4", split.outer)}>
        <div className={cn("relative in-data-touched:group-data-[state=open]/accordion-content:animate-soak", bracket && "ps-5", split.inner)}>
          {bracket ? <Bracket kind={bracket} /> : null}
          {children}
        </div>
      </div>
    </AccordionPrimitive.Content>
  )
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
