# Socrat Universal Learning Engine: product spec and gap list

Written 2026-11-10 against `feat/universal-engine` at `ce6a493`, from the owner's description of
the final product and a read of the code. Part 1 is what the product is. Part 2 is where the code
stands. Part 3 is every gap, why it exists (with the file), and how to fix it, in priority order.

Earlier documents this builds on: `docs/implementation/HANDOFF.md`, `ule-gap-audit.md`,
`universal-engine-audit-3.md`, `experience-plan.md`, `docs/engine/README.md`.

### Owner's clarifications (2026-11-10): these override anything below that disagrees

1. **The engine finds the material itself.** It searches and reads YouTube, articles, papers,
   open books and free courses, then writes the course from them. The learner is never asked
   for a link, a PDF or a book.
2. **Checks must let good lessons through.** A check that fails every lesson is a broken
   check. Code repairs what it can, drops a bad item instead of the whole lesson, and holds a
   lesson back only for a real defect.
3. **Nothing may be stuck in the DSA template.** Code, UI, UX and generation adapt to the
   course. A course that needs a section the template lacks gets that section.
4. **Stronger agents, low cost.** A strong model where judgement matters, a cheap one where
   it does not, and reuse wherever the same work was already paid for.
5. **Borrow ideas from Wondering, not its product.** Small contracts, skeleton first, the
   next lesson prepared ahead, the answer marked inside the item, one idea per page.

6. **Any age, any style.** The 5-year-old and the university student are examples, not the
   two audiences. A learner can be any age and can ask to be taught in any way they can
   describe. Age groups and style lists in the code are shortcuts for the learner, never a
   limit: the learner's own words decide.

---

## Part 1. The product

**One sentence.** Socrat is a personal tutor for any subject and any learner: you say what you
want to learn and how, it hands you a course within a minute, and it keeps reshaping that course
around how you actually do.

**What makes it not an AI wrapper.** The model writes; the engine decides. Every lesson is
sourced and cited, every answer is graded by code or a rubric, progress is evidence the learner
earned without help, and the plan changes for stated reasons the learner can undo.

### 1.1 The loop

| Step | What the learner experiences | Target |
|---|---|---|
| 1. Ask | One box: "quantum physics for a 5-year-old, gamified, 15 minutes a day" or "university-level computer science, 2 hours a day". Optional chips for who, level, style, time. At most two clarifying questions. The learner supplies nothing else | answer in under 5 s |
| 2. Match or build | The engine looks for a course that already fits. Exact fit: start it now. Close fit: start it, with the differences personalised. No fit: build from scratch | match in under 2 s |
| 3. Blueprint | Modules and lesson names, total time, days at the learner's daily time. "Request changes" or "Start" | visible in 15 s, complete in 30 to 60 s |
| 4. First lesson | Readable while the rest of the course is still being written | 60 s after the ask |
| 5. Learn | One idea per page, sized for this learner, a small check every page or two, visuals where they teach, listen mode | next lesson always ready |
| 6. Practise | A Practice section built for the subject (see 1.4), plus checkpoints and assessments | no waiting |
| 7. Visualise | "Show me" on anything unclear: a sketch, a 3D film or a simulation, made from the prompt | 30 to 60 s, cached after |
| 8. Adapt | The coach watches, explains what it sees and proposes the next move | every session |

### 1.2 Any learner

The same engine serves a 5-year-old and a graduate student because four things are computed
from the request, never fixed: **register** (words, examples, tone), **page size and rhythm**
(30 words and a game scene, or 500 words and a derivation), **depth and rigor** (overview,
practitioner, mastery), and **session length** (5 minutes to 2 hours a day).

- Children under 13 learn through a **guardian account** (a parent signs up, adds a child
  profile, sees progress). Game mechanics are real product features for them: quests, stars,
  levels, streaks.
- University and professional courses carry **structure**: units, weekly load, graded
  assignments, exams, a syllabus that can be imported, a deadline the plan is paced against.

### 1.3 Build fast, build gradually

1. Blueprint first, as names and one-line hooks. Details fill in behind it.
2. The first lesson starts being written the moment the blueprint's first names exist, before
   the learner has finished reading the plan.
3. The first lesson is released on fast checks; the deep checks (fact check, review) run right
   after and can upgrade or withdraw it.
4. The engine keeps two to three lessons, their practice and their checks ready ahead of the
   learner. If the learner outruns it, they get review or practice, never a spinner.
5. Sources are gathered once per course (videos, open textbooks, articles, papers), ranked,
   and shared by every lesson. Everything used is cited; nothing is copied.
6. A lesson written once is shared by every later learner who needs the same thing.

### 1.4 Practice shaped by the subject

| Subject kind | Practice section |
|---|---|
| Programming | Editor, judged problems, tests |
| Math | Workbench: step-checked derivations, numeric answers, graphs |
| Physics, chemistry, engineering | Predict, run a simulation, explain |
| Languages | Fill the gap, listening, speaking, conversation |
| Young children | Tap, match, order and drag games with instant feedback |
| Humanities, business, everything else | Cases, short written answers graded by rubric, recall sets |

