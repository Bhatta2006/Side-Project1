"use client"

import * as React from "react"

import { Paper, type PaperProps } from "@/components/ui/paper"
import { usePaperDecor } from "@/hooks/use-paper-object"
import { stickyNoteRecipe } from "@/lib/ink/recipes/sticky-note-ink"
import { REVEAL_DASH, REVEAL_WHEN_CHECKED } from "@/lib/ink/recipes/draw-on-ink"
import { cn } from "@/lib/utils"

type StickyColor = "yellow" | "green" | "orange" | "pink" | "blue"

type StickyNoteProps = Omit<PaperProps, "stock"> & {
  color?: StickyColor
  done?: boolean
  onDoneChange?: (done: boolean) => void
  doneLabel?: string
}

function StickyNote({ className, children, ref, color = "yellow", done, onDoneChange, doneLabel = "Done", seed, tilt, size, style, ...props }: StickyNoteProps) {
  const tickable = done !== undefined
  const o = usePaperDecor({ recipe: stickyNoteRecipe, params: {}, kind: "sticky", ref, seed, tilt, tiltMax: 1.6, size, enabled: tickable })
  const el = React.useRef<HTMLElement | null>(null)
  const seen = React.useRef(done)
  React.useEffect(() => {
    if (seen.current === done) return
    seen.current = done
    el.current?.setAttribute("data-touched", "")
  }, [done])
  const setRef = React.useCallback(
    (node: HTMLElement | null) => {
      el.current = node
      return (o.paper.ref as React.RefCallback<HTMLElement>)(node)
    },
    [o.paper.ref],
  )
  return (
    <Paper
      data-slot="sticky-note"
      data-color={color}
      data-state={tickable ? (done ? "checked" : "unchecked") : undefined}
      stock={`sticky-${color}`}
      size={size}
      {...o.paper}
      ref={setRef}
      {...props}
      className={cn(
        o.paper.className,
        "flex min-h-40 w-44 flex-col gap-1 px-4 pt-6 pb-4 font-script text-[1.35rem] leading-[1.15] text-ink break-words",
        tickable && ["pt-8", REVEAL_DASH, REVEAL_WHEN_CHECKED, "data-[state=checked]:[&_[data-slot=sticky-note-content]]:line-through data-[state=checked]:[&_[data-slot=sticky-note-content]]:decoration-1"],
        className,
      )}
      style={{ ...o.paper.style, ...style }}
    >
      {o.decor}
      {tickable && onDoneChange ? (
        <button
          type="button"
          role="checkbox"
          aria-checked={!!done}
          aria-label={doneLabel}
          data-slot="sticky-note-check"
          onClick={() => onDoneChange(!done)}
          className="absolute end-[3.5px] top-[2.5px] z-(--ll-z-prop) size-8 cursor-pointer rounded-full hover:bg-ink/10"
        />
      ) : tickable && done ? (
        <span className="sr-only">{doneLabel}. </span>
      ) : null}
      {children}
    </Paper>
  )
}

function StickyNoteTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="sticky-note-title" className={cn("text-[1.7rem] leading-none font-bold", className)} {...props} />
}

function StickyNoteContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="sticky-note-content" className={cn("flex-1", className)} {...props} />
}

function StickyNoteFooter({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="sticky-note-footer" className={cn("mt-auto pt-2 font-hand text-sm text-ink-soft", className)} {...props} />
}

export { StickyNote, StickyNoteTitle, StickyNoteContent, StickyNoteFooter }
export type { StickyNoteProps, StickyColor }
