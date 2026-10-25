# Adaptive core: follow-up QA

Date: 25 October 2026 (Asia/Calcutta). Branch: `fix/adaptive-core`, targeting `main`.

The follow-up closes the executable defects found while checking the adaptive branch. The
44 unwritten lessons remain hidden. New question content is provisional and has no invented
human review record.

## Disposition of the open list

| Item | Result |
| --- | --- |
| Browser suites | Reran `learner-journey`, `keyboard`, `learning-scope`, `login-design`, plus `landing`, against local dev servers. Final result is recorded below. |
| Pull request | Prepared this branch for a pull request into `main`; no merge or deployment performed. |
| Landing copy | Replaced “Practised with help” with “Check passed” and explained that a missed check brings support and another check. Updated the old landing assertions to the current design. |
| Small quiz banks | Added 60 original, language-neutral questions in 15 Zero-course families. Every live Zero concept now has at least five practice items available per supported language. The new families remain provisional, without human approval. |
| Draft concepts | Confirmed 81 live and 44 draft concepts. Kept all 44 drafts hidden; authoring complete lessons is a separate content pass. |
| Dev login | Recover a legacy slug account only when the saved name exactly matches after Unicode normalization. Preserve its user ID, enrollment and read-lesson state. Existing hashed identities are not moved when another spelling signs in. |
| Plan reasons | Concept rows show the existing reason chips from the actual queued activities, including support after a missed check. |
| Long titles | Reduced and constrained hero typography on Today, the plan and lessons so long titles wrap within the available space. |
| QA C/E/F/G | Reran bounded tutor/security probes, learner flows, keyboard navigation, responsive layouts and accessibility checks. Coverage and limitations are explicit below. |
| Windows dev crash | A development Proactor retries transient WinError 64 accepts and closes abandoned provisional sockets. It retains async subprocess support. The demo also detects a live process with an unresponsive API. |
| Java limits | Signed native jobs carry the problem's millisecond limit. Local and Docker runners enforce it, bounded by the approved profile's safety limits; compilation has its own budget. Old queued signatures remain valid. |
| Next.js notice | The lockfile already pinned 16.4.3, but installed modules contained 16.4.0. `npm ci` restored 16.4.3. `npm audit --audit-level=high` reports zero vulnerabilities. No dependency bump was necessary. |

