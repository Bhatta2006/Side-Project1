"use client"

import * as React from "react"

import { Handwritten } from "@/components/ui/handwritten"
import { cn } from "@/lib/utils"

const SIZE = {
  sm: "text-3xl",
  md: "text-5xl",
  lg: "text-6xl",
  xl: "text-7xl sm:text-8xl",
  hero: "text-7xl sm:text-9xl",
} as const

const TONE = {
  marker: "[--ll-riso:var(--ll-marker)]",
  tomato: "[--ll-riso:var(--ll-tomato)]",
  tangerine: "[--ll-riso:var(--ll-tangerine)]",
  lemon: "[--ll-riso:var(--ll-lemon)]",
  grass: "[--ll-riso:var(--ll-grass)]",
  teal: "[--ll-riso:var(--ll-teal)]",
  sky: "[--ll-riso:var(--ll-sky)]",
  grape: "[--ll-riso:var(--ll-grape)]",
  bubblegum: "[--ll-riso:var(--ll-bubblegum)]",
} as const

const DUOTONE =
  "[text-shadow:calc(0.055em*var(--ll-misreg-k))_calc(0.045em*var(--ll-misreg-k))_0_var(--ll-riso),calc(-0.035em*var(--ll-misreg-k))_calc(0.07em*var(--ll-misreg-k))_0_var(--ll-riso-b)]"

function Lettering({
  as: Comp = "h2",
  size = "lg",
  tone = "marker",
  duotone,
  wobble = 0,
  seed,
  className,
  style,
  children,
  ...props
}: Omit<React.ComponentProps<"h2">, "ref"> & {
  as?: React.ElementType
  size?: keyof typeof SIZE
  tone?: keyof typeof TONE
  duotone?: keyof typeof TONE
  wobble?: number
  seed?: string | number
  ref?: React.Ref<HTMLElement>
}) {
  const second = duotone ? ({ "--ll-riso-b": `var(--ll-${duotone})` } as React.CSSProperties) : undefined
  return (
    <Comp
      data-slot="lettering"
      data-size={size}
      style={{ ...second, ...style }}
      className={cn("ll-riso font-script leading-[0.95] font-bold tracking-tight text-balance text-ink", SIZE[size], TONE[tone], duotone && DUOTONE, className)}
      {...props}
    >
      {wobble > 0 ? (
        <Handwritten as="span" strength={wobble} seed={seed}>
          {children}
        </Handwritten>
      ) : (
        children
      )}
    </Comp>
  )
}

export { Lettering }
