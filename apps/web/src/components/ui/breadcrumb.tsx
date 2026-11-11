"use client"

import * as React from "react"
import { Slot } from "radix-ui"

import { Icon } from "@/components/ui/icon"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { breadcrumbPageRecipe } from "@/lib/ink/recipes/breadcrumb-ink"
import { cn } from "@/lib/utils"

function Breadcrumb({ ...props }: React.ComponentProps<"nav">) {
  return <nav aria-label="breadcrumb" data-slot="breadcrumb" {...props} />
}

function BreadcrumbList({ className, ...props }: React.ComponentProps<"ol">) {
  return <ol data-slot="breadcrumb-list" className={cn("flex flex-wrap items-center gap-1.5 font-hand text-base leading-6 break-words text-muted-foreground sm:gap-2", className)} {...props} />
}

function BreadcrumbItem({ className, ...props }: React.ComponentProps<"li">) {
  return <li data-slot="breadcrumb-item" className={cn("inline-flex items-center gap-1.5", className)} {...props} />
}

function BreadcrumbLink({
  asChild,
  className,
  ...props
}: React.ComponentProps<"a"> & {
  asChild?: boolean
}) {
  const Comp = asChild ? Slot.Root : "a"

  return <Comp data-slot="breadcrumb-link" className={cn("-mx-1 px-1 transition-colors hover:ll-swipe focus-visible:ll-swipe", className)} {...props} />
}

function BreadcrumbPage({ className, seed, ref, children, ...props }: React.ComponentProps<"span"> & { seed?: string | number }) {
  const { hostRef, hostProps, node } = useInk({ recipe: breadcrumbPageRecipe, params: {}, kind: "crumb", seed, still: true })
  return (
    <span
      data-slot="breadcrumb-page"
      role="link"
      aria-disabled="true"
      aria-current="page"
      ref={useMergedRef<HTMLSpanElement>(hostRef, ref)}
      {...(node ? hostProps : {})}
      className={cn("relative isolate inline-block px-0.5 pb-1 font-bold text-foreground", className)}
      {...props}
    >
      {node}
      {children}
    </span>
  )
}

function BreadcrumbSeparator({ children, className, ...props }: React.ComponentProps<"li">) {
  return (
    <li data-slot="breadcrumb-separator" role="presentation" aria-hidden="true" className={cn("text-pencil-mark [&>svg:not(.absolute):not([class*='size-'])]:size-4", className)} {...props}>
      {children ?? <Icon name="slash" size={16} />}
    </li>
  )
}

function BreadcrumbEllipsis({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span data-slot="breadcrumb-ellipsis" role="presentation" aria-hidden="true" className={cn("flex size-9 items-center justify-center", className)} {...props}>
      <Icon name="ellipsis" size={16} />
      <span className="sr-only">More</span>
    </span>
  )
}

export { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator, BreadcrumbEllipsis }
