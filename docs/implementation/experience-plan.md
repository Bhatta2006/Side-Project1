# Experience plan: calm lessons, fast courses, honest practice

Written 2026-11-05 on `feat/universal-engine` after the owner's review: "ours is so complex and
so much text based that a user can get overwhelmed". This plan joins three sources:

1. **Our own code**, read for this plan (the lesson page, `/new`, Today, the quiz page, the
   package job). Facts below cite files.
2. **Wondering's signed-in record** (`research/wondering/2026-11-05/`, analysis in
   `universal-engine-audit-3.md` sections 7 to 10).
3. **Learning research** on how much to show at once. These references are from the author's
   knowledge and were not re-checked against the publications for this plan; the evidence
   library rule applies (`engine/evidence_library.py`, `REVIEWED_BY` stays empty until a
   qualified person checks them).

Nothing here is built yet except where it says "done". It needs the owner's approval of the
direction (section 9) before any page is edited; the standing UI rule is "show an audit and
direction before editing a new page, scoped per page".

---

## 1. What we found

### 1.1 The lesson page shows everything at once

`apps/web/src/app/learn/[...concept]/page.tsx` renders, top to bottom, up to **twenty blocks**
around one long Markdown text: header card, Read/Check/Practice stepper, summary, Listen,
the concept visual, a locked notice, weak prerequisites, a support step, a translation notice,
**the AI-generated warning box (a triangle-alert icon, above the lesson)**, "Your path through
this lesson", the lesson, "Where each claim comes from", feel controls, "Explain it
differently", the finish block, key reminders, pitfalls, written answers, practice problems,
"Practise this topic", Python skill builders, external practice and resources. The desktop side
column repeats the stepper, adds "Why it is taught this way", "On this page", Ask Soc, key
reminders and pitfalls.

The lesson itself is one scroll of **2,000 to 4,000 characters** (`package.MIN_LESSON`;
bite lessons are shorter, `style/spec.BITE_RANGE`). Nothing in it asks the learner to do
anything until the concept check at the end.

### 1.2 The course plan reads like a report

`apps/web/src/app/new/page.tsx` shows, for every lesson of the plan: title, every objective,
minutes, the evidence types ("You will recognise, apply, explain"), **prerequisites as raw ids**
(`After: what-is-ml, loss`) and, above, "What the plan assumes" and a paragraph on how lessons
are written. Fifteen lessons is a page of small grey text.

### 1.3 Today has nine sections

`apps/web/src/app/today/page.tsx`: next step, Ask Soc, today's session, skill map, practice
picked for you, skills to learn next, the week, course progress, and more. The one thing to do
next competes with eight others.

### 1.4 Generation waits on five models in a row

One package round (`coursegen/jobs.run_package`) is a chain: researcher → author (up to 16,000
tokens) → quiz and atoms together → code runs → fact checker and reviewer together → designer.
Up to three rounds. The first live run: outline 48 s, 4 of 6 first lessons in 10 minutes.
Wondering: outline 6.6 s, first lesson about 50 s after "Create", from one joint lesson-and-
practice call of about 38 s.

### 1.5 What Wondering does that makes it feel easy

| Pattern | Evidence in the record |
|---|---|
| **One idea per screen.** A lesson is 7 pages of 600-1,000 characters, a progress bar of dots, one Next button (`15-reading.png`) | `responses/101-lesson_sessions.json` `pages[]` |
| **At most one interactive piece per page**, from 6 generic components (table, stepper, compare toggle, comparison, pyramid, "lens") | same file, `{{interactive:...}}` |
| **Guess first.** Page 1 asks a question and the "lens" says "make your guess now, then check it as you read on" | page 1 of lesson 1 |
| **Terms defined on tap** (`keywords`), **three follow-up questions** at the end | `keywords`, `followUpQuestions` |
| **Outline is names only**, expandable, with chips "4 sections · 12 lessons · ~1 hr · ~3 days at 20 min", and two buttons: Request changes, Create course (`11-outline.png`) | `004-generate-lesson-plan-from-content.json` |
| **The path is a map, not a list**: lessons, an applied lesson, section review, live challenge (`13-course.png`) | `isAppliedLesson` rows |
| **One choice before starting**: Read, Listen or Watch (`12-created.png`) | |
| **Small contracts**: outline = 3 strings per lesson; practice menu and count fixed per lesson before writing; correct option marked in the item | `007-course_nodes.json`, `055-practices.json` |

What they do not show: any fact check, review round, graded evidence or verified practice.
Those stay Socrat's strength (section 6).

### 1.6 What the research says (from the author's knowledge, to be checked)

