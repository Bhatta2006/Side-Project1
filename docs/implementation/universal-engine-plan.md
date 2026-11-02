# Universal Learning Engine + International scale: audit and phased plan

- **Status:** Draft for owner approval (2026-11-02). Source brief: `SOCRAT_Universal_Learning_Engine_Master_Prompt.txt`.
- **Branch:** `feat/engine-hardening-2` (phase branches cut from it; no merges into it without approval).
- **Re-prioritised 2026-11-02 (owner):** the product is the *engine*, a "Claude Code for learning": any topic, any way of learning, personal to each learner. Engine phases (intent → compiler → adapters/renderers → adaptive loop) come first; i18n (Phase 1 below) runs in parallel as a cross-cutting layer, not as the headline. Work branch: `feat/universal-engine`, cut from `origin/main` (post #59). Local commits only until the owner says push.
- **Rule:** nothing here replaces a working system. Every phase is additive, flagged, and has a rollback.

## A. Repository and architecture summary

| Layer | What exists (verified in repo) |
|---|---|
| Web | Next.js 16 app (`apps/web`), ~30 routes, CodeMirror, Pyodide/Clang-WASI in-browser run, JSXGraph, `@xyflow` graph, PWA. `<html lang="en">` hardcoded, no i18n library, all copy inline in components |
| API | FastAPI modular monolith (`services/api/src/socrat`), 33 Alembic migrations, SQLite local / Postgres staging+prod, outbox worker (`worker.py`) |
| Course generation | `coursegen/` (outline, research, package, exercise, project, quality, prefetch, jobs, roles): architect → critic → researcher → authors → fact check → reviewer, lazy per-batch, admin-triggered |
| Engine | `harness/` (typed sandboxed capabilities: math, physics, library), `workbench/`, `mentor/` (teaching moves + "why" log), `adaptive/` (stuck ladder, proposals), `mastery/`, `diagnostics/`, `planner/`, `quiz/` (Elo adaptive quiz), `assessment/`, `reminders.py` |
| Content | Hand-authored gold packs `content/courses/{zero,dsa,cp}`, patterns, quiz families verified by execution, 13.9k-problem library index |
| Money | Razorpay subscriptions, INR + USD price tables, entitlements |
| Infra | OCI Hyderabad single-VM staging (A1.Flex), Postgres container, gVisor execution design, nightly CI (e2e, tutor eval, link check, lighthouse) |

## B. Reusable as-is

Course generation pipeline and its state machine; harness registry; evidence and learner-state projections; mentor policy and "why" log; spaced scheduler and reminders; provenance and license gate; quiz generators with execution verification; playground sandbox; passport; billing/entitlements; provider-agnostic gateway (`assistant/gateway.make_provider`) with per-role model config.

## C. Critical gaps against the brief and the "international, every student" goal

1. **No internationalization at all.** English-only UI, English-only prompts, `lang="en"`, no locale routing, no RTL, no locale-aware number/date formats, no translated legal pages.
2. **Content is not language-addressable.** Brief declares code languages, not human languages. A lesson has one text. No translation memory, no per-locale review state.
3. **Tutor and generators are English-in/English-out.** No language detection, no glossary lock for technical terms, no leak-guard or help-ladder tests in other languages.
4. **Generation is admin-triggered only.** Learner-typed "teach me X" (brief §2, §20.1) is not wired. No intent parser, no learner diagnostic for non-DSA domains.
5. **Domain coverage is DSA-centric.** Harness has math and physics; no adapter registry, no music/electronics/animation adapters, no declared "needs physical practice / human evaluator" flag.
6. **Renderer registry is implicit.** Playground, JSXGraph, graph and code studio are separate special cases, not manifests with schema, fallback and accessibility alternative.
7. **Scale limits:** single VM, in-process worker, in-memory per-visitor rate limit, no CDN/edge config, no regional data plan, no per-tenant cost metering beyond global AI budgets.
8. **Low-bandwidth reality:** first-load JS budget 250 KB exists, but Pyodide/WASM runtimes and generated visuals have no offline or lite mode.
9. **Compliance for other countries:** DPDP (India), GDPR/UK, COPPA/minors, with account erasure already built (M10) but no regional policy matrix, consent copy per locale, or tax/currency beyond INR/USD.
10. **Payments:** Razorpay supports INR + international cards; no local-method strategy (UPI is covered; Brazil/Indonesia/Africa wallets are not).

## D. Target architecture (mapped to the repo)

```
                    ┌─────────── Intent Parser (new, coursegen/intent.py) ───────────┐
Learner request ──► │ subject, goal, level, time, language(human), constraints       │
                    └───────────────┬────────────────────────────────────────────────┘
                                    ▼
                  Domain Adapter registry (new, harness/domains/)  ──► capabilities (existing harness)
                                    ▼
          Existing coursegen pipeline (architect → critic → research → authors → review)
                                    ▼
              Locale layer (new, localize/): translate + glossary lock + verify + review state
                                    ▼
              Renderer registry (new, manifests over existing studios) ──► web (renders typed specs only)
```

Principles kept from the brief and `engine-is-the-harness`: models explain, harness verifies; deterministic code owns state, scoring, permissions; agents are bounded; generated code never runs in the browser unsandboxed.

### Internationalization design (the "international" half)

- **Locale model:** BCP-47 tags. Course content keyed `(artifact_id, locale)` with `source_locale`, `status` (machine / verified / human-reviewed), `translated_from_version`, and the model+prompt+glossary version that produced it. A translation is never published as "reviewed" without a named reviewer (same rule as quiz review).
- **What is translated vs. verified:** prose, hints, quiz stems and rationales are translated. Code, expected outputs, math, identifiers and test cases are **never** translated; execution verification re-runs on the localized item so a translation cannot change the answer key. Technical terms use a per-language glossary (e.g. "pointer", "recursion") that is injected and checked after translation.
- **UI strings:** message catalogs (ICU MessageFormat) with extraction lint in CI; English is the source, missing keys fall back to English, never to a blank.
- **Tutor:** learner language detected on first message, remembered as a preference, overridable. Help ladder and leak guard are re-tested per supported language in the nightly tutor eval.
- **Engines per language family:** Indic languages through Sarvam (translate, transliterate, TTS/STT, language-ID) because it is purpose-built for them; other languages through the existing provider gateway, selectable per role. Fully provider-agnostic: no language is tied to one vendor.
- **Voice and low-literacy access:** TTS for lessons and STT for tutor input are optional capabilities behind flags (Phase 6).
- **RTL, fonts, numerals:** logical CSS properties, `dir` set per locale, Noto subset fonts loaded per script only.
- **Pricing/legal:** locale and country are separate. Currency, tax, privacy notice and age-of-consent default come from country, not language.

### Scale design (the "scaling" half)

1. Stateless API behind a load balancer; managed Postgres with PITR; Redis (or Postgres `SKIP LOCKED` queue, already used) for jobs. Do not add Kafka/microservices.
2. Worker split: `gen-worker` (LLM, cost-capped), `outbox-worker`, `exec-workers` (gVisor), each scaled independently.
3. CDN in front of static, lesson JSON and generated-course reads (courses are shared and immutable per version, so this caches well).
4. Per-tenant/per-learner cost metering and budgets extended from the existing global AI budget.
5. Regional plan: start India (Hyderabad), add one EU region only when GDPR customers exist. Data stays in region of residence; content catalog is global and replicated.
6. Load tests as acceptance gates; nothing claims capacity without a measured number.

## E. Data model and API changes (all additive migrations, each with downgrade)

| Migration | Adds |
|---|---|
| 0034 `locales` | `user.locale`, `user.country`, `user.content_locales` |
| 0035 `content_translation` | `(artifact_kind, artifact_id, artifact_version, locale, body, status, glossary_ver, model, prompt_ver, reviewer, created_at)`, unique on the first five |
| 0036 `learning_request` | learner-typed intents: raw text, parsed intent JSON, status, resulting course id, idempotency key |
| 0037 `renderer_manifest` | registry rows mirrored from code manifests, for audit |
| 0038 `cost_ledger` | per learner / course / workflow token + fee entries |

New endpoints (versioned under `/api/v1`): `PUT /me/locale`, `GET /content/{kind}/{id}?locale=`, `POST /learning-requests`, `GET /learning-requests/{id}`, `GET /renderers`, `GET /admin/translations/queue`.
Old endpoints keep their shape; locale is an optional parameter defaulting to `en`.

## F. Risks, dependencies, unresolved decisions

| Risk / dependency | Mitigation |
|---|---|
| Machine translation can silently break a technical claim | Glossary lock, execution re-verification, `machine` label in UI, human review queue, back-translation spot-checks in the eval |
| Quality of low-resource languages is uneven | Launch only languages that pass a benchmark we define; others stay "preview" |
| Learner-typed courses cost real money | Hard per-learner budget, quota by plan, shared cache of identical intents, admin kill switch |
| Non-code domains cannot be verified by the sandbox | Adapter must declare verifiability; unverifiable domains are labelled and capped, never claimed as certified |
| Regulatory differences | Region policy matrix reviewed by a qualified person before launch in that region |
| Scope creep | Each phase has an exit test; later phases do not start until it is green |

**API keys (will ask when needed, not before):** (1) Sarvam key for Indic translation/TTS/STT in Phase 3; (2) a general LLM key for non-Indic languages and the intent parser in Phase 3/4 (not ChatGPT, as instructed; Anthropic or the existing Nebius endpoint both fit the gateway); (3) Razorpay live keys only at Phase 9. Keys go in untracked `.env`, never committed.

**Decisions I am taking by default unless you object:** launch locales = `en`, `hi`, `te`, `ta`, `bn`, `mr`, then `es`, `pt-BR`, `id`, `ar` (RTL proof). Translation is machine-first with a visible label. India stays the primary region.

## G. Phased plan (order = user value, dependency, risk)

| Phase | Deliverable | Exit test (must be green before next) |
|---|---|---|
| **0 Baseline** | This doc, baseline test results, string inventory, current-state diagram | Baseline recorded; no production behavior changed |
| **1 i18n foundation** | Locale in profile + cookie, `lang`/`dir` on `<html>`, message-catalog loader with English fallback, extraction lint, locale-aware dates/numbers, language switcher; landing + nav + Today translated for `hi` as proof | `en` pixel-identical (visual tests pass); missing key falls back to English; `hi` renders with correct font; typecheck + build + bundle budget pass |
| **2 Locale-addressable content** | Migration 0035, translation store, `localize/` service with glossary lock and execution re-verification, `?locale=` on content APIs, status badges | A translated quiz item whose answer key differs from the source is rejected; unreviewed translation is never marked reviewed |
| **3 Multilingual tutor + content pipeline** | Language detection, glossary-locked tutor, Sarvam + gateway translation backends (**needs keys**), batch translation job on the existing worker, per-language tutor eval | Help ladder and leak guard pass eval in every launch locale; translation job is idempotent on retry |
| **4 Learner-typed courses** | `coursegen/intent.py`, `learning_request` table, short diagnostic, budget and quota, reuse of cached identical intents | A typed request becomes an inspectable blueprint in one flow; duplicate submit creates one course; over-budget pauses with a clear state |
| **5 Domain adapters + renderer registry** | `DomainAdapter` interface, adapters for math/science, CS, plus one non-code domain (electronics via simulation), manifest registry over existing studios with schema, fallback, accessibility alt | Adding a trivial renderer needs no change to the compiler; every renderer has a static fallback test |
| **6 Access and low-bandwidth** | TTS/STT flags, lite mode (no WASM until needed), offline lesson cache, Noto font subsets, WCAG audit | Lighthouse/axe gates per locale; lesson usable on throttled 3G in test |
| **7 Scale** | Worker split, CDN/cache headers for immutable course reads, cost ledger, per-tenant budgets, Redis-backed rate limits, load tests | Measured p95 latency and cost per active learner at target concurrency, recorded in repo |
| **8 Region and compliance** | Region policy matrix, per-country consent and minors rules, data-residency toggle, regional deploy runbook | Policy matrix reviewed; erasure and export tested per region |
| **9 Payments and launch** | Currency/tax expansion, local methods, staged rollout, rollback drill | Rollback drill executed; launch checklist signed off |
| **10 Research loop** | Outcome experiments (retention, transfer, hint dependence) per locale, scheduler and mastery model calibration | Pre-registered measures reported; no claim beyond the data |

Every phase ships behind a flag that defaults off, with its migration downgrade tested and its acceptance tests committed.

## H. First vertical slice (start immediately after approval of this doc)

**Phase 1, thin cut:** a Hindi learner opens the landing page, Today and the nav in Hindi, the choice persists across refresh and devices, and an English learner sees no change.

Acceptance tests:
1. `locale=en` renders byte-equivalent copy to today (visual regression suite unchanged).
2. `locale=hi` renders translated strings for landing, nav, Today; a deliberately removed key shows the English string, not a key name.
3. `<html lang>` and `dir` follow the locale; unsupported locale falls back to `en`.
4. Setting locale while signed in persists to the profile and survives a new session.
5. CI lint fails when a component adds a user-visible literal in a migrated file without a catalog key.
6. Bundle report stays within the 250 KB first-load budget.

## Baseline (Phase 0)

API suite on 2026-11-02 (branch `feat/engine-hardening-2`): **711 passed, 24 skipped, 0 failed** in 16m43s. On Windows, run pytest with `--basetemp <writable dir>`; the default temp folder raised `PermissionError`. No production code has been modified for this plan.

## Progress log

| Date | Slice | Status |
|---|---|---|
| 2026-11-02 | Engine slice 1: **Intent Parser** (`coursegen/intent.py`), `learning_requests` table (migration 0034), learner API `/api/v1/learning-requests` (create, list, get, confirm), flag `learning_requests_enabled` default off, rules fallback when no model, quota and idempotency | Done, 8 new tests, ruff/mypy clean |
| 2026-11-02 | Engine slice 2: fixed learner choices (who/register incl. age 5, level, style incl. gamified, daily time; subject stays free text with suggestions), learner-owned private courses (migration 0035 `owner_id`), `/publish`, private listing and enroll guard, web page `/new` | Done; 10 request tests + 78 related tests pass, web typecheck clean |
| 2026-11-02 | Engine slice 3: **community courses** (opt-in, revocable sharing with credit choice; AI-generated label), **creator perks** (tiers at 10 / 50 / 250 other active learners: creator badge, 30 and 90 days of Plus; idempotent sweep in the worker), pause/resume between courses (`GET /enrollments`, `POST /enrollments/switch`, learner-made courses skip the one-course rule), lessons-ready count, Build-your-own card on Today. Migration 0036 | Done; 13 request tests + 128 related tests pass, web typecheck clean |
| next | Slice 4: learner diagnostic (needs a real model and a key), course moderation for shared courses (reports, admin takedown, abuse limits on perks), domain adapters and the renderer registry | Planned |

Perk design notes: a learner counts only if they enrolled in someone else's course and have recorded progress, so idle sign-ups do not count. Self-farmed accounts are still possible; before billing is switched on, add an account-age or verified-email floor and admin review of Plus grants.
