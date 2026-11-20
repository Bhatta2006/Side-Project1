# Gamified UI ("Daybreak"): what is built, what is left

Branch `gbuild/feat/gamified-ui` (from `gbuild/main`). First slice committed 2026-11-21 (`f619a9b7`).
Read this before touching any page's look. Gaps that are built but not checked end to end are also listed in
`docs/implementation/not-verified.md`: keep both current in the same change.

## The brief (owner decisions, 2026-11-21)

- **Feel like Duolingo and Wondering, never copy them.** Same energy (chunky pressable buttons, a path, instant
  feedback, combos, celebrations), Socrat's own art, copy, colours and sounds.
- **Game layer is evidence-based.** XP, streaks, daily goal, levels, combo, quests, badges, celebrations, all computed
  from what the server proved. **No** hearts or energy, gem shop, XP leagues, or anything that can be bought or earned
  without the work.
- **No AI look.** No gradients, glows, colour washes or sparkles. Flat colour with a solid darker ledge underneath.
- **A hint of paper.** Buttons and cards carry a faint grain and paper fibres and slightly uneven corners. Subtle.
- **The ground is never empty.** Cream with paper grain and a faint pebble-beach pattern in the palette colour.
- **Custom emoji only** for game moments (`components/socrat/game-emoji.tsx`), never system emoji or stock icons.
- **Our own sounds** (`lib/game-sound.ts`), never anyone's jingles.
- **Mascot:** Soc the dark speckled pebble stays exactly as drawn. Friends in the same style, other shapes:
  Ember (flame, streaks), Jade (bean, review and right answers), Ami (gem, levels), Amber (cushion, quests and XP),
  Lazuli (shield, checkpoints). See `components/socrat/pebble-friend.tsx`.
- **The learner picks colours:** six Daybreak palettes (Daybreak, Ruby, Ocean, Lagoon, Sunset, Berry) and the six old
  notebook ones, light, dark or match device, in Settings.
- Design preview the owner approved: https://claude.ai/artifact/Q3MXZYyvH8ULpQAT5Cg8fN (Home, Lesson, Done,
  Profile, Create boards are the reference for the screens still to do).

## How it works (read before you style anything)

- **Two looks on `<html data-look>`**: `daybreak` (default) or `notebook`. Set before paint by `PALETTE_BOOT_SCRIPT`
  (`lib/palette-boot.ts`) and by `applyPalette` (`lib/palette.ts`). Palette ids are saved on the account as
  `"palette:mode"` (`users.appearance`; the API allow-list is `APPEARANCE_PALETTES` in `learn/routes.py`).
- **All Daybreak styling lives in `apps/web/src/app/daybreak.css`**, scoped `:root[data-look="daybreak"]`. It is
  **unlayered on purpose**, so it beats Tailwind's layered utilities without `!important`. Restyle by `data-slot`,
  `data-variant` and existing classes rather than editing every component.
- **Ink frames are off under Daybreak.** `useInkCore` (`lib/ink/react/hooks.ts`) skips every recipe except the
  decorative marks in `DAYBREAK_INK_KINDS` (highlight, underline, circled, tally...). The provider observes `data-look`.
- **Tokens:** `--db-*` (primary, ledge, tint, surface, line, ink, muted, and the fixed game colours `--db-xp`,
  `--db-streak`, `--db-correct`, `--db-wrong`, `--db-info` with `-ink` and `-tint`). Tailwind names: `bg-db-primary`,
  `text-db-xp-ink`, etc. A plain `:root` block gives every `--db-*` a notebook fallback, so game parts still read there.
  Game colours never change with the palette.
- **Markup per look:** `.db-only` shows only in Daybreak, `.nb-only` only in Notebook (used in `answer-flow.tsx`).
- **Motion helpers:** `.db-pop`, `.db-rise`, `.db-bob`, `.db-flicker`, `.db-shake`, `.db-sheet-up`, `.db-confetti`,
  all off under reduced motion.
- **Gotchas found the hard way:**
  - Lightning CSS drops `background: var(--a), var(--b)`. Use `background-image` with gradient-only values
    (a flat colour is written `linear-gradient(c, c)`).
  - The ground pattern is `body::before` at `z-index: -1`; any full-page wrapper with an opaque background hides it
    (`.ll-desk` is made transparent for this).
  - Tailwind `@theme inline` inlines `font-script` / `font-sans`, so Daybreak overrides those classes explicitly.
  - Run API tests from the repo root (`alembic.ini` lives there). In a sandbox add
    `--basetemp=D:\Socrat\.cache\pytest-x -p no:cacheprovider`.
  - Local onboarding with `SOCRAT_AI_PROVIDER=offline` never finishes writing a course, so Today stays empty.
    Use the dev board below, or a live run (`live-journey-api.ps1 -Keep`).

## Built in slice 1

