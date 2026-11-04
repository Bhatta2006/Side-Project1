# Universal engine: Phase 0 audit against the "Principal Engineering Implementation Brief"

Written 2026-11-04 on branch `ccr-410653a4-72kc43`, which carries `feat/universal-engine` merged
in (up to `66038fe`) plus the fixes below. This is the short audit the brief asks for before any
major architectural change. It does not replace `HANDOFF.md` or `universal-engine-plan.md`;
read those for the full build history.

**How to read the status column.** *Verified now*: exercised by a test or a browser check in
this session. *Built, per log*: the handoff and progress log record it as built and tested; I
did not re-run it here beyond the full API suite. *Partial* and *Not built* mean what they say.
Nothing below has been run against a live model in this session.

## 1. Finding: most of the brief already exists

The brief describes a pipeline (goal → analysis → skill graph → experience plan → teaching →
practice → evidence → feedback → adaptation). The repository already implements almost every
stage as separate modules. The brief says "preserve working infrastructure; avoid wholesale
rewrites", so this pass **repairs defects and closes isolation gaps** instead of building a
second engine next to the first.

| Brief section | Where it lives | Status |
|---|---|---|
| 3 Goal interpreter | `coursegen/intent.py`, `learning_requests` (fixed choices, clarification questions, rules fallback) | Built, per log. Gap: no separate immutable-versioned "requirements spec"; the confirmed intent and brief act as it |
| 4 Skill graph | `coursegen/outline.py`, `catalog/registry.py` (cycles, missing refs), competency categories and evidence contracts | Built, per log |
| 5 Experience architect | `engine/strategy.py`, `engine/evidence_library.py`, `engine/domains.py` (adapters) | Built, per log. Gap: language and workplace communication run on the `general` adapter |
| 6 Lesson composer | `Concept.sequence`, renderer manifests, lesson page follows the sequence | Built, per log |
| 7 Practice studio | Code: judge + sandbox. Math: `workbench/`. Exploration: `lab/`, `engine/simulate`. Projects: milestones. Offline/practical: `Task` with honest "a person must check". **New: practice sets for every course (`drills/`)** | Partial. Audio/speaking, image annotation and file-upload grading not built |
| 8 Assessment | Adaptive quiz, judged code, rubric grading of written answers, lab explanations, weekly assessment | Partial: no spoken or practical-demonstration grading (correctly not faked) |
| 9 Dynamic UI | `engine/renderers.py` typed registry; web host renders only registered components; sketches and 3D films are data for fixed host code | Built, per log. Unknown components fall back to text |
| 10 Tutor | `assistant/` with hint ladder, leak guard, teaching moves | **Verified now for course scoping** (fix 2.2) |
| 11 Mastery and adaptation | `mastery/` (stages unknown → demonstrated), `adaptive/` (stuck ladder, proposals), spaced reviews | Built, per log. Stage names differ from the brief's (see 4) |
| 12 Resources | `coursegen/search.py`, research step may only cite search results, provenance stored per concept | Built, per log. Search providers off by default |
| 14 Pipeline | Staged jobs with retries, backoff, dead letter, progressive start | Built, per log. **Concurrency gap fixed now** (2.3) |
| 15 Isolation | Course-scoped reads via `learn.curriculum()`; course isolation test | **Three gaps found and fixed now** (2.1 to 2.3) |
| 16 Verification | `engine/benchmark.py` (8 archetypes), `test_course_isolation.py`, `test_engine_e2e.py` | Partial: only one subject was run against a live model (fractions, per log) |

## 2. Defects found this session, root causes, and fixes

### 2.1 The app drew every course as a programming course (reported by the owner)

A children's math course showed "Company questions", a Python language picker and a Codeforces
card.

Root causes, in order of impact:
1. **Stale session after creating or resuming a course.** `/new` enrolled the learner and went
   to Today without reloading the session, so the whole UI kept rendering the previous course
   (Zero or DSA) until a full reload. Fixed in `apps/web/src/app/new/page.tsx` (refresh before
   navigating, both for "start" and "resume").
2. **The course shape reached admin accounts only** (`studios_for`), and the web defaulted a
   missing shape to "code". Every learner now gets the shape and a `features` map from one
   place (`catalog/shape.py: features`).
