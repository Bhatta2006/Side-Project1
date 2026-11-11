"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { Paper } from "@/components/ui/paper"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { alertRecipe, type AlertTone } from "@/lib/ink/recipes/alert-ink"
import { cn } from "@/lib/utils"

const alertVariants = cva(
  "relative isolate grid w-full grid-cols-[0_1fr] items-start gap-y-0.5 px-4 py-3 text-sm compact:py-2.5 calm:px-3 calm:py-2 has-[>svg:not(.absolute)]:grid-cols-[calc(var(--spacing)*4)_1fr] has-[>svg:not(.absolute)]:gap-x-3 [&>svg:not(.absolute)]:size-4 [&>svg:not(.absolute)]:translate-y-0.5 [&>svg:not(.absolute)]:text-current [&:not(:has(>svg:not(.absolute)))>svg_[data-part=icon-mark]]:hidden",
  {
    variants: {
      variant: {
        default: "text-card-foreground",
        destructive: "text-destructive *:data-[slot=alert-description]:text-destructive [&>svg:not(.absolute)]:text-current",
        info: "text-card-foreground [&>svg:not(.absolute)]:text-ink-you",
        success: "text-card-foreground [&>svg:not(.absolute)]:text-green",
        warning: "text-card-foreground",
        note: "px-5 py-4 text-ink *:data-[slot=alert-description]:text-ink-soft",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Alert({
  className,
  variant,
  seed,
  ref,
  children,
  ...props
}: React.ComponentProps<"div"> &
  VariantProps<typeof alertVariants> & {
    seed?: string | number
  }) {
  const tone: AlertTone = variant ?? "default"
  const { hostRef, hostProps, node } = useInk({ recipe: alertRecipe, params: { tone }, kind: "alert", seed, still: true })
  const merged = useMergedRef<HTMLDivElement>(hostRef, ref)

  if (tone === "note") {
    return (
      <Paper
        data-slot="alert"
        role="alert"
        stock="sticky-yellow"
        tape="corner"
        seed={seed}
        ref={ref as React.Ref<HTMLElement> | undefined}
        className={cn(alertVariants({ variant }), className)}
        {...props}
      >
        {children}
      </Paper>
    )
  }

  return (
    <div
      data-slot="alert"
      data-variant={tone}
      role="alert"
      ref={merged}
      {...hostProps}
      className={cn(alertVariants({ variant }), className)}
      {...props}
    >
      {node}
      {children}
    </div>
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="alert-title" className={cn("col-start-2 line-clamp-1 min-h-4 font-bold", className)} {...props} />
}

function AlertDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn("col-start-2 grid justify-items-start gap-1 text-sm text-muted-foreground [&_p]:leading-relaxed", className)}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription }
