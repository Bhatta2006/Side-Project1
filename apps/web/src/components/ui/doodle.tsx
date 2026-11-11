"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { useEnsureInkDefs } from "@/lib/ink/react"
import { doodles, type DoodleName } from "@/lib/ink/art/doodles"
import { drawSkeleton, memo } from "@/lib/ink/art-draw"
import type { ArtAccent, ArtDef } from "@/lib/ink/art/types"

function Doodle({
  name,
  size = 96,
  accent,
  seed,
  label,
  rotate,
  flip,
  className,
  style,
  ...props
}: Omit<React.ComponentProps<"svg">, "name" | "children" | "viewBox"> & {
  name: DoodleName | (string & {})
  size?: number
  accent?: ArtAccent
  seed?: string | number
  label?: string
  rotate?: number
  flip?: boolean
}) {
  useEnsureInkDefs()
  const def = (doodles as Record<string, ArtDef>)[name]
  if (!def) return null
  const px = Math.max(24, Math.round(size))
  const res = memo(`doodle|${name}|${px}|${accent ?? ""}|${seed ?? ""}`, () => drawSkeleton(def, px, seed ?? name, { tone: "doodle", accent, kind: "doodle" }))
  return (
    <svg
      data-slot="doodle"
      data-ink="doodle"
      data-doodle={name}
      aria-hidden={label ? undefined : true}
      role={label ? "img" : undefined}
      aria-label={label}
      focusable="false"
      viewBox={`0 0 ${res.w} ${res.h}`}
      width={px}
      height={px}
      style={rotate ? { rotate: `${rotate}deg`, ...style } : style}
      className={cn("pointer-events-none shrink-0 overflow-visible", flip && "-scale-x-100", className)}
      dangerouslySetInnerHTML={{ __html: res.svg }}
      {...props}
    />
  )
}

export { Doodle }
export type { DoodleName }
