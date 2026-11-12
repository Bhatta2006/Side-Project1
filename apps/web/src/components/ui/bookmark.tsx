"use client"

import * as React from "react"
import { Toggle as TogglePrimitive } from "radix-ui"

import { useShapedSheet } from "@/hooks/use-paper-object"
import type { Accent } from "@/lib/ink/paper/props"
import { bookmarkRecipe } from "@/lib/ink/recipes/bookmark-ink"
import { cn } from "@/lib/utils"

const RIBBON_TILT = "[&>svg]:[rotate:clamp(calc(var(--ll-tilt-max)*-1),var(--ll-tilt,0deg),var(--ll-tilt-max))]"
const RIBBON_SHADOW = "data-[state=on]:[&>svg]:[filter:var(--ll-drop-sticker)]"

const FORCED_ON = "forced-colors:data-[state=on]:bg-[Highlight]"

type BookmarkProps = React.ComponentProps<typeof TogglePrimitive.Root> & {
  tone?: Accent
  tilt?: boolean | number
  seed?: string | number
  size?: readonly [number, number]
}

function Bookmark({ className, style, children, ref, tone = "tomato", tilt, seed, size, disabled, ...props }: BookmarkProps) {
  const o = useShapedSheet({ recipe: bookmarkRecipe, params: { tone, mode: "toggle", disabled: !!disabled }, ref: ref as React.Ref<HTMLElement>, seed, tilt, tiltMax: 1.4, size, kind: "bookmark" })
  return (
    <TogglePrimitive.Root
      data-slot="bookmark"
      disabled={disabled}
      {...o.root}
      {...props}
      className={cn("relative isolate inline-block h-12 w-8 shrink-0 cursor-pointer align-top after:absolute after:-inset-1.5 disabled:cursor-not-allowed", RIBBON_TILT, RIBBON_SHADOW, FORCED_ON, className)}
      style={{ ...o.root.style, ...style }}
    >
      {o.node}
      <span className="sr-only">{children ?? "Bookmark"}</span>
    </TogglePrimitive.Root>
  )
}

type BookmarkRibbonProps = React.ComponentProps<"div"> & {
  tone?: Accent
  tilt?: boolean | number
  seed?: string | number
  size?: readonly [number, number]
}

function BookmarkRibbon({ className, style, ref, tone = "tomato", tilt, seed, size, ...props }: BookmarkRibbonProps) {
  const o = useShapedSheet({ recipe: bookmarkRecipe, params: { tone, mode: "static", disabled: false }, ref: ref as React.Ref<HTMLElement>, seed, tilt, tiltMax: 1.4, size, kind: "bookmark" })
  return (
    <div
      data-slot="bookmark-ribbon"
      aria-hidden="true"
      {...o.root}
      {...props}
      className={cn("pointer-events-none relative isolate inline-block h-14 w-8 shrink-0 [&>svg]:[filter:var(--ll-drop-sticker)]", RIBBON_TILT, className)}
      style={{ ...o.root.style, ...style }}
    >
      {o.node}
    </div>
  )
}

export { Bookmark, BookmarkRibbon }
export type { BookmarkProps, BookmarkRibbonProps }
