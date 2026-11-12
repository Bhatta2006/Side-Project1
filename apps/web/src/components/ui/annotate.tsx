"use client"

import * as React from "react"

import { Circled } from "@/components/ui/circled"
import { Highlight } from "@/components/ui/highlight"
import { Scribble } from "@/components/ui/scribble"
import { Strike } from "@/components/ui/strike"
import { Underline } from "@/components/ui/underline"
import type { HighlightTone, MarkPen, MarkWeight } from "@/lib/ink/recipes/text-marks-ink"
import type { UnderlineKind } from "@/lib/ink/recipes/underline-ink"

export type AnnotateType = "underline" | "box" | "circle" | "highlight" | "strike-through" | "crossed-off" | "brackets" | "scribble"

type Common = {
  type: AnnotateType
  color?: HighlightTone | MarkPen
  weight?: MarkWeight
  kind?: UnderlineKind
  show?: boolean
  animate?: boolean
  delay?: number
  seed?: string | number
  className?: string
  children?: React.ReactNode
}

const HIGHLIGHTS: readonly string[] = ["yellow", "pink", "green", "blue", "orange", "lilac", "teal"]
const PENS: readonly string[] = ["ink", "blue", "red", "green", "pencil", "marker", "orange"]

function Annotate({ type, color, weight, kind, ...props }: Common & Omit<React.ComponentProps<"span">, keyof Common | "color">) {
  const pen: MarkPen | undefined = color && PENS.includes(color) ? (color as MarkPen) : undefined
  const tone: HighlightTone | undefined = color && HIGHLIGHTS.includes(color) ? (color as HighlightTone) : undefined
  switch (type) {
    case "highlight":
      return <Highlight data-annotate={type} tone={tone} weight={weight === "fine" ? "light" : weight === "brush" ? "heavy" : undefined} {...(props as React.ComponentProps<"mark">)} />
    case "underline":
      return <Underline data-annotate={type} kind={kind} tone={pen} weight={weight} {...props} />
    case "circle":
      return <Circled data-annotate={type} shape="circle" tone={pen} weight={weight} {...props} />
    case "box":
      return <Circled data-annotate={type} shape="box" tone={pen} weight={weight} {...props} />
    case "brackets":
      return <Circled data-annotate={type} shape="brackets" tone={pen} weight={weight} {...props} />
    case "strike-through":
      return <Strike data-annotate={type} kind="single" tone={pen} weight={weight} {...(props as React.ComponentProps<"s">)} />
    case "crossed-off":
      return <Strike data-annotate={type} kind="cross" tone={pen} weight={weight} {...(props as React.ComponentProps<"s">)} />
    case "scribble":
      return <Scribble data-annotate={type} tone={pen} weight={weight} {...props} />
    default:
      return <span {...props} />
  }
}

export { Annotate }
