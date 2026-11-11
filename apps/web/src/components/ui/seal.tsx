"use client"

import * as React from "react"

import { useEnsureInkDefs, useInkTier } from "@/lib/ink/react"
import { memo } from "@/lib/ink/art-draw"
import { hashSeed } from "@/lib/ink/rng"
import { sealArt, sealMarkList, sealVariantList, type SealMark, type SealParams, type SealTone, type SealVariant } from "@/lib/ink/recipes/seal-ink"
import { cn } from "@/lib/utils"

const autoTilt = (seed: string): number => ((hashSeed(seed) % 640) - 320) / 100

function describe(p: { variant: SealVariant; text?: string; sub?: string; mark?: SealMark }): string {
  if (p.text) return p.sub ? `${p.text}, ${p.sub}` : p.text
  if (p.mark === "check") return "Verified"
  if (p.mark === "star") return "Award"
  return `${p.variant} seal`
}

type SealProps = Omit<React.ComponentProps<"svg">, "children" | "viewBox" | "name"> & {
  variant?: SealVariant
  text?: string
  sub?: string
  mark?: SealMark
  tone?: SealTone
  ribbon?: SealTone
  ring?: string
  deco?: "tick" | "star" | "sparkle" | "swoosh" | "percent"
  size?: number
  tier?: "lo" | "hi"
  tilt?: number | "auto"
  shadow?: boolean
  label?: string
  decorative?: boolean
  seed?: string | number
}

function Seal({
  variant = "scallop",
  text,
  sub,
  mark,
  tone,
  ribbon,
  ring,
  deco,
  size = 96,
  tier: tierProp,
  tilt = 0,
  shadow = true,
  label,
  decorative = false,
  seed,
  className,
  style,
  ...props
}: SealProps) {
  useEnsureInkDefs()
  const providerTier = useInkTier()
  const tier = tierProp ?? providerTier
  const s = `${seed ?? `${variant}:${text ?? mark ?? ""}`}`
  const params: SealParams = { variant, text, sub, mark, tone, ribbon, ring, deco }
  const px = Math.max(16, Math.round(size))
  const res = memo(`seal|${px}|${tier}|${s}|${JSON.stringify(params)}`, () => sealArt(params, px, s, tier), 200)
  const deg = tilt === "auto" ? autoTilt(s) : tilt
  return (
    <svg
      data-slot="seal"
      data-ink="badge"
      data-variant={variant}
      role={decorative ? undefined : "img"}
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : (label ?? describe({ variant, text, sub, mark }))}
      focusable="false"
      viewBox={`0 0 ${res.w} ${res.h}`}
      width={res.w}
      height={res.h}
      style={{ ...(deg ? { rotate: tilt === "auto" ? `clamp(calc(var(--ll-tilt-max) * -1.6), ${deg}deg, calc(var(--ll-tilt-max) * 1.6))` : `${deg}deg` } : null), ...style }}
      className={cn("pointer-events-none inline-block shrink-0 overflow-visible align-middle", shadow && "ll-drop-sticker", className)}
      dangerouslySetInnerHTML={{ __html: res.svg }}
      {...props}
    />
  )
}

export { Seal, sealVariantList, sealMarkList }
export type { SealProps, SealVariant, SealMark }
