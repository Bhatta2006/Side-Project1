"use client"

import * as React from "react"
import { Popover as PopoverPrimitive } from "radix-ui"

import { Paper, type PaperProps } from "@/components/ui/paper"
import { PropSvg } from "@/lib/ink/paper/prop-svg"
import type { Accent } from "@/lib/ink/paper/props"
import { useDensity, useInkScope, useInkSeed, useInkTier } from "@/lib/ink/react"
import { pointerMark } from "@/lib/ink/recipes/overlay-ink"
import { cn } from "@/lib/utils"

function Popover({ ...props }: React.ComponentProps<typeof PopoverPrimitive.Root>) {
  return <PopoverPrimitive.Root data-slot="popover" {...props} />
}

function PopoverTrigger({ ...props }: React.ComponentProps<typeof PopoverPrimitive.Trigger>) {
  return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />
}

function PopoverAnchor({ ...props }: React.ComponentProps<typeof PopoverPrimitive.Anchor>) {
  return <PopoverPrimitive.Anchor data-slot="popover-anchor" {...props} />
}

function PopoverPointer({ seed }: { seed: string }) {
  const tier = useInkTier()
  const calm = useDensity() === "calm"
  const res = React.useMemo(() => pointerMark(`${seed}|pointer`, { tier, calm }), [seed, tier, calm])
  return (
    <PopoverPrimitive.Arrow asChild>
      <PropSvg
        res={res}
        kind="prop"
        data-slot="popover-arrow"
        width={res.w}
        height={res.h}
        viewBox={`0 0 ${res.w} ${res.h}`}
        preserveAspectRatio="xMidYMid meet"
        className="pointer-events-none"
      />
    </PopoverPrimitive.Arrow>
  )
}

function useOpenerFocus({ onOpenAutoFocus, onCloseAutoFocus, onInteractOutside }: Pick<React.ComponentProps<typeof PopoverPrimitive.Content>, "onOpenAutoFocus" | "onCloseAutoFocus" | "onInteractOutside">) {
  const opener = React.useRef<Element | null>(null)
  const outside = React.useRef(false)
  return {
    onOpenAutoFocus(event: Event) {
      outside.current = false
      const id = event.target instanceof HTMLElement ? event.target.id : ""
      const hasTrigger = !!id && Array.from(document.querySelectorAll("[aria-controls]")).some((el) => el.getAttribute("aria-controls") === id)
      opener.current = hasTrigger ? null : document.activeElement
      onOpenAutoFocus?.(event)
    },
    onInteractOutside(event: Parameters<NonNullable<typeof onInteractOutside>>[0]) {
      outside.current = true
      onInteractOutside?.(event)
    },
    onCloseAutoFocus(event: Event) {
      onCloseAutoFocus?.(event)
      const el = opener.current
      opener.current = null
      if (event.defaultPrevented || !el || outside.current) return
      const active = document.activeElement
      if (active && active !== document.body && active !== el) return
      if (el instanceof HTMLElement && el !== document.body && el.isConnected) el.focus({ preventScroll: true })
    },
  }
}

function PopoverContent({
  className,
  align = "center",
  sideOffset = 8,
  collisionPadding = 8,
  stock = "slip",
  edge,
  tilt = true,
  pin = false,
  tape = false,
  arrow = false,
  seed: seedProp,
  "data-slot": slot = "popover-content",
  children,
  onOpenAutoFocus,
  onCloseAutoFocus,
  onInteractOutside,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Content> &
  Pick<PaperProps, "stock" | "edge" | "tilt" | "tape" | "seed"> & {
    pin?: boolean | Accent
    arrow?: boolean
    "data-slot"?: string
  }) {
  const scope = useInkScope()
  const seed = useInkSeed(seedProp)
  const focus = useOpenerFocus({ onOpenAutoFocus, onCloseAutoFocus, onInteractOutside })
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content asChild align={align} sideOffset={sideOffset} collisionPadding={collisionPadding} {...props} {...focus}>
        <Paper
          data-slot={slot}
          stock={stock}
          edge={edge}
          tilt={tilt}
          tape={tape}
          fastener={pin ? "pin" : false}
          fastenerTone={typeof pin === "string" ? pin : undefined}
          rules="none"
          seed={seed}
          {...scope}
          className={cn(
            "z-(--ll-z-popover) w-72 max-w-[calc(100vw-1rem)] origin-(--radix-popover-content-transform-origin) p-4 text-popover-foreground outline-hidden compact:p-3.5 calm:p-3",
            "data-[side]:[--ll-sheet-shadow:var(--ll-shadow-lift)] data-[side]:calm:[--ll-sheet-shadow:var(--ll-shadow-hair)]",
            "duration-(--ll-dur-pop) data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
            className
          )}
        >
          {children}
          {arrow && <PopoverPointer seed={seed} />}
        </Paper>
      </PopoverPrimitive.Content>
    </PopoverPrimitive.Portal>
  )
}

function PopoverHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="popover-header" className={cn("flex flex-col gap-1 text-sm", className)} {...props} />
}

function PopoverTitle({ className, ...props }: React.ComponentProps<"h2">) {
  return <div data-slot="popover-title" className={cn("font-script text-[1.4rem] leading-none font-semibold", className)} {...props} />
}

function PopoverDescription({ className, ...props }: React.ComponentProps<"p">) {
  return <p data-slot="popover-description" className={cn("text-muted-foreground", className)} {...props} />
}

export { Popover, PopoverTrigger, PopoverContent, PopoverAnchor, PopoverHeader, PopoverTitle, PopoverDescription }
