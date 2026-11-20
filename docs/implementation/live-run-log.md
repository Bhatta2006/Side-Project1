# Live run log: a stand-in model builds a lesson in the real app

Running log of what happened, what broke and who was at fault, kept honest on purpose.
The "model" is a Sonnet agent answering the app's real model requests through a relay
(an OpenAI-compatible endpoint backed by files). The app code is unchanged. It is not a real
provider: no real latency, rate limits, token counts or refusals.

## Setup deviations (all test-environment, none in app code)

- Sandbox DNS and proxy block the public web, so the resource-link check was replaced with
  "every link is reachable" in the launcher. **No resource link in this run was verified.**
- Token counts and cost are estimated by the relay (characters / 4), so cost figures are rough.

## Errors and mistakes

| # | When | What | Whose | Outcome |
|---|---|---|---|---|
| 1 | setup | My relay selftest used a 5 s client timeout against 8 s keepalives and timed out | mine (test harness) | keepalive cut to 3 s, retested OK |
| 2 | setup | `PATCH /me` birth year 2015 refused with `minimum_age` | not a bug: minors cannot register | learner is an adult |
| 3 | outline round 1 | Stand-in model listed concepts as both prerequisite and related; the graph check rejected it and sent feedback | model output, caught by app | fixed in round 2 (retry loop worked) |
| 4 | outline round 2 | Critic asked for revision: a wrong number in an objective (9%, should be 9/98), labs with no simulation tool, missing odds concept, unverifiable calibration claim | model output, caught by critic | fixed in round 3, critic passed |
| 5 | lesson atoms | Atom hook had three sentences; schema allows two | model output, caught by gate | atoms re-asked alone; lesson and quiz kept |
| 6 | lesson review | Fact checker raised four warnings (overstatements such as "casino games", "must profit") | model output, caught by checker | released as `human_review_required`, as designed for this domain |
| 7 | learner step | Generated lesson `expected-value` returned `concept_locked` (HTTP 423) for the learner placed at it | **app bug** (see below) | fix written, verifying |
| 8 | my test for #7 | First regression test passed without the fix, so it did not reproduce the bug | mine | test changed (more concepts in module 2); now fails without the fix |
| 9 | process | I cancelled the queue with the app's own cancel after the first lesson; one job (`house-edge`) was already running and finished | mine (scope control) | two lessons exist; not a defect |
| 10 | after the fix | My `learner.py login` reloaded the previous session cookie, saved a stale one, and the next call returned 401 | mine (test harness) | login now starts with a clean session |
| 11 | after restart | Re-enrolling put the learner into placement, not active, because the start lesson was now written | not a bug: expected behaviour | placement answered as a learner who knows the topic |
| 12 | after restart | Lessons still locked (HTTP 423), now behind module 1's checkpoint: placement left unwritten earlier concepts unknown whenever the start lesson was written. **My first fix covered only the unwritten-start branch** | **app bug, and my fix was incomplete** | placement now marks every unwritten earlier concept known in both branches; second regression test added, fails without the fix |
| 13 | writing the test for #12 | I copied an existing concept that referenced a problem not in the new course (`unknown problem echo-reading`) | mine | removed its problems and practice links |
| 14 | after re-enrolling | Enrolling started background generation again (prefetch keeps three lessons ahead), unrequested | by design, not a bug | cancelled through the app; `house-edge` had already finished before the first cancel, so two lessons exist, not one |
| 15 | placement after the fix | I answered placement questions in a guessed order; the app answered `stale_question` (HTTP 409) | mine; the app was right to refuse | now read each question before answering; options are shuffled per learner |
| 16 | database check | `concept_states` showed two rows for one concept after I deleted the enrolment with raw SQL (no cascade) | mine (harness); not an app defect | leftover rows from my delete; the app's own delete path cascades |
| 17 | grading step | The first stand-in agent quit after two idle waits while I was debugging; the grader request (025) waited unanswered 10+ minutes | mine (I told it to stop on idle) | new stand-in started that only stops on STOP |
| 18 | quiz step | The raffle question got my deliberate wrong answer; the session finished at 4/5 and a GET afterwards opened a retake | not a bug: by design | evidence recorded once at 0.8, independent, `quiz` kind |
| 19 | observation | Citations are checked only against the model's own paraphrase (no search provider configured): 2 of 4 flagged weak, correctly, because they attach a source to the lesson's own arithmetic | limitation, not a defect | real passage text needs a search provider run |
| 20 | observation | Resource records show an empty licence although the lesson's credit line names licences ("CC BY-NC-SA (reported)") | **app bug, fixed** | `research.attach` only added provenance for sources the author had not listed; it now fills blank licence, author, date and reason on listed ones, author's own words win |
| 21 | grading step | Graded 1.0 with per-criterion notes and useful feedback; the response band says "strong" while the evidence stage says "proficient: not yet shown without help on a real task" | wording mismatch between the older band names and the newer stage names; not changed | for the owner to decide |
| 22 | task step | I posted to `/tasks/<course>` instead of `/tasks/<course>:<concept>` and got 404 | mine | retried; the self-checked task saved as `self_checked` and wrote no evidence, as designed |
| 23 | reviews step | The Reviews page I built listed 11 reviews; 10 were concepts placement had only assumed known, with reasons claiming practice that never happened | **app bug in my own feature**, found by the live run | assumed-and-never-practised concepts are not listed; regression test fails without the fix |
| 24 | browser step | I started the web dev server from the wrong folder (no app directory found) | mine | used the repo's `npm run dev` |
| 25 | browser step | First desktop pass reported the path list, citations and AI label missing | mine (no wait for the cold compile) | rerun with a wait: all present on desktop and phone |
| 26 | browser step, phone width | Every page is 20px wider than a 390px screen (settings far wider); the avatar in the top bar is cut off | **existing app bug in the shared top bar**, not caused by generated content | fixed: Feedback is icon-only on phones, settings grid has a shrinkable column; eight pages measured 390 vs 390 in a real browser |
| 27 | browser step | The sidebar shows "Mastered" with the reason "Not yet shown without help on a real task" under it, and the step list says "Practice: Mastered", after one 4/5 quiz and one graded answer | **wording defect on screen**: older band names ("strong" shown as Mastered) vs newer evidence stages | fixed on the lesson page: "Strong so far" until the evidence stage is "demonstrated"; app-wide band names unchanged |
| 28 | browser step | The lesson text still says insurance "must profit", the sentence the fact checker flagged as too strong; it was released with the warning and the "a person needs to confirm" label | by design (warnings do not block) | fixed: a passing package with imprecise fact claims gets one polish round (only under half the lesson budget); if that round fails, the first passing version is released as it was |
| 29 | researcher step (reported by the stand-in) | The registry the researcher is told to prefer is mostly competitive-programming sources, which suit a probability course poorly; the stand-in used only the few general ones, and said its URLs were not checked | **app quality issue**: registry hint is not filtered by the course's domain | fixed: only software courses (and courses with no adapter) see the full registry; other adapters see subject-neutral sources |