| Finding | Source | What it means here |
|---|---|---|
| Learners do better when a lesson is cut into **learner-paced segments** than as one continuous piece | Mayer, segmenting principle (Multimedia Learning, 2009; Mayer & Pilegard 2014) | Pages with Next, not one scroll |
| Removing material that is not needed for the goal improves learning (**coherence**); **signalling** the structure helps | Mayer, coherence and signalling principles | Move trust details, resources, pitfalls and "why taught this way" off the reading path |
| Knowing the **key terms before** the lesson eases it (**pre-training**) | Mayer, pre-training principle | Key terms on tap; a term list before page 1 for new subjects |
| Working memory is small; extraneous load competes with learning | Sweller, cognitive load theory (1988; Sweller, van Merriënboer & Paas 1998) | One idea and at most one visual per page |
| **Questions inside** the reading beat the same questions only at the end; testing beats re-reading | Roediger & Karpicke 2006 (testing effect); adjunct-question research (Hamaker 1986) | Put one check between pages, not all at the end |
| Answering **before** being taught (pretesting), even wrongly, improves later recall | Richland, Kornell & Kao 2009 | Guess-first opening page |
| Worked examples help novices; the benefit fades and reverses with expertise | Kalyuga et al. 2003, expertise reversal effect | Depth on request: "Go deeper" pages, not longer default lessons |
| Show the few options people need and keep the rest one step away | Nielsen Norman Group, progressive disclosure | Details in disclosures, one primary action per screen |

---

## 2. Principles (every change below follows these)

1. **One thing per screen.** One idea, one interactive piece, one primary button.
2. **Do before read more.** A check, a guess or a choice every one or two pages.
3. **Details on demand.** Anything not needed to learn the next idea moves behind a disclosure
   or to the end of the lesson.
4. **Honest, not loud.** Trust information stays visible and complete, but at the end of the
   lesson (section 5), not as a warning above it.
5. **Depth is a choice, not a default.** Short by default; "Go deeper" adds pages.
6. **Models write, code decides** (unchanged). Every new contract is checked by code.
7. **Measured.** Each phase has a number that must move (section 8).

---

## 3. Lesson experience (web), phase A

### A1. Lesson in pages (the core change)

- The lesson renders as **pages**: one `## ` section per page, a dot progress bar, Back and
  Next, keyboard (arrow keys) and swipe on phones. Works for **every existing lesson** at once:
  `components/markdown.outline` already splits by heading. No generation change is needed for
  this step.
- A setting "Show the whole lesson on one page" keeps today's scroll for those who prefer it
  (and for printing and screen readers who want it), remembered per device.
- **A check between pages.** The concept's atom checks (`predict`, `explanation`, `trace`
  steps, already generated and validated) are placed after the page they belong to, one at a
  time. They are practice, not evidence (as today).
- **Last page is a recap**: the key points (`key_points`), the two most common pitfalls, and
  one button, "Take the concept check".
- Self-check questions inside `<details>` become the last check page instead of a block of
  text.

### A2. What moves off the reading path

| Today (above or around the lesson) | Moves to |
|---|---|
| AI-generated warning box | "About this lesson" footnote (section 5) |
| Translation notice | Footnote, plus a small language chip in the header |
| "Your path through this lesson" box | The dot progress bar |
| Stepper (Read/Check/Practice) twice | Once, in the header, as three small marks |
| "Where each claim comes from" | Footnote |
| "Why it is taught this way" | Footnote |
| Key reminders, pitfalls (side column and mobile) | Recap page |
| Explain it differently | A small toolbar on each page: "Simpler", "Another example", "Go deeper" |
| Resources, handbook, implementations | "Go further" on the recap page, collapsed |
| Practice problems, practise this topic, skill builders, external practice | One "Practice" card on the recap page, linking to the Practice page |
| Feel controls | The recap page |

Above the first page stays only: title, the three marks, Listen, and the concept visual when
it teaches the first idea.

### A3. Key terms and follow-up questions

- Terms are underlined; a tap shows the definition (popover, keyboard reachable). For existing
  lessons, terms come from the course glossary where there is one; for new lessons, from A-B1
  below.
- The recap page shows three follow-up questions as chips that open Ask Soc with the question
  filled in.

### A4. Done means

Above the fold before the first Next: at most **120 words** of learner-facing text besides the
lesson's first page (today it is several hundred with the notices). A Playwright check counts it
on a generated and a hand-authored lesson, desktop and phone, with an axe pass.

---

## 4. Course plan, Today and Practice screens, phase B

### B-UI1. The plan on `/new`

- Module names and lesson names only; a lesson expands to its objectives and minutes.
- Chips at the top: modules, lessons, total time, and **days at the learner's own daily time**,
  worked out by code from `estimated_minutes` and the request's minutes per day.
