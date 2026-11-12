"use client"

import * as React from "react"

import { Icon } from "@/components/ui/icon"
import { useInk, useMergedRef } from "@/lib/ink/react"
import { stepperRecipe, stepperTallyRecipe, tallyWidth, TALLY_H } from "@/lib/ink/recipes/stepper-ink"
import { cn } from "@/lib/utils"

type Direction = 1 | -1

interface StepperContextValue {
  value: number | undefined
  min?: number
  max?: number
  step: number
  disabled: boolean
  readOnly: boolean
  invalid: boolean
  atMin: boolean
  atMax: boolean
  holding: 0 | Direction
  motion: { dir: Direction; n: number } | null
  format: (n: number) => string
  commitText: (text: string) => boolean
  adjust: (delta: number) => void
  jump: (to: number | undefined) => void
  startHold: (dir: Direction) => void
  stopHold: () => void
  largeStep: number
  wheel: boolean
  hiddenName: string | undefined
  inputProps: { id?: string; name?: string; form?: string; required?: boolean; "aria-label"?: string; "aria-labelledby"?: string; "aria-describedby"?: string }
  inputRef: React.RefObject<HTMLInputElement | null>
  reset: () => void
  nudge: () => void
}

const StepperContext = React.createContext<StepperContextValue | null>(null)

function useStepper(): StepperContextValue {
  const ctx = React.useContext(StepperContext)
  if (!ctx) throw new Error("Stepper parts must be used inside <Stepper>")
  return ctx
}

const decimals = (n: number | undefined): number => {
  if (n === undefined || !Number.isFinite(n)) return 0
  const s = String(n)
  if (s.includes("e-")) return Number(s.split("e-")[1])
  const i = s.indexOf(".")
  return i < 0 ? 0 : s.length - i - 1
}

