"use client"

import * as React from "react"
import { AlertDialog as AlertDialogPrimitive } from "radix-ui"

import { Button } from "@/components/ui/button"
import { Paper, type PaperProps } from "@/components/ui/paper"
import { Tape } from "@/components/ui/tape"
import { useInk, useInkScope, useInkSeed, useMergedRef } from "@/lib/ink/react"
import { alertMediaRecipe, type AlertMediaTone } from "@/lib/ink/recipes/alert-dialog-ink"
import { cn } from "@/lib/utils"

function AlertDialog({ ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Root>) {
  return <AlertDialogPrimitive.Root data-slot="alert-dialog" {...props} />
}

function AlertDialogTrigger({ ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Trigger>) {
  return <AlertDialogPrimitive.Trigger data-slot="alert-dialog-trigger" {...props} />
}

function AlertDialogPortal({ ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Portal>) {
  return <AlertDialogPrimitive.Portal data-slot="alert-dialog-portal" {...props} />
}

function AlertDialogOverlay({ className, ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Overlay>) {
  const scope = useInkScope()
  return (
    <AlertDialogPrimitive.Overlay
      data-slot="alert-dialog-overlay"
      {...scope}
      className={cn(
        "fixed inset-0 z-(--ll-z-overlay) flex overflow-y-auto overscroll-contain p-4 [background:var(--ll-overlay-dim)] [scrollbar-gutter:stable_both-edges] max-sm:p-0",
        "duration-(--ll-dur-sheet) data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogContent({
  className,
  size = "default",
  tone = "default",
  children,
  stock = "paper",
  edge,
  tilt,
  seed: seedProp,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Content> &
  Pick<PaperProps, "stock" | "edge" | "tilt" | "seed"> & {
    size?: "default" | "sm"
    tone?: "default" | "danger"
  }) {
  const scope = useInkScope()
  const seed = useInkSeed(seedProp)
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay>
        <AlertDialogPrimitive.Content asChild {...props}>
          <Paper
            data-slot="alert-dialog-content"
            data-size={size}
            data-tone={tone}
            stock={stock}
            edge={edge}
            tilt={tilt}
            rules="none"
            seed={seed}
            {...scope}
            className={cn(
              "group/alert-dialog-content m-auto grid w-full max-w-lg gap-4 p-6 text-foreground outline-hidden compact:p-5 calm:p-4 data-[size=sm]:max-w-xs",
              "max-sm:mb-0 max-sm:max-w-none max-sm:pb-[max(1.5rem,env(safe-area-inset-bottom))] max-sm:compact:pb-[max(1.25rem,env(safe-area-inset-bottom))] max-sm:calm:pb-[max(1rem,env(safe-area-inset-bottom))] max-sm:[--ll-tilt:0deg]!",
              "data-[state=open]:animate-sheet-drop max-sm:data-[state=open]:animate-in max-sm:data-[state=open]:slide-in-from-bottom-16 max-sm:data-[state=open]:fade-in-0",
              "duration-(--ll-dur-fade) data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 max-sm:data-[state=closed]:slide-out-to-bottom-8",
              className
            )}
          >
            {tone === "danger" && (
              <>
                <Tape kind="washi-stripes" color="tomato" length={68} height={20} angle={-38} seed={`${seed}:hz-a`} className="absolute -top-2 -left-7 z-(--ll-z-prop) max-sm:hidden calm:hidden" />
                <Tape kind="washi-stripes" color="tomato" length={68} height={20} angle={36} seed={`${seed}:hz-b`} className="absolute -top-2 -right-7 z-(--ll-z-prop) max-sm:hidden calm:hidden" />
              </>
            )}
            {children}
          </Paper>
        </AlertDialogPrimitive.Content>
      </AlertDialogOverlay>
    </AlertDialogPortal>
  )
}

function AlertDialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-header"
      className={cn(
        "grid grid-rows-[auto_1fr] place-items-center gap-1.5 text-center has-data-[slot=alert-dialog-media]:grid-rows-[auto_auto_1fr] has-data-[slot=alert-dialog-media]:gap-x-6 sm:group-data-[size=default]/alert-dialog-content:place-items-start sm:group-data-[size=default]/alert-dialog-content:text-start sm:group-data-[size=default]/alert-dialog-content:has-data-[slot=alert-dialog-media]:grid-rows-[auto_1fr]",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-footer"
      className={cn(
        "flex flex-col-reverse gap-2 group-data-[size=sm]/alert-dialog-content:grid group-data-[size=sm]/alert-dialog-content:grid-cols-2 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogTitle({ className, ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Title>) {
  return (
    <AlertDialogPrimitive.Title
      data-slot="alert-dialog-title"
      className={cn(
        "font-script text-[1.7rem] leading-none font-semibold sm:group-data-[size=default]/alert-dialog-content:group-has-data-[slot=alert-dialog-media]/alert-dialog-content:col-start-2",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogDescription({ className, ...props }: React.ComponentProps<typeof AlertDialogPrimitive.Description>) {
  return <AlertDialogPrimitive.Description data-slot="alert-dialog-description" className={cn("text-sm text-muted-foreground", className)} {...props} />
}

function AlertDialogMedia({
  className,
  tone = "default",
  seed: seedProp,
  children,
  ref,
  ...props
}: React.ComponentProps<"div"> & {
  tone?: AlertMediaTone
  seed?: string | number
}) {
  const seed = useInkSeed(seedProp)
  const { hostRef, hostProps, node } = useInk({ recipe: alertMediaRecipe, params: { tone }, kind: "plate", size: [64, 64], seed })
  return (
    <div
      data-slot="alert-dialog-media"
      ref={useMergedRef<HTMLElement>(hostRef, ref as React.Ref<HTMLElement> | undefined)}
      {...hostProps}
      className={cn(
        "relative isolate mb-2 inline-flex size-16 items-center justify-center sm:group-data-[size=default]/alert-dialog-content:row-span-2 *:[svg:not(.absolute):not([class*='size-'])]:size-8",
        className
      )}
      {...props}
    >
      {node}
      {children}
    </div>
  )
}

function AlertDialogAction({
  className,
  variant = "default",
  size = "default",
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Action> & Pick<React.ComponentProps<typeof Button>, "variant" | "size">) {
  return (
    <Button variant={variant} size={size} asChild>
      <AlertDialogPrimitive.Action data-slot="alert-dialog-action" className={cn(className)} {...props} />
    </Button>
  )
}

function AlertDialogCancel({
  className,
  variant = "outline",
  size = "default",
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Cancel> & Pick<React.ComponentProps<typeof Button>, "variant" | "size">) {
  return (
    <Button variant={variant} size={size} asChild>
      <AlertDialogPrimitive.Cancel data-slot="alert-dialog-cancel" className={cn(className)} {...props} />
    </Button>
  )
}

export {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogOverlay,
  AlertDialogPortal,
  AlertDialogTitle,
  AlertDialogTrigger,
}