3. **Code-only features were unconditional** (company questions, Codeforces, external library,
   language picker, LeetCode tour copy, tutor tools). They are now gated by `features`:
   company questions DSA only; library and sprints for the hand-authored programming courses;
   language choice for code courses. The API refuses the library and company endpoints for
   other courses (404 `not_in_course`).
4. **No practice for non-code courses.** Practice is now one page for every course: practice
   sets written for the course (`drills/`, graded on the server), then the course's extras.

Verified: `test_course_shape.py`, `test_drills.py`, `apps/web/tests/course-features.test.mjs`,
and a browser check with a mocked math course (`/companies` redirects to the course's Practice;
Settings has no Codeforces or language picker).

### 2.2 The tutor carried one course's conversation into another

`general` and `plan` chats were stored once per learner, not per course
(`AssistantThread.scope == "general"`). A learner who paused a Kannada course and opened a math
course had the Kannada history sent to the math tutor, listed in its chat history and shown in
"what Soc reads". Problem and concept chats were already course-specific.

Fix: `assistant/service.py` stores these chats as `general@<course id>` through one helper
(`stored_scope`), used by every read and write (thread, history, new chat, list, resume,
context); another course's chat is a 404. The web shell's Ask Soc remounts per course so its
in-memory messages cannot survive a switch either.

Verified: `test_tutor_course_scope.py`, which **fails on the previous code** (the Zero message
appears inside DSA) and passes now. Known effect: general and plan chats written before this
change are stored without a course, so they are no longer shown. Nothing is deleted; they could
be reattached by a one-off script if the owner wants them back.

### 2.3 Concurrent requests could queue the same lesson twice

Every caller checked `jobs.active()` and then inserted. Two concurrent page loads (prefetch runs
on learner visits), a double-clicked "regenerate" or two releases could both pass the check, so
the same lesson was written and paid for twice.

Fix: migration `0045_one_open_generation_job` adds a partial unique index (one queued or
running job per course, kind and target). Existing duplicates are marked `cancelled`, oldest
kept, nothing deleted; the downgrade drops the index. `jobs.enqueue` turns the conflict into
`AlreadyQueued` (409 `generation_in_progress`) inside a savepoint; background callers use
`enqueue_once` and skip.

Verified: `test_one_open_job.py` (database refusal, savepoint, failed job not blocking, migration
cleanup and downgrade) and the existing migration tests.

### 2.4 Smaller fixes in the same pass

- The public `/library/stats` was refused when signed out after the library guard; fixed.
- The "newly unlocked module" memory on the plan page was shared across courses (module ids
  repeat); now per course.
- The tutor prompt said every course leads to contest programming; it now stays inside a
  non-programming subject, and library and Codeforces tools are not offered there.
- The Skill Passport no longer prints a programming language for a non-code course.

## 3. Checked and found sound (no change)

- Lesson, quiz, workbench, lab and problem reads are scoped to the active course's curriculum
  (`learn.curriculum`, `require_unlocked`); cross-course prerequisites are deliberate bridges.
- Reviews are scoped to the active course by default; the all-courses view is opt-in and labelled.
- Generation prompts per course are covered by `test_course_isolation.py` (three concurrent
  courses with unique markers).
- Playground visuals are a personal gallery across courses by design; they are not tutor
  context or course content.

## 4. Known gaps, next priorities (in order)

