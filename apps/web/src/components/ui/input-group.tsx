"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { Button } from "@/components/ui/button"
import { InputControl } from "@/components/ui/input"
import { TextareaControl } from "@/components/ui/textarea"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { inputGroupRecipe, inputGroupRuleRecipe } from "@/lib/ink/recipes/input-group-ink"
import { cn } from "@/lib/utils"

function InputGroup({ className, seed, ref, children, ...props }: React.ComponentProps<"div"> & { seed?: string | number }) {
  const { hostRef, hostProps, node } = useInk({ recipe: inputGroupRecipe, params: {}, kind: "field", seed, still: true })
  return (
    <div
      data-slot="input-group"
      role="group"
      ref={useMergedRef<HTMLDivElement>(hostRef, ref)}
      {...hostProps}
      className={cn(
        "group/input-group relative isolate flex w-full min-w-0 items-center font-hand text-base text-(--ll-input-ink) caret-(--ll-caret) calm:text-[15px]",
        "h-9 compact:h-8 calm:h-7 has-[>textarea]:h-auto",

        "has-[>[data-align=inline-start]]:[&>input]:ps-2",
        "has-[>[data-align=inline-end]]:[&>input]:pe-2",
        "has-[>[data-align=block-start]]:h-auto has-[>[data-align=block-start]]:flex-col has-[>[data-align=block-start]]:[&>input]:pb-3",
        "has-[>[data-align=block-end]]:h-auto has-[>[data-align=block-end]]:flex-col has-[>[data-align=block-end]]:[&>input]:pt-3",

        "has-[[data-slot=input-group-control]:focus-visible]:[&>svg>[data-layer=focus]]:visible has-[[data-slot=input-group-control]:focus-visible]:[&>svg>[data-layer=focus]]:opacity-100",
        "has-[[data-slot=input-group-control][aria-invalid=true]]:[&>svg>[data-layer=invalid]]:visible has-[[data-slot=input-group-control][aria-invalid=true]]:[&>svg>[data-layer=invalid]]:opacity-100",
        "has-[[data-slot=input-group-control][aria-invalid=true]]:[&>svg_[data-hide-on~=invalid]]:invisible has-[[data-slot=input-group-control][aria-invalid=true]]:[&>svg_[data-hide-on~=invalid]]:opacity-0",
        "has-[[data-slot=input-group-control]:disabled]:[&>svg>[data-layer=disabled]]:visible has-[[data-slot=input-group-control]:disabled]:[&>svg>[data-layer=disabled]]:opacity-100",
        "has-[[data-slot=input-group-control]:disabled]:[&>svg_[data-hide-on~=disabled]]:invisible has-[[data-slot=input-group-control]:disabled]:[&>svg_[data-hide-on~=disabled]]:opacity-0",
        "has-[[data-slot=input-group-control]:disabled]:[&>svg>[data-layer=hover]]:hidden data-[disabled=true]:[&>svg>[data-layer=hover]]:hidden",
        className
      )}
      {...props}
    >
      {node}
      {children}
    </div>
  )
}

const inputGroupAddonVariants = cva(
  "flex h-auto cursor-text items-center justify-center gap-2 py-1.5 font-hand text-[15px] font-bold text-muted-foreground select-none group-has-[[data-slot=input-group-control]:disabled]/input-group:text-pencil-text group-data-[disabled=true]/input-group:text-pencil-text [&>kbd]:font-mono [&>svg:not(.absolute):not([class*='size-'])]:size-4",
  {
    variants: {
      align: {
        "inline-start": "order-first ps-3 has-[>button]:-ms-[0.45rem] has-[>kbd]:-ms-[0.35rem]",
        "inline-end": "order-last pe-3 has-[>button]:-me-[0.45rem] has-[>kbd]:-me-[0.35rem]",
        "block-start": "order-first w-full justify-start px-3 pt-3 group-has-[>input]/input-group:pt-2.5 [.border-b]:pb-3",
        "block-end": "order-last w-full justify-start px-3 pb-3 group-has-[>input]/input-group:pb-2.5 [.border-t]:pt-3",
      },
    },
    defaultVariants: {
      align: "inline-start",
    },
  }
)

const hasClass = (className: string | undefined, name: string) => !!className && className.split(/\s+/).includes(name)

function InputGroupAddon({ className, align = "inline-start", onClick, ref, children, ...props }: React.ComponentProps<"div"> & VariantProps<typeof inputGroupAddonVariants>) {
  const edge = hasClass(className, "border-b") ? "bottom" : hasClass(className, "border-t") ? "top" : null
  const { hostRef, hostProps, node } = useInk({ recipe: inputGroupRuleRecipe, params: { edge: edge ?? "bottom" }, kind: "rule", still: true })
  const drawn = edge !== null
  return (
    <div
      role="group"
      data-slot="input-group-addon"
      data-align={align}
      ref={useMergedRef<HTMLDivElement>(drawn ? hostRef : undefined, ref)}
      {...(drawn && node ? hostProps : {})}
      className={cn(inputGroupAddonVariants({ align }), drawn && "[.border-b]:border-transparent [.border-t]:border-transparent forced-colors:outline-0!", className)}
      onClick={(e) => {
        onClick?.(e)
        if ((e.target as HTMLElement).closest("button, a[href], select, input, textarea, [role=button], [role=combobox], [role=checkbox], [role=switch]")) {
          return
        }
        e.currentTarget.parentElement?.querySelector<HTMLElement>("input, textarea")?.focus()
      }}
      {...props}
    >
      {drawn ? node : null}
      {children}
    </div>
  )
}

const inputGroupButtonVariants = cva("flex items-center gap-2 font-hand text-sm shadow-none", {
  variants: {
    size: {
      xs: "h-6 gap-1 px-2 has-[>svg:not(.absolute)]:px-2 [&>svg:not(.absolute):not([class*='size-'])]:size-3.5",
      sm: "h-8 gap-1.5 px-2.5 has-[>svg:not(.absolute)]:px-2.5",
      "icon-xs": "size-6 p-0 has-[>svg:not(.absolute)]:p-0",
      "icon-sm": "size-8 p-0 has-[>svg:not(.absolute)]:p-0",
    },
  },
  defaultVariants: {
    size: "xs",
  },
})

function InputGroupButton({
  className,
  type = "button",
  variant = "ghost",
  size = "xs",
  ...props
}: Omit<React.ComponentProps<typeof Button>, "size"> & VariantProps<typeof inputGroupButtonVariants>) {
  return <Button type={type} data-size={size} variant={variant} size={size} className={cn(inputGroupButtonVariants({ size }), className)} {...props} />
}

function InputGroupText({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="input-group-text"
      className={cn("flex items-center gap-2 font-hand text-[15px] text-muted-foreground [&_svg]:pointer-events-none [&_svg:not(.absolute):not([class*='size-'])]:size-4", className)}
      {...props}
    />
  )
}

function InputGroupInput({ className, ...props }: React.ComponentProps<"input">) {
  return <InputControl data-slot="input-group-control" className={cn("flex-1 aria-invalid:pe-3", className)} {...props} />
}

function InputGroupTextarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return <TextareaControl data-slot="input-group-control" className={cn("flex-1 resize-none py-3 aria-invalid:pe-3", className)} {...props} />
}

export { InputGroup, InputGroupAddon, InputGroupButton, InputGroupText, InputGroupInput, InputGroupTextarea }
