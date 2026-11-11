"use client"

import * as React from "react"
import { createPortal } from "react-dom"
import { Command as CommandPrimitive, useCommandState } from "cmdk"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Icon } from "@/components/ui/icon"
import { Kbd } from "@/components/ui/kbd"
import { Mascot } from "@/components/ui/mascot"
import { Paper, type PaperProps } from "@/components/ui/paper"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { commandInputRecipe } from "@/lib/ink/recipes/command-ink"
import { cn } from "@/lib/utils"

type CommandSheet = Pick<PaperProps, "stock" | "edge" | "tilt" | "tape" | "tapeKind" | "shadow" | "seed">

const NESTED =
  "[[data-slot=popover-content]_&]:before:hidden [[data-slot=dialog-content]_&]:before:hidden [[data-slot=sheet-content]_&]:before:hidden [[data-slot=drawer-content]_&]:before:hidden [[data-slot=hover-card-content]_&]:before:hidden [[data-slot=select-content]_&]:before:hidden [[data-slot=card]_&]:before:hidden [[data-slot=dropdown-menu-content]_&]:before:hidden [[data-slot=dropdown-menu-sub-content]_&]:before:hidden [[data-slot=context-menu-content]_&]:before:hidden [[data-slot=context-menu-sub-content]_&]:before:hidden [[data-slot=menubar-content]_&]:before:hidden [[data-slot=menubar-sub-content]_&]:before:hidden"

function Command({
  className,
  sheet = true,
  children,
  ...props
}: React.ComponentProps<typeof CommandPrimitive> & {
  sheet?: boolean | CommandSheet
}) {
  const paper: CommandSheet = typeof sheet === "object" ? sheet : {}
  return (
    <CommandPrimitive data-slot="command" className={cn("flex h-full w-full flex-col text-popover-foreground", className)} {...props}>
      {sheet ? (
        <Paper data-slot="command-sheet" stock="slip" edge="cut" tilt={false} rules="none" shadow="lift" {...paper} className={cn("flex h-full w-full flex-col", NESTED)}>
          {children}
        </Paper>
      ) : (
        children
      )}
    </CommandPrimitive>
  )
}

function CommandDialog({
  title = "Command Palette",
  description = "Search for a command to run...",
  children,
  className,
  showCloseButton = false,
  stock = "napkin",
  edge,
  tape,
  tilt,
  seed,
  commandProps,
  ...props
}: React.ComponentProps<typeof Dialog> &
  Pick<PaperProps, "stock" | "edge" | "tape" | "tilt" | "seed"> & {
    title?: string
    description?: string
    className?: string
    showCloseButton?: boolean
    commandProps?: Omit<React.ComponentProps<typeof Command>, "children">
  }) {
  const opener = React.useRef<Element | null>(null)
  return (
    <Dialog {...props}>
      <DialogContent
        stock={stock}
        edge={edge}
        tape={tape}
        tilt={tilt}
        seed={seed}
        showCloseButton={showCloseButton}
        onOpenAutoFocus={() => {
          opener.current = document.activeElement
        }}
        onCloseAutoFocus={() => {
          const el = opener.current
          opener.current = null
          const active = document.activeElement
          const moved = active !== null && active !== document.body && active !== el
          if (!moved && el instanceof HTMLElement && el !== document.body && el.isConnected) el.focus({ preventScroll: true })
        }}
        className={cn("mt-[12dvh] mb-auto max-w-lg gap-0 p-3 max-sm:mt-2 compact:p-2.5 calm:p-2", className)}
      >
        <DialogHeader className="sr-only">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <Command sheet={false} {...commandProps}>
          {children}
        </Command>
      </DialogContent>
    </Dialog>
  )
}

const defaultResultsLabel = (count: number): string => (count === 0 ? "No results" : count === 1 ? "1 result" : `${count} results`)

function ResultsAnnouncer({ label }: { label: (count: number) => string }) {
  const search = useCommandState((s) => s.search) as string
  const count = useCommandState((s) => s.filtered.count) as number
  return (
    <span role="status" aria-live="polite" className="sr-only">
      {search ? label(count) : ""}
    </span>
  )
}

function useFreshActiveDescendant(input: React.RefObject<HTMLInputElement | null>) {
  const search = useCommandState((s) => s.search) as string
  const value = useCommandState((s) => s.value) as string
  const count = useCommandState((s) => s.filtered.count) as number
  const recorded = useCommandState((s) => s.selectedItemId) as string | undefined
  React.useLayoutEffect(() => {
    const el = input.current
    if (!el) return
    const list = el.ownerDocument.getElementById(el.getAttribute("aria-controls") ?? "")
    const row = list?.querySelector<HTMLElement>('[cmdk-item][aria-selected="true"]')
    if (row?.id) {
      if (el.getAttribute("aria-activedescendant") !== row.id) el.setAttribute("aria-activedescendant", row.id)
    } else el.removeAttribute("aria-activedescendant")
  }, [input, search, value, count, recorded])
}

function ActiveDescendant({ input }: { input: React.RefObject<HTMLInputElement | null> }) {
  useFreshActiveDescendant(input)
  return null
}

