"use client"

import * as React from "react"
import { Avatar as AvatarPrimitive } from "radix-ui"

import { useInk, useMergedRef } from "@/lib/ink/react"
import {
  avatarBadgeRecipe,
  avatarCountRecipe,
  avatarFallbackRecipe,
  avatarRingRecipe,
  avatarTone,
  initials,
  type AvatarRing,
  type AvatarStatus,
  type AvatarTone,
} from "@/lib/ink/recipes/avatar-ink"
import { cn } from "@/lib/utils"

const CUT = "shadow-[0_0_0_2px_var(--ll-avatar-ring,transparent)]"

function Avatar({
  className,
  size = "default",
  ring = "ink",
  seed,
  ref,
  children,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Root> & {
  size?: "default" | "sm" | "lg" | "xl"
  ring?: AvatarRing | "none"
  seed?: string | number
}) {
  const { hostRef, hostProps, node } = useInk({ recipe: avatarRingRecipe, params: { ring: ring === "none" ? "ink" : ring }, kind: "avatar", seed, still: true })
  const drawn = ring !== "none"
  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      data-size={size}
      ref={useMergedRef<HTMLSpanElement>(drawn ? hostRef : undefined, ref)}
      {...(drawn && node ? hostProps : {})}
      className={cn(
        "group/avatar relative isolate flex size-8 shrink-0 rounded-full select-none data-[size=lg]:size-10 data-[size=sm]:size-6 data-[size=xl]:size-14 forced-colors:outline-0!",
        CUT,
        className
      )}
      {...props}
    >
      {drawn ? node : null}
      {children}
    </AvatarPrimitive.Root>
  )
}

function AvatarImage({ className, ...props }: React.ComponentProps<typeof AvatarPrimitive.Image>) {
  return <AvatarPrimitive.Image data-slot="avatar-image" className={cn("aspect-square size-full rounded-full object-cover", className)} {...props} />
}

function AvatarFallback({
  className,
  name,
  tone,
  seed,
  children,
  ref,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Fallback> & {
  name?: string
  tone?: AvatarTone
  seed?: string | number
}) {
  const basis = name ?? (typeof children === "string" ? children : "")
  const t = tone ?? avatarTone(basis)
  const { hostRef, hostProps, node } = useInk({ recipe: avatarFallbackRecipe, params: { tone: t }, kind: "disc", seed: seed ?? (basis || undefined), still: true })
  return (
    <AvatarPrimitive.Fallback
      data-slot="avatar-fallback"
      data-tone={t}
      ref={useMergedRef<HTMLSpanElement>(hostRef, ref)}
      {...(node ? hostProps : {})}
      className={cn(
        "relative isolate flex size-full items-center justify-center rounded-full font-hand text-sm font-bold text-ink forced-colors:outline-0! group-data-[size=sm]/avatar:text-xs group-data-[size=lg]/avatar:text-base group-data-[size=xl]/avatar:text-xl",
        className
      )}
      {...props}
    >
      {node}
      {name && children === undefined ? (
        <>
          <span aria-hidden="true">{initials(name)}</span>
          <span className="sr-only">{name}</span>
        </>
      ) : (
        children
      )}
    </AvatarPrimitive.Fallback>
  )
}

function AvatarBadge({
  className,
  status = "marker",
  seed,
  ref,
  children,
  ...props
}: React.ComponentProps<"span"> & {
  status?: AvatarStatus
  seed?: string | number
}) {
  const { hostRef, hostProps, node } = useInk({ recipe: avatarBadgeRecipe, params: { status }, kind: "dot", seed, still: true })
  return (
    <span
      data-slot="avatar-badge"
      data-status={status}
      ref={useMergedRef<HTMLSpanElement>(hostRef, ref)}
      {...(node ? hostProps : {})}
      className={cn(
        "absolute end-0 bottom-0 z-10 isolate inline-flex items-center justify-center rounded-full text-ink select-none forced-colors:outline-0!",
        "group-data-[size=sm]/avatar:size-2 group-data-[size=sm]/avatar:[&>svg]:hidden",
        "group-data-[size=default]/avatar:size-2.5 group-data-[size=default]/avatar:[&>svg:not(.absolute)]:size-2",
        "group-data-[size=lg]/avatar:size-3 group-data-[size=lg]/avatar:[&>svg:not(.absolute)]:size-2",
        "group-data-[size=xl]/avatar:size-3.5 group-data-[size=xl]/avatar:[&>svg:not(.absolute)]:size-2.5",
        className
      )}
      {...props}
    >
      {node}
      {children}
    </span>
  )
}

function AvatarGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="avatar-group"
      className={cn(
        "group/avatar-group flex items-center *:data-[slot=avatar]:[--ll-avatar-ring:var(--ll-avatar-group-ring,var(--card))] [&>*+*]:-ms-1.5 has-data-[size=sm]:[&>*+*]:-ms-1 has-data-[size=lg]:[&>*+*]:-ms-2 has-data-[size=xl]:[&>*+*]:-ms-3.5",
        className
      )}
      {...props}
    />
  )
}

function AvatarGroupCount({ className, seed, ref, children, ...props }: React.ComponentProps<"div"> & { seed?: string | number }) {
  const { hostRef, hostProps, node } = useInk({ recipe: avatarCountRecipe, params: {}, kind: "disc", seed, still: true })
  return (
    <div
      data-slot="avatar-group-count"
      ref={useMergedRef<HTMLDivElement>(hostRef, ref)}
      {...(node ? hostProps : {})}
      className={cn(
        "relative isolate flex size-8 shrink-0 items-center justify-center rounded-full font-hand text-sm font-bold text-ink-soft [--ll-avatar-ring:var(--ll-avatar-group-ring,var(--card))] forced-colors:outline-0!",
        CUT,
        "group-has-data-[size=lg]/avatar-group:size-10 group-has-data-[size=sm]/avatar-group:size-6 group-has-data-[size=xl]/avatar-group:size-14 group-has-data-[size=sm]/avatar-group:text-xs [&>svg:not(.absolute)]:size-4 group-has-data-[size=lg]/avatar-group:[&>svg:not(.absolute)]:size-5 group-has-data-[size=sm]/avatar-group:[&>svg:not(.absolute)]:size-3",
        className
      )}
      {...props}
    >
      {node}
      {children}
    </div>
  )
}

export { Avatar, AvatarImage, AvatarFallback, AvatarBadge, AvatarGroup, AvatarGroupCount }
