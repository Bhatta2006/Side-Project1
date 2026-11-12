"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { Separator } from "@/components/ui/separator"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { buttonGroupTextRecipe } from "@/lib/ink/recipes/button-group-ink"
import { cn } from "@/lib/utils"

const buttonGroupVariants = cva(
  "flex w-fit items-stretch has-[>[data-slot=button-group]]:gap-2 [&>*]:focus-visible:relative [&>*]:focus-visible:z-10 [&>[data-slot=select-trigger]:not([class*='w-'])]:w-fit [&>input]:flex-1 [&>[data-slot=input-frame]]:flex-1 [&>*:has(+[data-slot=button-group-separator])]:[--cl-e:15px] [&>*:not([data-slot=button-group-separator]):not(:first-child)]:[--cl-s:15px]",
  {
    variants: {
      orientation: {
        horizontal:
          "[&>*:not([data-slot=button-group-separator]):not(:focus-visible):not(:has(:focus-visible))>svg.absolute]:[clip-path:inset(-14px_var(--cl-e,-14px)_-14px_var(--cl-s,-14px))] rtl:[&>*:not([data-slot=button-group-separator]):not(:focus-visible):not(:has(:focus-visible))>svg.absolute]:[clip-path:inset(-14px_var(--cl-s,-14px)_-14px_var(--cl-e,-14px))]",
        vertical:
          "flex-col [&>*:not([data-slot=button-group-separator]):not(:focus-visible):not(:has(:focus-visible))>svg.absolute]:[clip-path:inset(var(--cl-s,-14px)_-14px_var(--cl-e,-14px)_-14px)]",
      },
    },
    defaultVariants: {
      orientation: "horizontal",
    },
  }
)

function ButtonGroup({
  className,
  orientation,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof buttonGroupVariants>) {
  return (
    <div
      role="group"
      data-slot="button-group"
      data-orientation={orientation ?? "horizontal"}
      className={cn(buttonGroupVariants({ orientation }), className)}
      {...props}
    />
  )
}

function ButtonGroupText({
  className,
  asChild = false,
  seed,
  children,
  ref,
  ...props
}: React.ComponentProps<"div"> & {
  asChild?: boolean
  seed?: string | number
}) {
  const { hostRef, hostProps, node } = useInk({ recipe: buttonGroupTextRecipe, params: {}, kind: "cell", seed })
  const shared = {
    ref: useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined),
    ...hostProps,
    className: cn(
      "relative isolate flex min-h-9 items-center gap-2 px-4 font-hand text-base compact:min-h-8 calm:min-h-7 [&_svg]:pointer-events-none [&_svg:not(.absolute):not([class*='size-'])]:size-4",
      className
    ),
    ...props,
  }
  if (asChild) {
    return (
      <Slot.Root data-slot="button-group-text" {...shared}>
        <Slot.Slottable>{children}</Slot.Slottable>
        {node}
      </Slot.Root>
    )
  }
  return (
    <div data-slot="button-group-text" {...shared}>
      {node}
      {children}
    </div>
  )
}

function ButtonGroupSeparator({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<typeof Separator>) {
  return (
    <Separator
      data-slot="button-group-separator"
      orientation={orientation}
      className={cn("relative m-0! self-stretch data-[orientation=vertical]:h-auto", className)}
      {...props}
    />
  )
}

export {
  ButtonGroup,
  ButtonGroupSeparator,
  ButtonGroupText,
  buttonGroupVariants,
}
