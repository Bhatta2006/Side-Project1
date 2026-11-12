"use client"

import * as React from "react"

import { useInkContext } from "@/lib/ink/react"

export function motionIsOff(el?: Element | null, providerReduced = false): boolean {
  if (providerReduced) return true
  if (typeof window === "undefined") return false
  const node = el ?? document.documentElement
  if (node.closest?.('[data-motion="reduced"]')) return true
  if (window.getComputedStyle(node).getPropertyValue("--ll-motion").trim() === "0") return true
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false
}

export function useReducedMotion(ref?: React.RefObject<Element | null>): boolean {
  const provider = useInkContext().motion === "reduced"
  const [off, setOff] = React.useState(false)
  React.useLayoutEffect(() => {
    const check = () => setOff(motionIsOff(ref?.current, provider))
    check()
    const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)")
    mq?.addEventListener?.("change", check)
    const mo = new MutationObserver(check)
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-motion"] })
    return () => {
      mq?.removeEventListener?.("change", check)
      mo.disconnect()
    }
  }, [ref, provider])
  return off
}
