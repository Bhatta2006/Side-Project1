"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { useEnsureInkDefs } from "@/lib/ink/react"
import { mascot, mascotProps, type MascotPose } from "@/lib/ink/art/mascots"
import { drawMascot } from "@/lib/ink/art/mascot-draw"
import { memo } from "@/lib/ink/art-draw"
import type { ArtDef } from "@/lib/ink/art/types"

const frames = mascotProps.frames as Record<string, ArtDef>

function Mascot({
  pose = "idle",
  size = 96,
  seed,
  label,
  frame,
  tier = "lo",
  shadow = true,
  className,
  style,
  ...props
}: Omit<React.ComponentProps<"svg">, "children" | "viewBox"> & {
  pose?: MascotPose | (string & {})
  size?: number
  seed?: string | number
  label?: string
  frame?: number
  tier?: "lo" | "hi"
  shadow?: boolean
}) {
  useEnsureInkDefs()
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, "")
  const flip = frame === undefined ? undefined : frames[`${pose}-${frame}`]
  const def = flip ?? (mascot as Record<string, ArtDef>)[pose]
  if (!def) return null
  const px = Math.max(16, Math.round(size))
  const res = memo(`mascot|${pose}|${flip ? frame : ""}|${px}|${tier}|${seed ?? ""}|${uid}`, () => drawMascot(def, px, seed ?? pose, { tier, idPrefix: `ll-${uid}` }), 240)
  return (
    <svg
      data-slot="mascot"
      data-ink="mascot"
      data-pose={pose}
      data-frame={flip ? frame : undefined}
      aria-hidden={label ? undefined : true}
      role={label ? "img" : undefined}
      aria-label={label}
      focusable="false"
      viewBox={`0 0 ${res.w} ${res.h}`}
      width={res.w}
      height={res.h}
      style={style}
      className={cn("pointer-events-none shrink-0 overflow-visible", shadow && "ll-drop-sticker", className)}
      dangerouslySetInnerHTML={{ __html: res.svg }}
      {...props}
    />
  )
}

export { Mascot }
export type { MascotPose }