function CommandInput({
  className,
  wrapperClassName,
  seed,
  resultsLabel = defaultResultsLabel,
  ref,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Input> & { wrapperClassName?: string; seed?: string | number; resultsLabel?: (count: number) => string }) {
  const { hostRef, hostProps, node } = useInk({ recipe: commandInputRecipe, params: {}, kind: "rule", seed, still: true })
  const inputRef = React.useRef<HTMLInputElement | null>(null)
  return (
    <div
      data-slot="command-input-wrapper"
      data-ink-focus="within"
      ref={hostRef}
      {...hostProps}
      className={cn("relative isolate flex h-12 items-center gap-2 px-3 text-(--ll-input-ink) compact:h-10 calm:h-9", wrapperClassName)}
    >
      {node}
      <Icon name="search" size={18} className="shrink-0 text-ink-soft" />
      <CommandPrimitive.Input
        data-slot="command-input"
        ref={useMergedRef<HTMLInputElement>(inputRef, ref)}
        className={cn(
          "flex h-10 w-full bg-transparent py-3 font-hand text-base caret-(--ll-caret) outline-hidden placeholder:text-(--ll-placeholder) disabled:cursor-not-allowed disabled:text-pencil-text calm:text-[15px]",
          className
        )}
        {...props}
      />
      <ActiveDescendant input={inputRef} />
      <ResultsAnnouncer label={resultsLabel} />
    </div>
  )
}

const StatusSlotContext = React.createContext<HTMLElement | null>(null)

function CommandList({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.List>) {
  const [slot, setSlot] = React.useState<HTMLElement | null>(null)
  return (
    <StatusSlotContext.Provider value={slot}>
      <CommandPrimitive.List
        data-slot="command-list"
        className={cn("max-h-[300px] scroll-py-1 overflow-x-hidden overflow-y-auto overscroll-contain p-1 [scrollbar-width:thin]", className)}
        {...props}
      />
      <div data-slot="command-status" ref={setSlot} />
    </StatusSlotContext.Provider>
  )
}

function CommandEmpty({ className, children, mascot = true, ...props }: React.ComponentProps<typeof CommandPrimitive.Empty> & { mascot?: boolean }) {
  const slot = React.useContext(StatusSlotContext)
  const node = (
    <CommandPrimitive.Empty data-slot="command-empty" className={cn("grid justify-items-center gap-1 px-4 py-5 text-center font-script text-xl leading-tight text-ink-muted", className)} {...props}>
      {mascot && <Mascot pose="search" size={64} />}
      <span>{children}</span>
    </CommandPrimitive.Empty>
  )
  return slot ? createPortal(node, slot) : node
}

function CommandLoading({ className, children, ...props }: React.ComponentProps<typeof CommandPrimitive.Loading>) {
  const slot = React.useContext(StatusSlotContext)
  const node = (
    <CommandPrimitive.Loading data-slot="command-loading" className={cn("flex items-center justify-center gap-2 px-4 py-4 font-hand text-sm text-ink-muted", className)} {...props}>
      <Spinner variant="loops" size={14} />
      <span>{children}</span>
    </CommandPrimitive.Loading>
  )
  return slot ? createPortal(node, slot) : node
}

function CommandGroup({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Group>) {
  return (
    <CommandPrimitive.Group
      data-slot="command-group"
      className={cn(
        "p-1 text-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:font-type [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-ink-muted",
        className
      )}
      {...props}
    />
  )
}

function CommandSeparator({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Separator>) {
  return (
    <CommandPrimitive.Separator asChild {...props}>
      <Separator role="none" data-slot="command-separator" className={cn("pointer-events-none -mx-1 my-1 w-auto", className)} />
    </CommandPrimitive.Separator>
  )
}

function CommandItem({ className, ...props }: React.ComponentProps<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      data-slot="command-item"
      className={cn(
        "relative flex min-h-9 cursor-default items-center gap-2 px-2 py-1.5 font-hand text-base outline-hidden select-none compact:min-h-8 calm:min-h-7 calm:py-1 calm:text-[15px]",
        "data-[selected=true]:ll-swipe data-[disabled=true]:pointer-events-none data-[disabled=true]:text-pencil-text",
        "forced-colors:data-[selected=true]:bg-[color:Highlight]! forced-colors:data-[selected=true]:text-[color:HighlightText]! forced-colors:data-[selected=true]:[&_svg]:text-[color:HighlightText]!",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not(.absolute):not([class*='size-'])]:size-4 [&_svg:not(.absolute):not([class*='text-'])]:text-ink-soft",
        className
      )}
      {...props}
    />
  )
}

function CommandShortcut({ className, children, ...props }: React.ComponentProps<"span">) {
  return (
    <span data-slot="command-shortcut" className={cn("ms-auto inline-flex items-center gap-1 text-xs text-muted-foreground", className)} {...props}>
      {typeof children === "string" ? <Kbd>{children}</Kbd> : children}
    </span>
  )
}

export { Command, CommandDialog, CommandInput, CommandList, CommandEmpty, CommandLoading, CommandGroup, CommandItem, CommandShortcut, CommandSeparator, useCommandState, useFreshActiveDescendant }
