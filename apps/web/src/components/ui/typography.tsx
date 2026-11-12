"use client"

import * as React from "react"

import { TYPOGRAPHY_QUOTE_BAR, TYPOGRAPHY_RULE_1, TYPOGRAPHY_RULE_2, TYPOGRAPHY_TABLE_HEAD, TYPOGRAPHY_TABLE_RULE } from "@/lib/ink/typography-tiles.generated"
import { hashSeed } from "@/lib/ink/rng"
import { useInkSeed } from "@/lib/ink/react"
import { cn } from "@/lib/utils"

const RULES_CSS = [
  ":root{",
  `--ll-rule-1a:${TYPOGRAPHY_RULE_1[0]};`,
  `--ll-rule-1b:${TYPOGRAPHY_RULE_1[1]};`,
  `--ll-rule-1c:${TYPOGRAPHY_RULE_1[2]};`,
  `--ll-rule-2a:${TYPOGRAPHY_RULE_2[0]};`,
  `--ll-rule-2b:${TYPOGRAPHY_RULE_2[1]};`,
  `--ll-rule-2c:${TYPOGRAPHY_RULE_2[2]};`,
  `--ll-bar-a:${TYPOGRAPHY_QUOTE_BAR[0]};`,
  `--ll-bar-b:${TYPOGRAPHY_QUOTE_BAR[1]};`,
  `--ll-bar-c:${TYPOGRAPHY_QUOTE_BAR[2]};`,
  "}",
].join("")

const RULE =
  "after:mt-2 after:block after:h-[2px] after:w-full after:rounded-full after:bg-current after:opacity-55 after:content-['']"

const RULE_1 = ["", "", ""] as const
const RULE_2 = ["", "", ""] as const

const BAR =
  "relative border-s-[3px] border-marker/70 supports-[mask-image:none]:border-s-0 " +
  "supports-[mask-image:none]:before:pointer-events-none supports-[mask-image:none]:before:absolute supports-[mask-image:none]:before:inset-y-0.5 supports-[mask-image:none]:before:start-0 " +
  "supports-[mask-image:none]:before:w-2 supports-[mask-image:none]:before:bg-marker supports-[mask-image:none]:before:opacity-80 supports-[mask-image:none]:before:content-[''] " +
  "supports-[mask-image:none]:before:[mask-repeat:no-repeat] supports-[mask-image:none]:before:[mask-size:100%_100%]"
const BARS = [
  "supports-[mask-image:none]:before:[mask-image:var(--ll-bar-a)]",
  "supports-[mask-image:none]:before:[mask-image:var(--ll-bar-b)]",
  "supports-[mask-image:none]:before:[mask-image:var(--ll-bar-c)]",
] as const

function RuleStyle() {
  return (
    <style href="ll-typography-rules" precedence="low">
      {RULES_CSS}
    </style>
  )
}

type HeadingProps = React.ComponentProps<"h1"> & {
  rule?: boolean
  seed?: string | number
}

function H1({ rule = true, seed, className, children, ...props }: HeadingProps) {
  const s = useInkSeed(seed)
  return (
    <h1
      data-slot="typography-h1"
      className={cn("scroll-m-20 font-script text-5xl leading-[1.02] font-bold tracking-tight text-balance text-ink", rule && RULE, rule && RULE_1[hashSeed(s) % 3], className)}
      {...props}
    >
      {rule ? <RuleStyle /> : null}
      {children}
    </h1>
  )
}

function H2({ rule = true, seed, className, children, ...props }: HeadingProps) {
  const s = useInkSeed(seed)
  return (
    <h2
      data-slot="typography-h2"
      className={cn("scroll-m-20 font-script text-4xl leading-[1.08] font-bold tracking-tight text-balance text-ink", rule && RULE, rule && RULE_2[hashSeed(s) % 3], className)}
      {...props}
    >
      {rule ? <RuleStyle /> : null}
      {children}
    </h2>
  )
}

