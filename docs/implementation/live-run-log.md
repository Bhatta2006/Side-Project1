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
| 9 | process | I cancelled the queue with the app's own cancel after the first lesson; one job (`house-edge`) was already running and finished or was dropped | mine (scope control) | noted, not a defect |

### Bug #7 in detail

A learner placed at a later concept of a generated course had only that concept's prerequisites
marked known. The start concept sat in module 3, but an earlier concept of module 2 was deeper in
the dependency order, so it was neither known nor written. Module 2's checkpoint then locked the
module-3 lesson that had just been generated for the learner, and Today offered nothing.
Fix: `learn/placement.py` now marks everything earlier in either dependency order or the course's
own module order as known. Regression test: `test_a_later_start_counts_every_earlier_module_as_known`.