Every course also gets: a check inside each lesson, a concept check at its end, a module
checkpoint, an "Apply" lesson per module, and spaced reviews across all the learner's courses.

### 1.5 The coach

Signals it watches: right and wrong answers, help used, time against plan, pages reread,
"explain it simpler" taps, questions asked to the tutor, days away, repeated mistakes.

| It sees | It does |
|---|---|
| Comfortable, answering everything | "Take the checkpoint and skip ahead"; offers a harder path |
| Stuck on a problem | Names the idea underneath; offers an easier problem that builds the intuition first |
| Stuck on a concept | Worked example, then a simpler explanation, then a prerequisite check, then a bridge lesson |
| Slow or behind the deadline | Shorter sessions, fewer optional topics, or a new date; the learner picks |
| Back after a break | A short re-check and a gentler week |
| Forgetting | Reviews, scheduled per item |

Every change has a reason in plain words and an undo. The tutor (Soc) knows the course, the
lesson, the learner's history and how they asked to be taught, and never hands over an answer
the learner has not tried for.

### 1.6 What else the product needs to feel complete

1. **Learner memory across courses**: what they know, how they like to be taught, their goals.
2. **Trust on every lesson**: sources, what was checked and by what, a report button.
3. **Proof of skill**: a shareable record built only from independent evidence.
4. **A source shelf per course**: the videos, chapters, articles, papers and free courses the
   engine found and used, open to the learner as further study.
5. **Go deeper / simpler / another example** on any page.
6. **Any language, and voice**: lessons and tutor in the learner's language; listen and speak.
7. **Phone first**: installable, works on slow connections, lessons readable offline.
8. **Community**: share a course with consent and credit; creators earn perks.
9. **Plans and limits**: generation and visual quotas per plan, shown before they are hit.
10. **A quality loop**: a benchmark of representative courses run on every change; outcome
    numbers (retention, transfer, hint dependence) per course.

---

## Part 2. Where the code stands

| Pillar | State | Evidence |
|---|---|---|
| Ask and understand the request | Built | `coursegen/intent.py`, `requests.py`, `/new` |
| Match an existing course | **Missing** | only byte-identical briefs reuse an outline (`jobs.design_key`) |
| Blueprint | Built, slow | `jobs.run_outline`: 48 s in the one live run; shown only when complete |
| First lesson in a minute | **Missing** | 4 of 6 first lessons took 10 minutes; nothing is written until the learner presses Start |
| Next lesson ready ahead | Built, fragile | `prefetch.py` keeps 3 ahead; one job at a time by default, no priority |
| Sources | Partial, off | Wikipedia, Wikibooks, arXiv, Open Library, YouTube; no web or article search; off by default |
| Lesson experience | Mostly built | pages, recap, footnote; in-lesson checks and terms not built |
| Practice by subject | Partial | 4 studios (code, workbench, lab, reading) plus generic practice sets that count for nothing |
| Visualise anything | Built, not connected | Playground is a separate page, zero uses on the free plan, no link from a lesson |
| Adaptive coach | Strong for code, thin elsewhere | planner, stuck ladder, proposals exist; non-code courses feed them almost no signals |
| Any learner | Partial | registers and page profiles exist; under-13 cannot register; "gamified" is only a writing instruction |
| Shipped | **No** | branch is 76 commits ahead of `main`, 3 behind, 6 merge conflicts, no PR, no CI run, every flag off |

Verified in this session: 58 engine tests pass (`test_learning_requests`, `test_engine_e2e`,
`test_drills`, `test_coursegen`, `test_engine_coach`, `test_resource_search`, `test_scale`).
Not run: the full suite, the browser suites, any live model.

---

## Part 3. Gaps and fixes

### P0: these break the core promise

**G1. Speed: 10 minutes where the product needs 1.**
Why, in the code:
- `jobs.run_outline` saves the plan only after architect (16,000-token budget, high effort),
  detail calls and the critic have all finished. The learner sees nothing until then.
- Lessons are queued in `requests.publish`, so no lesson is written while the learner reads
  the plan.
- `jobs.run_package` is a chain of waits: search, researcher, author (16,000 tokens),
  quiz and atoms, code runs, fact check and reviewer, a polish round, up to 3 rounds (5 in the
  local `.env`). Nothing reaches the learner until all of it passes.
- `gen_runner_concurrency` defaults to 1 and `jobs.claim` takes the oldest job of any course,
  so a new learner's first lesson waits behind other learners' prefetch.
- The web polls; nothing streams.

Fix:
1. Save and show the skeleton (names and hooks) as soon as the architect's first reply parses;
   details and critic continue behind it. Ask for the skeleton alone, at low effort.