| Piece | Where |
|---|---|
| Six palettes, look switch, fonts (Bricolage Grotesque, Plus Jakarta Sans, self-hosted) | `lib/palette.ts`, `lib/palette-boot.ts`, `app/daybreak.css`, `app/globals.css` |
| Buttons, cards, fields, checkbox, radio, switch, progress, tabs, badges, menus, skeletons, choice tiles | `app/daybreak.css` |
| Pebble friends, game emoji (12) | `components/socrat/pebble-friend.tsx`, `game-emoji.tsx` |
| Levels (Novice to Sage, by proven skills), evidence points, daily goal names | `lib/game.ts`, test `apps/web/tests/game.test.mjs` |
| Today: game strip, Path tab (default) | `components/socrat/game-bar.tsx`, `skill-path.tsx`, `app/today/page.tsx` |
| Answer feel: mint/coral sheets with a pebble, flame combo chip, shake, sounds, vibration | `components/socrat/answer-flow.tsx`, `lib/game-sound.ts` |
| Session end: sun rays, confetti, stat tiles, ember streak days | `components/socrat/celebrate.tsx`, `session-end.tsx` |
| Settings: palettes grouped by look, Sounds switch | `components/palette-picker.tsx` |
| Dev board (404 in production) | `/dev-mascots/daybreak` |

## Built in slice 2 (2026-11-21)

Owner decisions: Daybreak **stays the default look** (no flag on the look itself); capability quests wait for their
own change (they need an API and a table).

| Piece | Where |
|---|---|
| Lesson: green lesson bar (pages), one page per card, Soc's speech bubble on Check pages, sticky Next/Back bar on phones, thick reading bar, dark code blocks, tap clack on page turns | `components/lesson-pages.tsx`, `app/learn/[...concept]/page.tsx`, `app/daybreak.css` |
| Quiz: choice tiles click with `playInDaybreak('tap')`, marigold bar on a run (`Progress` now sets `data-tone`), sticky Check bar on phones (`data-slot="answer-bar"`, also in adaptive check) | `components/choice.tsx`, `components/ui/progress.tsx`, `app/quiz/[...activity]/page.tsx`, `components/socrat/adaptive-check.tsx` |
| Shell: nav icons drawn as game emoji (`NavIcon`, Lucide stays for Notebook), the current place as a tinted pill in the tab bar and sidebar | `components/shell.tsx` |
| Nine more game emoji: home, map, bulb, flag, chart, gear, blocks, code, snow | `components/socrat/game-emoji.tsx` |
| Progress: Daybreak header (Soc on the main colour, level bar from `levelFor`, four count-up stat tiles, frozen pebbles); notebook header is `.nb-only` | `components/socrat/profile-header.tsx`, `app/progress/page.tsx` |
| Game moments behind `game_moments` (API flag, default off, test `test_game_moments.py`): daily goal reached on Today (Jade), level-up once per level (Ami), streak milestone ribbon and frozen pebbles on the session-end streak screen (Ember), Jade on the goal-reached session-end screen, badges as pebble stickers on Progress, `useCountUp` | `components/socrat/game-moments.tsx`, `lib/game.ts` (`streakMilestone`, `nextStreakMilestone`, `levelUpDue`, tested) |
| Onboarding visuals: pebble trio on the first question (stacked above it on phones), goal names (Steady, Serious, Deep) on the time choices, Amber celebration when the plan is ready | `app/start/page.tsx` (visual only; the flow is the cofounder's) |
| Landing and login: the notebook's tilted handwriting becomes flat bold notes in the main colour; the headline stays "Learn it. Then prove it." | `app/daybreak.css` |
| Contrast fixes: Ruby, Lagoon and Sunset primaries darkened to pass 4.5:1 under white; dark mode keeps the light primary for fills; correct/wrong Check buttons deepened | `app/daybreak.css`, `lib/palette.ts` |
| Dev board shows every new piece (kept as the living style board) | `/dev-mascots/daybreak` |

## Backlog, in order

### 1. Verify with a real course (nothing counts until this passes)
- Everything in `not-verified.md` under "Playful look: Daybreak": Today, a lesson, a quiz, session end, Progress and the
  shell with a generated course, at 360px, in Daybreak light, Daybreak dark and Classic.
- Sounds on a real Android and iPhone home-screen app.
- An axe pass. Known gap: text on the fixed game colours (white on `--db-correct`, 2.9:1) where slice 1 used it.
- Decide with the owner when to turn `game_moments` on (`SOCRAT_GAME_MOMENTS_ENABLED=true`).

### 2. Still to build
- **Capability quests** with Amber (owner: later, its own change): two or three a week, each tied to proving a named
  skill; needs a small API (quest = skill + check, done when the check passes) and an additive migration with a
  tested downgrade. No quest for time or clicks alone.
- **Passport**: game styling around the record (header, pebble), never on the evidence itself. Untouched so far.
- **Lesson**: one *step* per card is done for paged reading; the scroll view and the side column (stepper, Ask Soc)
  still use the shared restyle only.
- Today's moments stack if both fire on one visit; show one at a time if that feels busy on a real day.

### 3. Housekeeping
- Re-baseline the Playwright visual specs once the e2e specs are re-seeded with a generated course.
- Check the JS budget in CI (410 KB on `gbuild/main`) with the new components and fonts.
- Replace any stock icon left in a game moment with a game emoji as screens are reviewed.

## When you finish a piece
Update this file (move the line to "Built"), update `not-verified.md`, run `npx tsc --noEmit -p apps/web`,
`node --experimental-strip-types --test apps/web/tests/*.test.mjs` and the API tests you touched, and check the page in
the browser at phone width in Daybreak light, Daybreak dark and Classic.
