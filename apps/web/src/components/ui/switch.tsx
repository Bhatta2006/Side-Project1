"use client"

import * as React from "react"
import { Switch as SwitchPrimitive } from "radix-ui"

import { useInk, useMergedRef } from "@/lib/ink/react"
import { switchRecipe, switchThumbRecipe } from "@/lib/ink/recipes/switch-ink"
import { cn } from "@/lib/utils"

function SwitchThumb({ className, seed, disabled, ref, ...props }: React.ComponentProps<typeof SwitchPrimitive.Thumb> & { seed: string; disabled: boolean }) {
  const { hostRef, hostProps, node } = useInk({ recipe: switchThumbRecipe, params: { disabled }, kind: "thumb", seed, still: true })
  return (
    <SwitchPrimitive.Thumb
      data-slot="switch-thumb"
      ref={useMergedRef<HTMLSpanElement>(hostRef, ref)}
      {...hostProps}
      className={cn(
        "pointer-events-none relative isolate block shrink-0 transition-transform duration-(--ll-dur-pop) ease-pop forced-colors:rounded-full forced-colors:bg-[ButtonText]",
        "size-(--sw-t) data-[state=unchecked]:translate-x-1 rtl:data-[state=unchecked]:-translate-x-1 data-[state=checked]:translate-x-(--sw-on) rtl:data-[state=checked]:-translate-x-(--sw-on)",
        className
      )}
      {...props}
    >
      {node}
    </SwitchPrimitive.Thumb>
  )
}

function Switch({
  className,
  size = "default",
  seed,
  disabled,
  ref,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root> & {
  size?: "sm" | "default"
  seed?: string | number
}) {
  const invalid = props["aria-invalid"] === true || props["aria-invalid"] === "true"
  const { hostRef, hostProps, node, seed: hostSeed } = useInk({ recipe: switchRecipe, params: { disabled: !!disabled, invalid }, kind: "switch", seed })
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      data-size={size}
      ref={useMergedRef<HTMLButtonElement>(hostRef, ref)}
      {...hostProps}
      disabled={disabled}
      className={cn(
        "peer group/switch relative isolate inline-flex shrink-0 items-center after:absolute after:-inset-1 disabled:cursor-not-allowed",
        "h-6 w-11 [--sw-on:1.5rem] [--sw-t:1rem] data-[size=sm]:h-5 data-[size=sm]:w-9 data-[size=sm]:[--sw-on:1.25rem] data-[size=sm]:[--sw-t:0.75rem] calm:h-5 calm:w-9 calm:[--sw-on:1.25rem] calm:[--sw-t:0.75rem]",
        "forced-colors:border forced-colors:border-[ButtonText] forced-colors:data-[state=checked]:bg-[Highlight]",
        "group-hover/field:[&>svg_[data-layer=hover]]:visible group-hover/field:[&>svg_[data-layer=hover]]:opacity-100",
        "has-[+[data-slot=label]:hover]:[&>svg_[data-layer=hover]]:visible has-[+[data-slot=label]:hover]:[&>svg_[data-layer=hover]]:opacity-100",
        "has-[+input+[data-slot=label]:hover]:[&>svg_[data-layer=hover]]:visible has-[+input+[data-slot=label]:hover]:[&>svg_[data-layer=hover]]:opacity-100",
        className
      )}
      {...props}
    >
      {node}
      <SwitchThumb seed={`${hostSeed}|thumb`} disabled={!!disabled} />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
