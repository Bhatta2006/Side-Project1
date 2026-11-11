"use client"

import * as React from "react"

import { MARK_REVEAL, useMarkPhase } from "@/hooks/use-mark-ink"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { arrowRecipe, type ArrowCurve, type ArrowDirection, type ArrowHead } from "@/lib/ink/recipes/arrow-ink"
import type { MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import { cn } from "@/lib/utils"

type Target = React.RefObject<Element | null> | Element | string | null | undefined

const LABEL_SIDE: Record<ArrowDirection, string> = {
  right: "end-full top-1/2 me-2 -translate-y-1/2",
  left: "start-full top-1/2 ms-2 -translate-y-1/2",
  up: "top-full left-1/2 mt-1 -translate-x-1/2",
  down: "bottom-full left-1/2 mb-1 -translate-x-1/2",
  "up-right": "end-full bottom-0 me-2",
  "up-left": "start-full bottom-0 ms-2",
  "down-right": "end-full top-0 me-2",
  "down-left": "start-full top-0 ms-2",
}

function resolveTarget(t: Target): Element | null {
  if (!t) return null
  if (typeof t === "string") return document.querySelector(t)
  if (t instanceof Element) return t
  return t.current
}

function vectorTo(host: Element, target: Element, gap: number): { dx: number; dy: number } | null {
  const a = host.getBoundingClientRect()
  const b = target.getBoundingClientRect()
  const cx = a.left + a.width / 2, cy = a.top + a.height / 2
  const vx = b.left + b.width / 2 - cx, vy = b.top + b.height / 2 - cy
  const len = Math.hypot(vx, vy)
  if (len < 1) return null
  const enter = (lo: number, hi: number, o: number, v: number) => (v === 0 ? (o >= lo && o <= hi ? -Infinity : Infinity) : Math.min((lo - o) / v, (hi - o) / v))
  const t = Math.max(enter(b.left, b.right, cx, vx), enter(b.top, b.bottom, cy, vy))
  if (!(t >= 0 && t <= 1)) return null
  const reach = Math.max(0, len * t - gap)
  return { dx: Math.round(((vx / len) * reach) / 2) * 2, dy: Math.round(((vy / len) * reach) / 2) * 2 }
}

function Arrow({
  direction = "right",
  curve = "straight",
  head = "v",
  tone = "ink",
  weight = "regular",
  bend = "up",
  mirror = true,
  pointAt,
  gap = 6,
  animate = false,
  show = true,
  delay,
  seed,
  className,
  style,
  children,
  ref,
  ...props
}: React.ComponentProps<"span"> & {
  direction?: ArrowDirection
  curve?: ArrowCurve
  head?: ArrowHead
  tone?: MarkPen
  weight?: MarkWeight
  bend?: "up" | "down"
  mirror?: boolean
  pointAt?: Target
  gap?: number
  animate?: boolean
  show?: boolean
  delay?: number
  seed?: string | number
}) {
  const [host, setHost] = React.useState<HTMLElement | null>(null)
  const [vec, setVec] = React.useState<{ dx: number; dy: number } | null>(null)
  const aimed = pointAt !== undefined && pointAt !== null

  React.useLayoutEffect(() => {
    if (!aimed || !host) return
    const update = () => {
      const t = resolveTarget(pointAt)
      const v = t ? vectorTo(host, t, gap) : null
      setVec((prev) => (prev && v && prev.dx === v.dx && prev.dy === v.dy ? prev : v))
    }
    update()
    const stops: Array<() => void> = []
    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(update)
      ro.observe(host)
      const t = resolveTarget(pointAt)
      if (t) ro.observe(t)
      ro.observe(document.documentElement)
      stops.push(() => ro.disconnect())
    }
    window.addEventListener("resize", update)
    stops.push(() => window.removeEventListener("resize", update))
    void document.fonts?.ready?.then(update)
    return () => stops.forEach((s) => s())
  }, [aimed, host, pointAt, gap])

  const params = { direction, curve, head, tone, weight, bend, mirror, animate, ...(aimed && vec ? { dx: vec.dx, dy: vec.dy } : {}) }
  const { hostRef, hostProps, node } = useInk({ recipe: arrowRecipe, params, kind: "arrow", seed })
  const { phaseRef, phaseProps } = useMarkPhase({ animate, show })
  const ready = !!node && show && !(aimed && !vec)
  return (
    <span
      data-slot="arrow"
      data-direction={aimed ? undefined : direction}
      ref={useMergedRef<HTMLElement>(hostRef, phaseRef, ref as React.Ref<HTMLElement> | undefined, setHost)}
      {...(ready ? hostProps : {})}
      {...phaseProps}
      style={{ ...(animate ? ({ "--ll-draw-delay": `${delay ?? 0}ms` } as React.CSSProperties) : undefined), ...style }}
      className={cn("relative isolate inline-block shrink-0 align-middle outline-none", aimed ? "size-6" : "h-10 w-20", animate && MARK_REVEAL, className)}
      {...props}
    >
      {ready ? node : null}
      {children ? (
        <span
          data-slot="arrow-label"
          className={cn("absolute font-script text-xl leading-none whitespace-nowrap text-ink-you", !aimed && LABEL_SIDE[direction], aimed && "start-full top-1/2 ms-2 -translate-y-1/2")}
        >
          {children}
        </span>
      ) : null}
    </span>
  )
}

export { Arrow }
