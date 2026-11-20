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

## Backlog, in order

### 1. Owner decision first
- **Flag or default?** Project rule: new features default off behind a flag. Daybreak is currently the default look.
  Ask the owner whether to keep it default or gate it (for example a `daybreak_look` feature that changes the boot
  default). Do not decide alone.

### 2. Verify slice 1 with a real course (nothing below counts until this passes)
- Today with a generated course: game strip numbers match `/today`, Path tab shows the module, current stone and
  Start bubble, labels never overlap the stones on 360px phones.
- A real quiz with `lesson_feel` on: sheet, combo chip, sounds, Enter to continue, focus moves to the button.
- A real session end with `session_end` on: each screen kind (evidence, streak, badge, next) and the celebration sound
  plays once only.
- Sounds on a real Android and iPhone (home-screen app): first sound after a tap, silent switch, the Settings switch.
- Dark mode in Daybreak, and a walk through the notebook palettes (Classic) to catch regressions from the ink change.
- Contrast: white text on every palette's primary (Sunset and Lagoon are the risky ones) and the `-ink` colours on
  their tints, to WCAG AA.

### 3. Screens still to design in Daybreak (use the approved boards)
- **Lesson page** (`app/learn/[...concept]/page.tsx`): a top progress bar with a close button, one step per card,
  Soc in a speech bubble for the Socratic prompts, a fixed bottom Check/Continue bar (`.stamp`) on phones,
  code blocks in Daybreak style, a tap clack on choices (`play('tap')`).
- **Quiz page** (`app/quiz/[...activity]/page.tsx`): answer options as choice tiles with a selected state, the same
  fixed bottom bar, the progress bar glowing marigold from `RUN_GLOW` (flat colour change, not a glow effect).
- **Profile / Progress / Passport** (`app/progress`, `app/passport`): violet header with Soc, level bar from
  `levelFor`, stat tiles (streak, XP, skills proven, mastered), the week calendar in ember, badges as pebble stickers.
  Passport stays the proof record: game styling around it, never on the evidence itself.
- **Shell and navigation** (`components/shell.tsx`): bottom tab bar and sidebar in Daybreak, custom icons drawn in the
  game-emoji style, the active tab as a tinted pill.
- **Onboarding `/start`**: visual only, the cofounder owns the flow (`docs/implementation/onboarding-handoff.md`).
  Pebble trio on the first question, daily goal choices named Taste 5 / Steady 10 / Serious 20 / Deep 30
  (`DAILY_GOALS`), a short celebration when the course plan is ready.
- **Landing and login**: still half notebook (script headline, highlighter). Restyle to match, keeping
  "Learn it. Then prove it." as the line.

### 4. Game features still to build (each behind a flag, evidence only)
- **Daily goal reached** moment on Today and at session end (Jade, `play('streak')`), from `minutes.reached`.
- **Capability quests** with Amber: two or three per week, each tied to proving a named skill (needs a small API:
  quest = skill + check, done when the check passes). No quest for time or clicks alone.
- **Badges as pebble stickers** on the profile, from the existing badge screens.
- **Streak milestones** (7, 30, 100) with Ember, freezes shown as frozen pebbles.
- **Level-up moment** when `levelFor` crosses a boundary (Ami), shown once.
- Optional: count-up animation on XP and stat tiles.

### 5. Polish and housekeeping
- More game emoji as screens need them (book, map, lightbulb, flag); same rim and flat style.
- Replace remaining stock icons in game moments with game emoji.
- Re-baseline the Playwright visual specs once the e2e specs are re-seeded with a generated course.
- Check the JS budget in CI (410 KB on `gbuild/main`) with the new components and fonts.
- Remove `/dev-mascots/daybreak` once every piece is visible on a real page, or keep it as the living style board.

## When you finish a piece
Update this file (move the line to "Built"), update `not-verified.md`, run `npx tsc --noEmit -p apps/web`,
`node --experimental-strip-types --test apps/web/tests/*.test.mjs` and the API tests you touched, and check the page in
the browser at phone width in Daybreak light, Daybreak dark and Classic.
