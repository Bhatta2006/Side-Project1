"use client"

import * as React from "react"
import { ScrollArea as ScrollAreaPrimitive } from "radix-ui"

import { useInk, useMergedRef } from "@/lib/ink/react"
import { scrollThumbRecipe, scrollTrackRecipe } from "@/lib/ink/recipes/scroll-area-ink"
import { cn } from "@/lib/utils"

function ScrollArea({
  className,
  children,
  bleed = false,
  orientation = "vertical",
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.Root> & {
  bleed?: boolean
  orientation?: "vertical" | "horizontal" | "both"
}) {
  return (
    <ScrollAreaPrimitive.Root data-slot="scroll-area" className={cn("relative", className)} {...props}>
      <ScrollAreaPrimitive.Viewport
        data-slot="scroll-area-viewport"
        className={cn(
          "size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-(--ll-focus)",
          orientation === "vertical" && "[&>div]:block!",
          bleed && "p-3"
        )}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      {orientation !== "horizontal" ? <ScrollBar /> : null}
      {orientation !== "vertical" ? <ScrollBar orientation="horizontal" /> : null}
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

function ScrollBar({
  className,
  orientation = "vertical",
  seed,
  ref,
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar> & {
  seed?: string | number
}) {
  const track = useInk({ recipe: scrollTrackRecipe, params: { orientation }, kind: "track", seed: seed === undefined ? undefined : `${seed}|track`, still: true })
  const thumb = useInk({ recipe: scrollThumbRecipe, params: { orientation }, kind: "thumb", seed: seed === undefined ? undefined : `${seed}|thumb`, still: true })
  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot="scroll-area-scrollbar"
      orientation={orientation}
      ref={useMergedRef<HTMLDivElement>(track.hostRef, ref)}
      {...(track.node ? track.hostProps : {})}
      className={cn(
        "isolate flex touch-none p-px transition-colors select-none forced-colors:outline-0! data-[state=hidden]:animate-out data-[state=hidden]:fade-out-0 data-[state=visible]:animate-in data-[state=visible]:fade-in-0",
        orientation === "vertical" && "h-full w-2.5 border-l border-l-transparent",
        orientation === "horizontal" && "h-2.5 flex-col border-t border-t-transparent",
        className
      )}
      {...props}
    >
      {track.node}
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot="scroll-area-thumb"
        ref={thumb.hostRef}
        {...(thumb.node ? thumb.hostProps : {})}
        className="relative isolate flex-1 forced-colors:bg-[CanvasText] forced-colors:outline-0!"
      >
        {thumb.node}
      </ScrollAreaPrimitive.ScrollAreaThumb>
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  )
}

export { ScrollArea, ScrollBar }
