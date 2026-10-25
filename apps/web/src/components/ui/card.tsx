import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

// Paper cards: white sheets on the notebook, a hairline and a soft lift (flat in dark mode).
const cardVariants = cva(
  "group/card flex flex-col gap-(--card-spacing) overflow-hidden rounded-card py-(--card-spacing) text-[15px] [--card-spacing:20px] has-data-[slot=card-footer]:pb-0 has-[>img:first-child]:pt-0 lg:[--card-spacing:24px] data-[size=sm]:[--card-spacing:16px] data-[size=sm]:has-data-[slot=card-footer]:pb-0",
  {
    variants: {
      tone: {
        surface: "border bg-card text-card-foreground shadow-[0_1px_0_rgb(21_22_30/0.03),0_12px_30px_-20px_rgb(21_22_30/0.22)] dark:shadow-none",
        hero: "bg-forest text-forest-foreground shadow-[0_18px_40px_-22px_rgb(35_64_232/0.7)] dark:shadow-none [--card-muted:color-mix(in_srgb,var(--forest-foreground),transparent_18%)] [--card-line:color-mix(in_srgb,var(--forest-foreground),transparent_55%)] lg:[--card-spacing:32px] [--card-spacing:24px]",
        violet: "bg-violet text-violet-foreground [--card-muted:color-mix(in_srgb,var(--violet-foreground),transparent_8%)] [--card-line:color-mix(in_srgb,var(--violet-foreground),transparent_55%)]",
        lilac: "bg-secondary text-secondary-foreground [--card-muted:color-mix(in_srgb,var(--secondary-foreground),transparent_22%)] [--card-line:color-mix(in_srgb,var(--secondary-foreground),transparent_50%)]",
        cream: "bg-cream text-cream-foreground [--card-muted:color-mix(in_srgb,var(--cream-foreground),transparent_22%)] [--card-line:color-mix(in_srgb,var(--cream-foreground),transparent_50%)]",
        raised: "bg-raised text-foreground",
        outlined: "border border-border-strong bg-transparent text-foreground",
      },
    },
    defaultVariants: { tone: "surface" },
  }
)

function Card({
  className,
  size = "default",
  tone = "surface",
  ...props
}: React.ComponentProps<"div"> & { size?: "default" | "sm" } & VariantProps<typeof cardVariants>) {
  return (
    <div
      data-slot="card"
      data-size={size}
      data-tone={tone}
      // A labelled card is a region; ARIA does not allow names on generic elements.
      role={props.role ?? (props['aria-label'] || props['aria-labelledby'] ? 'region' : undefined)}
      className={cn(cardVariants({ tone }), className)}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "group/card-header @container/card-header grid auto-rows-min items-start gap-1 px-(--card-spacing) has-data-[slot=card-action]:grid-cols-[1fr_auto] has-data-[slot=card-description]:grid-rows-[auto_auto] [.border-b]:pb-(--card-spacing)",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({
  className,
  as: Tag = "h3",
  ...props
}: React.ComponentProps<"h3"> & { as?: "h2" | "h3" | "div" }) {
  return (
    <Tag
      data-slot="card-title"
      className={cn(
        "font-display text-lg leading-snug font-bold tracking-[-0.02em] group-data-[size=sm]/card:text-base",
        className
      )}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground group-data-[tone=hero]/card:text-(--card-muted) group-data-[tone=lilac]/card:text-(--card-muted) group-data-[tone=violet]/card:text-(--card-muted) group-data-[tone=cream]/card:text-(--card-muted)", className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-(--card-spacing)", className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        "flex items-center border-t p-(--card-spacing)",
        className
      )}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
  cardVariants,
}