The [official Next.js advisory](https://nextjs.org/blog/nextjs-security-update-october-14-2026)
identifies 16.4.1 as the patched release for the October advisory. The installed 16.4.3
matches this repository's existing lockfile.

## Defects found during the rerun

- A choice card moved out from under the pointer on hover and oscillated indefinitely on
  the DSA onboarding step. Its hover treatment now changes the border without moving the target.
- Small sidebar red text failed contrast. Lesson labels, landing book text and a highlighted
  code line also needed contrast fixes. Loading library rows retain readable contrast.
- Reduced-motion detection in the landing companion differed between server rendering and
  hydration. It now uses the existing hydration-safe hook.
- Attribution's table and the shared loading skeleton could widen a phone page. Their grid
  tracks now allow shrinking; the table itself remains horizontally scrollable.
- The first request could build the catalog and adaptive bank while a browser waited. Demo
  and e2e servers now prewarm them before accepting requests. Unit fixtures keep prewarming off.
- A client could manufacture effort with repeated `new_attempt: true`. Help escalation now
  consumes only newly completed runs/submissions belonging to that learner and problem.
- A rejected model reply could expose its hidden approach in an SSE delta before replacement.
  Protected problem replies are now buffered until the complete leak check passes.
- The beginner journey guessed the first shuffled option despite claiming to pass its check.
  It now chooses authored answer text and asserts that the server actually passed the check.
- The live tutor's valid explanation that `input()` “waits for you to type” failed a grader
  accepting only read/take/get wording. The grader now recognizes that definition, with positive
  and negative regression cases.

## Verification

| Check | Result |
| --- | --- |
| Requested browser suites plus landing | **31 passed, 3 expected skips**; isolated single-worker dev-server run. |
| Full Python coverage run | **490 passed, 24 skipped; 91.44% coverage**, above the required 85%. Three existing collection warnings concern the `TestInput` model name. |
| Focused regressions | 25 native/login/loop/contract tests, 16 tutor/learner tests, and 11 quiz/review/grading tests passed in their focused runs. |
| Live tutor scenarios | All seven scenarios validated; terminology passed its focused rerun after the grading correction. |
| Responsive/accessibility grid | Initial 137/144 passed; affected routes were rechecked in 40 combinations, then the remaining loading-state overflow passed all eight Attribution combinations. All initial failures have passing reruns. |
| Production build and TypeScript | Passed. |
| First-load JavaScript | All routes below the 250 KB gzip budget; largest is Today at 246 KB. |
| Ruff and mypy | Passed; 198 Python files formatted and 120 source files type-checked. |
| npm audit | Zero vulnerabilities; installed Next.js 16.4.3 matches the lockfile. |
| M0 contracts/model tests | 13 passed. |

Commands used:

```powershell
npx playwright test learner-journey keyboard learning-scope login-design landing --workers=1
.venv/Scripts/python.exe -m pytest services/api/tests -q --cov=socrat --cov-report=term --cov-fail-under=85 --basetemp=.cache/adaptive-final-all-20261025
.venv/Scripts/ruff.exe check services/api services/execution
.venv/Scripts/ruff.exe format --check services/api services/execution
.venv/Scripts/mypy.exe services/api/src services/execution/src
npm run typecheck
npm run build
npm audit --audit-level=high
.venv/Scripts/python.exe scripts/evals/tutor_eval.py --json
```

The system pytest temporary directory was inaccessible on this machine. Test runs used fresh
workspace-local temporary directories. No learner database or user-owned QA folder was removed.

### C: tutor

Seven real-model evaluation scenarios used the configured OpenAI-compatible provider and
`nvidia/nemotron-3-super-120b-a12b`: stuck, cruising, deadline, plan changes, planning conversation,
answer demand and beginner terminology. The first six passed. The terminology reply was correct;
after correcting the grading rule, its focused live rerun passed too.

Synthetic-provider regressions inspect every streamed delta for a protected approach. API and
browser probes cover filler chat, zero-attempt reveal refusal, forged effort, isolated histories,
and instruction blocking during an assessment. This is bounded coverage, not a claim that all
possible live-model jailbreaks, off-topic prompts or long-term memory behavior were exhausted.

### E/F: flows, layouts and accessibility

The browser suites exercise onboarding, placement, reading and checks, practice, tutor, settings,
plan changes, checkpoints, assessments, sprints, search and playground recovery. A separate grid
visited 18 routes in light/dark themes at 360, 768, 1280 and 1920 px: 144 combinations. It recorded
page errors, horizontal overflow, headings and screenshots, with axe scans at 360 and 1280 px.
Failures were reproduced and fixed; affected routes were checked again.

These checks use Chromium with desktop and phone emulation. They do not establish Safari,
Firefox, real-phone keyboard behavior, every historical QA matrix interaction, or long-duration
performance on other machines.

### G: robustness and ownership

An independent review ran 51 focused Python tests and direct API probes for anonymous access,
Origin/CSRF enforcement, logout replay, malformed input, private drafts, learning sessions,
adaptive quizzes, submissions, assessments, tutor histories and assessment instruction blocking.
Fresh QA accounts owned all resources used in cross-user checks.

Three waves of 12 concurrent health/feature requests passed before the final tutor fixes. Another
three waves of 12 requests passed afterward; the Windows listener stayed responsive. Injected
WinError 64, fatal error, closed-listener, cancellation, socket cleanup and subprocess regressions
also passed. This bounded load check is not a long-duration stress certification.

Local raw evidence is under `.cache/adaptive-*` and `temp/adaptive-*`; these scratch artifacts
are not committed. The existing user-owned `qa-report/` is unchanged.

## Remaining work and release notes

- A human must review the 60 provisional questions before they can be treated as approved
  question content. They write no mastery evidence until a review record exists. Existing check
  completion scores can include provisional answers; the review gate applies to mastery evidence.
- Author and review the 44 hidden draft concepts in a separate content change.
- Legacy dev accounts whose saved display name was changed, or which already have conflicting
  duplicate accounts, need an explicit data migration. This change does not guess which account
  to merge or discard.
- Native Docker execution requires rebuilding the runtime images with the updated `launch.py`
  and updating approved image profiles before enabling the new jobs in a deployment. Actual
  gVisor/Docker sandbox integration tests are unavailable on this Windows host; their skips are
  reported by pytest.
- No production deployment, PR merge, or full replay of the historical exhaustive QA campaign
  was performed.
