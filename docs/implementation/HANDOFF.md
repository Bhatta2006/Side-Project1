# Socrat Universal Learning Engine: handoff

Written 2026-11-02 and refreshed at the end of slice 9b, for any person or agent (any coding agent,
not only Claude Code) who continues this work. A root `AGENTS.md` and `CLAUDE.md` point here.
Read this file first, then `docs/implementation/universal-engine-plan.md` (the audit, the target
architecture, the phase table and the progress log). This file is the operating manual and the
honest status report; the plan is the strategy.

Branch: `feat/universal-engine` (pushed to `origin/feat/universal-engine`, 17 commits on top of
`main`, **no pull request opened**). `main` is one commit ahead (`039573e`, #60, a CI fix) and has no
new migrations. Slices 1 to 8, 9a and 9b are done. Last full API run: **798 passed, 24 skipped**
(21 min, after slice 9a; slice 9b added 5 tests and was verified with the related subsets only).
Ruff, mypy (187 files) and web typecheck clean, web production build clean at slice 8,
`tests/e2e/visuals.spec.ts` passes on desktop and mobile. **Never run on this branch:** CI, the older
Playwright suites, the visual-regression suite, any live model (see 5.1 and 5.4).

Commits on the branch, oldest first: `17b3c06` slice 1, `1481a78` 2, `afd1559` 3, `b0ebe0f` 4a,
`4d8a37d` 4b, `dfdcc53` 4c, `b2609ef` 5, `d57ae46` 6, `9f70ac8` 7, `4e6ff72` fix-ups, `48fc9d0` 8,
`688d13d` and `6098527` this document, `c235e33` slice 9a, `0a72e4d` slice 9b.

**Do this first (15 minutes):** read sections 1, 2 and 9 (rules, environment, git), run
`git log --oneline origin/main..HEAD` to confirm the state above, run the related test subset for
the area you will touch, then pick work from section 6.

**Update 2026-11-03 (gap closure against the master prompt).** The master prompt was found at
`D:\Downloads\SOCRAT_Universal_Learning_Engine_Master_Prompt.txt` on this machine. A depth audit
(`docs/implementation/ule-gap-audit.md`, section 0 has the current status of all 20 acceptance
criteria) led to twelve items, all committed on this branch after slice 10a: generation recovery
and progressive start, validation reports, competency graph and assessment contracts, evidence
types and stages with confidence calibration, review controls, grounded resource search,
declarative sketches and the `playground-visual` renderer, tasks and activity order,
Learning Evidence Library and Pedagogical Strategist, bridge lessons with visible revisions,
benchmark and outcome report, deterministic safety notes. How the engine fits together and how
to extend it: `docs/engine/README.md`. Migrations now run to `0044_course_revisions`. Owner
decision recorded: sketches become declarative (flag `explainer_sketch_declarative`, off until
switched). Every role is still only exercised with hand-written replies; a live-model run of
`scripts/dev/benchmark.py` is the first thing to do with a key.

**Update 2026-11-05 (Wondering ideas and calm lessons, section 4.11).** Answers are marked inside
quiz items, an Apply lesson closes each module, lessons read one page at a time with a recap
page, the AI and sources information moved to a ★ footnote at the end, and page size is worked
out per learner (`style/pages.py`). Three new flags, all off: `gen_marked_answers`,
`gen_applied_lessons`, `gen_lesson_pages` (the pager itself is on for every lesson). What is left
is in section 6, "Experience plan". Full API suite after this work: 988 passed, 24 skipped
(26 min). On this machine pytest needs `--basetemp` pointing at a
folder you own, or every test using a temp folder errors at setup (421 errors, no failures).


**Update 2026-11-07 (strict placement, branch `fix/strict-placement`).** The owner asked for
placements that are hard to pass and for today's lesson to start where placement ended, never
back at the start. Placement now asks only hard questions: a new placement-only bank
(`content/placement/{zero,dsa,cp}.yaml`, 283 items: edge cases, traces, fill-in-the-blank, bugs;
loaded by `socrat/placement/bank.py`), then the concept's own difficulty 4-5 quiz items. A concept
counts as known only after two right answers; one miss or "not sure" marks it unknown; two spot
checks test concepts below the frontier that the search only inferred; at most 60% of a path can
be placed (`SKIP_CAP`, was 85%). The planner puts placement confirmation checks after the first
lesson at the frontier instead of before it, and the placement summary names the concept the
plan really opens with plus the topics placement caught as gaps. Every code question in the bank
is executed in Python, C++ and Java by `scripts/dev/verify_placement_bank.py` (all pass). This is
a behaviour change, not behind a flag, because the owner asked for it as a fix. Not verified: a
real learner session in the browser.

---

## 1. What the owner wants (do not re-ask these)

The owner of Socrat asked for a "grade up" of Socrat into a **Universal Learning Engine**: scalable
and international, so any student can learn anything without going elsewhere. Their framing:

> We are not generating another course. We are generating a complete engine. Think of it as Claude
> Code, not exactly code, but an analogy. Our engine is Claude Code for course generation: how
> Claude Code can create any project, Socrat can generate any course, whatever the learner wants
> to learn and however they want to learn. A complete, adaptive, personalised engine.

The master prompt is `d:\FireFox Downloads\SOCRAT_Universal_Learning_Engine_Master_Prompt.txt`
(1,140 lines, outside the repo; if you do not have it, section C and G of the plan doc restate its
requirements as audited gaps and phases). Its rules that matter most: audit first, small
reviewable steps, additive migrations with tested downgrades, deterministic code over an LLM
wherever possible, be honest about domains that cannot be verified, never claim an unfinished
deliverable, wait for approval before destructive migrations, every phase behind a flag that
defaults off.

Explicit instructions from the owner:

- **API keys:** ask the owner when a key is actually needed; they will supply one. **Do not use
  ChatGPT 5.5.** Never commit a key. Keys live in untracked `.env`.
- **Intent UX:** the subject is free text with suggested options; the learner's level, age or
  register, style and daily time are **fixed options** (for example "I am 5 years old", gamified,
  daily 5 minute read, university level, intermediate).
- **Community:** a course a learner makes can be published to other learners **only if they agree**;
  when it gets a good number of enrolments, the creator gets **perks** so a community forms.
- **Testing anything that needs a model:** "treat yourself as the model and do what the model is
  intended to do." That is how the end-to-end tests were written: the engine code is real, the
  model's replies are written by hand in the test (see `tests/test_engine_e2e.py`).
- **Workflow:** work in phases, use whatever skills help, commit locally, push only when told
  (the owner told us on 2026-11-02 to push the branch; it is pushed). Earlier standing rule from the
  owner (memory note `course-generation-architecture`): do **not** merge `main` into a feature
  branch; keep changes merge-friendly (small additive edits to shared files, new code in new
  modules). Migrations may need renumbering at merge time (`down_revision` and
  `services/api/src/socrat/schema_revision.py`) if `main` gains newer ones. Right now `main` has
  no new migrations.
- **Pronouns:** use they/them for people whose pronouns are not stated.
- Commit trailer used on this branch: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

Product principle from the owner (memory note `engine-is-the-harness`): the engine's **verified
capabilities are the product; the model is a replaceable part**. Models explain and word things;
deterministic code decides, verifies and grades. New abilities go into `socrat/harness/` as typed,
sandboxed capabilities, not as special cases elsewhere.

---

## 2. How to work in this repo (environment quirks that cost real time)

Windows 11, Git Bash and PowerShell. Python via `uv`. Run everything from the **repo root**
`D:\Socrat` (the test fixtures open `alembic.ini` relatively, so running pytest from
`services/api` fails with "No 'script_location' key found").

```bash
# API tests (full suite is ~19 minutes; run a subset while iterating)
uv run --project services/api pytest services/api/tests/test_localize.py -q \
  --basetemp "<a folder you own>"          # default temp raises PermissionError on this machine
uv run --project services/api ruff check services/api
uv run --project services/api ruff format services/api
uv run --project services/api mypy services/api/src
# Web
cd apps/web && npx tsc --noEmit -p . && npx next build
# Real browser (starts the API on :8000 with a fresh socrat.e2e.db and Next on :3000 itself)
npx playwright test tests/e2e/visuals.spec.ts          # both projects: desktop and mobile
```

Gotchas:

1. **CRLF line endings.** Most source files are CRLF in the working copy. A Python script that
   does `s.replace("a\nb", ...)` on a file read in text mode will silently not match. Read with
   `newline=""`, detect `nl = "\r\n" if "\r\n" in s else "\n"`, normalise to `\n`, edit, write back
   with the original `nl`. The Edit tool handles this correctly. Git warns "CRLF will be replaced
   by LF" on commit; that is expected.
2. **Bash heredocs** containing apostrophes or several heredocs in one command sometimes fail with
   "unexpected EOF" and apply nothing. Use the Write tool for large files, or write a small Python
   patch script to a scratch folder and run it. A `\n` typed inside a Python string in a heredoc
   can also end up as a real newline inside a TypeScript string literal (this happened once).
3. `ruff format` rewrites files; commit after running it, and re-read a file before editing it
   after a format pass.
4. Importing a test fixture (`from test_learner_api import client, login`) needs
   `# ruff: noqa: F811` at the top of the test module (a test parameter "redefines" the fixture).
5. In Playwright, **`locator.isVisible()` does not wait**, and the first sign-in shows a plans dialog
   ("Maybe later") that makes the rest of the page `aria-hidden` until dismissed. Dismiss it with
   `click({timeout}).catch(() => undefined)` before `getByRole` assertions.
6. `apps/web/next-env.d.ts` is regenerated by every Next build and shows as modified. Do not commit it.
7. Next.js here is **v16 with breaking changes**. Read `node_modules/next/dist/docs/` (at the repo
   root `node_modules`) before writing Next code. `cookies()` is async and using it in the root
   layout makes every page dynamic; that is why the locale is applied client-side (see 4.6).
8. Repo rule: use `npx ctx7@latest` for library or API documentation questions (not used so far).
9. Untracked directories (`.agents/`, `.kiro/`, `.windsurf/`, `qa-report/`, `apps/web/.next-*`)
   are not part of this work; stage specific paths, never `git add -A` at the root.

---

## 3. Status against the master plan phases

The plan's phase table (section G of the plan doc) and what is actually done:

| Phase | Status | What is done | What is not |
|---|---|---|---|
| 0 Baseline | Done | Plan doc, baseline (711 passed at start) | |
| 1 i18n foundation | **Partial** | Locale on profile (`PATCH /me`), provider with English fallback, `lang`/`dir` set client-side, language picker, Hindi catalog (Today card, settings, lesson notice, nav, `/new`) | Landing page not translated; no extraction lint (CI check for new literals); locale-aware dates and numbers; no cookie (signed-out choice is in `localStorage` only); visual regression and bundle budget were not re-run after the web changes |
| 2 Locale-addressable content | Done, with a gap | `content_translations`, glossary lock, placeholder masking, deterministic checks, stale detection, review by a named person, `?locale=`, status labels, quiz text served | "Execution re-verification" of translated code or quiz keys is **not** implemented: code is masked and never sent to a model, so it cannot change, but nothing re-executes it |
| 3 Multilingual tutor and pipeline | **Partial** | Tutor reply-language directive; admin-triggered translation through the gateway role `translator` | No language detection; **Sarvam backend not wired (needs the owner's key)**; no batch translation job on the worker; no per-language tutor eval for the help ladder and leak guard |
| 4 Learner-typed courses | Done, with gaps | Intent parser (model, rules fallback), fixed choices, learning requests API, diagnostic, private courses, community sharing with consent and credit, moderation, creator perks, pause and resume | "Reuse of cached identical intents across learners" not done; plan-based quotas beyond the per-learner budget and open-request cap not done |
| 5 Adapters and renderers | Done, with gaps | 6 adapters, 8 renderer manifests with typed params, Experience Designer, host in web with `markdown`, `function-plot`, `concept-map`, `self-check`, `simulation`, `timeline`, `code-studio` | `concept-playground` (sandboxed iframe) not served; visuals write **no evidence** yet |
| 6 Access and low bandwidth | **Started** (10a) | System-font fallbacks for Indic and Arabic; lite mode (flag `lite_mode_enabled`, Settings "Data use"); lazy UI catalogs and lesson visuals host | TTS and STT, offline lesson cache (owner chose: opt-in, signed-in only, lesson reads only, cleared on sign-out), Noto subsets, WCAG audit per locale, throttled-3G test |
| 7 Scale | **Partial** (9a) | Per-learner limits (per process), public cache headers on catalogue lists, per-course cost report, load tool with recorded results, cold-start stall fixed, worker can run generation with heartbeat health check and queue depth | Real-stack exercise of the worker split, CDN rules for course reads, shared Redis limits, per-tenant budgets, staging load test |
| 8 Region and compliance | Not started | | Region policy matrix, per-country consent and minors rules, data residency, regional runbook |
| 9 Payments and launch | Not started | | Currency and tax expansion, local methods, staged rollout, rollback drill |
| 10 Research loop | Not started | | Outcome experiments per locale, calibration, benchmark and regression harness of representative courses |

Additional work done beyond the phase table (all described in section 4): Course Maintainer,
version history and rollback, Adaptive Coach audit and tutor "how you asked to be taught" block,
`code.judge`.

---

## 4. What was built, slice by slice

Everything is behind a flag or an owner-only route unless noted. Migrations are additive with
downgrades; the downgrade test is `tests/test_quiz_runtime_tables.py` (add new tables to its
`TABLES` set) and the head revision constant is `services/api/src/socrat/schema_revision.py`
(currently `0039_course_maintenance`).

### 4.1 Slice 1: Intent Parser (`17b3c06`)
- `coursegen/intent.py`: `Intent` model (subject, domain, adapter, goal, levels, approach, balance,
  register, minutes per day, accessibility, code languages, verifiability, safety notes,
  clarifications, `blocked`), `from_rules` fallback when no model, `parse`, `to_brief`, `slug`.
  Free text from the learner is treated as data in the prompt.
- `coursegen/requests.py`: learner API `/api/v1/learning-requests` (create, list, get, confirm).
  Flag `learning_requests_enabled` (default **off**); max 3 open requests; budget $3; idempotent
  (same text from the same learner returns the same request).
- Migration 0034 `learning_requests`; role `intent` in `coursegen/roles.py`.

### 4.2 Slice 2: fixed choices and private courses (`1481a78`)
- `PRESETS` (groups who, level, style, time), `SUBJECT_SUGGESTIONS`, `check_choices`,
  `apply_choices`, `GET /learning-requests/options`, `/publish`.
- Migration 0035 `generated_courses.owner_id`. A learner's course is private to them (hidden in
  `/courses`, enrol guard in `learn/routes.py`).
- Web page `apps/web/src/app/new/page.tsx`.

### 4.3 Slice 3: community and creator perks (`afd1559`)
- Migration 0036: `visibility`, `shared_at`, `credit_name`, table `creator_perks`.
- `coursegen/community.py`: share and unshare with **consent required** and credit choice
  (anonymous or name); perk tiers at 10 (badge), 50 (30 days Plus), 250 (90 days Plus) **other
  active learners**; one-day account-age floor; idempotent `sweep`, run by the worker
  (`worker.award_perks`); `entitlements.plan_of` honours creator Plus perks.
- Enrolments: `GET /enrollments`, `POST /enrollments/switch` (a learner has one *active* course;
  switching pauses others); learner-made courses skip the one-course rule.
- Today page card "Build your own course", gated by `features.learning_requests`.

### 4.4 Slice 4: moderation, adapters, renderers, diagnostic (`b0ebe0f`, `4d8a37d`, `dfdcc53`)
- Migration 0037: `moderation`, `course_reports`, `diagnostics`.
- `coursegen/moderation.py`: learner report `POST /api/v1/community/courses/{id}/report`, auto-hold
  at 3 reporters (reason "unsafe" counts double), admin queue under
  `/api/v1/admin/community/courses`; sharing requires a published course with at least one live
  concept; max 5 shared courses per learner; a removed course cannot be re-shared.
- `engine/domains.py`: adapters math-science, software, electronics, music, animation-movement,
  general. Each states verifiability, whether it needs physical practice or an external
  evaluator, safety notes. `intent.apply_adapter` can only make an intent **more** cautious.
- `engine/renderers.py`: 8 manifests with typed params, events, runtime, evidence kind, accessible
  alternative, error handling; `VisualizationSpec` and `validate_spec`; deterministic `select`.
  Public catalogue routes `/api/v1/engine/domains` and `/renderers`.
- `coursegen/diagnostic.py` and `diagnostic_routes.py`: the model writes questions, **code**
  validates, shuffles and keeps the answer key server-side, scores deterministically, suggests a
  level, writes no evidence, returns 503 offline (no invented offline questions).

### 4.5 Slice 5: typed visuals and the e2e run (`b2609ef`)
- `catalog/schema.py`: `Visual` and `Concept.visuals`, validated against the renderer registry.
- `engine/design.py`: Experience Designer (role `experience`, flag `gen_visuals` default off). It sees
  only the renderers its adapter allows, results are validated and capped at 2, it never blocks a
  lesson, and the reviewer prompt mentions visuals. `markdown` and `code-studio` are never offered
  to the designer.
- `tests/test_engine_e2e.py`: a teenager asks for circuits; intent, adapter honesty, outline,
  critic, diagnostic, private publish, enrol at the diagnosed level, first lesson authored,
  fact-checked, reviewed, designed and released, learner view. **It found a real production bug**:
  enrolling at a level whose start concept is still `planned` crashed with `IndexError` (500);
  fixed in `learn/placement.py` (earlier concepts become placed-known, start becomes None).

### 4.6 Slice 6: multilingual layer (`d57ae46`, plus fix-ups in `4e6ff72`)
- Migration 0038: `users.locale` (default `en`), `content_translations` (concept, locale, source
  hash, units, status `machine|reviewed`, model, glossary version, reviewer).
- `localize/locales.py` (10 locales: en, hi, te, ta, bn, mr, es, pt-BR, id, ar; script, RTL,
  `engine` hint sarvam or gateway, `preview` flag for languages not yet benchmarked),
  `localize/glossary.py` (data-structure terms kept in English), `localize/translate.py`
  (mask code, math, links, tags as placeholders; never send answer keys; deterministic checks:
  placeholders exactly once, numbers equal as a multiset, target script share, English leftovers
  for Latin-script targets, glossary terms, heading count, empty or out-of-proportion text; one
  retry round that names the problems), `localize/service.py` (save, `current`, `overlay`,
  `quiz_item`, `stale`), `localize/routes.py` (`GET /api/v1/locales` with an Accept-Language
  suggestion; admin `POST/GET /api/v1/admin/translations`, `POST .../{concept}/{locale}/review`
  needing a reviewer's full name, one translation at a time).
- Concept view overlays translated text only while the source hash still matches; otherwise
  English. `?locale=en` shows the original for one view. Quiz prompt, options and explanation are
  translated in the **standard quiz** (`learn/quizzes.session_view`), with ids, the answer index
  and the shuffle (which depends only on the id and option count) untouched.
- Tutor: `localize.tutor_directive` adds a `reply_language` section; help ladder and leak guard
  unchanged.
- Web: `apps/web/src/lib/i18n/` (provider, `t`, `tx`, `en.ts`, `hi.ts`), `components/language-picker.tsx`,
  `components/nav-label.tsx`, `<html lang/dir>` set in an effect (static pages stay prerendered).

### 4.7 Slice 7: Course Maintainer and coach (`9f70ac8`, plus `4e6ff72`)
- Migration 0039: `concept_versions` (every replacement of a released generated concept is kept,
  deduplicated by digest, written inside `catalog/generated.store_concept` via `keep_version`),
  `resource_health`.
- `coursegen/maintain.py` (flag `maintainer_enabled` default **off**, no model for the core loop):
  scheduled link checks of released generated concepts (a link is **dead** only after 3 failures
  spread over at least 2 days); dead links removed as a new version when at least two good links
  remain; `find_replacements` asks the researcher for sources where fewer than two remain
  (the model proposes, the link check decides; a nominal 10 minute reading time is recorded and the
  version reason says it was found by search, not reviewed); queue of what needs a person (dead
  without replacement, ageing lessons: 180 days for code courses, 365 otherwise, resources
  learners mark unhelpful); `rollback` (refused with 409 while a rewrite job is active; itself
  undoable); `lost_ids` reports quiz, problem and exercise ids a rewrite would orphan. Learners are
  not shown dead links (`learn/resources.personalised`). Owner API `/api/v1/admin/maintenance`.
  Worker runs it every 6 hours when the flag is on. Admin web tab "Upkeep"
  (`components/engine-upkeep.tsx`): maintenance queue, version restore, translation review.
- Adaptive Coach audit for generated courses (`tests/test_engine_coach.py`): today, plan, progress,
  profile, proposals, nudges, path options, weekly review, tutor context and the standard quiz all
  work for a generated course and quiz evidence reaches the profile. **Gap found and fixed:** the
  learner's own picks (register or age, approach, balance, minutes) shaped how lessons were written
  but not how the tutor talks. `coursegen/audience.py` now adds a "How you asked to be taught"
  block from the **validated enum fields only**, only for the learner's own course; free text and
  other authors' courses never reach the tutor through it. The block repeats that the help ladder
  and the no-early-solution rule still apply.

### 4.8 Slice 8: `code.judge` and the remaining renderers (`48fc9d0`)
- `harness/library.py`: `code.judge` is a real capability. It judges **finished runs**
  (accepted, wrong_answer, runtime_error, time_limit) using `execution.protocol.same_output`, the
  same comparison as the learner judge. It does not run code (running stays with the execution
  service). `tutor=False`. The special case that pretended it existed in
  `engine/domains.check_adapter_renderers` was removed.
- `engine/routes.py`: `GET /api/v1/engine/simulations` (ranges, units, defaults) and
  `POST /api/v1/engine/simulate` (signed-in, CSRF, inputs default to the experiment's defaults,
  out-of-range refused with 422, computed by `physics.simulate` through the sandboxed harness).
  `Simulation` params in `engine/renderers.py` are validated against the same ranges.
- Web: `components/visuals/{simulation,timeline,code-task}.tsx`, wired in
  `components/visualization-host.tsx` (wrapper has `role="group"`). The dev gallery
  (`app/dev-gallery/gallery.tsx`) shows one of each; `tests/e2e/visuals.spec.ts` drives them in a
  real browser against the real API.

---

### 4.9 Slice 9a: scale guards (`c235e33`)
- `limits.py`: sliding-window limiter (`LIMITER`, `enforce(scope, user_id, limit, window)`),
  **per process** (no Redis provisioned; stated in the module). Applied to `POST /engine/simulate`
  (`simulate_per_minute`, default 60) and diagnostic creation (`diagnostic_per_hour`, default 10);
  0 turns a limit off. Model calls were already limited by `assistant/budget.py` (database-backed).
- `httpcache.py`: ETag and `public, max-age=300` with 304 for `/engine/domains`, `/renderers`,
  `/simulations`. `main.boundary` now uses `setdefault` so everything else stays `no-store`.
  `/locales` is deliberately not cached (it varies with `Accept-Language`).
- `coursegen/costs.py`, `cost_routes.py`: `GET /api/v1/admin/engine-costs` (per course: jobs, cost,
  released concepts, cost per released concept; per role this month from `ai_usage`).
- `scripts/dev/loadtest.py` and `docs/implementation/load-test-results.md`: 25 learners p95 85 ms,
  100 learners p95 295 ms, zero errors, on one laptop process with SQLite (not production capacity).
- **Bug found by the load test and fixed:** `default_catalog()` used `functools.cache`, which lets
  every concurrent caller compute on a miss, so 25 learners on a cold server each parsed the catalog
  (about 6 s CPU apiece) and `/courses` timed out for all of them. Now `catalog.registry.single_flight`
  plus a catalog load at API start (awaited when `SOCRAT_PREWARM_CONTENT=true`, background thread
  otherwise, skipped in tests). Regression test in `tests/test_scale.py`.

### 4.10 Slice 9b: API/worker split (`0a72e4d`)
- The worker (`worker.py`) did not run course-generation jobs; only the API did (`gen_runner`).
  Turning the API runner off would have stopped generation. Now the worker can run them
  (`worker_runs_generation`, `worker_generation_concurrency`); `jobs.claim` is atomic so both running
  is safe; a dead generation loop raises and stops the worker.
- Heartbeat: `worker.beat/healthy`, setting `worker_heartbeat_file`, `python -m socrat.worker --check`
  (stale after 300 s), wired as the worker healthcheck in `infra/runtime/production/compose.yaml`
  and `staging/compose.yaml`. Compose defaults keep today's behaviour.
- `costs.queue` adds queued, running and oldest-queued seconds (paused courses excluded) to
  `/admin/engine-costs`.
- Runbook `docs/operations/api-worker-split.md` (switch order, rollback, what to watch). The staging
  worker has no AI settings, so do not enable generation there without adding them.
- Tests: `tests/test_worker_split.py` (5). **Not exercised on a real Compose stack.**

### 4.11 Wondering ideas and calm lessons (`ea3c983`, `9a1512b`, `33fd9a5`, 2026-11-05)
Source: the signed-in Wondering record (`research/wondering/2026-11-05/`, audit in
`universal-engine-audit-3.md` section 10) and the owner's notes on text overload. Plan:
`docs/implementation/experience-plan.md` (phases A to D, owner decisions in its section 9).
- **Answers marked in the item** (`coursegen/keyed.py`, flag `gen_marked_answers`): quiz items and
  atom checks mark the right option; code derives the index and drops an item whose key is
  unclear. Both forms are always parsed. 12 tests.
- **Apply lesson per module** (`coursegen/applied.py`, flag `gen_applied_lessons`): code adds an
  application lesson after each module of a learner's course, depending on up to four of its
  concepts. 5 tests. It writes **no transfer evidence** yet (owner decision 4 in the plan).
- **Lessons one page at a time** (web, not flagged; the owner approved it and "Show the whole
  lesson on one page" is the way back): `components/lesson-pages.tsx`, `lib/pages.ts`. Each `## `
  section is a page; visuals and tasks are pages in the planned order; the last page is a recap
  (key reminders, two pitfalls, feel controls, Mark as read, concept check). `<details>` answers
  render as a reveal (`components/markdown.tsx`). The old "Your path through this lesson" box,
  the side column reminders and the finish section were folded into the pager.
- **★ About this lesson** (owner approved): how it was written, checked, translated and sourced,
  and why it is taught this way, moved from the top of the lesson to `#about-lesson` after it; a
  ★ link by the title jumps there. The course brief's safety notes stay above page 1
  (`ConceptView.safety`, `learn/views._safety`).
- **Page size per learner** (`style/pages.py`, flag `gen_lesson_pages`). Owner's rule: no fixed
  sizes and not only "kids" or "university"; length and style follow the learner. A page
  profile (words per page, pages per sitting, ideas per page, check rhythm, page elements) is
  computed from register, starting and target level, approach, theory or practice balance,
  minutes per day, accessibility, depth and rigor. It goes into the author's prompt and
  `package.check_lesson` checks the draft against it instead of the character floor.
  `Brief.learner` carries the learner's picks. 5 API tests, 4 web tests.
- Browser check (offline API, Programming from Zero, `programs-and-output`): 8 pages, arrow keys
  and focus, recap, ★ link and footnote, the one-page toggle, no sideways scroll at 375 px.
  **Not run:** the Playwright suites, any lesson written by a live model under `gen_lesson_pages`.

## 5. Reports

### 5.1 Test and tooling results
| When | Result |
|---|---|
| Start of work (main after #59) | 711 passed, 24 skipped (16m43s) |
| After slice 7 | 784 passed, 24 skipped (19m28s) |
| After slice 8 and fix-ups | 791 passed, 24 skipped (19m02s); ruff, mypy (183 files), web typecheck, `next build` clean |
| After slice 9a | **798 passed, 24 skipped (21m34s)**; ruff, mypy (187 files) clean |
| After slice 9b | `test_worker_split`, `test_production_runtime`, `test_staging_contract`, `test_foundation` (18 + 15 tests) pass; full suite not re-run |
| Load test (9a) | 25 learners p95 85 ms; 100 learners p95 295 ms; 0 errors; single laptop process, SQLite |
| Browser | `tests/e2e/visuals.spec.ts` passes on desktop and mobile Chromium |
| 2026-11-05, after section 4.11 | **988 passed, 24 skipped (25m51s)**; ruff, mypy (208 files), web typecheck clean; web unit tests 20 pass; Playwright suites not run |

Tests added on this branch: `test_learning_requests.py` (slices 1 to 3, community, perks, pause and
resume), `test_diagnostic.py`, `test_engine_registry.py` (adapters, renderers, `code.judge`,
simulations), `test_engine_experience.py`, `test_engine_e2e.py`, `test_localize.py` (17 test functions),
`test_maintainer.py` (10), `test_engine_coach.py` (4), `test_scale.py` (7), `test_worker_split.py` (5),
`tests/e2e/visuals.spec.ts`. Modified:
`test_link_health.py`, `test_quiz_runtime_tables.py`.

**Not run after the web changes:** the existing Playwright suites (`learner-journey`, `layout`,
`accessibility`, `landing`, `keyboard`, and the visual regression config `playwright.visual.config.ts`),
the Lighthouse budgets, and the CI pipeline itself. The shell nav now renders through `NavLabel`
and `/new`, Today and Settings use `useI18n`; for English the strings are identical, but this has
**not** been proven by the visual suite. Run it before merging.

### 5.2 Bugs and gaps found by testing, and what was done
| Finding | Where found | Resolution |
|---|---|---|
| Enrolling at a level whose start concept is still `planned` returned 500 (`IndexError`) | End-to-end run, slice 5 | Fixed in `learn/placement.py` |
| `domains.classify`: the hint `general` outweighed real keyword matches | Slice 4 tests | Hint "general" excluded from the bonus |
| Designer examined only the first 4 entries | Slice 5 | Now 8, cap 2 kept |
| Changed number slipped through when the same digit appeared elsewhere | Slice 6 tests | Numbers are compared as multisets |
| New `ResourceHealth` rows had `failures=None` until flush (TypeError) | Slice 7 tests | Fields set explicitly |
| Tutor ignored the learner's own picks (age, approach, balance) in their own course | Coach audit | `coursegen/audience.py` |
| Invalid ARIA (`aria-label` on a plain div) hid visuals from assistive tech | Real-browser test | Wrapper now `role="group"` |
| Duplicate `generation_in_progress` key in `lib/api.ts` MESSAGES | Slice 2 | Removed |
| Request idempotency key mismatch (trailing space and `|`) | Slice 1 tests | Text normalised before keying |

### 5.3 Honesty decisions (keep these; the plan forbids overclaiming)
- Diagnostic and intent have **no invented offline fallback** for questions; intent has a rules
  fallback only. Without a model the diagnostic returns 503.
- Translations are labelled `machine` until a named person confirms them. Latin-script targets
  (es, pt-BR, id) are only checked heuristically for English leftovers, so they, and mr and ar,
  stay `preview` until a native reviewer signs off.
- Creator perks have an account-age floor, but **self-farming is still possible**; admin review of
  Plus grants is recommended before billing is switched on.
- Visuals claim **no evidence**: events such as `predicted`, `observed`, `marker_placed` are not
  recorded server-side. Free-practice code tasks are labelled "not judged".
- Replacement resources found by the maintainer carry an invented nominal reading time (10
  minutes) and are not human reviewed; the version reason says so.
- The adaptive-quiz engine is not calibrated for generated concepts; it reports `engine: legacy`
  and the standard quiz serves them.

### 5.4 Not verified against a live model
**Every model-facing role has only run against scripted replies**: intent, architect, critic,
researcher, author, quiz, atoms, facts, reviewer, experience, diagnostic, translator. The roles
share the gateway (`assistant/gateway.make_provider`) and per-role settings in
`coursegen/roles.py` (`SOCRAT_GEN_ROLES`). Prompt quality, JSON conformance rates, cost per course,
latency and translation quality are therefore **unmeasured**. This is the biggest open risk.

---

## 6. Remaining work, in the order I recommend

Items marked KEY need something from the owner.

### Experience plan (calm lessons, fast courses, honest practice): started 2026-11-05
Done: phase A1-A2 core (pager, recap, footnote), C2 page profiles (flagged), D1 marked answers
(flagged), the Apply lesson (flagged). Left, in this order (details in `experience-plan.md`):
1. Run the Playwright suites (`visuals`, `learner-journey`, `layout`, `accessibility`, `keyboard`
   and the visual config) against the paged lesson; the visual baselines for the lesson page
   will need updating on purpose. Add the A4 check (at most 120 words above the first Next).
2. A1 remainder: atom checks between pages, swipe on phones, the per-page "Simpler / Another
   example / Go deeper" toolbar, resources and practice folded into the recap.
3. B-UI1 plan on `/new` (names, chips, Request changes, details disclosure), B-UI3 Today with one
   Continue card.
4. C2 remainder and A3: `terms` and `follow_ups` in the author's contract, terms on tap,
   follow-up chips; one visual per page.
5. C3, C1: fewer models in a row, plan skeleton first. KEY: a live-model key to measure.
6. D1 true-or-false and fill-the-gap kinds, C4 practice menu per lesson, B-UI2 course path.
7. KEY D2-D4: practice evidence at a lower weight, one review across courses, transfer evidence
   from the Apply lesson (owner decisions 3 to 5).
8. A live-model run with `gen_marked_answers`, `gen_applied_lessons` and `gen_lesson_pages` on,
   then a person reading the lessons, before any of the three flags is turned on by default.

### Slice 9: scale (Phase 7). Started (9a done, 2026-11-02), remainder below
Done in 9a: per-learner sliding-window limits on `POST /engine/simulate` and diagnostic creation
(`limits.py`, settings `simulate_per_minute`, `diagnostic_per_hour`; **per process**, 0 turns off);
ETag and `public` cache headers on `/engine/domains|renderers|simulations` (`httpcache.py`; every
other route stays `no-store`); `GET /api/v1/admin/engine-costs` (generation spend per course, cost
per released concept, per role); load test tool `scripts/dev/loadtest.py` with recorded results in
`docs/implementation/load-test-results.md`; **fixed a cold-start stall** (catalog parsed once per
concurrent request; now `catalog.registry.single_flight` plus a load at API start).
Already existed (do not rebuild): `ai_usage` ledger with per-learner and global daily and monthly
budgets (`assistant/budget.py`, `GET /admin/ai-costs`), multi-process-safe `jobs.claim`.
Remaining:
1. **Shared rate limits.** Swap `limits.LIMITER` for a Redis-backed class with the same `allow`
   signature once Redis is provisioned (it is not in `compose.yaml`). Until then N processes allow N times the limit.
2. **Worker split (9b, code and runbook done, not yet exercised on a real stack):** the worker can
   run generation (`SOCRAT_WORKER_RUNS_GENERATION`), has a heartbeat health check, and the queue
   depth is in `/admin/engine-costs`. Follow `docs/operations/api-worker-split.md` on staging
   (needs AI settings added to the staging worker), then production. Defaults keep today's behaviour.
3. **CDN rules** for released course reads (`/courses`, concept GETs). They vary by user (private
   courses, locale overlay), so they need `Vary` or a public/private split before any cache header.
4. **Per-tenant or per-plan budgets** and quota for learner-typed courses; cached reuse of identical intents.
5. **Load test against the staging stack** (Postgres, several processes), including write paths
   (enrol, quiz answers, submissions). Add the result to `load-test-results.md`.

### Slice 10: access and low bandwidth (Phase 6)
**10a done (lite mode):** `apps/web/src/lib/lite.ts` (`useLite`, per-device `socrat:data-use`, Auto
follows `navigator.connection.saveData` or 2G), `components/data-use.tsx` in Settings, warm-up of
Pyodide skipped in lite mode (`problems/[id]`, `landing/try-tutor`), `HEAVY` renderers
(`function-plot`, `simulation`) held behind a button in `visualization-host.tsx`. The e2e server sets
`SOCRAT_LITE_MODE_ENABLED=true`. Budget finding: before 10a, 5 routes on this branch were over the
250 KB CI budget; after it, only `/today` (250.4 KB), fixed in the next commit by loading the
"How Socrat is adapting to you" card on demand (`/today` 246.1 KB; every route now within budget,
covered by `tests/e2e/today.spec.ts`).
**Next (10b), decided by the owner:** offline lesson cache, opt-in (flag plus a setting), signed-in
only, lesson reads only (never quiz answers, chat or progress), cleared on sign-out; then Noto subsets.
Text-to-speech and speech-to-text behind flags (**KEY: Sarvam key for Indic**; the owner's session
has Sarvam MCP tools available, but the product code needs a key in its own environment), lite mode
(no WASM until needed), offline lesson cache, Noto font subsets instead of relying on system fonts,
WCAG audit and axe per locale, throttled-3G test of a lesson.

### Slice 11: i18n completion (Phases 1 to 3)
Translate the landing page and the rest of the shell; add the CI extraction lint (fail when a
migrated file adds a literal without a catalog key); locale-aware dates, numbers and currency;
a cookie so signed-out visitors keep their language; per-language tutor eval proving the help
ladder and leak guard hold in each launch locale (extend `tests/eval` style tests; look at the
nightly tutor eval); language detection; a batch translation job on the worker (idempotent on
retry); re-execute translated code and quiz keys. **KEY: Sarvam backend** (`locales.engine ==
"sarvam"` marks which locales should use it; the gateway path already works for any provider) and a
key for non-Indic languages. **KEY: native reviewers** per language to remove the `preview` flag.

### Slice 12: region, compliance, payments (Phases 8 and 9)
Region policy matrix reviewed by a qualified person (DPDP India, GDPR and UK, COPPA and minors),
consent copy per locale, data-residency toggle, regional runbook; currency and tax, local payment
methods; staged rollout and a rollback drill. Razorpay live keys are needed only here (**KEY**).
Existing account erasure and export are built; test them per region.

### Slice 13: research and evaluation loop (Phase 10)
A benchmark and regression harness of representative generated courses (the master plan asks for
one), outcome experiments per locale (retention, transfer, hint dependence), calibration of the
scheduler and mastery model. No claims beyond the data.

### Do these before or alongside slice 9 (they de-risk everything)
1. **Live-model pass. KEY: the owner's API key** (not ChatGPT 5.5; Anthropic or the existing Nebius
   endpoint both fit the gateway). Run the real pipeline once for a few subjects (a technical one,
   a school one, a non-code one such as music or electronics), record JSON conformance, cost and
   latency per role, and fix the prompts. Set per-role models with `SOCRAT_GEN_ROLES`.
2. **Run the existing Playwright suites and visual regression** on this branch (see 5.1).
3. **Run CI on the branch** (open a draft pull request) to see the real pipeline.
4. Open items inside finished slices: visuals recording evidence; serving `concept-playground`;
   `web` UI for diagnosing a failed maintenance pass; admin review of Plus perk grants;
   evidence from the timeline and simulation events; a "report a bad translation" learner control;
   Maintainer detection of stale **content** beyond age (no model is used for it today).

### Before merging to `main`
Open a PR, run CI, run the full API suite and the browser suites, rebase or merge per the owner's
instruction (the standing rule is no merging `main` into the feature branch), renumber migrations
if `main` gained any, review flags (all new features default **off**: `learning_requests_enabled`,
`gen_visuals`, `maintainer_enabled`; translations only appear once an admin stores them), and
decide with the owner when to turn each on.

---

## 7. Where things are (read these first)

| Need | Look at |
|---|---|
| Strategy, audit, phase table, progress log | `docs/implementation/universal-engine-plan.md` |
| Generation pipeline and jobs | `services/api/src/socrat/coursegen/` (`jobs.py` run loop, `package.py` gates, `roles.py` per-role model, `budget` metering) |
| Intent, choices, requests | `coursegen/intent.py`, `coursegen/requests.py` |
| Diagnostic | `coursegen/diagnostic.py`, `diagnostic_routes.py` |
| Community, perks, moderation | `coursegen/community.py`, `coursegen/moderation.py` |
| Adapters, renderers, designer, simulation API | `engine/domains.py`, `engine/renderers.py`, `engine/design.py`, `engine/routes.py` |
| Verified capabilities (the harness) | `harness/registry.py`, `harness/library.py`, `harness/physics.py`, `harness/sandbox.py` |
| Languages | `localize/` (and `apps/web/src/lib/i18n/`) |
| Maintenance, versions | `coursegen/maintain.py`, `catalog/generated.py` (`store_concept`, `keep_version`) |
| Tutor context | `assistant/service.py` (`learner_sections`, turn plan), `coursegen/audience.py` |
| Generated course storage | `models.py` (`GeneratedCourse`, `GeneratedConcept`, `ConceptVersion`, `ContentTranslation`, `LearningRequest`) |
| Flags and settings | `config.py` (search `_enabled`, `gen_`, `maintainer_`, `community_`) |
| Web visual host | `apps/web/src/components/visualization-host.tsx`, `components/visuals/` |
| Admin UI | `apps/web/src/app/admin/page.tsx`, `components/engine-upkeep.tsx`, `course-builder.tsx` |
| Test patterns | `tests/test_learner_api.py` (`client`, `login`, `onboard`), `tests/test_coursegen.py` (`Scripted`, `OUTLINE`, `run`), `tests/test_coursegen_package.py` (`published`, `generate`, `lesson`, `web`), `tests/test_engine_e2e.py` (the hand-played model) |
| Owner's standing notes | Memory notes: `socrat-design-system-v1` (notebook design direction is the brand; avoid generic "AI" UI tells), `course-generation-architecture`, `engine-is-the-harness`, `engine-hardening-2026-11`, `playground-3d-direction` |

Existing, unrelated-to-this-branch constraints worth knowing: `services/api/tests/test_content_quality.py`
is a hard rule (no authored or family MCQ answer longer than 1.3 times the longest distractor);
unreviewed quiz family items do not write per-item mastery evidence (human review gate); never
auto-fill `provenance.review`; the first-load JS budget is 250 KB.

---

## 8. Rules of thumb for the next agent

1. Verify, do not assume: run the test, open the browser. The two most valuable findings of this
   work (the enrolment crash, the invalid ARIA wrapper) came from running things end to end.
2. Keep the model out of decisions: a model may propose; a deterministic check disposes (link
   check, schema validation, placeholder and number checks, harness verdicts).
3. Say what is not verified. Prefer a labelled limit over a plausible claim.
4. Small, additive, reversible: new module, new migration with a downgrade, flag off by default,
   test added to the downgrade set, plan doc progress log updated, full suite run before pushing.
5. Do not use `git add -A` from the repo root; do not merge `main` into this branch; do not push
   to `main`; do not commit keys.
6. Ask the owner when a key, a reviewer, a legal decision or a product trade-off is needed. Do not
   ask for things you can verify in the code.

---

## 9. Git, pushing and the remote (read before you commit)

- Remote: `origin` = `https://github.com/Bhatta2006/Socrat.git`. Work branch: `feat/universal-engine`.
  GitHub owner: `Bhatta2006`; git user on this machine: "Ramakrishna".
- Pushing needs the owner's GitHub credentials, which live in this machine's git credential manager
  (nothing in the repo). From the repo root: `git push origin feat/universal-engine`. If it asks to
  authenticate, the owner must complete it; do not look for or write tokens anywhere in the repo.
- **Never** force-push, never push to `main`, never merge `main` into this branch (owner's standing
  rule). `main` is one commit ahead (#60); the owner decides when and how to reconcile. If `main` gains
  migrations, renumber ours at merge time (`down_revision` in `services/api/migrations/versions/` and
  `schema_revision.py`).
- Commit only files you changed (`git add <paths>`, never `git add -A` from the root: many untracked
  tool folders live there, and `apps/web/next-env.d.ts` is rewritten by every Next build and must not
  be committed). CRLF warnings on commit are expected.
- Commit message style on this branch: `Engine slice N: what changed`, a body that says why, and a
  trailer naming the assistant that wrote it (earlier commits use
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; use your own tool's attribution).
- Before each push: ruff check and format, mypy, the tests for what you touched, and for anything wide
  the full API suite (about 21 minutes). Update the progress log in the plan doc and this file.
- Pull request: none opened yet and the owner has not asked for one. Open it only when told, as a draft
  first so CI runs.
- Scratch files outside git that may be stale on your machine: `socrat.e2e.db*`, `socrat.local.db`,
  `temp/`, `test-results/`. They are not part of the work.

---

## 10. The owner's standing notes (copied here because another agent cannot read Claude's memory folder)

**Brand and design (confirmed 2026-10-31).** The "notebook" direction is the brand: ruled paper, red
margin line, red pen (`--pen`), yellow highlighter (`.hl`, `--highlight`); Soc is a stone bust on a
stack of primary-colour books; type is Geist Sans for everything, Delicious Handrawn for pen notes,
JetBrains Mono for code; accent is book blue `--primary`, used only for the main action and selected
items, no glow. Unslop rules: highlighter only on the hero headline and on passed tests; landing
headings weight 500; nothing lifts on hover; no glass pill nav; Log in is a text link; landing
overrides are scoped to `.landing` in `globals.css`. The earlier "Scholar / Midnight Lab / Fraunces /
violet" plan is superseded; do not steer back. Show an audit and direction before editing a new page
and keep changes scoped per page; the owner is serious about UI quality.

**Course generation architecture (approved 2026-10-24).** Shared canonical course generated lazily
per batch when the first learner approaches, cached for all; auto-release after deterministic checks
plus a separate reviewer agent, labelled AI-generated, learner reports, batch quarantine; assessment
via code exercises (existing judge), auto-graded quizzes, AI-rubric free text and projects; in-product
background worker, one agent per role, output in the database (versioned, status, provenance); repo
YAML stays as gold packs and the reviewer's quality bar (DSA, CP, Zero stay hand-authored); depth from
the enrolment goal (overview, practitioner, mastery); researcher agent with sources cited, never copied;
provider-agnostic, model per role; prefetch about 2 concepts ahead; configurable per-course and
per-batch budget caps that pause and alert; outline up front, lesson content lazy; languages declared
per course. Branch rule from that time: keep changes merge-friendly, no merging main into the branch.

**Engine is the harness (2026-10-28).** The owner wants Socrat built like Claude Code: a strong core
engine with an LLM plugged in. New subject abilities (math check, units, simulations, CAD constraints,
music theory) are registered as capabilities in `socrat/harness/` (typed input, sandboxed run with a
timeout, uniform Result). Tutor tools, builder gates and studio grading all call the same registry.
Models only explain and word; rules and capabilities decide and verify. Code execution
(`coursegen/execute.py` Broker) is not yet a harness capability; `code.judge` (slice 8) judges
finished runs only.

**Engine hardening (2026-11-01).** Unreviewed family quiz items do not write per-item mastery evidence
(human review gate kept); a finished check with zero reviewed items writes ONE session-level `quiz`
evidence row (`details.unreviewed=True`). The stuck ladder escalates (example, explain, check-in,
defer proposal); concept checks top up from any band then previously seen practice, never from the
assessment pool; the next course opens only when the current one is complete (zero to dsa to cp).
`services/api/tests/test_content_quality.py` is a hard rule (no authored or family MCQ answer 1.3x
longer than the longest distractor). Keep new content execution-verified and never auto-fill
`provenance.review`. Check `git ls-files` before adding problems (`watchtowers` already exists).

**Playground 3D (2026-10-31).** Declarative scene plus timeline JSON spec played by a host-owned player
(not model-written HTML); keep and fix the hand-ported WebGL2 renderer
(`services/api/src/socrat/explainer/clicky3d-*.js`); absorb Labs into Playground tools then delete
Labs. Phases: P1 look, P2 timeline (shipped), P3 picking, isolate, explode, section, P4 Labs into
Playground sim tools. HeyClicky is a quality bar, not a look to copy (Socrat fonts and tokens);
every visualization must be reachable from the prompt alone (Auto mode, no required pickers); the
engine must generate any model from a prompt, nothing is a preset. A visual-review loop with a
vision model is **not** to be implemented until the owner says so.

**Video editing (unrelated to the engine).** The owner keeps a `ue-video-editing` skill for Remotion
reels; not part of this repository's work.

---

## 11. Checklist for the first hour of the next agent

1. `git fetch origin && git status && git log --oneline origin/main..HEAD`: confirm you are on
   `feat/universal-engine` with 17 commits ahead and a clean tree apart from untracked tool folders and
   `apps/web/next-env.d.ts`.
2. Read `docs/implementation/universal-engine-plan.md` (section G and the progress log), then section 6
   here. Read `docs/implementation/load-test-results.md` and `docs/operations/api-worker-split.md` if
   you touch scale or deployment.
3. Run `uv run --project services/api pytest services/api/tests/test_scale.py services/api/tests/test_worker_split.py -q`
   (with `--basetemp` somewhere you own) to prove your environment works before changing anything.
4. Ask the owner for what only they can give: an API key for a live-model pass (not ChatGPT 5.5), the
   Sarvam key, native reviewers per language, legal review for regions, Razorpay live keys. Do not
   guess or invent any of these.
5. Pick the next item from section 6 (recommended: the live-model pass if a key arrives, otherwise
   slice 10 access and low bandwidth, which needs no keys), work in small commits, update the plan's
   progress log and this file, run the checks in section 9, push.
