"use client"

import * as React from "react"
import { HoverCard as HoverCardPrimitive } from "radix-ui"

import { Paper, type PaperProps } from "@/components/ui/paper"
import { useInk, useInkScope, useInkSeed, useMergedRef } from "@/lib/ink/react"
import { hoverCardMediaRecipe } from "@/lib/ink/recipes/hover-card-ink"
import { cn } from "@/lib/utils"

function HoverCard({ ...props }: React.ComponentProps<typeof HoverCardPrimitive.Root>) {
  return <HoverCardPrimitive.Root data-slot="hover-card" {...props} />
}

function HoverCardTrigger({ ...props }: React.ComponentProps<typeof HoverCardPrimitive.Trigger>) {
  return <HoverCardPrimitive.Trigger data-slot="hover-card-trigger" {...props} />
}

function HoverCardContent({
  className,
  align = "center",
  sideOffset = 8,
  collisionPadding = 8,
  stock = "photo",
  edge,
  tilt = true,
  tape = false,
  seed: seedProp,
  children,
  ...props
}: React.ComponentProps<typeof HoverCardPrimitive.Content> & Pick<PaperProps, "stock" | "edge" | "tilt" | "tape" | "seed">) {
  const scope = useInkScope()
  const seed = useInkSeed(seedProp)
  return (
    <HoverCardPrimitive.Portal data-slot="hover-card-portal">
      <HoverCardPrimitive.Content asChild align={align} sideOffset={sideOffset} collisionPadding={collisionPadding} {...props}>
        <Paper
          data-slot="hover-card-content"
          stock={stock}
          edge={edge}
          tilt={tilt}
          tape={tape}
          rules="none"
          seed={seed}
          {...scope}
          className={cn(
            "z-(--ll-z-popover) w-64 max-w-[calc(100vw-1rem)] origin-(--radix-hover-card-content-transform-origin) p-2.5 pb-4 text-popover-foreground outline-hidden compact:p-2 calm:p-2",
            "duration-(--ll-dur-pop) data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
            className
          )}
        >
          {children}
        </Paper>
      </HoverCardPrimitive.Content>
    </HoverCardPrimitive.Portal>
  )
}

function HoverCardMedia({ className, seed: seedProp, children, ref, ...props }: React.ComponentProps<"div"> & { seed?: string | number }) {
  const seed = useInkSeed(seedProp)
  const { hostRef, hostProps, node } = useInk({ recipe: hoverCardMediaRecipe, params: {}, kind: "frame", seed })
  return (
    <div
      data-slot="hover-card-media"
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn("relative isolate grid h-28 place-items-center bg-paper-shade/60 p-2 *:[img]:size-full *:[img]:object-cover", className)}
      {...props}
    >
      {node}
      {children}
    </div>
  )
}

function HoverCardCaption({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="hover-card-caption" className={cn("mt-2.5 px-1 font-script text-[1.4rem] leading-tight text-foreground", className)} {...props} />
}

export { HoverCard, HoverCardTrigger, HoverCardContent, HoverCardMedia, HoverCardCaption }
