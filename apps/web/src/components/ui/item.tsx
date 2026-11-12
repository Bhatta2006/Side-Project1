"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Separator as SeparatorPrimitive, Slot } from "radix-ui"

import { Separator } from "@/components/ui/separator"
import { useInkSeed } from "@/lib/ink/react"
import { hashSeed } from "@/lib/ink/rng"
import { ITEM_FRAMES, itemCss } from "@/lib/ink/recipes/item-ink"
import { cn } from "@/lib/utils"

const InList = React.createContext(false)

function ItemStyles() {
  return (
    <style href="ll-item" precedence="low">
      {itemCss()}
    </style>
  )
}

function ItemGroup({ className, ruled = false, ...props }: React.ComponentProps<"div"> & { ruled?: boolean }) {
  return (
    <InList value>
      <ItemStyles />
      <div role="list" data-slot="item-group" data-ruled={ruled ? "" : undefined} className={cn("group/item-group flex flex-col", className)} {...props} />
    </InList>
  )
}

function ItemSeparator({
  className,
  variant = "pencil",
  seed,
  decorative = true,
  orientation = "horizontal",
  children,
  ...props
}: React.ComponentProps<typeof Separator>) {
  const frame = hashSeed(useInkSeed(seed)) % ITEM_FRAMES
  if (variant !== "pencil" || orientation !== "horizontal" || children) {
    return (
      <Separator data-slot="item-separator" orientation={orientation} variant={variant} seed={seed} decorative={decorative} className={cn("my-0", className)} {...props}>
        {children}
      </Separator>
    )
  }
  return (
    <SeparatorPrimitive.Root
      data-slot="item-separator"
      data-variant="pencil"
      data-frame={frame}
      decorative={decorative}
      orientation="horizontal"
      className={cn("my-0 h-px w-full shrink-0", className)}
      {...props}
    />
  )
}

const itemVariants = cva(
  "group/item flex flex-wrap items-center font-hand text-[15px] outline-offset-2 focus-visible:outline-2 focus-visible:outline-focus [&:is(a,button)]:cursor-pointer [&:is(a,button)]:transition-colors [&:is(a,button)]:duration-(--ll-dur-hover) [&:is(a,button)]:hover:ll-swipe",
  {
    variants: {
      variant: {
        default: "",
        outline: "",
        muted: "",
      },
      size: {
        default: "gap-4 p-4 compact:p-3 calm:p-2.5",
        sm: "gap-2.5 px-4 py-3 compact:px-3 compact:py-2.5 calm:py-2",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Item({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  seed,
  role,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof itemVariants> & { asChild?: boolean; seed?: string | number }) {
  const inList = React.useContext(InList)
  const frame = hashSeed(useInkSeed(seed)) % ITEM_FRAMES
  const Comp = asChild ? Slot.Root : "div"
  const row = (
    <Comp
      data-slot="item"
      data-variant={variant}
      data-size={size}
      data-frame={frame}
      role={inList && asChild && role === "listitem" ? undefined : (role ?? (inList && !asChild ? "listitem" : undefined))}
      className={cn(itemVariants({ variant, size, className }))}
      {...props}
    />
  )
  const inner = <InList value={false}>{row}</InList>
  return (
    <>
      {inList ? null : <ItemStyles />}
      {inList && asChild ? (
        <div role="listitem" className="flex flex-col">
          {inner}
        </div>
      ) : (
        inner
      )}
    </>
  )
}

const itemMediaVariants = cva(
  "flex shrink-0 items-center justify-center gap-2 group-has-[[data-slot=item-description]]/item:translate-y-0.5 group-has-[[data-slot=item-description]]/item:self-start [&_svg]:pointer-events-none",
  {
    variants: {
      variant: {
        default: "bg-transparent",
        icon: "size-9 [&_svg:not([class*='size-'])]:size-4",
        image:
          "size-10 overflow-hidden bg-photo p-0.5 shadow-hair group-odd/item:-rotate-1 group-even/item:rotate-[.8deg] calm:rotate-0 [&_img]:size-full [&_img]:object-cover",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function ItemMedia({
  className,
  variant = "default",
  seed,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof itemMediaVariants> & { seed?: string | number }) {
  const frame = hashSeed(useInkSeed(seed)) % ITEM_FRAMES
  return <div data-slot="item-media" data-variant={variant} data-frame={frame} className={cn(itemMediaVariants({ variant, className }))} {...props} />
}

function ItemContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="item-content" className={cn("flex min-w-0 flex-1 flex-col gap-1 [&+[data-slot=item-content]]:flex-none", className)} {...props} />
}

function ItemTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="item-title" className={cn("flex w-fit items-center gap-2 text-base leading-snug font-bold", className)} {...props} />
}

function ItemDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="item-description"
      className={cn(
        "line-clamp-2 text-sm leading-normal font-normal text-balance text-muted-foreground",
        "[&>a]:text-link [&>a]:underline [&>a]:underline-offset-4 [&>a:hover]:text-link-hover",
        className
      )}
      {...props}
    />
  )
}

function ItemActions({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="item-actions" className={cn("flex items-center gap-2", className)} {...props} />
}

function ItemHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="item-header" className={cn("flex basis-full items-center justify-between gap-2", className)} {...props} />
}

function ItemFooter({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="item-footer" className={cn("flex basis-full items-center justify-between gap-2", className)} {...props} />
}

export { Item, ItemMedia, ItemContent, ItemActions, ItemGroup, ItemSeparator, ItemTitle, ItemDescription, ItemHeader, ItemFooter }
