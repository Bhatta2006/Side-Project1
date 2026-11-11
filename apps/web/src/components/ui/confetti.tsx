"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { motionIsOff } from "@/hooks/use-live-motion"
import { useMergedRef } from "@/lib/ink/react"
import {
  CONFETTI_COLORS,
  CONFETTI_KINDS,
  STEP_MS,
  confettiPiece,
  simulate,
  type ConfettiColor,
  type ConfettiKind,
} from "@/lib/ink/recipes/confetti-ink"
import { cn } from "@/lib/utils"

type Origin = Element | { x: number; y: number } | { clientX: number; clientY: number } | null | undefined

interface ConfettiOptions {
  origin?: Origin
  count?: number
  spread?: number
  angle?: number
  velocity?: number
  gravity?: number
  drift?: number
  duration?: number
  colors?: readonly ConfettiColor[]
  shapes?: readonly ConfettiKind[]
  scalar?: number
  seed?: number
  onDone?: () => void
}

let bursts = 0
const layers = new WeakMap<Element, HTMLElement>()

function layerFor(host: HTMLElement): HTMLElement {
  const known = layers.get(host)
  if (known?.isConnected) return known
  const layer = document.createElement("div")
  layer.setAttribute("data-slot", "confetti-layer")
  layer.setAttribute("aria-hidden", "true")
  const s = layer.style
  s.pointerEvents = "none"
  s.overflow = "hidden"
  s.position = host === document.body ? "fixed" : "absolute"
  s.inset = "0"
  s.zIndex = "var(--ll-z-splash)"
  host.appendChild(layer)
  layers.set(host, layer)
  return layer
}

const centreOf = (el: Element) => {
  const r = el.getBoundingClientRect()
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 }
}

function confetti(options: ConfettiOptions & { container?: HTMLElement | null } = {}): () => void {
  if (typeof document === "undefined") return () => {}
  const host = options.container ?? document.body
  if (motionIsOff(host)) return () => {}
  const layer = layerFor(host)
  const box = layer.getBoundingClientRect()
  const at = options.origin
  const o = at && "getBoundingClientRect" in at ? centreOf(at) : at && "clientX" in at ? { x: at.clientX, y: at.clientY } : at && "x" in at ? at : { x: box.left + box.width / 2, y: box.top + box.height / 2 }
  const ox = o.x - box.left, oy = o.y - box.top
  const duration = options.duration ?? 2600
  const flights = simulate(
    {
      count: Math.min(400, Math.max(0, Math.round(options.count ?? 70))),
      spread: options.spread ?? 70,
      angle: options.angle ?? 90,
      velocity: options.velocity ?? 1100,
      gravity: options.gravity ?? 520,
      drift: options.drift ?? 0,
      duration,
      seed: options.seed ?? ++bursts,
    },
    options.shapes ?? CONFETTI_KINDS,
    options.colors ?? CONFETTI_COLORS,
  )
  const scalar = options.scalar ?? 1
  const live = new Set<Animation>()
  const pieces: Element[] = []
  const done = (el: Element) => {
    el.remove()
    if (!layer.childElementCount) layer.remove()
  }
  let over = false
  const end = () => {
    if (over) return
    over = true
    live.clear()
    pieces.length = 0
    options.onDone?.()
  }
  for (const f of flights) {
    const p = confettiPiece(f.kind, f.color, f.variant)
    const k = f.scale * scalar
    const wrap = document.createElement("div")
    wrap.innerHTML = `<svg aria-hidden="true" focusable="false" viewBox="0 0 ${p.w} ${p.h}" width="${(p.w * k).toFixed(1)}" height="${(p.h * k).toFixed(1)}" style="position:absolute;left:${(-p.w * k / 2).toFixed(1)}px;top:${(-p.h * k / 2).toFixed(1)}px;will-change:transform,opacity;overflow:visible">${p.svg}</svg>`
    const el = wrap.firstElementChild as SVGElement
    layer.appendChild(el)
    pieces.push(el)
    if (typeof el.animate !== "function") {
      done(el)
      continue
    }
    const anim = el.animate(
      f.frames.map((fr) => ({
        transform: `translate(${(ox + fr.x).toFixed(1)}px, ${(oy + fr.y).toFixed(1)}px) rotate(${fr.rot.toFixed(0)}deg) scale(1, ${fr.flip.toFixed(2)})`,
        opacity: fr.opacity,
      })),
      { duration: (f.frames.length - 1) * STEP_MS, easing: "linear", fill: "forwards" },
    )
    live.add(anim)
    anim.onfinish = () => {
      live.delete(anim)
      done(el)
      if (!live.size) end()
    }
  }
  if (!live.size) end()
  return () => {
    for (const a of live) a.cancel()
    for (const el of pieces) done(el)
    end()
  }
}

