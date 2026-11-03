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
