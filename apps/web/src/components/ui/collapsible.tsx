"use client"

import * as React from "react"
import { Collapsible as CollapsiblePrimitive } from "radix-ui"

import { Icon } from "@/components/ui/icon"
import { useInk } from "@/lib/ink/react"
import { MARGIN_BRACKET_DRAW, marginBracketRecipe, type MarginBracketParams } from "@/lib/ink/recipes/margin-bracket-ink"
import { markTouched } from "@/lib/ink/recipes/draw-on-ink"
import { cn } from "@/lib/utils"

const FOLD = `@keyframes ll-collapsible-down { from { height: 0; clip-path: inset(0); } to { height: var(--radix-collapsible-content-height); clip-path: inset(0); } }
@keyframes ll-collapsible-up { from { height: var(--radix-collapsible-content-height); clip-path: inset(0); } to { height: 0; clip-path: inset(0); } }`

function Collapsible({ className, onClickCapture, ...props }: React.ComponentProps<typeof CollapsiblePrimitive.Root>) {
  return (
    <>
      <style href="ll-collapsible" precedence="low">
        {FOLD}
      </style>
      <CollapsiblePrimitive.Root
        data-slot="collapsible"
        className={cn("group/collapsible", className)}
        onClickCapture={(e) => {
          markTouched(e)
          onClickCapture?.(e)
        }}
        {...props}
      />
    </>
  )
}

function CollapsibleTrigger({ className, ...props }: React.ComponentProps<typeof CollapsiblePrimitive.CollapsibleTrigger>) {
  return <CollapsiblePrimitive.CollapsibleTrigger data-slot="collapsible-trigger" className={cn("group/collapsible-trigger", className)} {...props} />
}

function Bracket({ kind }: { kind: MarginBracketParams["kind"] }) {
  const { hostRef, hostProps, node } = useInk({ recipe: marginBracketRecipe, params: { kind }, kind: "bracket", still: true })
  return (
    <span
      data-slot="collapsible-bracket"
      aria-hidden="true"
      ref={hostRef}
      {...(node ? hostProps : {})}
      className={cn("pointer-events-none absolute inset-y-0 start-0 block w-3.5 forced-colors:hidden", MARGIN_BRACKET_DRAW)}
    >
      {node}
    </span>
  )
}

function CollapsibleContent({
  className,
  children,
  bracket = false,
  ...props
}: React.ComponentProps<typeof CollapsiblePrimitive.CollapsibleContent> & {
  bracket?: MarginBracketParams["kind"] | false
}) {
  return (
    <CollapsiblePrimitive.CollapsibleContent
      data-slot="collapsible-content"
      className={cn(
        "group/collapsible-content data-[state=closed]:animate-[ll-collapsible-up_var(--ll-dur-sheet)_var(--ll-ease-out)] data-[state=open]:animate-[ll-collapsible-down_var(--ll-dur-sheet)_var(--ll-ease-out)]",
        className
      )}
      {...props}
    >
      {bracket ? (
        <div className="relative ps-5 group-data-[state=open]/collapsible-content:animate-soak">
          <Bracket kind={bracket} />
          {children}
        </div>
      ) : (
        children
      )}
    </CollapsiblePrimitive.CollapsibleContent>
  )
}

function CollapsibleIndicator({ className, ...props }: Omit<React.ComponentProps<typeof Icon>, "name">) {
  return (
    <Icon
      data-slot="collapsible-indicator"
      name="chevron-down"
      size={16}
      className={cn("transition-transform duration-(--ll-dur-sheet) ease-settle group-data-[state=open]/collapsible-trigger:rotate-180", className)}
      {...props}
    />
  )
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent, CollapsibleIndicator }