function parseNumber(text: string): number | undefined {
  const t = text
    .trim()
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x660))
    .replace(/[\u06f0-\u06f9]/g, (d) => String(d.charCodeAt(0) - 0x6f0))
    .replace(/\u066b/g, ".")
    .replace(/\u066c/g, ",")
    .replace(/[\s\u00a0\u202f']/g, "")
  const m = /^([-+\u2212]?)([\d.,]*)$/.exec(t)
  if (!m || !/\d/.test(m[2])) return undefined
  const body = m[2]
  const dots = body.split(".").length - 1
  const commas = body.split(",").length - 1
  const point = dots && commas ? (body.lastIndexOf(".") > body.lastIndexOf(",") ? "." : ",") : dots === 1 && !commas ? "." : commas === 1 && !dots ? "," : ""
  const group = point === "." ? "," : point === "," ? "." : dots > 1 ? "." : commas > 1 ? "," : ""
  const at = point ? body.lastIndexOf(point) : -1
  const whole = at < 0 ? body : body.slice(0, at)
  const frac = at < 0 ? "" : body.slice(at + 1)
  if (!(group ? new RegExp(`^(\\d{1,3}(\\${group}\\d{3})*)?$`) : /^\d*$/).test(whole) || !/^\d*$/.test(frac)) return undefined
  const n = Number(`${whole.replace(/[.,]/g, "") || "0"}${frac ? `.${frac}` : ""}`)
  return Number.isFinite(n) ? (m[1] === "-" || m[1] === "\u2212" ? -n : n) : undefined
}

const HOLD_DELAY = 420
const HOLD_EVERY = 90

interface StepperProps extends Omit<React.ComponentProps<"div">, "defaultValue" | "onChange" | "id"> {
  value?: number | undefined
  defaultValue?: number
  onValueChange?: (value: number | undefined) => void
  min?: number
  max?: number
  step?: number
  largeStep?: number
  snap?: boolean
  precision?: number
  format?: (value: number) => string
  parse?: (text: string) => number | undefined
  wheel?: boolean
  id?: string
  name?: string
  form?: string
  required?: boolean
  disabled?: boolean
  readOnly?: boolean
  invalid?: boolean
  "aria-label"?: string
  "aria-labelledby"?: string
  "aria-describedby"?: string
  seed?: string | number
}

function Stepper(props: StepperProps) {
  const {
    value: _value,
    defaultValue,
    onValueChange,
    min,
    max,
    step: stepProp = 1,
    largeStep: largeStepProp,
    snap = false,
    precision: precisionProp,
    format: formatProp,
    parse: parseProp,
    wheel = false,
    id,
    name,
    form,
    required,
    disabled = false,
    readOnly = false,
    invalid = false,
    "aria-label": ariaLabel,
    "aria-labelledby": ariaLabelledby,
    "aria-describedby": ariaDescribedby,
    seed,
    className,
    children,
    ref,
    ...rest
  } = props
  void _value
  const step = Number.isFinite(stepProp) && stepProp > 0 ? stepProp : 1
  const controlled = "value" in props
  const [inner, setInner] = React.useState<number | undefined>(defaultValue)
  const rawValue = controlled ? props.value : inner
  const value = rawValue !== undefined && Number.isFinite(rawValue) ? rawValue : undefined
  const latest = React.useRef(value)
  latest.current = value
  const [motion, setMotion] = React.useState<StepperContextValue["motion"]>(null)
  const [holding, setHolding] = React.useState<0 | Direction>(0)
  const [limit, setLimit] = React.useState(0)
  const nudge = React.useCallback(() => setLimit((n) => n + 1), [])
  const inputRef = React.useRef<HTMLInputElement | null>(null)

  const places = precisionProp ?? Math.max(decimals(step), decimals(min))
  const round = React.useCallback((n: number, from?: number) => Number(n.toFixed(Math.min(Math.max(places, decimals(from)), 12))), [places])
  const clamp = React.useCallback((n: number) => Math.min(max ?? Infinity, Math.max(min ?? -Infinity, n)), [min, max])
  const format = React.useCallback((n: number) => (formatProp ? formatProp(n) : precisionProp !== undefined ? n.toFixed(precisionProp) : String(n)), [formatProp, precisionProp])
  const parse = React.useCallback(
    (text: string): number | undefined => {
      if (parseProp) return parseProp(text)
      return parseNumber(text)
    },
    [parseProp]
  )
  const largeStep = largeStepProp ?? step * 10

  const set = React.useCallback(
    (next: number | undefined) => {
      latest.current = next
      if (!controlled) setInner(next)
      onValueChange?.(next)
    },
    [controlled, onValueChange]
  )
  const snapTo = React.useCallback(
    (n: number) => {
      if (!snap) return n
      const origin = min ?? 0
      return origin + Math.round((n - origin) / step) * step
    },
    [snap, min, step]
  )
  const adjust = React.useCallback(
    (delta: number) => {
      if (disabled || readOnly) return
      const from = latest.current
      const next = clamp(round(snapTo((from ?? 0) + delta), from))
      if (next === from) {
        if (delta !== 0) nudge()
        return
      }
      setMotion((m) => ({ dir: delta > 0 ? 1 : -1, n: (m?.n ?? 0) + 1 }))
      set(next)
    },
    [disabled, readOnly, clamp, round, snapTo, set, nudge]
  )
  const jump = React.useCallback(
    (to: number | undefined) => {
      if (disabled || readOnly || to === undefined || to === latest.current) return
      setMotion((m) => ({ dir: latest.current === undefined || to > latest.current ? 1 : -1, n: (m?.n ?? 0) + 1 }))
      set(to)
    },
    [disabled, readOnly, set]
  )
  const commitText = React.useCallback(
    (text: string): boolean => {
      if (text.trim() === "") {
        if (required) return false
        set(undefined)
        return true
      }
      const n = parse(text)
      if (n === undefined || !Number.isFinite(n)) return false
      const next = clamp(Number(snapTo(n).toPrecision(12)))
      if (next !== latest.current) set(next)
      return true
    },
    [set, parse, clamp, round, snapTo, required]
  )

  const timers = React.useRef<{ wait?: number; run?: number; count: number }>({ count: 0 })
  const stopHold = React.useCallback(() => {
    window.clearTimeout(timers.current.wait)
    window.clearInterval(timers.current.run)
    timers.current = { count: 0 }
    setHolding(0)
  }, [])
  const startHold = React.useCallback(
    (dir: Direction) => {
      stopHold()
      if (disabled || readOnly) return
      adjust(dir * step)
      setHolding(dir)
      const tickOnce = () => {
        const before = latest.current
        adjust(dir * step * (timers.current.count > 24 ? 5 : 1))
        timers.current.count++
        if (latest.current === before) stopHold()
      }
      timers.current.wait = window.setTimeout(() => {
        timers.current.run = window.setInterval(tickOnce, HOLD_EVERY)
      }, HOLD_DELAY)
    },
    [stopHold, disabled, readOnly, adjust, step]
  )
  React.useEffect(() => stopHold, [stopHold])

  const reset = React.useCallback(() => {
    if (!controlled) {
      latest.current = defaultValue
      setInner(defaultValue)
    }
  }, [controlled, defaultValue])

  const hasValue = value !== undefined
  const atMin = hasValue && min !== undefined && value <= min
  const atMax = hasValue && max !== undefined && value >= max

  const ctx = React.useMemo<StepperContextValue>(
    () => ({
      value, min, max, step, disabled, readOnly, invalid, atMin, atMax, holding, motion, format, commitText, adjust, jump, startHold, stopHold, largeStep, wheel,
      hiddenName: formatProp ? name : undefined,
      inputProps: { id, name: formatProp ? undefined : name, form, required, "aria-label": ariaLabel, "aria-labelledby": ariaLabelledby, "aria-describedby": ariaDescribedby },
      inputRef, reset, nudge,
    }),
    [value, min, max, step, disabled, readOnly, invalid, atMin, atMax, holding, motion, format, commitText, adjust, jump, startHold, stopHold, largeStep, wheel, formatProp, id, name, form, required, ariaLabel, ariaLabelledby, ariaDescribedby, reset, nudge]
  )

  const { hostRef, hostProps, node } = useInk({ recipe: stepperRecipe, params: { disabled, invalid: invalid && !disabled, plain: false }, kind: "field", seed, still: true })
  return (
    <StepperContext.Provider value={ctx}>
      <style href="ll-stepper" precedence="low">
        {STEPPER_CSS}
      </style>
      <div
        data-slot="stepper"
        role="group"
        data-ink-focus="within"
        data-disabled={disabled ? "" : undefined}
        data-invalid={invalid ? "" : undefined}
        data-limit={limit ? (limit % 2 ? "a" : "b") : undefined}
        ref={useMergedRef<HTMLDivElement>(hostRef, ref)}
        {...hostProps}
        className={cn("relative isolate inline-flex h-9 w-fit items-stretch font-hand text-base text-(--ll-input-ink) compact:h-8 calm:h-7", className)}
        {...rest}
      >
        {node}
        {children ?? (
          <>
            <StepperDecrement />
            <StepperInput />
            <StepperIncrement />
          </>
        )}
      </div>
    </StepperContext.Provider>
  )
}

const STEPPER_CSS =
  "@keyframes ll-step-shake-a{0%{rotate:0deg}20%{rotate:-1.6deg}45%{rotate:1.3deg}70%{rotate:-.7deg}100%{rotate:0deg}}@keyframes ll-step-shake-b{0%{rotate:0deg}20%{rotate:-1.6deg}45%{rotate:1.3deg}70%{rotate:-.7deg}100%{rotate:0deg}}" +
  '[data-slot=stepper][data-limit=a]{animation:ll-step-shake-a var(--ll-dur-toss) ease-out both}[data-slot=stepper][data-limit=b]{animation:ll-step-shake-b var(--ll-dur-toss) ease-out both}' +
  "@keyframes ll-step-up-a{0%{translate:0 38%;opacity:.35}100%{translate:0 0;opacity:1}}@keyframes ll-step-up-b{0%{translate:0 38%;opacity:.35}100%{translate:0 0;opacity:1}}" +
  "@keyframes ll-step-down-a{0%{translate:0 -38%;opacity:.35}100%{translate:0 0;opacity:1}}@keyframes ll-step-down-b{0%{translate:0 -38%;opacity:.35}100%{translate:0 0;opacity:1}}" +
  '[data-slot=stepper-input][data-tick="up-a"]{animation:ll-step-up-a var(--ll-dur-pop) var(--ll-ease-settle) both}[data-slot=stepper-input][data-tick="up-b"]{animation:ll-step-up-b var(--ll-dur-pop) var(--ll-ease-settle) both}' +
  '[data-slot=stepper-input][data-tick="down-a"]{animation:ll-step-down-a var(--ll-dur-pop) var(--ll-ease-settle) both}[data-slot=stepper-input][data-tick="down-b"]{animation:ll-step-down-b var(--ll-dur-pop) var(--ll-ease-settle) both}'

const BUTTON =
  "relative m-[3px] calm:m-0.5 grid aspect-square shrink-0 cursor-default place-items-center text-ink outline-hidden select-none hover:ll-swipe focus-visible:ll-swipe focus-visible:[outline:2px_solid_var(--ll-focus)] focus-visible:outline-offset-[-2px] active:[background:color-mix(in_srgb,var(--ll-hi)_85%,transparent)] data-[holding=true]:[background:color-mix(in_srgb,var(--ll-hi)_85%,transparent)] aria-disabled:pointer-events-none aria-disabled:text-pencil-text [&_svg]:pointer-events-none"

function StepperButton({ direction, className, children, onPointerDown, onClick, onKeyDown, ...props }: React.ComponentProps<"button"> & { direction: Direction }) {
  const ctx = useStepper()
  const off = ctx.disabled || ctx.readOnly || (direction === 1 ? ctx.atMax : ctx.atMin)
  return (
    <button
      type="button"
      tabIndex={-1}
      data-holding={ctx.holding === direction || undefined}
      aria-disabled={off || undefined}
      disabled={ctx.disabled}
      onMouseDown={(e) => e.preventDefault()}
      onPointerDown={(e) => {
        onPointerDown?.(e)
        if (e.defaultPrevented || (e.pointerType === "mouse" && e.button !== 0)) return
        if (off) {
          if (!ctx.disabled && !ctx.readOnly) ctx.nudge()
          return
        }
        ctx.startHold(direction)
        const stop = () => {
          ctx.stopHold()
          window.removeEventListener("pointerup", stop)
          window.removeEventListener("pointercancel", stop)
        }
        window.addEventListener("pointerup", stop)
        window.addEventListener("pointercancel", stop)
      }}
      onClick={(e) => {
        onClick?.(e)
        if (e.defaultPrevented || e.detail !== 0 || off) return
        ctx.adjust(direction * ctx.step)
      }}
      onKeyDown={(e) => {
        onKeyDown?.(e)
        e.stopPropagation()
      }}
      className={cn(BUTTON, className)}
      {...props}
    >
      {children}
    </button>
  )
}

function StepperDecrement({ className, children, "aria-label": label = "Decrease", ...props }: React.ComponentProps<"button">) {
  return (
    <StepperButton direction={-1} data-slot="stepper-decrement" aria-label={label} className={className} {...props}>
      {children ?? <Icon name="minus" size={18} />}
    </StepperButton>
  )
}

function StepperIncrement({ className, children, "aria-label": label = "Increase", ...props }: React.ComponentProps<"button">) {
  return (
    <StepperButton direction={1} data-slot="stepper-increment" aria-label={label} className={className} {...props}>
      {children ?? <Icon name="plus" size={18} />}
    </StepperButton>
  )
}

function StepperInput({ className, style, ref, onKeyDown, onBlur, onChange, ...props }: Omit<React.ComponentProps<"input">, "value" | "defaultValue" | "type">) {
  const ctx = useStepper()
  const { inputRef, inputProps } = ctx
  const [draft, setDraft] = React.useState<{ text: string; base: string } | null>(null)
  const text = ctx.value === undefined ? "" : ctx.format(ctx.value)
  const shown = draft && draft.base === text ? draft.text : text

  const { adjust, jump, step, largeStep, min, max, wheel, disabled, reset } = ctx
  React.useEffect(() => {
    const el = inputRef.current
    if (!el || !wheel || disabled) return
    const onWheel = (e: WheelEvent) => {
      if (document.activeElement !== el || e.deltaY === 0) return
      e.preventDefault()
      adjust(e.deltaY < 0 ? step : -step)
    }
    el.addEventListener("wheel", onWheel, { passive: false })
    return () => el.removeEventListener("wheel", onWheel)
  }, [inputRef, wheel, disabled, adjust, step])
  React.useEffect(() => {
    const form = inputRef.current?.form
    if (!form) return
    const onReset = () => {
      setDraft(null)
      reset()
    }
    form.addEventListener("reset", onReset)
    return () => form.removeEventListener("reset", onReset)
  }, [inputRef, reset])

  const commit = (): void => {
    if (!draft || draft.base !== text) return
    if (ctx.commitText(draft.text)) setDraft(null)
    else setDraft(null)
  }
  const tick = ctx.motion ? `${ctx.motion.dir === 1 ? "up" : "down"}-${ctx.motion.n % 2 ? "a" : "b"}` : undefined
  return (
    <>
      <input
        type="text"
        inputMode="decimal"
        role="spinbutton"
        autoComplete="off"
        spellCheck={false}
        data-slot="stepper-input"
        data-tick={tick}
        aria-valuenow={ctx.value}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={ctx.value === undefined ? undefined : text}
        aria-invalid={ctx.invalid || undefined}
        disabled={ctx.disabled}
        readOnly={ctx.readOnly}
        value={shown}
        style={{ minWidth: `${Math.max(3, shown.length) + 1}ch`, ...style }}
        ref={useMergedRef<HTMLInputElement>(inputRef, ref)}
        {...inputProps}
        onChange={(e) => {
          onChange?.(e)
          setDraft({ text: e.target.value, base: text })
        }}
        onBlur={(e) => {
          onBlur?.(e)
          commit()
        }}
        onKeyDown={(e) => {
          onKeyDown?.(e)
          if (e.defaultPrevented || ctx.disabled) return
          const big = e.shiftKey ? largeStep : step
          switch (e.key) {
            case "ArrowUp":
              e.preventDefault()
              setDraft(null)
              adjust(big)
              break
            case "ArrowDown":
              e.preventDefault()
              setDraft(null)
              adjust(-big)
              break
            case "PageUp":
              e.preventDefault()
              setDraft(null)
              adjust(largeStep)
              break
            case "PageDown":
              e.preventDefault()
              setDraft(null)
              adjust(-largeStep)
              break
            case "Home":
              if (min !== undefined) {
                e.preventDefault()
                setDraft(null)
                jump(min)
              }
              break
            case "End":
              if (max !== undefined) {
                e.preventDefault()
                setDraft(null)
                jump(max)
              }
              break
            case "Enter":
              commit()
              break
            case "Escape":
              if (draft) {
                e.preventDefault()
                setDraft(null)
              }
              break
          }
        }}
        className={cn(
          "h-full w-16 min-w-0 flex-1 bg-transparent px-1 text-center font-script text-[1.65rem] leading-none font-bold text-(--ll-input-ink) caret-(--ll-caret) outline-hidden [appearance:textfield] disabled:cursor-not-allowed disabled:text-pencil-text calm:text-[1.35rem]",
          className
        )}
        {...props}
      />
      {ctx.hiddenName ? <input type="hidden" name={ctx.hiddenName} form={inputProps.form} value={ctx.value === undefined ? "" : String(ctx.value)} disabled={ctx.disabled} /> : null}
    </>
  )
}

function StepperTally({ className, style, max = 20, seed, value: valueProp, ...props }: Omit<React.ComponentProps<"span">, "children" | "value"> & { max?: number; seed?: string | number; value?: number }) {
  const ctx = React.useContext(StepperContext)
  const shown = valueProp ?? ctx?.value ?? 0
  const count = Math.max(0, Math.min(Number.isFinite(shown) ? Math.floor(shown) : 0, max))
  const width = tallyWidth(Math.max(count, 1))
  const { hostRef, hostProps, node } = useInk({ recipe: stepperTallyRecipe, params: { count }, kind: "tally", size: [width, TALLY_H + 4], seed, still: true })
  return (
    <span data-slot="stepper-tally" aria-hidden="true" ref={hostRef} {...hostProps} style={{ width, ...style }} className={cn("relative isolate inline-block h-5 shrink-0 text-ink", className)} {...props}>
      {count > 0 ? node : null}
    </span>
  )
}

export { Stepper, StepperDecrement, StepperInput, StepperIncrement, StepperTally, useStepper }
export type { StepperProps }