1. **Live-model run of the eight benchmark subjects** (needs the owner's key). Until then, every
   generation claim rests on scripted model replies.
2. **Remaining failure-path tests**: delete a course during generation, submit during a lesson
   rewrite, refresh mid-generation in the browser.
3. **Practice sets do not write mastery evidence.** They are generated questions with no review,
   so they count as practice only. Deciding whether and how they count is an owner decision.
4. **Speaking and listening practice** is not built (needs speech infrastructure and a key).
5. **Stage names**: the brief asks for Not Started → Introduced → Practicing → Demonstrated →
   Needs Review; the code uses unknown → emerging → developing → proficient → demonstrated,
   with reviews tracked separately. Renaming is cosmetic; I left it.
6. **The older Playwright and visual suites** have not been run on this branch.

## 5. Branch note

`AGENTS.md` asks agents to work on `feat/universal-engine`. This session was assigned
`ccr-410653a4-72kc43` and pushes only there; it contains `feat/universal-engine` merged in. The
owner decides whether to merge it into `feat/universal-engine` or open a pull request.

## 6. Test results for this pass

- Full API suite: **938 passed, 30 skipped, 5 failed** (20 min). The 5 failures fail the same way
  on the code before this pass (`c3b9c03`) and are environmental here: four need a sandboxed
  Chromium this container cannot start (`test_explainer.py` x3, `test_sketch_spec.py`), and
  `test_resource_search.py::test_researcher_may_only_choose_search_results_and_keeps_their_provenance`
  also fails on the old code (cause not investigated).
- Ruff, ruff format and mypy (205 files): clean. Web typecheck: clean. Web unit tests: 10 passed.
- Not run: the Playwright end-to-end, visual and accessibility suites; any live model.

## 7. Second pass: competitor comparison (Wondering) and generation fixes

### What could and could not be analysed

The owner asked for a reverse-engineering analysis of **Wondering** (wondering.app, YC S26).
The REA skill was installed, but this session's network policy blocks `wondering.app` for both
the container and the web-fetch tool, so **none of Wondering's shipped code was inspected**.
Everything below comes from public descriptions (their site's listing in search results, the
App Store listing, YC and directory pages, and a competitor's comparison post), so it describes
their product, not how they build it:

- Input: a topic, a link, a PDF or a goal; they ask why, prior knowledge and desired depth.
- Output: a path of roughly three-minute lessons, each watched (visuals), heard (generated
  podcast) or read, with interactive exercises.
- Retention: one global review across all courses, scheduled with FSRS; daily streaks, friend
  streaks and XP per lesson.
- Reported weakness (one Product Hunt comment, one competitor blog): content can sit below the
  learner's stated level, and reading is stronger than practice.

Their likely speed comes from small lessons generated as the learner goes. Socrat already
generates progressively (first lesson first, lessons in parallel); what it lacked was making
lessons small when the learner asked for short sessions (fixed below). Socrat's differentiators
remain depth on request, verified practice (judge, CAS workbench, lab simulations) and graded
evidence.

### Strategies adopted, and generation defects fixed

| # | Change | Root cause | Test (fails on old code) |
|---|---|---|---|
| 1 | Planned activities fitted to the studio | Outlines planned a lab or code assessment for maths; the outline is the writer's contract and the reviewer failed the lesson every round (the live run's planning mismatch) | `test_planning_fit.py` |
| 2 | Unreadable quiz or atoms reply re-asked once inside the round | Each cost one of three rounds and could trigger a lesson rewrite | `test_part_reask.py` |
| 3 | Session length decides lesson size (bite format at 10 minutes or less, as the presets) | "5 minutes a day" was a sentence to the writer while the gate demanded 2,000-4,000 characters | `test_session_length.py` |
| 4 | Course from the learner's own notes (pasted text, 20,000 characters; migration 0046) | Wondering's link/PDF input; links not fetched (SSRF risk and network policy), PDFs not parsed | `test_learner_material.py` |
| 5 | Listen to a lesson with the browser's speech synthesis | Wondering's listen mode; no key, nothing uploaded | `apps/web/tests/speech.test.mjs` |
| 6 | Account deletion with learning requests | `learning_requests.user_id` has no ON DELETE CASCADE: delete returned 500 and kept the learner's words; requests were also missing from the data export | `test_learner_material.py` |

Security notes for this pass: the learner's notes are untrusted data, cleaned of markup and
control characters before any prompt (so a forged closing tag cannot escape the data block),
marked as data, kept out of the brief JSON, part of the idempotency key, read by the intent
reader so the harm check covers them, never returned by the API (only their size), exported
with the account and deleted with it. The re-ask adds at most one call per part per round and
is metered like every other call.

Not done, honestly: generated podcasts (needs a speech provider and key), link and PDF import,
XP and friend streaks, FSRS (Socrat has its own spaced scheduler), a live-model run of any of
this. Listen was checked by unit test, not in a real browser with speech; the notes box was
checked in a real browser at phone width with a mocked API.
