"use client"

import * as React from "react"
import { createPortal } from "react-dom"
import { Toaster as Sonner, toast, useSonner, type ToasterProps } from "sonner"

import { Icon } from "@/components/ui/icon"
import { useInkScope } from "@/lib/ink/react"
import { cn } from "@/lib/utils"

type ToastClassNames = NonNullable<NonNullable<ToasterProps["toastOptions"]>["classNames"]>

type LooseleafToasterProps = ToasterProps & {
  decoration?: "none" | "tape" | "pin"
  portal?: boolean
}

const SLIP = cn(
  "ll-paper ll-tooth-fine ll-stock-slip ll-sheet-slip pointer-events-auto flex w-(--width) items-center gap-3 p-4 font-hand text-[15px] text-foreground compact:p-3.5 calm:p-3",
  "data-[type=success]:ll-stock-check data-[type=success]:ll-sheet-check data-[type=success]:[--ll-tilt:-0.5deg]",
  "data-[type=error]:ll-stock-sticky-pink data-[type=error]:ll-sheet-sticky data-[type=error]:[--ll-tilt:0.9deg]",
  "data-[type=warning]:ll-stock-sticky-yellow data-[type=warning]:ll-sheet-sticky data-[type=warning]:[--ll-tilt:-0.8deg]",
  "data-[type=info]:ll-stock-sticky-blue data-[type=info]:ll-sheet-sticky data-[type=info]:[--ll-tilt:0.6deg]",
  "data-[type=loading]:[--ll-tilt:0.35deg] data-[type=default]:[--ll-tilt:-0.3deg]",
  "[&[data-expanded=false][data-front=false]>*]:opacity-0",
  "data-[x-position=right]:animate-[ll-toss_var(--ll-dur-toss)_var(--ll-ease-settle)_backwards] data-[x-position=left]:animate-[ll-drop_var(--ll-dur-drop)_var(--ll-ease-settle)_backwards] data-[x-position=center]:animate-[ll-drop_var(--ll-dur-drop)_var(--ll-ease-settle)_backwards]"
)

const TAPE =
  "after:pointer-events-none after:absolute after:-top-3 after:left-1/2 after:h-4.5 after:w-14 after:-translate-x-1/2 after:-rotate-3 after:border-y after:border-tape-edge after:bg-[color-mix(in_srgb,var(--ll-kraft)_70%,transparent)] after:[background-image:linear-gradient(90deg,transparent_29%,var(--ll-tape-edge)_29%_30%,transparent_30%_69%,var(--ll-tape-edge)_69%_70%,transparent_70%)] after:content-[''] after:[clip-path:polygon(0_0,100%_0,96%_20%,100%_40%,96%_60%,100%_80%,96%_100%,0_100%,4%_80%,0_60%,4%_40%,0_20%)] calm:after:hidden"
const PIN =
  "after:pointer-events-none after:absolute after:-top-2 after:left-1/2 after:size-3.5 after:-translate-x-1/2 after:rounded-full after:bg-tomato after:content-[''] after:[background-image:radial-gradient(circle_at_34%_30%,var(--ll-photo)_0_13%,transparent_15%),radial-gradient(circle_at_66%_70%,rgb(var(--ll-shade)/0.32),transparent_60%)] after:shadow-[0_2px_2px_rgb(var(--ll-shade)/0.35)] calm:after:hidden"

const BASE: ToastClassNames = {
  toast: SLIP,
  content: "flex min-w-0 flex-1 flex-col gap-0.5",
  title: "text-[15px] leading-snug font-bold",
  description: "text-sm leading-snug text-muted-foreground",
  icon: "relative flex size-5 shrink-0 items-center justify-center text-ink",
  loader: "text-ink",
  actionButton:
    "ll-swipe ms-auto min-h-6 shrink-0 cursor-pointer px-2.5 py-0.5 text-sm font-bold whitespace-nowrap transition-[translate] duration-(--ll-dur-press) active:translate-y-(--ll-press-sink)",
  cancelButton: "ms-auto min-h-6 shrink-0 cursor-pointer px-2 py-0.5 text-sm whitespace-nowrap text-ink-muted underline decoration-wavy underline-offset-4 hover:text-foreground",
  closeButton:
    "absolute end-1.5 top-1.5 z-(--ll-z-raised) grid size-6 cursor-pointer place-items-center text-ink hover:ll-swipe",
}

function Toaster({ className, toastOptions, decoration = "none", theme = "light", icons, style, portal = false, ...props }: LooseleafToasterProps) {
  const scope = useInkScope()
  const [mounted, setMounted] = React.useState(false)
  React.useEffect(() => {
    if (portal) setMounted(true)
  }, [portal])
  const user = toastOptions?.classNames ?? {}
  const merged = Object.fromEntries(
    (Object.keys({ ...BASE, ...user }) as Array<keyof ToastClassNames>).map((k) => [k, cn(BASE[k], k === "content" && decoration !== "none" && (decoration === "tape" ? TAPE : PIN), user[k])])
  ) as ToastClassNames
  const stack = (
    // lint-house-disable-next-line data-slot
    <Sonner
      theme={theme}
      className={cn("toaster group pointer-events-auto", className)}
      icons={{
        success: <Icon name="circle-check" size={20} />,
        info: <Icon name="info" size={20} />,
        warning: <Icon name="triangle-alert" size={20} />,
        error: <Icon name="octagon-x" size={20} />,
        loading: <Icon name="loader-circle" size={20} className="animate-spin" />,
        close: <Icon name="x" size={14} />,
        ...icons,
      }}
      style={{ zIndex: "var(--ll-z-toast)", "--width": "min(360px, calc(100vw - 32px))", ...style } as React.CSSProperties}
      toastOptions={{ unstyled: true, ...toastOptions, classNames: merged }}
      {...props}
    />
  )
  if (!portal) return stack
  return mounted ? createPortal(<div data-slot="toaster-portal" {...scope} className="contents">{stack}</div>, document.body) : null
}

export { Toaster, toast, useSonner }
export type { LooseleafToasterProps as ToasterProps }
