"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { useInk, useMergedRef } from "@/lib/ink/react"
import { RIBBON_SIZES, ribbonDrop, ribbonGutter, ribbonInset, ribbonRecipe, ribbonSizeList, ribbonToneList, ribbonVariantList, type RibbonSize, type RibbonTone, type RibbonVariant } from "@/lib/ink/recipes/ribbon-ink"
import { cn } from "@/lib/utils"

type RibbonProps = Omit<React.ComponentProps<"span">, "color"> & {
  variant?: RibbonVariant
  tone?: RibbonTone
  size?: RibbonSize
  asChild?: boolean
  seed?: string | number
}

function Ribbon({ className, variant = "banner", tone = "marker", size = "default", asChild = false, seed, style, children, ref, ...props }: RibbonProps) {
  const S = RIBBON_SIZES[size]
  const inset = ribbonInset(variant, size)
  const drop = ribbonDrop(variant, size)
  const interactive = asChild || props.onClick !== undefined || (props as { href?: string }).href !== undefined
  const { hostRef, hostProps, node } = useInk({
    recipe: ribbonRecipe,
    params: { variant, tone, size, hoverable: interactive },
    kind: "ribbon",
    seed,
  })
  const Comp = asChild ? Slot.Root : "span"
  const pad = inset + ribbonGutter(variant)
  return (
    <Comp
      data-slot="ribbon"
      data-variant={variant}
      data-tone={tone}
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn(
        "relative isolate inline-flex items-center justify-center gap-1.5 font-hand font-bold whitespace-nowrap text-ink transition-[translate] duration-(--ll-dur-hover) ease-(--ll-ease-settle)",
        S.text,
        "[&_svg:not(.absolute):not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:shrink-0",
        interactive && "cursor-pointer hover:-translate-y-px",
        className
      )}
      style={{ height: S.band + drop, paddingInline: pad, paddingBottom: drop, minWidth: 2 * inset + 24, ...style }}
      {...props}
    >
      <Slot.Slottable>{children}</Slot.Slottable>
      {node}
    </Comp>
  )
}

export { Ribbon, ribbonVariantList, ribbonToneList, ribbonSizeList }
export type { RibbonProps }