### Bug #7 in detail

A learner placed at a later concept of a generated course had only that concept's prerequisites
marked known. The start concept sat in module 3, but an earlier concept of module 2 was deeper in
the dependency order, so it was neither known nor written. Module 2's checkpoint then locked the
module-3 lesson that had just been generated for the learner, and Today offered nothing.
Fix: `learn/placement.py` now marks everything earlier in either dependency order or the course's
own module order as known. Regression test: `test_a_later_start_counts_every_earlier_module_as_known`.

### Bug #7 and #12: a learner placed late is locked out of their own lessons (two shapes)

Shape 1 (start lesson not written): only the start's prerequisites were marked known, so an
earlier-module concept that sat deeper in dependency order stayed unknown and its module
checkpoint locked the start. Shape 2 (start lesson written, found only after re-enrolling):
placement probes the start and left every unwritten earlier concept unknown, so module 1's
checkpoint locked everything generated. Fix in `learn/placement.py` covers both; tests:
`test_a_later_start_counts_every_earlier_module_as_known` and
`test_a_written_start_lesson_is_not_locked_behind_unwritten_earlier_modules`.

## What worked end to end (stand-in model, real app)

Request in plain words, intent parsed with safety notes, 35-concept outline through three
architect rounds and two critic rounds, a six-question diagnostic scored by code, publish and
enrol, background generation of the first lessons with retries, a 9.5k-character lesson with
a visual, quiz, atoms, four citations and an honest "a person must confirm" label, a quiz
with server-side answer keys, a model-graded written answer with per-criterion feedback,
a self-checked task that correctly wrote no evidence, reviews, and a real browser pass at
desktop and phone width.

