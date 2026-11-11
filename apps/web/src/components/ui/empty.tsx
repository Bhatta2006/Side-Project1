"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { Doodle } from "@/components/ui/doodle"
import { Mascot, type MascotPose } from "@/components/ui/mascot"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { emptyFrameRecipe, emptyMediaRecipe } from "@/lib/ink/recipes/empty-ink"
import { cn } from "@/lib/utils"

const hasClass = (className: string | undefined, name: string) => !!className && className.split(/\s+/).includes(name)

function Empty({ className, seed, ref, children, ...props }: React.ComponentProps<"div"> & { seed?: string | number }) {
  const framed = hasClass(className, "border")
  const { hostRef, hostProps, node } = useInk({ recipe: emptyFrameRecipe, params: {}, kind: "frame", seed, still: true })
  return (
    <div
      data-slot="empty"
      ref={useMergedRef<HTMLDivElement>(framed ? hostRef : undefined, ref)}
      {...(framed && node ? hostProps : {})}
      className={cn(
        "relative isolate flex min-w-0 flex-1 flex-col items-center justify-center gap-6 p-6 text-center text-balance md:p-12 [.border]:border-transparent",
        className
      )}
      {...props}
    >
      {framed ? node : null}
      {children}
    </div>
  )
}

function EmptyHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="empty-header" className={cn("flex max-w-sm flex-col items-center gap-2 text-center", className)} {...props} />
}

const emptyMediaVariants = cva("mb-2 flex shrink-0 items-center justify-center [&_svg]:pointer-events-none [&_svg]:shrink-0", {
  variants: {
    variant: {
      default: "bg-transparent",
      icon: "relative isolate flex size-11 shrink-0 items-center justify-center text-foreground [&_svg:not(.absolute):not([class*='size-'])]:size-6",
    },
  },
  defaultVariants: {
    variant: "default",
  },
})

function EmptyMedia({
  className,
  variant = "default",
  pose,
  doodle,
  size,
  seed,
  ref,
  children,
  ...props
}: React.ComponentProps<"div"> &
  VariantProps<typeof emptyMediaVariants> & {
    pose?: MascotPose
    doodle?: string
    size?: number
    seed?: string | number
  }) {
  const tile = variant === "icon"
  const { hostRef, hostProps, node } = useInk({ recipe: emptyMediaRecipe, params: {}, kind: "tile", seed, still: true })
  return (
    <div
      data-slot="empty-icon"
      data-variant={variant}
      ref={useMergedRef<HTMLDivElement>(tile ? hostRef : undefined, ref)}
      {...(tile && node ? hostProps : {})}
      className={cn(emptyMediaVariants({ variant }), className)}
      {...props}
    >
      {tile ? node : null}
      {pose ? <Mascot pose={pose} size={size ?? 96} seed={seed} /> : null}
      {doodle ? <Doodle name={doodle} size={size ?? 80} seed={seed} /> : null}
      {children}
    </div>
  )
}

function EmptyTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="empty-title" className={cn("font-script text-[1.65rem] leading-none font-semibold", className)} {...props} />
}

function EmptyDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <div
      data-slot="empty-description"
      className={cn("text-sm/relaxed text-muted-foreground [&>a]:text-link [&>a]:underline [&>a]:underline-offset-4 [&>a:hover]:text-link-hover", className)}
      {...props}
    />
  )
}

function EmptyContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="empty-content" className={cn("flex w-full max-w-sm min-w-0 flex-col items-center gap-4 text-sm text-balance", className)} {...props} />
}

export { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyContent, EmptyMedia }