- Two buttons: **Request changes** (a text box; the request goes to the architect as notes, as
  revise does today) and **Start this course**.
- "What the plan assumes", evidence types and prerequisites move into a "Plan details"
  disclosure; prerequisites shown as **titles**, never ids.
- The paragraph on how lessons are written becomes one line under the chips.

### B-UI2. The course path

A vertical path like the plan page's list, but with the module's **Apply lesson** (done, flag
`gen_applied_lessons`) and the module checkpoint shown as their own stops, locked stops
greyed. One primary "Continue" button.

### B-UI3. Today

One large card: **Continue: <lesson>, about N minutes**, with Read or Listen. Reviews due
appear as one line under it ("3 reviews, 2 minutes"). Everything else (skill map, week, course
progress, practice picked for you, skills to learn next) moves to Progress or behind "More".

### B-UI4. Practice page

Practice sets already show one question at a time. Keep that; add a short result screen (score,
the one idea to revisit, "Practise again" or "Back to lesson").

---

## 5. Trust information at the end of each lesson

The owner's wish: AI-generated and fact-check information should not pop up at the front; it
can be a star at the end of each lesson.

- The lesson title carries a small **★** (an accessible link, label "About this lesson"). It
  jumps to an **"About this lesson"** footnote after the last page.
- The footnote holds, in plain words: written by Socrat AI and checked by AI models (or
  confirmed by a named person); the validation state label; when it needs a person
  (`human_review_required`); the translation state with "show the original"; where each claim
  comes from; why it is taught this way; Report a problem.
- **Kept at the front, deliberately:** a lesson labelled `human_review_required` for a hazardous
  or high-stakes subject (health, law, money, physical safety; `engine/safety.py`) keeps a
  one-line note above page 1, because its safety notes must be read before acting. Everything
  else moves to the footnote.
- The course card and the course plan keep their one-line "Made by AI" label (the community
  and moderation rules rely on it), small and without a warning icon.
- Needs the owner's confirmation (section 9) because it changes an honesty label.

---

## 6. Generation: faster, smaller contracts, phase C

Targets, measured by `scripts/dev/benchmark.py` with a live model: **plan visible in 15 s or
less, first lesson readable in 90 s or less**, cost per released lesson not higher than today.

### C1. Plan in two steps

The architect already writes a skeleton and then details (`outline.skeleton_of`, `_detail`).
Show the **skeleton** (module and lesson titles plus a one-line hook per lesson, the Wondering
contract) as soon as it exists; details and the critic finish in the background before Start
is allowed. The learner's "Request changes" is a real review step; the critic stays.

### C2. Lesson pages as the contract (B1 in generation terms)

The author returns `pages: [{heading, body}]` instead of one `lesson` string:
5-8 pages for standard, 3-4 for bite, 8-12 for deep; each page 400-1,000 characters; at most one
visual per page; page 1 opens with a question the learner answers before reading; plus
`terms: [{term, definition}]` and `follow_ups: [3 questions]`. Code checks every number; terms
not found in the text are dropped; the page count replaces the character floor. The stored
`lesson` stays the pages joined with `## ` headings, so every reader of `Concept.lesson`
(translation, fact check, tutor, search) keeps working. Old lessons need no migration.
Behind flag `gen_lesson_pages`.

### C3. Fewer models in a row

1. **Quiz and atoms start from the lesson brief, beside the author**, not after it: the
   outline's objectives and misconceptions plus the strategist's plan are enough for items,
   which Wondering does with its concept brief. The fact checker already compares quiz keys
   with the lesson, so a drift is caught. Saves one model wait per round. Measure first: run
   the benchmark with both orders and compare `incorrect` quiz claims.
2. **Designer after release.** Visuals never block a lesson today; write them after release
   and add them as a new version (as the maintainer does), so the learner is not kept waiting.
3. **Researcher only with search providers.** Without providers it names sources from memory,
   which the link check then removes or keeps; skip the call and let the author list sources,
   as it does already.
4. **First lesson first, smallest first.** The first lesson of a new course is written as a
   bite lesson (3-4 pages) whatever the format, with "Go deeper" available at once; the rest
   follow the learner's format.

Expected: two model waits in a row instead of five, before any revision round. Not measured.

### C4. Practice menu fixed per lesson