interface ConfettiHandle {
  burst(options?: ConfettiOptions): () => void
}

type ConfettiProps = Omit<React.ComponentProps<"div">, "children"> &
  ConfettiOptions & {
    active?: boolean
    burstKey?: number | string
    apiRef?: React.Ref<ConfettiHandle>
  }

function Confetti({ className, active, burstKey, apiRef, origin, count, spread, angle, velocity, gravity, drift, duration, colors, shapes, scalar, seed, onDone, ref, ...props }: ConfettiProps) {
  const el = React.useRef<HTMLDivElement | null>(null)
  const opts = { origin, count, spread, angle, velocity, gravity, drift, duration, colors, shapes, scalar, seed, onDone }
  const latest = React.useRef(opts)
  latest.current = opts
  const flying = React.useRef(new Set<() => void>())
  const throwIt = React.useCallback((extra?: ConfettiOptions) => {
    const merged = { ...latest.current, ...extra }
    let over = false
    let stop: () => void = () => {}
    stop = confetti({
      ...merged,
      container: el.current,
      onDone: () => {
        over = true
        flying.current.delete(stop)
        merged.onDone?.()
      },
    })
    if (!over) flying.current.add(stop)
    return stop
  }, [])
  React.useImperativeHandle(apiRef, () => ({ burst: throwIt }), [throwIt])
  React.useEffect(() => {
    if (active) throwIt()
  }, [active, throwIt])
  const key = React.useRef(burstKey)
  React.useEffect(() => {
    if (key.current !== burstKey) {
      key.current = burstKey
      throwIt()
    }
  }, [burstKey, throwIt])
  React.useEffect(() => {
    const set = flying.current
    return () => {
      for (const stop of [...set]) stop()
      set.clear()
    }
  }, [])
  return (
    <div
      data-slot="confetti"
      aria-hidden="true"
      ref={useMergedRef<HTMLDivElement>(el, ref)}
      className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}
      {...props}
    />
  )
}

type ConfettiTriggerProps = React.ComponentProps<"button"> & ConfettiOptions & { asChild?: boolean }

function ConfettiTrigger({ asChild = false, onClick, origin, count, spread, angle, velocity, gravity, drift, duration, colors, shapes, scalar, seed, onDone, ...props }: ConfettiTriggerProps) {
  const Comp = asChild ? Slot.Root : "button"
  return (
    <Comp
      data-slot="confetti-trigger"
      type={asChild ? undefined : "button"}
      onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
        onClick?.(e)
        if (!e.defaultPrevented) confetti({ origin: origin ?? e.currentTarget, count, spread, angle, velocity, gravity, drift, duration, colors, shapes, scalar, seed, onDone })
      }}
      {...props}
    />
  )
}

function useConfetti(defaults: ConfettiOptions = {}): (options?: ConfettiOptions) => () => void {
  const latest = React.useRef(defaults)
  latest.current = defaults
  return React.useCallback((options?: ConfettiOptions) => confetti({ ...latest.current, ...options }), [])
}

export { confetti, Confetti, ConfettiTrigger, useConfetti }
export type { ConfettiOptions, ConfettiProps, ConfettiHandle, ConfettiTriggerProps, ConfettiColor, ConfettiKind }
