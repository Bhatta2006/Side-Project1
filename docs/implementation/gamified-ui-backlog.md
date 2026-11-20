# Gamified UI in the paper look: what is built, what is left

Branch `gbuild/feat/gamified-ui` (from `gbuild/main`). Slice 1 `f619a9b7`, slice 2 `ed3fc223` (both in the retired
Daybreak look), then the paper redo (2026-11-21, this file). Read this before touching any page's look. Gaps that are
built but not checked end to end are also listed in `docs/implementation/not-verified.md`: keep both current in the
same change.

## The brief (owner decisions, 2026-11-21)

- **The look is the notebook, rendered light.** The owner rejected the flat Duolingo-like "Daybreak" look the same
  day it shipped. The app is the old notebook paper style with its six palettes (Classic, Tide, Lilac, Meadow, Riso,
  Dusk), but frames are drawn in CSS instead of the heavy per-element ink renderer. The gamified layer sits on top.
- **Everything in the paper style, emoji included.** Game emoji and pebbles are die-cut stickers (an ink edge, a paper
  rim, a short drop); chips, stones, badges and tiles are slips, sticky notes and tape.
- **Game layer is evidence-based.** XP, streaks, daily goal, levels, combo, quests, badges, celebrations, all computed
  from what the server proved. **No** hearts or energy, gem shop, XP leagues, or anything that can be bought or earned
  without the work.
- **No AI look.** No gradients, glows, colour washes or sparkles.
- **Custom emoji only** for game moments (`components/socrat/game-emoji.tsx`), never system emoji or stock icons.
- **Our own sounds** (`lib/game-sound.ts`), never anyone's jingles.
- **Mascot:** Soc the dark speckled pebble stays exactly as drawn. Friends in the same style: Ember (streaks), Jade
  (review and right answers), Ami (levels), Amber (quests and XP), Lazuli (checkpoints). `components/socrat/pebble-friend.tsx`.

## How it works (read before you style anything)

- **One look, `<html data-look="paper">`**, set before paint by `PALETTE_BOOT_SCRIPT` (`lib/palette-boot.ts`) and by
  `applyPalette` (`lib/palette.ts`). Palette ids are saved on the account as `"palette:mode"` (`users.appearance`).
  A saved retired Daybreak id falls back to Classic (the API allow-list `APPEARANCE_PALETTES` still accepts them).
- **Ink frames are off.** `useInkCore` (`lib/ink/react/hooks.ts`) skips every recipe except the decorative marks in
  `LIGHT_INK_KINDS` (highlight, underline, circled, arrow, tally, ribbon...). Stickers keep drawing (memoized art).
- **All paper frame styling lives in `apps/web/src/app/paper.css`**, scoped `:root[data-look="paper"]`, unlayered so
  it beats Tailwind utilities without `!important`. It restyles by `data-slot`, `data-variant` and existing classes:
  buttons (marker / red / sticky yellow / slip, ink line, ink drop, press), `.stamp` (Check, Continue), fields,
  checkbox, radio, switch, toggles, progress, folder tabs, badges, menus and dialogs, choice tiles
  (`data-slot="choice"`), the answer sheet (`.feedback-sheet`). In dark mode the ink turns light, so filled buttons
  print in dark ink (`#1b1a17`) to stay readable.
- **Paper tokens:** `--pp-ink`, `--pp-line` (1.5px), `--pp-drop`, `--pp-drop-lift`, `--pp-cut` (uneven corners),
  `--pp-fibre` (the paper texture InkTiles sets). Classes: `.pp-card` (slip, ink line, drop), `.pp-note[data-tone]`
  (sticky note in xp / streak / correct / wrong / info / paper), `.pp-tape` (tape strip on top).
- **Game tokens `--db-*`** are kept as names but mapped to notebook colours in `paper.css` (primary = marker, xp =
  highlighter, correct = green, wrong = red, every `-ink` = ink). Game pieces: `.gm-chip`, `.gm-stone[data-tone]`,
  `.gm-say`, `.db-lesson-bar`, `.db-level-track`, `.db-ribbon`, `.db-bubble`.
- **Sounds:** `playInGame()` plays only under the paper look; `play()` honours the Sounds switch.
- **Motion helpers:** `.db-pop`, `.db-rise`, `.db-bob`, `.db-flicker`, `.db-shake`, `.db-sheet-up`, `.db-confetti`,
  all off under reduced motion.