2. Queue lesson 1 when the skeleton is saved, not at publish. If the learner asks for changes
   that drop it, cancel the job.
3. A fast path for the first lesson of a course: one joint call for lesson, checks and quiz in
   bite size; release on deterministic gates only; fact check and reviewer run after release
   and either confirm it, patch it as a new version or withdraw it.
4. Job priority in `claim`: first lesson, then the lesson a learner is waiting on, then
   prefetch, with fairness per course. Raise concurrency and run generation in the worker.
5. Gather sources once per course at outline time; lessons pick from that shelf.
6. Stream lesson pages to the browser as they are written (server-sent events).
7. Measure each step with `scripts/dev/benchmark.py` on a live model. Done means: skeleton in
   15 s, first lesson in 60 s, for the eight benchmark subjects.

**G2. No "does this course already exist?"**
Why: `intents.slug` puts the learner's id in the course id, every course is private, and
`jobs.reusable_outline` matches only a byte-identical brief among the last 200 outline jobs,
then copies the outline and rewrites every lesson. Cost and wait grow with every learner.

Fix:
1. A canonical course key from the normalised intent (subject, level, register, style,
   minutes bucket, language) plus an embedding of the subject and goal.
2. Three outcomes at confirm: exact (enrol in the shared course now), close (fork it: keep
   matching lessons, rewrite what differs), none (build).
3. A lesson cache keyed by concept and audience profile, so a released lesson is reused
   across courses. Only moderated, passing lessons enter it.
4. Show the learner the match: "This course exists. Start now, or customise."

**G3. The engine has never run for real.**
Why: every role has only seen hand-written replies, apart from one fractions run. The
eight-subject benchmark has not been run. The local `.env` already has a provider, a model and
research providers set, so it can be run today.

Fix: run the benchmark for the eight archetypes plus the two examples in this spec; record
JSON conformance, time and cost per role; fix prompts until the gates pass in one round.

