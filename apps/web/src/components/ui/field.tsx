"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { fieldErrorRecipe } from "@/lib/ink/recipes/field-error-ink"
import { fieldChoiceRecipe } from "@/lib/ink/recipes/field-ink"
import { cn } from "@/lib/utils"

function FieldSet({ className, ...props }: React.ComponentProps<"fieldset">) {
  return (
    <fieldset
      data-slot="field-set"
      className={cn(
        "flex flex-col gap-6 calm:gap-4",
        "has-[>[data-slot=checkbox-group]]:gap-3 has-[>[data-slot=radio-group]]:gap-3",
        className
      )}
      {...props}
    />
  )
}

function FieldLegend({ className, variant = "legend", ...props }: React.ComponentProps<"legend"> & { variant?: "legend" | "label" }) {
  return (
    <legend
      data-slot="field-legend"
      data-variant={variant}
      className={cn(
        "mb-3 font-bold",
        "data-[variant=legend]:font-script data-[variant=legend]:text-[1.6rem] data-[variant=legend]:leading-none",
        "data-[variant=label]:font-hand data-[variant=label]:text-[15px]",
        className
      )}
      {...props}
    />
  )
}

function FieldGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-group"
      className={cn(
        "group/field-group @container/field-group flex w-full flex-col gap-7 calm:gap-5 data-[slot=checkbox-group]:gap-3 [&>[data-slot=field-group]]:gap-4",
        className
      )}
      {...props}
    />
  )
}

const fieldVariants = cva("group/field flex w-full gap-3 data-[invalid=true]:text-destructive", {
  variants: {
    orientation: {
      vertical: ["flex-col [&>*:not([data-slot=toggle-group])]:w-full [&>.sr-only]:w-auto"],
      horizontal: [
        "flex-row items-center",
        "[&>[data-slot=field-label]]:flex-auto",
        "has-[>[data-slot=field-content]]:items-start has-[>[data-slot=field-content]]:[&>[role=checkbox],[role=radio]]:mt-px",
      ],
      responsive: [
        "flex-col @md/field-group:flex-row @md/field-group:items-center [&>*:not([data-slot=toggle-group])]:w-full @md/field-group:[&>*:not([data-slot=toggle-group])]:w-auto [&>.sr-only]:w-auto",
        "@md/field-group:[&>[data-slot=field-label]]:flex-auto",
        "@md/field-group:has-[>[data-slot=field-content]]:items-start @md/field-group:has-[>[data-slot=field-content]]:[&>[role=checkbox],[role=radio]]:mt-px",
      ],
    },
  },
  defaultVariants: {
    orientation: "vertical",
  },
})

function Field({ className, orientation = "vertical", ...props }: React.ComponentProps<"div"> & VariantProps<typeof fieldVariants>) {
  return <div role="group" data-slot="field" data-orientation={orientation} className={cn(fieldVariants({ orientation }), className)} {...props} />
}

function FieldContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="field-content" className={cn("group/field-content flex flex-1 flex-col gap-1.5 leading-snug", className)} {...props} />
}

function FieldLabel({
  className,
  children,
  card,
  seed,
  ref,
  ...props
}: React.ComponentProps<typeof Label> & {
  card?: boolean
}) {
  const isCard = card ?? React.Children.toArray(children).some((c) => React.isValidElement(c) && c.type === Field)
  const content = React.Children.map(children, (c) => (React.isValidElement<{ role?: string }>(c) && c.type === Field ? React.cloneElement(c, { role: c.props.role ?? "none" }) : c))
  const { hostRef, hostProps, node } = useInk({ recipe: fieldChoiceRecipe, params: {}, kind: "card", seed, still: true })
  return (
    <Label
      data-slot="field-label"
      ref={useMergedRef<HTMLLabelElement>(isCard ? hostRef : undefined, ref as React.Ref<HTMLLabelElement> | undefined)}
      {...(isCard ? hostProps : {})}
      className={cn(
        "group/field-label peer/field-label flex w-fit gap-2 leading-snug group-data-[disabled=true]/field:text-pencil-text",
        "has-[>[data-slot=field]]:w-full has-[>[data-slot=field]]:flex-col has-[>[data-slot=field]]:outline-hidden [&>*]:data-[slot=field]:p-4",
        "has-data-[state=checked]:[&>svg>[data-layer=checked]]:visible has-data-[state=checked]:[&>svg>[data-layer=checked]]:scale-100 has-data-[state=checked]:[&>svg>[data-layer=checked]]:rotate-0 has-data-[state=checked]:[&>svg>[data-layer=checked]]:opacity-100",
        isCard && "cursor-pointer forced-colors:has-data-[state=checked]:bg-[Highlight] forced-colors:has-data-[state=checked]:text-[HighlightText]",
        className
      )}
      {...props}
    >
      {isCard ? node : null}
      {content}
    </Label>
  )
}

function FieldTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-label"
      className={cn("flex w-fit items-center gap-2 font-hand text-[15px] leading-snug font-bold group-data-[disabled=true]/field:text-pencil-text", className)}
      {...props}
    />
  )
}

function FieldDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="field-description"
      className={cn(
        "text-sm leading-normal font-normal text-muted-foreground group-has-[[data-orientation=horizontal]]/field:text-balance",
        "last:mt-0 nth-last-2:-mt-1 [[data-variant=legend]+&]:-mt-1.5",
        "[&>a]:text-link [&>a]:underline [&>a]:underline-offset-4 [&>a:hover]:text-link-hover",
        className
      )}
      {...props}
    />
  )
}

function FieldSeparator({ children, className, ...props }: React.ComponentProps<"div"> & { children?: React.ReactNode }) {
  return (
    <div data-slot="field-separator" data-content={!!children} className={cn("relative -my-2 flex h-5 items-center text-sm group-data-[variant=outline]/field-group:-mb-2", className)} {...props}>
      {children ? <Separator data-slot="field-separator-content">{children}</Separator> : <Separator />}
    </div>
  )
}

function FieldError({
  className,
  children,
  errors,
  seed,
  ref,
  ...props
}: React.ComponentProps<"div"> & {
  errors?: Array<{ message?: string } | undefined>
  seed?: string | number
}) {
  const content = React.useMemo(() => {
    if (children) {
      return children
    }

    if (!errors?.length) {
      return null
    }

    const uniqueErrors = [...new Map(errors.map((error) => [error?.message, error])).values()]

    if (uniqueErrors?.length == 1) {
      return uniqueErrors[0]?.message
    }

    return (
      <ul className="ms-4 flex list-disc flex-col gap-1">
        {uniqueErrors.map((error, index) => error?.message && <li key={index}>{error.message}</li>)}
      </ul>
    )
  }, [children, errors])
  const { hostRef, hostProps, node } = useInk({ recipe: fieldErrorRecipe, params: {}, kind: "underline", seed, still: true })
  const mergedRef = useMergedRef<HTMLDivElement>(hostRef, ref)

  if (!content) {
    return null
  }

  return (
    <div
      role="alert"
      data-slot="field-error"
      ref={mergedRef}
      {...hostProps}
      className={cn("relative isolate w-fit max-w-full pb-1 text-sm font-normal text-destructive outline-hidden forced-colors:underline forced-colors:decoration-wavy", className)}
      {...props}
    >
      {node}
      {content}
    </div>
  )
}

export { Field, FieldLabel, FieldDescription, FieldError, FieldGroup, FieldLegend, FieldSeparator, FieldSet, FieldContent, FieldTitle }