- **Gotchas found the hard way:**
  - Lightning CSS drops `background: var(--a), var(--b)`. Use `background-image` with gradient-only values.
  - Run API tests from the repo root (`alembic.ini` lives there). In a sandbox add
    `--basetemp=D:\Socrat\.cache\pytest-x -p no:cacheprovider`.
  - Local onboarding with `SOCRAT_AI_PROVIDER=offline` never finishes writing a course, so Today stays empty.
    Use the dev board `/dev-mascots/game` (404 in production), or a live run (`live-journey-api.ps1 -Keep`).

## Built

| Piece | Where |
|---|---|
| Paper look: six notebook palettes, light/dark/device, frames in CSS, light ink marks only | `app/paper.css`, `lib/palette.ts`, `lib/palette-boot.ts`, `lib/ink/react/*` |
| Pebble friends; 21 game emoji as die-cut stickers | `components/socrat/pebble-friend.tsx`, `game-emoji.tsx` |
| Levels (Novice to Sage, by proven skills), evidence points, daily goal names, streak milestones | `lib/game.ts`, test `apps/web/tests/game.test.mjs` |
| Today: game strip chips (slip, ink, drop), Path tab with paper stones and a pencil trail | `components/socrat/game-bar.tsx`, `skill-path.tsx`, `app/today/page.tsx` |
| Lesson: ink lesson tube, page dots, Soc's bubble on Check pages, sticky Next bar on phones, tap sound | `components/lesson-pages.tsx` |
| Quiz: paper choice tiles (picked = highlighter wash), highlighter bar on a run, paper Check stamp, sticky Check bar on phones | `components/choice.tsx`, `components/ui/progress.tsx`, `app/quiz/[...activity]/page.tsx` |
| Answer feel: sticky-note answer sheet with an ink edge, pebble + emoji, orange run ribbon, shake, sounds | `components/socrat/answer-flow.tsx`, `lib/game-sound.ts` |
| Session end: highlighter rays on a paper disc, notebook confetti, sticky-note stat tiles | `components/socrat/celebrate.tsx`, `session-end.tsx` |
| Shell: nav icons as game emoji stickers, current place on a highlighter pill | `components/shell.tsx` |
| Progress: taped level card with Soc and an ink tube, four sticky-note tiles, notebook header below | `components/socrat/profile-header.tsx`, `app/progress/page.tsx` |
| Game moments behind `game_moments` (API flag, default off, `test_game_moments.py`): goal reached, level-up, streak ribbon, frozen pebbles, badges as sticky notes | `components/socrat/game-moments.tsx` |
| Onboarding visuals: pebble trio on the first question, goal names on the time choices | `app/start/page.tsx` (visual only; the flow is the cofounder's) |
| Settings: one row of notebook palettes, Sounds switch | `components/palette-picker.tsx` |

## Backlog, in order

### 1. Verify with a real course (nothing counts until this passes)
- Everything in `not-verified.md` under "Gamified layer in the paper look": Today, a lesson, a quiz, session end,
  Progress and the shell with a generated course, at 360px, in Classic light, Classic dark and one more palette.
- Sounds on a real Android and iPhone home-screen app.
- An axe pass over the sticky-note tones and the dark-mode stones.
- Decide with the owner when to turn `game_moments` on (`SOCRAT_GAME_MOMENTS_ENABLED=true`).

### 2. Still to build
- **Capability quests** with Amber (owner: later, its own change): two or three a week, each tied to proving a named
  skill; needs a small API and an additive migration with a tested downgrade. No quest for time or clicks alone.
- **Passport**: game styling around the record, never on the evidence itself. Untouched so far.
- **Lesson** scroll view and side column (stepper, Ask Soc) only have the shared restyle.
- Today's moments stack if both fire on one visit; show one at a time if that feels busy on a real day.

### 3. Housekeeping
- `@fontsource-variable/bricolage-grotesque` and `plus-jakarta-sans` are no longer imported; remove them from
  `apps/web/package.json` and the lockfile in their own change.
- The `--db-*` token and `.db-*` class names are Daybreak-era names kept to limit churn; rename to `--gm-*` if touched.
- Re-baseline the Playwright visual specs once the e2e specs are re-seeded with a generated course.
- Check the JS budget in CI (410 KB on `gbuild/main`).
- The week strip on `/dev-gallery` has a date-locale hydration warning (server and browser format dates differently);
  it predates this work.

## When you finish a piece
Update this file, update `not-verified.md`, run `npx tsc --noEmit -p apps/web`,
`node --experimental-strip-types --test apps/web/tests/*.test.mjs` and the API tests you touched, and check the page in
the browser at phone width in Classic light, Classic dark and one other palette.