## Not tested by this run

A real model (the stand-in is an agent through a relay: no real latency, rate limits,
refusals or token counts); resource links (replaced by "reachable"); search providers;
payments and email; more than one learner; the visual's interaction in the browser (loaded,
not driven); audio and video (not built).

---

# Live run 2: real Vertex model, Lesson 0 -> first lesson (2026-11-20, backlog 1.2)

**Setup.** Real provider: Vertex, `gemini-3.8-flash`, key from the local `.env`. API only (no web), local
SQLite, `SOCRAT_GEN_RUNNER=true` with 3 in-process slots, flags on: `learning_requests_enabled`,
`gen_learner_plan`, `gen_learner_brief`, `gen_waiting_learner`, `session_one_adaptation`, `learner_profile`.
Driven over HTTP by a script (dev login -> `POST /onboarding` -> `choose` (builder, door "Filtering a giant music
playlist") -> win -> snag (two deliberate misses, then right) -> `claim` with 25 minutes -> poll `view.start`).
Goal: "I want to learn SQL for my college project" (`onboarding-handoff.md` 4). Run A at `9ee458f` (partner's
head, before backlog 2.1-2.3); run B with `course_brain` on, at the working tree with 2.1-2.3.
Not driven: publish, enrol, Today, the web `/start` page.

## Run A: brain off

| Measure | Value | Target (backlog 2.5, proposals) |
|---|---|---|
| Claim -> roadmap (`roadmap_ready`) | **75 s** | <= 60 s |
| Claim -> first lesson (`first_lesson_ready`) | **196 s** | <= 150 s |
| Outline job cost | **$0.178** (stylist, architect skeleton + module-1 details, critic) | <= $0.25 |
| First lesson cost (package job) | **$0.338** (researcher, author, quiz, atoms, reviewer, facts) | <= $0.15 |
| Whole run, including Lesson 0 | $0.537 | |
| Roadmap size | 5 modules, 15 concepts (builder cap 6 / 18) | |
| Critic | pass in round 1 | |

- Job log: `profile_calibrated`, stylist, architect skeleton, `outline_stored`, critic pass, `outline_saved`.
  No `kept_for_learner` and no `constraint_unmet` (the goal has no explicit asks, so `constraints` is empty).
- The door opens lesson 1 (the intro starts with a streaming-music playlist and maps it to "column projection" and
  "row filtering"; "playlist" appears 7 times). The probe item is there:
  `operator-precedence-compound-evaluation` (`probe: true`), for the Lesson 0 gap `operator_precedence`.
- Timeline: skeleton at 31 s, module-1 details at 41 s, **critic answer at 73 s**: the first lesson waited
  32 s for the critic. This is what backlog 2.2 removes (built the same day, not yet measured live).
- Finding A1: the SQL course is a `python` code course (SQL is not a course language), so the lesson shows its
  SQL inside ```` ```python ```` blocks. See B2.

## Run B: `course_brain` on, two accounts, same goal

| Measure | Account 1 | Account 2 |
|---|---|---|
| Brain outcome | `extend_and_new` (new root, research job) | `from_material` ("no candidate under this subject") |
| Claim -> roadmap | 146 s (waits for the unit's research) | **5 s** (outline reused, no model call) |
| Claim -> first lesson | **864 s** | never: no first-lesson job (bug B3, fixed) |
| Model cost | $1.43 for the whole run (both accounts) | |

- **B1, by design but blocking:** with the brain on, a first request builds a *shared* family course, so
  `builds_private` is false and the Lesson 0 plan is not attached: no `profile_*` event, no roadmap caps
  (7 modules / 26 concepts, over builder 6 / 18), no lazy detail, no door, no probe. The learner's overlay is stored
  on `course_matches.private` but nothing reads it yet (backlog 3.3). **Keep `course_brain` off until 3.3 lands.**
- **B2:** the author wrote ```` ```sql ```` blocks; `package._common_lesson_checks` rejected them ("Code blocks in
  ['sql'] are outside the course languages") and the lesson went to a second round. Same root cause as A1: SQL is
  not a `Language`. Backlog 2.8.
- **B3, app bug, fixed:** account 2's outline was reused (`_reuse`) but `_reuse` never called
  `early_first_lesson`, so its `view.start` stayed `roadmap_ready` with nothing writing the lesson; a `/start` that
  waits for `first_lesson_ready` would wait forever. Reachable without the brain too (two identical learner briefs).
  Fix in `jobs._reuse`; test `test_a_reused_outline_still_starts_the_learners_first_lesson` (fails without it).
- **B4, latency:** one `reviser` call took **567 s** (7.8k in, 5.9k out), just under `gen_timeout_seconds = 600`.
  With `gen_waiting_learner` the heartbeat keeps such a job "alive", so the 2-minute re-claim never fires; the
  learner waits the full call. A shorter timeout for jobs a learner waits on is not built (backlog 7).
- **B5:** account 2 was not served account 1's course: it was still in review (never published), so it is not a
  candidate. The "second learner served with zero model calls" check needs account 1 to publish first; not run.
- **B6, unexplained:** one `POST /api/v1/onboarding` returned 500 on a fresh server with nothing in the log; the next
  account's identical call worked. Not reproduced.

## Not tested by these runs

Publish, enrol, Today and the session-one branches; backlog 2.2 (first lesson before the critic) and 2.3
(computed minutes, session gate) against the live model (run A predates them; run B had no plan, so neither
applied); the web `/start` page; a second learner served from a published shared course.

---

# Live run 3: claim -> Today benchmark (2026-11-20, backlog 2.5)

`scripts/dev/bench_claim_to_today.py` against a local API on Vertex `gemini-3.8-flash`, brain off, flags on
(`gen_learner_plan`, `gen_learner_brief`, `gen_waiting_learner`, `session_one_adaptation`, `learner_profile`),
`SOCRAT_GEN_RUNNER_CONCURRENCY=4`, three learners at a time. Code: the working tree with backlog 2.1-2.4 and the
first-lesson gate, *before* the three fixes listed at the end (the API was started before them).

| goal | mode | min | T1 s | T2 s | outline end s | outline $ | first lessons $ | modules/concepts | note |
|---|---|---|---|---|---|---|---|---|---|
| sql | sprint | 10 | 48 | 108 | 46 | 0.125 | 0.265 | 4/11 | smoke run, alone |
| sql | sprint | 10 | 39 | 103 | 37 | 0.121 | 0.305 | 4/12 | |
| sql | sprint | 25 | 51 | 120 | 50 | 0.149 | 0.299 | 4/11 | |
| sql | builder | 10 | 208 | 286 | 206 | 0.150 | 0.298 | 6/18 | slow outline under parallel load |
| sql | builder | 25 | 54 | 343 | 52 | 0.175 | 1.123 | 6/17 | first package failed (wrong Python wrapper caught by the fact checker), retried |
| sql | explorer | 10 | 81 | never | 137 | 0.361 | 1.207 | 7/21 | first lesson never under 16 min in 3 rounds: not released, twice |

The other 13 configurations (exam and music goals, sql/explorer/25) never started: `POST /onboarding` is rate
limited per visitor (`onboarding_per_hour = 12`) and every run came from 127.0.0.1. The owner stopped the
benchmark there (spent $4.72 for these runs). **Not measured:** the exam and non-programming goals.

Against the proposed targets (roadmap <= 60 s, first lesson <= 150 s, outline <= $0.25, first lesson <= $0.15):
sprint meets the time targets (T1 39-51 s, T2 103-120 s); builder and explorer do not; outline cost meets the target
except explorer; first-lesson cost is about double the target everywhere ($0.27-0.31 when nothing fails).

Findings, each now fixed in code:

- **Session gate made a 10-minute first lesson unreleasable** (sql/explorer/10): 6-7 quiz items already take 6-7
  computed minutes, and the author never got the reading under ~10 minutes. The first-lesson gate now sends a
  lesson back only while rounds remain; on the last round it is released and the job log says
  `first_lesson_gate_waived` with the issues.
- **SQL fences** cost a round in almost every SQL run, and once led to SQL wrapped in wrong Python. Owner decision:
  ```` ```sql ```` is shown (not run) in a code course until backlog 2.8 makes SQL a real language.
- **`outcome_rejected` in every run:** the "names what the learner did not ask for" check read SQL keywords
  (SELECT, GROUP BY, HAVING) as products. All-caps words are now ignored by that check.
- `first_lesson_early` fired in every run (2.2 works live); one `first_lesson_requeued` (the repair round changed
  module 1).
