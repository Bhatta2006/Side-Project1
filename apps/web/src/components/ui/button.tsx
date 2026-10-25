import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// Pills with a 44 px minimum target. Focus uses the global 2 px ring (globals.css).
const buttonVariants = cva(
  "group/button relative inline-flex shrink-0 items-center justify-center rounded-full border border-transparent font-medium tracking-[-0.01em] whitespace-nowrap transition-[background-color,border-color,color,transform] duration-200 ease-[var(--ease-soft)] outline-none select-none active:not-aria-[haspopup]:not-disabled:scale-[0.98] disabled:pointer-events-none disabled:opacity-45 aria-busy:pointer-events-none aria-invalid:border-attention [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-[18px] [&_svg]:stroke-[1.75]",
  {
    variants: {
      variant: {
        // Primary on neutral surfaces.
        default: "bg-primary text-primary-foreground shadow-[var(--primary-glow)] hover:bg-[color-mix(in_srgb,var(--primary),white_10%)] hover:shadow-[var(--primary-glow),0_10px_28px_-10px_rgb(35_64_232/0.7)]",
        // Primary on a violet card: ink pill, white arrow disc.
        ink: "bg-ink text-ink-foreground hover:bg-[color-mix(in_srgb,var(--ink),white_14%)]",
        // Primary on lilac or sand surfaces: ink fill.
        solid: "bg-ink text-ink-foreground hover:bg-[color-mix(in_srgb,var(--ink),white_14%)]",
        // Supporting action.
        outline:
          "border-border-strong bg-card text-foreground hover:border-foreground/40 hover:bg-card aria-expanded:bg-raised",
        secondary:
          "bg-raised text-foreground hover:bg-[color-mix(in_srgb,var(--raised),var(--foreground)_6%)] aria-expanded:bg-raised",
        ghost:
          "text-foreground hover:bg-raised aria-expanded:bg-raised",
        // Run code: outlined brand colour.
        run: "border-primary bg-transparent text-brand hover:bg-[color-mix(in_srgb,var(--primary),transparent_88%)]",
        // Delete or remove: outlined coral.
        destructive:
          "border-attention bg-transparent text-attention hover:bg-[color-mix(in_srgb,var(--attention),transparent_90%)]",
        // Confirming a destructive action inside its dialog.
        attention: "bg-attention text-attention-foreground hover:bg-[color-mix(in_srgb,var(--attention),black_8%)]",
        link: "rounded-md px-0! text-foreground underline decoration-1 underline-offset-4 hover:decoration-2",
      },
      size: {
        default:
          "h-11 gap-2 px-5 text-[15px] has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4 has-data-[slot=arrow]:pr-4",
        xs: "h-8 gap-1 px-3 text-xs [&_svg:not([class*='size-'])]:size-3.5",
        sm: "h-9 gap-1.5 px-4 text-sm has-data-[slot=arrow]:pr-3 [&_svg:not([class*='size-'])]:size-4",
        lg: "h-13 gap-2.5 px-6 text-base has-data-[slot=arrow]:pr-5 lg:h-12",
        icon: "size-11",
        "icon-xs": "size-8 [&_svg:not([class*='size-'])]:size-3.5",
        "icon-sm": "size-9",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

/** The arrow at the end of a primary pill: a plain stroke that nudges right on hover. */
function ArrowCircle({ className, loading = false }: { className?: string; loading?: boolean }) {
  return (
    <span data-slot="arrow" aria-hidden="true" className={cn("grid size-5 flex-none place-items-center transition-transform duration-200 ease-[var(--ease-soft)] group-hover/button:translate-x-0.5 [&_svg]:size-[18px]!", className)}>
      {loading ? (
        <svg viewBox="0 0 24 24" fill="none" className="animate-spin"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2.5" /><path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      )}
    </span>
  )
}

export { Button, ArrowCircle, buttonVariants }