**G4. Nothing is shipped.**
Why: 76 commits ahead of `main` and 3 behind (#65 strict placement, #66, #67 UX polish); a
trial merge shows 6 conflicts; no PR, no CI; `learning_requests_enabled` and every other
engine flag is off. `main` has no new migrations, so numbering is safe.

Fix: owner decides how to reconcile (standing rule is no merging `main` into the branch);
resolve the 6 conflicts; open a draft PR for CI; run the full API and browser suites; turn
flags on for admins first.

**G5. A long course stops itself.**
Why: a learner's course has a $3 total budget (`learning_request_budget_usd`), and
`pause_for_budget` pauses generation when it is spent. A university course of 100 or more
lessons cannot finish.

Fix: budget per lesson and per plan tier, not per course; reuse (G2) pays for most of it;
show the learner a quota, not a pause.

### P1: these make it a tutor rather than a course generator

**G6. Practice is generic outside four studios, and it counts for nothing.**
Why: `catalog/shape.py` has code, workbench, lab and reading. Everything else gets
`drills/`: five questions, written on demand by one model call, 12 sets a day, no evidence.
No language, music, or children's formats.

Fix: a practice plan per course at outline time (kinds and counts by subject); an item bank
written with each lesson, not on demand; more kinds (fill the gap, true or false with a
reason, tap and label, listen and speak); items count as low-weight recall evidence once they
pass code checks and a fact check (owner decision D2 in `experience-plan.md`).

**G7. The coach is nearly blind in non-code courses.**
Why: `adaptive/profile.py` is built from scored evidence, verdicts and solve times. In a
generated course only the end-of-lesson quiz and graded answers produce evidence; in-lesson
checks, practice sets, visuals and reading behaviour produce none. "Solve this easier problem
first" exists only for the programming library.

Fix: record lesson events (page reached, time, check result, simpler or deeper taps, tutor
questions) as low-weight signals; practice evidence from G6; an intuition ladder for any
course (an easier item on the same idea, then on its prerequisite); a learner memory the
tutor and planner both read.

**G8. Visualise is a separate, paid page.**
Why: no link from a lesson to the Playground; the free plan allows 0 a day
(`entitlements.py`); lesson visuals are behind `gen_visuals` (off); visuals write no
evidence; nothing checks a 3D film against the real object.

Fix: "Show me" on any lesson page, sent with the lesson's context; cache visuals per concept
and share them; a small free allowance; turn on lesson visuals after a reviewed sample; the
vision review loop when the owner approves it.

**G9. The youngest and the most advanced learners are not really served.**
Why: `MIN_AGE = 13` in `learn/routes.py`, with no guardian account. "Gamified" is one
sentence in the author's prompt (`style/spec.py`), with no quests, stars or levels in the
app. Time presets stop at 1 hour. No deadline in the intent. No syllabus import, units or
graded assignments for university courses.

Fix: guardian accounts with child profiles (needs the legal review already listed for
minors); a game layer the web renders for gamified courses; 90 and 120 minute presets and a
target date; a university template (units, weekly load, assignments, exams) and syllabus
import.

**G10. Sources are narrow and shallow.**
Why: `coursegen/search.py` covers Wikipedia, Wikibooks, arXiv, Open Library and YouTube. No
general web or article search. Passages are search snippets, not page text. Video transcripts
are off. Links and PDFs are not read.

Fix: one web search provider behind the same interface; free-course catalogues (MIT
OpenCourseWare, OpenStax, Khan Academy, LibreTexts) as providers; a safe page fetcher (no
private addresses, size and type limits) with text extraction, so lessons are written from
the page and not the snippet; transcripts on. The learner is never asked for material.

### P2: finish and harden

| Gap | Fix |
|---|---|
| Lesson experience leftovers: checks between pages, terms on tap, follow-up chips, swipe | `experience-plan.md` A1, A3 |
| `/new` plan is a report; Today has nine sections | `experience-plan.md` B-UI1, B-UI3 |
| A failed lesson stays failed for the learner (`prefetch.SETTLED` skips it) | automatic retry with a different model; a visible "try again" |
| No "your next lesson is ready" notice | event to the open page and a reminder |
| Rate limits are per process; worker split untested on a real stack | Redis limiter; run the runbook on staging |
| Everything not fully verifiable is labelled "a person must confirm" forever | reviewer queue with named sign-off; sample-based confidence |
| Translations partial; no speech | finish the i18n slice; speech provider |
| Older Playwright and visual suites never run on the branch | run before merge; update lesson baselines on purpose |
| No outcome numbers | `engine/outcomes.py` report on a schedule |

### Order of work

1. G3 live run (it tells us the real numbers for everything else).
2. G1 speed, measured against that run.
3. G4 reconcile with `main` and get CI running.
4. G2 match and reuse, with G5 budgets.
5. G6 and G7 together (practice that counts feeds the coach).
6. G8, then G9, then G10.
7. P2 alongside, starting with the lesson experience.

### Decisions only the owner can make

1. How to reconcile with `main` (merge, rebase, or a fresh branch).
2. May the first lesson be released before the fact check and review finish (G1 fix 3)?
3. May lessons be shared across learners' private courses (G2)?
4. May practice items count as evidence (G6)?
5. Under-13 learners through guardian accounts: yes or no, and who does the legal review (G9)?
6. Which web search provider, and are video transcripts allowed (G10)?

---

## Part 4. Progress log

### 2026-11-10, slice 1: lessons that pass, plans that are not DSA, a first lesson that starts early

| Change | Why | Where |
|---|---|---|
| Only a programming course is shown the DSA course and the Socrat concept list when its plan is written; every other subject gets a short, subject-neutral instruction | A children's physics plan was asked for with hundreds of lines of DSA in the prompt: slower, dearer, and it pulled the plan towards code | `coursegen/outline.py` (`SOFTWARE_ADAPTERS`, `GRANULARITY`) |
| The DSA reference lesson ("sliding window") goes to code courses only; the lesson writer's rules no longer ask every subject for edge cases, invariants and "when not to use it", and tell it to write for the learner described | Same pull towards code in every lesson | `coursegen/package.py` (`gold`, `LESSON`) |
| A dead or missing resource link no longer sends a lesson back; a generated lesson may be released with fewer than two links | The writer's replacement links mostly failed the same check and cost a whole round | `coursegen/jobs.py`, `catalog/schema.py` |
| Missing `<details>` self-checks no longer block; the length floor has 20% slack; two headings are enough | Formatting slips are not defects | `coursegen/package.py` |
| A quiz item or atom the fact checker calls incorrect is dropped (while three remain) instead of the part being rewritten | Rewrites fixed one item and broke another | `package.drop_disputed`, `jobs.run_package` |
| A rubric dimension the reviewer forgot to score is "unknown", not zero | One missing key failed the package | `package.verdict`, `validation._review` |
| When rounds run out, a package that passed every code gate, has no incorrect fact and has correctness at the floor is released with the reviewer's findings as warnings | A hole in the course is worse for the learner than a lesson with a visible "could be deeper" note. A wrong fact or a failed gate is still never released | `jobs.run_package` |
| Jobs have a priority: a plan, then a first lesson or the lesson a learner is waiting on, then the first slice, then lessons written ahead | Jobs ran oldest first across all courses, so a new learner waited behind background work | migration `0047`, `jobs.PRIORITY`, `jobs.claim` |
| A learner's first lesson is queued the moment their plan is saved, not when they press Start (`SOCRAT_GEN_EARLY_FIRST_LESSON`, on) | It is written while they read the plan | `jobs.early_first_lesson`, `prefetch.initial` |
| "Plus a coding task" on the weekly exam only for code courses; the Skill Passport says "graded work", not "judged submissions" | Programming words on non-programming courses | `apps/web` |

Tests: `tests/test_engine_any_course.py` (7 new), `test_coursegen_package.py` updated to the new
rules (one test split in two: a lesson the reviewer calls *wrong* still stays planned).

Not done in this slice, in order: a live-model run to measure the effect; skeleton shown before
details; the fast path for the first lesson; course-specific sections beyond the four studios;
match and reuse; web and free-course sources; stronger models per role with a cost report.

### 2026-11-10, slice 2: a course can have sections of its own

The lesson-and-practice template had no place for what a subject keeps beyond lessons: a
language's vocabulary, a history timeline, a music repertoire, a list of cases.

| Change | Where |
|---|---|
| A course plan may declare up to four sections of its own: id, title, purpose, a layout (cards, table, timeline, list) and the fields one entry holds. The architect is told when a subject needs one and that many need none; a malformed or repeated section is dropped by code, never a failed outline | `catalog/schema.py` (`Section`, `Course.sections`), `coursegen/outline.py` (`tidy_sections`) |
| Each lesson adds its entries to those sections. The quiz writer is asked for them only when the course has sections; an entry that does not fit is dropped, never a reason to send a lesson back | `Concept.entries`, `package.entries_block`, `package.check_entries` |
| Every course, hand-authored ones included, gets four sections built from its lessons at no model cost: key ideas, mistakes to avoid, formulas and sources | `learn/sections.py` |
| `GET /api/v1/sections` returns the active course's sections, grouped by lesson. Only lessons the learner has finished are shown, so it is their notebook and never previews a check | `learn/sections.py` |
| A Notes page in the app, with a tab per section, linked from Today and the search palette | `apps/web/src/app/notes/page.tsx` |

Checked: 5 new API tests (`test_course_sections.py`), 82 related tests, lint, types, and the
page in a real browser on the hand-authored Programming from Zero course (tabs, table layout,
no sideways scroll at 375 px, no console errors). Not checked: the cards and timeline layouts
with real entries in a browser (covered by the API test only), any section planned by a live
model, the Playwright suites. No migration: sections live in the stored course and concept JSON.

### 2026-11-10, slice 3: the engine finds and reads its own material

| Change | Where |
|---|---|
| Four new sources that need no key: Wikiversity and MIT OpenCourseWare (free courses), OpenStax (peer-reviewed open textbooks), OpenAlex (open-access papers in every field) | `coursegen/search.py` |
| A `web` source for articles and the wider web, through the Brave Search API. It needs `SOCRAT_WEB_SEARCH_API_KEY` and does nothing without it; the key travels in a header, never the URL | `coursegen/search.py`, `config.py` |
| The pages the researcher chooses are now read, and their text is what the lesson is written from and checked against (before: a two-line search snippet). Public https only, re-checked on every redirect; robots.txt honoured; HTML or plain text only; 1.5 MB cap; scripts, navigation and forms stripped; 6,000 characters a page, three pages a lesson | `coursegen/fetch.py`, `jobs.run_package` |
| Stop words no longer count as a match ("Algebra and Trigonometry" for "supply and demand"); results from whole-document searches that share no subject word are dropped; the researcher sees the best 24 | `search.gather`, `search.rank` |
| Fixed, from slice 1: for a learner placed further into the course, the early first lesson could be written before their real first lesson. A waiting early lesson now steps aside at publish | `prefetch.initial` |

Checked: 8 new offline tests (`test_more_sources.py`), one more in `test_engine_any_course.py`,
the related suites, lint and types. Also run once against the real sites (not part of the test
suite): all eight keyless sources answered in 1 to 3 seconds for two subjects and four pages
were read in about a second. Not checked: the `web` source against the real Brave API (no key
here), any lesson written by a live model from page text, the full API suite for this slice.

To switch on locally, add the new names to `SOCRAT_RESEARCH_PROVIDERS` in `.env`.

Still open from the owner's point 1: sources are searched per lesson, not gathered once per
course; no Khan Academy or LibreTexts source (neither has a public search API); PDFs are not read.

### 2026-11-10, slice 4: any age, any style

Before: a learner's age was one of six groups and their style one of eight labels.

| Change | Where |
|---|---|
| A request carries the learner's exact age (3 to 110) when they give it: typed into the form, or stated in their words ("my 6 year old", "I am 70"). Only an explicit statement counts; nothing is guessed | `coursegen/intent.py` (`Intent.age`, `stated_age`, `settle`) |
| A known age under 18 decides the register; an adult keeps the register they asked for and is never put in an age group. The lesson writer is told the exact age; for adults it is told to use it for examples only and to assume nothing about ability | `intent.settle`, `intent.to_brief` |
| Page size and reading pace grow year by year under 18 (a 9-year-old and a 12-year-old no longer get the same page). Adults are not sized by age | `style/pages.py` (`BY_AGE`, `for_age`) |
| A request carries how the learner wants to be taught, in their own words, up to 400 characters. It goes first into the brief's style request, which the style interpreter turns into the style every writer follows | `Intent.style_request`, `to_brief` |
| The tutor is told the exact age of a learner under 18. The free-text style still never reaches the tutor (the existing rule: validated fields only) | `coursegen/audience.py` |
| The request form has three free inputs: how you want to learn it, age, minutes a day (1 to 480). They win over the fixed choices, which stay as shortcuts | `coursegen/requests.py`, `apps/web/src/app/new/page.tsx` |
| The "build it from your own notes" box is gone from the form (owner's clarification 1). The API still accepts notes | `apps/web/src/app/new/page.tsx` |
| A model reply with a slip in the age or style keeps everything else it understood | `intent._soften` |

Checked: 15 new tests (`test_any_age_any_style.py`), 56 with the related suites, lint, types,
and the form in a real browser against the offline API (age 8, 12 minutes, a treasure-hunt
style: all three came back in "What Socrat understood"). Not checked: a live model reading an
age or style from free text, or writing a lesson in an unusual style; the full API suite.

Still open: accounts need the holder to be 13 or older (`learn/routes.MIN_AGE`), so a child
learns through an adult's account and there is no guardian or child-profile feature; a
"gamified" course is still a writing style, with no game mechanics in the app; enrolment
accepts only fixed session lengths (15 to 120 minutes), so a 12-minute request is planned as
12 minutes but enrolled at the nearest allowed value.

### 2026-11-10, slice 5: stronger agents where they matter, cost in view

Before: every agent ran on one model unless each was overridden by hand, so a course was
either dear everywhere or weak everywhere.

| Change | Where |
|---|---|
| Three tiers. **Strong**: the course plan (one call shapes every lesson), the fact check, the review, and rewrites of lessons that failed. **Fast**: reading the request, the style, the sources and picking visuals. **Default**: the lesson's first draft, quiz, in-lesson checks and the rest. Configured with `SOCRAT_GEN_TIERS`; empty means one model for everything, as before | `coursegen/roles.py` (`ROLE_TIER`, `role_settings`), `config.py` |
| Escalation: a quiz or in-lesson-check reply the default model garbled is asked again of the strong model, and a part still failing on its last round is written by the strong model. The strong model is paid for only when the cheap one has failed | `roles.ask(escalate=)`, `jobs.run_package` |
| Each tier carries its own prices, so spend is counted at the right rate. Every model call in a lesson's log now records its tier | `roles.KEYS`, job log `calls[].tier` |
| The owner's cost report adds: which tier and model each role runs on (no keys or URLs), spend and cost per call for each model, and a mark on any course whose cost per released lesson is above `SOCRAT_GEN_LESSON_COST_TARGET_USD` (default 0.10; it marks, it does not stop) | `coursegen/costs.py` (`tiers`, `by_model`, `over_target`), `GET /admin/engine-costs` |

Checked: 7 new tests (`test_model_tiers.py`), 68 with the related suites, lint and types.
Not checked: any real model on any tier. Which models to put on each tier, and whether the
strong tier earns its price, can only be settled by a live run comparing cost per released
lesson and first-round pass rate with tiers off and on.

Earlier slices already cut cost: non-programming courses no longer carry the DSA outline and
reference lesson in every prompt, dead links and formatting slips no longer cost a rewrite
round, and a disputed quiz item is dropped instead of the quiz being rewritten.

### 2026-11-10, slice 6: a fast start

Before: after "write my plan" the learner saw a spinner until the whole plan was written,
detailed and reviewed, and a lesson being prepared was a locked page that never refreshed.

| Change | Where |
|---|---|
| The plan's shape (course title, modules, lesson titles) is logged the moment the architect answers and shown as a first draft while details are written and the critic reads it. Nothing can be started from it; a failed job's draft is not shown. The page asks every 2 s while waiting | `outline.titles`, `jobs.run_outline` (log event `skeleton`), `requests.view` (`skeleton`), `apps/web/src/app/new/page.tsx` |
| `SOCRAT_GEN_FAST_FIRST_LESSON` (off): a learner's first lesson takes the search's best-ranked results as its sources, text before video, without the researcher's model call. One model step fewer before the author starts. Links are still checked; if none survive, the researcher is asked as before. The log says who chose (`chosen_by`) | `research.best`, `jobs.run_package` |
| `SOCRAT_GEN_FIRST_LESSON_PREVIEW` (off): once the first lesson's draft passes the lesson gates, its owner may read it, labelled "a first draft, still being checked", while the quiz is written and the fact check and review run. Read-only: no quiz, no progress. Only the owner, on their own private course, for the job marked as their first lesson; never with safety notes, a learner under 13 or a child's register | `learn/preview.py` (`GET /api/v1/concepts/{id}/preview`), `jobs.run_package` (log event `preview_ready`) |
| A lesson being prepared now opens by itself when it is ready (asked every 5 s), with the draft shown meanwhile when there is one | `apps/web/src/app/learn/[...concept]/page.tsx` |

Checked: 10 new tests (`test_fast_start.py`), 110 with the related suites, lint, types, and
the web type check. Not checked: either page in a browser; any timing (the 30 to 60 second
plan and the one-minute first lesson can only be measured with a live model); the full API
suite and Playwright.

The preview answers the open decision "first lesson before the fact check" in code but not
in policy: it stays off until the owner turns it on. Not done in this slice: token-by-token
streaming, a single combined call for lesson and quiz, and reuse of a similar (not
identical) existing course.

### 2026-11-10, slice 7: practice shaped by the subject, seen by the coach

Before: outside the programming library every practice set was written on demand by one
model call (slow, 12 a day, unchecked), in the same five kinds for every subject, and no
answer reached the coach.

| Change | Where |
|---|---|
| `SOCRAT_PRACTICE_BANK` (off): a set is built by code from material the lesson already holds and that passed its gates and fact check: its in-lesson checks (those that stand without code), and the rows it adds to the course's own sections. A vocabulary becomes matching and typed recall, a timeline with years becomes ordering. Ready at once, no model call, not counted against the day's allowance. With fewer than 3 such questions the model writes the set as before. Nothing is taken from the lesson's closing quiz | `drills/bank.py` (`from_checks`, `from_sections`, `pool`), `drills/routes.py` |
| Question kinds are chosen per course, most fitting first: by studio, by the sections the course has, and tapping before typing for a young learner. The bank fills a set in that order and the model is told it | `bank.plan`, `drills/service.brief` |
| A new set brings back what the learner missed first, then questions never asked, then the rest, without two of a kind in a row | `bank.choose`, `bank.history` |
| `SOCRAT_PRACTICE_EVIDENCE` (off): a bank answer is recorded as recall evidence (`retrieval`), so mastery, the skill profile and the stuck detector see practice in any course. At most 3 answers per lesson a day, each question once a day; a model-written question never counts | `drills/routes.count_as_evidence` |
| When a set is finished the coach says what to do next, decided by code: move on or take the checkpoint when all were right, reread the lesson (with a link) when half or more were missed | `drills/service.advice`, `apps/web/src/components/studio/drills.tsx` |

Checked: 9 new tests (`test_practice_bank.py`), 73 with the related suites, lint, types and
the web type check. Not checked: a bank set in a browser (the shipped courses hold only two
code-free checks per lesson, under the minimum, so it needs a generated course); how many
bank questions a real generated lesson yields; the full API suite and Playwright.

Evidence weight: there is no lower weight for practice than the existing `retrieval` weight
(0.6, the same as a quiz item) without changing the scoring policy for every learner, so the
limit is by count, not by weight. Owner decision 4 (may practice count?) is answered in code
and stays off until the owner turns it on.

The open items listed here at first were taken up in slice 8, except listening and speaking.

### 2026-11-10, slice 8: the rest of practice and the coach (G6, G7)

| Change | Where |
|---|---|
| Two more question kinds, for the model and the bank alike. **True or false with a reason**: judge a statement, then pick why from 2 to 4 reasons; right only when both are right. **Fill the gaps**: a sentence with up to four gaps and a word bank with distractors, filled by tapping. Both graded exactly by the server; the key never leaves it before the answer | `drills/service.py` (`Question`, `judged`, `correct`), `apps/web/src/components/studio/drills.tsx` |
| The bank writes true-or-false questions by code from a course's sections: one row shown with another row's second field, false because of the pairing, with the right pairing as the reason | `drills/bank.from_sections` |
| The coach's ladder in a practice set: after a miss, one easier question on the same idea is added (recognising instead of recalling). If that is missed too, or the lesson has none left, a question from a lesson this one builds on, named as such. At most two a set; bank sets only. A question from an earlier lesson counts as evidence about that lesson | `drills/bank.follow_up`, `drills/routes.reply` |
| `SOCRAT_LESSON_SIGNALS` (off): the lesson page reports the furthest page reached, taps on "More simply" and "Go deeper", rereads of a finished lesson and questions asked from it. One record of counters per lesson; never scored, never evidence, so they cannot move mastery | `learn/memory.py` (`POST /api/v1/concepts/{id}/signals`), `apps/web/src/app/learn/[...concept]/page.tsx`, `components/lesson-pages.tsx` |
| The stuck detector gains two weak signs, "asked for a simpler explanation more than once" and "came back to reread the lesson". Like the others they only count together with another sign, and never before anything was scored | `adaptive/profile.py` (`simpler_requests`, `rereads`), `adaptive/stuck.py` |
| A learner memory: up to eight plain statements built by code from the signals and the latest practice set per lesson. The tutor is given it (section `what_socrat_has_noticed`) and the learner can read exactly the same lines at `GET /api/v1/memory`. No text a learner typed is in it | `learn/memory.py` (`remembered`, `tutor_block`), `assistant/service.learner_sections` |

Fixed on the way: a true-or-false or gaps question lost its answer key when a stored
question was validated a second time; it now validates to the same question.

Checked: 18 new or changed tests (`test_practice_bank.py`, `test_learner_memory.py`), 110
with the coach, tutor and practice suites, lint, types and the web type check. Not checked:
the two new question kinds, the follow-up question and the signals in a browser; whether a
live model writes good true-or-false reasons and gaps; the full API suite and Playwright.

Left for later, by the owner's decision: listening and speaking items. Also not built: tapping
a label onto a picture (it needs lesson diagrams with marked parts, so it belongs with
Visualise), time on page as a signal, and a screen in the app for the memory (the API is
there).

### 2026-11-10, slice 9: visualise from a lesson (G8)

What G8 said was missing was partly there already: the lesson page has had one shared visual
per lesson ("Watch it work"), made once, cached per lesson, depth and language, free for
every plan, retired when two learners flag it (`explainer/shared.py`). This slice adds what
was still missing.

| Change | Where |
|---|---|
| `SOCRAT_EXPLAINER_SECTION_VISUALS` (off): every reading page of a lesson offers "Show me this part". The visual is asked for with that page's own text (never anything a learner typed), made once and reused by everyone, keyed by lesson and page, rebuilt when that page's text changes, and not charged to anyone's plan. The server splits a lesson into pages by the same rule as the lesson page, so page N is the same page on both sides | `explainer/shared.py` (`parts`, `prompt_for_part`, `fingerprint_part`, `key_for`), `explainer/routes.serve_shared` (`section`), `apps/web/src/components/socrat/concept-visual.tsx`, `components/lesson-pages.tsx` |
| `SOCRAT_PLAYGROUND_FREE_PER_WEEK` (0): a small weekly allowance of the learner's own Playground questions on the free plan. Paid plans are unchanged | `entitlements.limits`, `main.py` |
| Opening a visual is a lesson signal (`visual`); twice or more on one lesson is kept in the learner memory | `learn/memory.py`, lesson page |
| The lesson view says whether pages offer visuals (`section_visuals`), so the button is shown only when the API will answer | `learn/routes.concept` |

Checked: 5 new tests (`test_visualise.py`), 75 with the visual, billing and memory suites,
plus the learner API suite; lint, types and the web type check. In a browser against the
offline API: each lesson page shows "See this part: <page title>", the click reaches the API
(refused there, as that server has no model) and the signal is recorded. Not checked: a
visual actually generated for a page; cost per page visual; the full API suite; Playwright.

Still open from G8: lesson visuals written with the lesson (`gen_visuals`) stay off until a
sample is reviewed; a visual writes no evidence; the vision review of a 3D film against the
real object needs the owner's approval; tapping a label onto a picture is not built.

### 2026-11-11, slice 10: match before build (G2, first part)

Step 2 of the loop ("the engine looks for a course that already fits") did not exist: every
request built a new course, even when the learner or someone else already had the same one.

| Change | Where |
|---|---|
| `SOCRAT_REQUEST_MATCHING` (off): an open request is compared with the courses this learner may already take: their own, and courses another learner agreed to share (public, in good standing, at least one released lesson). A private course is never compared, so a match shows nothing the course list does not already show. No model is called | `coursegen/match.py` (`find`) |
| The comparison is code over two validated intents. Same subject means the same words once filler, order and plurals are set aside ("Introduction to fractions" is "fractions basics"; "Linear algebra" is not "Algebra"). The language must be the same. A child is never offered an adult's course or the other way round. Exact: nothing differs. Close: the differences in register, level or style are listed in plain words | `match.subject_key`, `match.fit` |
| `GET /learning-requests/{id}/matches` lists up to three, exact first, the learner's own first. `POST /learning-requests/{id}/take` settles the request with one of its own matches (new status `matched`): nothing is generated, the request stops counting as open, and the view carries what to send to enrol | `coursegen/requests.py` |
| The request page shows "This course already exists" above the build button, with who shared it, how many lessons are ready and what differs. "Start this course" enrols and opens Today; "Write a new one for me" builds as before | `apps/web/src/app/new/page.tsx` |

Checked: 5 new tests (`test_match.py`), 31 with the learning-request and fast-start suites;
lint, types and the web type check. In a browser against the offline API, with a course
shared by another learner in a seeded database: the card appeared for "Teach me algebra",
"Start this course" enrolled the learner and opened Today, and the request became `matched`
with no generation job. Not checked: the full API suite; Playwright; matching at scale (every
candidate course is read on each lookup, which is fine for hundreds, not for many thousands).

Still open from G2 and G5: subjects that mean the same in different words ("maths" and
"mathematics", "ML" and "machine learning") do not match, since there is no embedding; a close
match is started as it is, not forked and personalised; released lessons are not reused across
learners' private courses (owner decision 3); the built-in courses are not offered, because a
learner can only take them in sequence; the per-course budget still pauses a long course (G5).