The outline already carries `practice` and `assessment` per concept, fitted to the studio
(section 7 of audit 3). Add, by code: which practice-set kinds fit the studio (`choice`,
`number`, `text`, `order`, `match`) and a count range, so every writer knows exactly what to
produce before writing (Wondering's `practiceTypes` and `targetPracticeCount`).

---

## 7. Quiz, practice sets and evidence, phase D

### D1. Item contracts (correctness inside the item)

- Done: the right option is marked in quiz and atom items (`coursegen/keyed.py`, flag
  `gen_marked_answers`).
- Add to practice sets (`drills/`): **true or false with a reason** (binary choice), and
  **fill the gap** written Anki-style inside the sentence (`the {{c1::denominator}} is 10`), so
  the blank and its answer cannot disagree; code derives both. Graded on the server like the
  other kinds.
- Every item keeps an explanation (already required).

### D2. Practice that counts (owner decision)

Practice sets write **no evidence** today (audit 3, section 4.3). Proposal:

- An item counts only after it passes the deterministic checks **and** the fact checker found
  nothing `incorrect` in it (one fact-check call per set, metered).
- It counts as `retrieval` evidence (recall) at a lower weight than a concept-check item, and
  never as application unless it is a `number` or `order` item checked by the workbench or by
  code.
- Unreviewed items stay labelled; the human-review gate for hand-authored families is not
  touched.

### D3. One review across courses

Reviews are per active course by default (`learn/reviews.py`, `?scope=all` is opt-in). Wondering
runs one global review of 8 items (4 for a quick one), interleaved by course. Proposal: Today's
review line offers "Review across your courses" with the same session sizes, using the
existing scheduler (not FSRS) and the items that count (D2).

### D4. Evidence from the Apply lesson

Today the Apply lesson's quiz and explanation are evidence for itself only. Proposal: when the
learner passes the Apply lesson's explanation (rubric-graded), write one `transfer` row for each
module concept it combined, at the transfer weight, with the Apply lesson as its source. This
is what the "demonstrated" stage needs and generated non-code courses cannot produce today.
Needs the owner's yes, because it changes what counts as mastery.

---

## 8. How we will know it worked

| Measure | Today | Target | How |
|---|---|---|---|
| Learner-facing words before the first action on a lesson | several hundred (notices, path box, summary) | at most 120 | Playwright count, desktop and phone |
| Blocks on the lesson page around the reading | up to 20 | 4 (title, marks, Listen, visual) plus pages | same |
| Time to plan visible | 48 s (one live run) | 15 s | benchmark, live model |
| Time to first lesson readable | minutes (4 of 6 in 10 min) | 90 s | benchmark |
| Quiz keys the fact checker marks `incorrect` | not measured | lower with `gen_marked_answers` | benchmark, flag off then on |
| Lesson pages finished / lessons opened | not recorded | recorded, then compared | activity events (page index), no new personal data |
| Concept check taken after reading | recorded | up | existing activity records |

---

## 9. Decisions only the owner can make

1. **Approve the direction** for the lesson page (pages, what moves off the reading path, the
   one-page setting) before any page is edited.
2. **Trust footnote**: move the AI-generated notice to the ★ footnote at the end, keeping the
   one-line safety note at the front for hazardous and high-stakes subjects, and the small
   "Made by AI" label on course cards.
3. **Practice that counts** (D2): may practice-set items write `retrieval` evidence at a lower
   weight, after the fact check?
4. **Apply lesson evidence** (D4): may passing it write `transfer` evidence for the module's
   concepts?
5. **Global review** (D3): one review across courses on Today?
6. A **live-model key** for the benchmark (phase C and the measures cannot be proven without it).
   Not ChatGPT 5.5.

---

## 10. Order of work

| Phase | What | Needs | Size |
|---|---|---|---|
| A1-A2 | Lesson in pages, things off the reading path, recap page | decision 1, 2 | 2-3 days with browser tests |
| 5 | ★ About this lesson footnote | decision 2 | half a day (with A2) |
| B-UI1 | Plan on `/new`: names, chips, Request changes, details disclosure | decision 1 | 1 day |
| B-UI3 | Today with one Continue card | decision 1 | 1 day |
| C2 | Lesson pages, terms and follow-ups as the generation contract (flag) | none | 1-2 days |
| A3 | Terms on tap, follow-up chips | C2 for new lessons | 1 day |
| C3, C1 | Fewer models in a row, plan skeleton first | live key to measure | 2 days |
| D1 | True or false and fill-the-gap practice kinds | none | 1 day |
| C4 | Practice menu per lesson | none | half a day |
| B-UI2 | Course path with Apply and checkpoint stops | none | 1 day |
| D2-D4 | Evidence from practice, global review, Apply evidence | decisions 3-5 | 2-3 days |

Each step: flag off by default where it changes behaviour, tests that fail on the old code
where it fixes something, the related test subsets plus the full API suite before pushing, the
Playwright visuals and accessibility suites for every web change, and an entry in the progress
log. Web work follows the notebook brand (`HANDOFF.md` section 10): highlighter only on the
hero, nothing lifts on hover, no glass, Geist, and the book-blue accent only for the main
action.
