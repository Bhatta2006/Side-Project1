"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { IconSizeContext, useInk, useMergedRef } from "@/lib/ink/react"
import { buttonRecipe } from "@/lib/ink/recipes/button-ink"
import { cn } from "@/lib/utils"

const swipe = "hover:[&>svg_[data-part=swipe]]:animate-[ll-wipe_var(--ll-dur-sheet)_var(--ll-ease-out)_both]"

const buttonVariants = cva(
  "relative isolate inline-flex shrink-0 items-center justify-center gap-2 font-hand font-bold whitespace-nowrap transition-[translate] duration-(--ll-dur-press) ease-out active:translate-y-(--ll-press-sink) [&[data-pressed]:not([data-pressed=false])]:translate-y-(--ll-press-sink) disabled:pointer-events-none disabled:text-pencil-text aria-disabled:pointer-events-none aria-disabled:text-pencil-text [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not(.absolute):not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "text-primary-foreground",
        destructive: "text-paper",
        outline: "text-ink",
        secondary: "text-secondary-foreground",
        ghost: `text-foreground ${swipe}`,
        link: `text-link hover:text-link-hover ${swipe}`,
      },
      size: {
        default: "h-9 px-4 py-2 text-base has-[>svg:not(.absolute)]:px-3 compact:h-8 calm:h-7",
        xs: "h-6 gap-1 px-2 text-sm has-[>svg:not(.absolute)]:px-1.5 [&_svg:not(.absolute):not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 px-3 text-[15px] has-[>svg:not(.absolute)]:px-2.5 compact:h-7 calm:h-7",
        lg: "h-10 px-6 text-[17px] has-[>svg:not(.absolute)]:px-4 compact:h-9 calm:h-8",
        icon: "size-9 compact:size-8 calm:size-7",
        "icon-xs": "size-6 [&_svg:not(.absolute):not([class*='size-'])]:size-3",
        "icon-sm": "size-8 compact:size-7 calm:size-7",
        "icon-lg": "size-10 compact:size-9 calm:size-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

type ButtonVariant = NonNullable<VariantProps<typeof buttonVariants>["variant"]>
/** Socrat names from before Looseleaf, mapped onto the drawn variants. */
type LegacyVariant = "ink" | "solid" | "run" | "attention"
const LEGACY: Record<LegacyVariant, ButtonVariant> = {
  ink: "default",
  solid: "default",
  run: "outline",
  attention: "destructive",
}
function resolveVariant(variant: ButtonVariant | LegacyVariant | null | undefined): ButtonVariant {
  if (!variant) return "default"
  return (LEGACY as Record<string, ButtonVariant>)[variant] ?? (variant as ButtonVariant)
}

function Button({
  className,
  variant,
  size,
  asChild = false,
  disabled,
  seed,
  children,
  ref,
  onClick,
  ...props
}: React.ComponentProps<"button"> &
  Omit<VariantProps<typeof buttonVariants>, "variant"> & {
    variant?: ButtonVariant | LegacyVariant | null
    asChild?: boolean
    seed?: string | number
  }) {
  const v = resolveVariant(variant)
  const s = size ?? "default"
  const pill = !!className && className.split(/\s+/).includes("rounded-full")
  const forced = "data-focus-visible" in props || "data-pressed" in props
  const { hostRef, hostProps, node } = useInk({
    recipe: buttonRecipe,
    params: { variant: v, size: s, disabled: !!disabled, shape: pill ? "pill" : "default" },
    kind: "button",
    seed,
    layers: forced ? "all" : undefined,
  })
  const mergedRef = useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)
  const iconPx = s === "xs" || s === "icon-xs" ? 12 : undefined
  const shared = {
    "data-variant": v,
    "data-size": s,
    "data-shape": pill ? "pill" : undefined,
    "data-ink-sink": "self",
    className: cn(buttonVariants({ variant: v, size: s, className })),
    ref: mergedRef,
    ...hostProps,
    ...props,
  }

  if (asChild) {
    const inert = disabled
      ? {
          "aria-disabled": true as const,
          "data-disabled": "",
          tabIndex: -1,
          onClick: (e: React.MouseEvent<HTMLElement>) => e.preventDefault(),
        }
      : { onClick: onClick as React.MouseEventHandler<HTMLElement> | undefined }
    return (
      <IconSizeContext value={iconPx}>
        <Slot.Root data-slot="button" {...shared} {...inert}>
          <Slot.Slottable>{children}</Slot.Slottable>
          {node}
        </Slot.Root>
      </IconSizeContext>
    )
  }

  return (
    <IconSizeContext value={iconPx}>
      <button data-slot="button" {...shared} disabled={disabled} onClick={onClick}>
        {node}
        {children}
      </button>
    </IconSizeContext>
  )
}

/** The arrow at the end of a primary button: a hand-drawn stroke that nudges right on hover. */
function ArrowCircle({ className, loading = false }: { className?: string; loading?: boolean }) {
  return (
    <span data-slot="arrow" aria-hidden="true" className={cn("grid size-5 flex-none place-items-center transition-transform duration-200 ease-out [button:hover_&]:translate-x-0.5 [a:hover_&]:translate-x-0.5 [&_svg]:size-[18px]!", className)}>
      {loading ? (
        <svg viewBox="0 0 24 24" fill="none" className="animate-spin"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2.2" /><path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12.5c4.5-.6 9.5-.3 15-.4M13.5 6.5c2 1.8 3.8 3.6 5.6 5.6-1.9 1.9-3.7 3.8-5.4 5.8" /></svg>
      )}
    </span>
  )
}

export { Button, ArrowCircle, buttonVariants }