function H3({ className, ...props }: React.ComponentProps<"h3">) {
  return <h3 data-slot="typography-h3" className={cn("scroll-m-20 font-script text-3xl leading-tight font-bold tracking-tight text-balance text-ink", className)} {...props} />
}

function H4({ className, ...props }: React.ComponentProps<"h4">) {
  return <h4 data-slot="typography-h4" className={cn("scroll-m-20 font-hand text-xl leading-snug font-bold tracking-tight text-balance text-ink", className)} {...props} />
}

function P({ className, ...props }: React.ComponentProps<"p">) {
  return <p data-slot="typography-p" className={cn("text-[17px] leading-[1.7] text-pretty [&:not(:first-child)]:mt-5", className)} {...props} />
}

function Lead({ className, ...props }: React.ComponentProps<"p">) {
  return <p data-slot="typography-lead" className={cn("text-xl leading-[1.55] text-muted-foreground", className)} {...props} />
}

function Large({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="typography-large" className={cn("text-lg font-bold", className)} {...props} />
}

function Small({ className, ...props }: React.ComponentProps<"small">) {
  return <small data-slot="typography-small" className={cn("text-sm leading-none font-bold", className)} {...props} />
}

function Muted({ className, ...props }: React.ComponentProps<"p">) {
  return <p data-slot="typography-muted" className={cn("text-sm text-muted-foreground", className)} {...props} />
}

function List({ ordered = false, className, ...props }: React.ComponentProps<"ul"> & { ordered?: boolean }) {
  const Comp = (ordered ? "ol" : "ul") as "ul"
  return (
    <Comp
      data-slot="typography-list"
      className={cn(
        "my-5 ms-6 text-[17px] leading-[1.6] marker:text-marker [&>li]:mt-2 [&>li]:ps-1",
        ordered ? "list-decimal marker:font-script marker:text-xl marker:font-bold" : "list-disc marker:text-xl",
        className,
      )}
      {...props}
    />
  )
}

function InlineCode({ className, ...props }: React.ComponentProps<"code">) {
  return (
    <code
      data-slot="typography-inline-code"
      className={cn("relative bg-muted box-decoration-clone px-[0.35rem] py-[0.15rem] font-mono text-[0.85em] font-medium text-ink wrap-anywhere [border-radius:2px_6px_3px_5px/5px_2px_6px_3px]", className)}
      {...props}
    />
  )
}

function Blockquote({ className, seed, children, ...props }: React.ComponentProps<"blockquote"> & {
  seed?: string | number
}) {
  const s = useInkSeed(seed)
  return (
    <blockquote data-slot="typography-blockquote" className={cn("mt-6 ps-5 font-script text-2xl leading-[1.35] text-ink-soft", BAR, BARS[hashSeed(s) % 3], className)} {...props}>
      <RuleStyle />
      {children}
    </blockquote>
  )
}

const PROSE_CSS = `@layer theme, base, components, utilities;
@layer components {
:root { --ll-prose-rule: ${TYPOGRAPHY_TABLE_RULE}; --ll-prose-head: ${TYPOGRAPHY_TABLE_HEAD}; }
[data-slot="typography-prose"] { color: var(--foreground); font-family: var(--font-hand); font-size: 17px; line-height: 1.7; max-width: 64ch; }
[data-slot="typography-prose"] :where(p, ul, ol, dl, blockquote, pre, figure, table, details, hr):not(:where(.ll-not-prose, .ll-not-prose *)) { margin-block: 1.15em; }
[data-slot="typography-prose"] > :where(:first-child) { margin-block-start: 0; }
[data-slot="typography-prose"] > :where(:last-child) { margin-block-end: 0; }
[data-slot="typography-prose"] :where(h1, h2, h3, h4, h5, h6):not(:where(.ll-not-prose *)) { font-family: var(--font-script); font-weight: 700; letter-spacing: -0.01em; text-wrap: balance; color: var(--ll-ink); scroll-margin-top: 5rem; }
[data-slot="typography-prose"] :where(h1) { font-size: 3rem; line-height: 1.02; margin-block: 0 0.7em; }
[data-slot="typography-prose"] :where(h2) { font-size: 2.25rem; line-height: 1.08; margin-block: 1.7em 0.6em; }
[data-slot="typography-prose"] :where(h3) { font-size: 1.75rem; line-height: 1.15; margin-block: 1.5em 0.4em; }
[data-slot="typography-prose"] :where(h4) { font-family: var(--font-hand); font-size: 1.25rem; line-height: 1.3; margin-block: 1.3em 0.3em; }
[data-slot="typography-prose"] :where(h5, h6) { font-family: var(--font-hand); font-size: 1rem; margin-block: 1.2em 0.3em; }
[data-slot="typography-prose"] :where(h1, h2) { border-bottom: 2px solid color-mix(in srgb, var(--ll-pencil-mark) 60%, transparent); padding-bottom: 0.2em; }
@supports (mask-image: none) {
  [data-slot="typography-prose"] :where(h1, h2) { border-bottom: 0; padding-bottom: 0; }
  [data-slot="typography-prose"] :where(h1, h2)::after { content: ""; display: block; height: 0.75rem; margin-top: 0.3rem; background: currentColor; opacity: 0.7; mask-repeat: no-repeat; mask-size: 100% 100%; -webkit-mask-repeat: no-repeat; -webkit-mask-size: 100% 100%; }
  [data-slot="typography-prose"] :where(h1)::after { mask-image: var(--ll-rule-1a); -webkit-mask-image: var(--ll-rule-1a); }
  [data-slot="typography-prose"] :where(h1:nth-of-type(3n+2))::after { mask-image: var(--ll-rule-1b); -webkit-mask-image: var(--ll-rule-1b); }
  [data-slot="typography-prose"] :where(h1:nth-of-type(3n))::after { mask-image: var(--ll-rule-1c); -webkit-mask-image: var(--ll-rule-1c); }
  [data-slot="typography-prose"] :where(h2)::after { mask-image: var(--ll-rule-2a); -webkit-mask-image: var(--ll-rule-2a); }
  [data-slot="typography-prose"] :where(h2:nth-of-type(3n+2))::after { mask-image: var(--ll-rule-2b); -webkit-mask-image: var(--ll-rule-2b); }
  [data-slot="typography-prose"] :where(h2:nth-of-type(3n))::after { mask-image: var(--ll-rule-2c); -webkit-mask-image: var(--ll-rule-2c); }
}
[data-slot="typography-prose"] :where(a) { color: var(--ll-link); font-weight: 700; text-decoration: underline; text-decoration-thickness: 1.5px; text-underline-offset: 0.28em; text-decoration-skip-ink: none; }
[data-slot="typography-prose"] :where(a:hover) { color: var(--ll-link-hover); text-decoration-thickness: 2.5px; }
[data-slot="typography-prose"] :where(strong, b) { font-weight: 700; }
[data-slot="typography-prose"] :where(em, i) { font-style: italic; }
[data-slot="typography-prose"] :where(ul, ol) { padding-inline-start: 1.6em; }
[data-slot="typography-prose"] :where(ul) { list-style: disc; }
[data-slot="typography-prose"] :where(ol) { list-style: decimal; }
[data-slot="typography-prose"] :where(li) { margin-block: 0.4em; padding-inline-start: 0.2em; }
[data-slot="typography-prose"] :where(li)::marker { color: var(--ll-marker); font-weight: 700; }
[data-slot="typography-prose"] :where(li > ul, li > ol) { margin-block: 0.4em; }
[data-slot="typography-prose"] :where(blockquote) { position: relative; border-inline-start: 3px solid color-mix(in srgb, var(--ll-marker) 70%, transparent); padding-inline-start: 1.1em; font-family: var(--font-script); font-size: 1.5rem; line-height: 1.35; color: var(--ll-ink-soft); }
@supports (mask-image: none) {
  [data-slot="typography-prose"] :where(blockquote) { border-inline-start: 0; }
  [data-slot="typography-prose"] :where(blockquote)::before { content: ""; position: absolute; inset-block: 2px; inset-inline-start: 0; width: 0.5rem; background: var(--ll-marker); opacity: 0.8; pointer-events: none; mask-image: var(--ll-bar-a); mask-size: 100% 100%; mask-repeat: no-repeat; -webkit-mask-image: var(--ll-bar-a); -webkit-mask-size: 100% 100%; -webkit-mask-repeat: no-repeat; }
  [data-slot="typography-prose"] :where(blockquote:nth-of-type(3n+2))::before { mask-image: var(--ll-bar-b); -webkit-mask-image: var(--ll-bar-b); }
  [data-slot="typography-prose"] :where(blockquote:nth-of-type(3n))::before { mask-image: var(--ll-bar-c); -webkit-mask-image: var(--ll-bar-c); }
}
[data-slot="typography-prose"] :where(blockquote p) { margin-block: 0.5em; }
[data-slot="typography-prose"] :where(code, kbd, samp) { font-family: var(--font-mono); font-size: 0.85em; }
[data-slot="typography-prose"] :where(code):not(:where(pre *)) { background: var(--muted); padding: 0.15em 0.35em; border-radius: 2px 6px 3px 5px / 5px 2px 6px 3px; }
[data-slot="typography-prose"] :where(kbd) { background: var(--ll-slip); border: 1.5px solid var(--ll-pencil-mark); padding: 0.05em 0.4em; border-radius: 3px 5px 3px 4px / 4px 3px 5px 3px; box-shadow: 0 1.5px 0 var(--ll-pencil-mark); }
[data-slot="typography-prose"] :where(pre) { background: var(--ll-slip); border: 1.5px dashed var(--ll-pencil-mark); padding: 0.9em 1.1em; overflow-x: auto; font-family: var(--font-mono); font-size: 0.85rem; line-height: 1.6; }
[data-slot="typography-prose"] :where(pre code) { background: none; padding: 0; font-size: inherit; }
[data-slot="typography-prose"] :where(hr) { border: 0; height: 0.75rem; background: var(--ll-pencil-mark); opacity: 0.6; margin-block: 2em; mask-image: var(--ll-rule-2b); mask-size: 100% 100%; mask-repeat: no-repeat; -webkit-mask-image: var(--ll-rule-2b); -webkit-mask-size: 100% 100%; -webkit-mask-repeat: no-repeat; }
[data-slot="typography-prose"] :where(img, video, svg:not([data-ink]), canvas) { max-width: 100%; height: auto; }
[data-slot="typography-prose"] :where(table) { width: 100%; border-collapse: collapse; font-size: 0.95em; }
[data-slot="typography-prose"] :where(th) { font-family: var(--font-script); font-size: 1.25rem; text-align: start; border-bottom: 2px solid var(--ll-pencil-mark); padding: 0.4em 0.6em; }
[data-slot="typography-prose"] :where(td) { border-bottom: 1px solid color-mix(in srgb, var(--ll-pencil-mark) 55%, transparent); padding: 0.4em 0.6em; }
@supports (mask-image: none) {
  [data-slot="typography-prose"] :where(table) {
    border-collapse: separate; border-spacing: 0; isolation: isolate; --ll-ptbl-img: var(--ll-prose-rule); --ll-ptbl-h: 8px;
    --ll-fade-s: linear-gradient(90deg, transparent, black 14px); --ll-fade-e: linear-gradient(90deg, black calc(100% - 26px), transparent);
    --ll-fade-se: linear-gradient(90deg, transparent, black 14px, black calc(100% - 26px), transparent);
  }
  [data-slot="typography-prose"] :where(table):dir(rtl) {
    --ll-fade-s: linear-gradient(270deg, transparent, black 14px); --ll-fade-e: linear-gradient(270deg, black calc(100% - 26px), transparent);
    --ll-fade-se: linear-gradient(270deg, transparent, black 14px, black calc(100% - 26px), transparent);
  }
  [data-slot="typography-prose"] :where(thead) { --ll-ptbl-img: var(--ll-prose-head); --ll-ptbl-h: 12px; }
  [data-slot="typography-prose"] :where(tr) { --ll-rx: 0px; }
  [data-slot="typography-prose"] :where(tr:nth-child(4n + 2)) { --ll-rx: -330px; }
  [data-slot="typography-prose"] :where(tr:nth-child(4n + 3)) { --ll-rx: -610px; }
  [data-slot="typography-prose"] :where(tr:nth-child(4n)) { --ll-rx: -140px; }
  [data-slot="typography-prose"] :where(th, td) { position: relative; border-bottom: 0; --ll-cx: 0px; }
  [data-slot="typography-prose"] :where(th:nth-child(5n + 2), td:nth-child(5n + 2)) { --ll-cx: -173px; }
  [data-slot="typography-prose"] :where(th:nth-child(5n + 3), td:nth-child(5n + 3)) { --ll-cx: -419px; }
  [data-slot="typography-prose"] :where(th:nth-child(5n + 4), td:nth-child(5n + 4)) { --ll-cx: -71px; }
  [data-slot="typography-prose"] :where(th:nth-child(5n), td:nth-child(5n)) { --ll-cx: -617px; }
  [data-slot="typography-prose"] :where(th, td)::after {
    content: ""; position: absolute; inset-inline: 0; bottom: -4px; height: var(--ll-ptbl-h); pointer-events: none; background-color: var(--ll-pencil-mark);
    mask-image: var(--ll-ptbl-img); mask-size: 960px var(--ll-ptbl-h); mask-repeat: repeat-x; mask-position: calc(var(--ll-rx) + var(--ll-cx)) 0;
  }
  [data-slot="typography-prose"] :where(th, td):is(:first-child, :last-child)::after {
    mask-size: 960px var(--ll-ptbl-h), 100% 100%; mask-repeat: repeat-x, no-repeat; mask-position: calc(var(--ll-rx) + var(--ll-cx)) 0, 0 0; mask-composite: intersect;
  }
  [data-slot="typography-prose"] :where(th, td):first-child::after { mask-image: var(--ll-ptbl-img), var(--ll-fade-s); }
  [data-slot="typography-prose"] :where(th, td):last-child::after { mask-image: var(--ll-ptbl-img), var(--ll-fade-e); }
  [data-slot="typography-prose"] :where(th, td):only-child::after { mask-image: var(--ll-ptbl-img), var(--ll-fade-se); }
  [data-slot="typography-prose"] :where(thead th, thead td)::after { bottom: -6px; background-color: var(--ll-ink-soft); }
}
[data-slot="typography-prose"] :where(mark) { padding-inline: 0.12em; }
[data-slot="typography-prose"] :where(figcaption) { font-size: 0.875rem; color: var(--muted-foreground); margin-block-start: 0.5em; }
@media (forced-colors: active) {
  [data-slot="typography-prose"] :where(h1, h2)::after, [data-slot="typography-prose"] :where(blockquote)::before, [data-slot="typography-prose"] :where(hr) { background: CanvasText; }
  [data-slot="typography-prose"] :where(th, td)::after { display: none; }
  [data-slot="typography-prose"] :where(th, td) { border-bottom: 1px solid CanvasText; }
}
}
`

function Prose({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <>
      <RuleStyle />
      <style href="ll-prose" precedence="low">
        {PROSE_CSS}
      </style>
      <div data-slot="typography-prose" className={className} {...props} />
    </>
  )
}

export { H1, H2, H3, H4, P, Lead, Large, Small, Muted, List, InlineCode, Blockquote, Prose }
