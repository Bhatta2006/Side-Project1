# Socrat

## Run on Windows without Docker

Install Node 22–24 and Python 3.12 or 3.13. Install the pinned dependency manager with `python -m pip install uv==0.12.20`, then run from PowerShell at the repository root:

```powershell
npm ci
./scripts/dev/doctor.ps1
npm run dev:demo
```

Open http://localhost:3000. The command installs locked Python dependencies, migrates a local SQLite database, generates untracked throwaway credentials in `.env.local`, builds the course content (judge tests are generated from each problem's reference solution into `.cache/content-tests`), and starts the API, native execution worker and web app. Ctrl+C stops the demo processes. Python works without optional C++ or Java tools. The doctor prints installation commands for MSYS2 GNU C++20 and Microsoft OpenJDK 21; restart the demo after installing tools. Bash users can run the same npm command or `bash scripts/dev/start-demo.sh`.

With the demo running, `npx playwright test` drives the learner journey on desktop and mobile; set `PW_CHANNEL=msedge` to use the installed Edge instead of downloading Chromium. `npm run test:visual` compares screenshots of key pages (light and dark, 1400 px and 390 px) with per-platform baselines in `tests/visual/__screenshots__`; add `-- --update-snapshots` after an intended design change. After a production build, `node scripts/web/bundle-report.mjs` prints first-load JavaScript per route against the 250 KB budget CI enforces.

### Tutor model

The tutor runs offline (curated hints) until a provider is configured in an untracked `.env` at the repository root. Any OpenAI-compatible endpoint works; for Nebius Token Factory:

```dotenv
NEBIUS_API_KEY=...            # also accepted as SOCRAT_OPENAI_API_KEY
SOCRAT_AI_PROVIDER=openai
SOCRAT_OPENAI_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1/
SOCRAT_OPENAI_MODEL=nvidia/nemotron-3-super-120b-a12b
```

For Claude, set `SOCRAT_AI_PROVIDER=anthropic` and `SOCRAT_ANTHROPIC_API_KEY` (model `SOCRAT_AI_MODEL`, default `claude-opus-5-5`). The tutor can call learner-scoped tools (progress, plan, recent work, the weekly report, concept guides and the adaptive profile); `SOCRAT_AI_TOOLS=false` turns them off. The server still enforces the Socratic help ladder and leak guard on every reply. Restart the demo after changing `.env`.

### Courses and practice

Socrat ships no built-in courses. Every course is generated for one learner from their goal and
onboarding answers (see `docs/architecture/course-generation.md` and `docs/engine/README.md`), and
every lesson, quiz and practice question is written for that course. Practice sets (`/studio`)
exist for every course; a code editor and judged problems (`/problems`) appear only in programming
courses. There is no external problem index, company bank or contest-rating link.

### Concept playground

Open `/playground` from Today and ask for any concept, comparison or confusing step. The AI
creates a complete interactive HTML/CSS/JavaScript visual inside the playground. No preset
lesson, numeric snapshots, deterministic sample inputs or algorithm templates are fed to it.
The model designs the visualization, controls and initial example from the learner's request.

The generated document passes markup/script validation, an isolated browser interaction check,
and an AI review of its relevance and conceptual consistency before being embedded in an
opaque-origin, network-blocked iframe. Dashboard colors
and light/dark themes carry into the canvas. Learners can change inputs, step, scrub, play,
reset, expand, read the explanation, reopen saved visuals and report an issue. Generated
material is labelled as not verified for factual accuracy. Failed generation preserves the
request; no substitute lesson is returned. Viewing never changes mastery, and independent
assessments block the feature. Existing provider credentials are reused, with an optional
playground-only code-generation model override.

Production requires a separate sandbox domain and browser checker service. See the
[visual playground implementation and deployment notes](docs/implementation/visual-playground.md).

### Beta features

- **Try before signing up.** The landing page runs one judged problem (`max-window-sum`) in the browser with the tutor, no account needed. The tutor uses the same help ladder and leak guard, is capped below pseudocode, and never sees the intended approach or reference. `SOCRAT_TRY_TUTOR_ENABLED`, `SOCRAT_TRY_DAILY_BUDGET_USD` (default 3) and `SOCRAT_TRY_MESSAGES_PER_HOUR` (per visitor, default 20) control it; the global AI budgets still apply. The per-visitor limit is in memory per API process, and it trusts the rightmost `X-Forwarded-For` entry, so the API must sit behind the web server's proxy.
- **Beta community.** Set `SOCRAT_COMMUNITY_WHATSAPP_URL` to a `https://chat.whatsapp.com/...` invite to show it on the landing page, Today, Settings and the account menu. Empty hides it.
- **Installable app.** `app/manifest.ts`, `public/sw.js` (offline page only; it never caches API data) and icons from `node scripts/make-icons.mjs` in `apps/web`. The service worker registers in production builds (set `NEXT_PUBLIC_SW_IN_DEV=1` to test it in dev).
- **Skill Passport.** Learners turn on a public page at `/passport/<random slug>` from Evidence. It is computed live from verified evidence and shows only the display name. Turning it off breaks the link at once.
- **Company sprints.** `/company-sprint` plans "Amazon SDE-1 in 6 weeks" from the company bank and the course graph, then files a goal proposal (target date, role, focus skills) that the learner accepts or declines.

### Owner metrics

`/admin` shows the activation funnel, retention, engagement, checkpoint pass rates and content that needs review, computed from learning data. Access is limited to accounts listed in `SOCRAT_ADMIN_SUBJECTS` (a JSON list of OIDC subjects, for example `SOCRAT_ADMIN_SUBJECTS='["your-subject"]'`; with the dev sign-in the subject is your lower-cased name with dashes).

This is an explicitly insecure local development sandbox. The coding workspace displays **Local dev sandbox — not secure for untrusted code**. Production still requires the existing Linux gVisor execution host and private HTTPS broker. See the archived [native execution operations](docs/archive/m6-execution.md) and the [editor ADR](docs/architecture/adr/0007-code-editor.md).

Socrat is a deterministic-first personalized learning platform. V1 delivers Data Structures and Algorithms preparation for complete beginners, interview learners, and competitive programmers in Python, C++, and Java. The core platform is designed to support additional skill packs after V1 without rewriting learner state, planning, assessment, or analytics.

## Repository status

M0 product validation remains in progress. The product owner authorized a scoped M1 engineering start while retaining the unpassed learner-pilot and human sign-off gates. The repository-side M1 foundation and hosted quality gates are implemented; cloud staging and operational proof remain pending in the [M1 gate](docs/delivery/milestones/m1-gate.md).

On 2 October 2026, the owner chose Google sign-in and deferred the remaining M1 operational work to proceed with [M2 skill-pack engineering](docs/delivery/milestones/m2-index.md). The kernel includes declarative schemas, graph validation, immutable versioning, editorial review/release/quarantine APIs, and DSA/non-DSA fixtures. M0, M1, and the M2 staging/human gates remain unpassed.

M3 onboarding and deterministic routing is implemented locally: reviewed goals, explicit target/language coverage, beginner bridges, version-pinned confirmation, and atomic funnel events. See the [M3 index](docs/delivery/milestones/m3-index.md) and [gate](docs/delivery/milestones/m3-gate.md). Onboarding is enabled in local Compose and defaults off in staging. No real launch content or completed hosted/staging M3 gate is claimed.

M4 adds resumable objective diagnostics, append-only evidence, deterministic learner-state projections, retention/misconception rules, and protected replay/correction/policy/calibration operations. Diagnostics are enabled in local Compose and default off in staging. Implementation-based placement awaits M6; live content and operational/human approvals remain in the [M4 gate](docs/delivery/milestones/m4-gate.md). See the [operations guide](docs/operations/m4-diagnostics.md).

M5 implements the deterministic curriculum and fourteen-day planner, with prerequisite-safe practice selection, immutable decisions/replay, confirmation, feasibility, workload controls, and missed-day recovery. Local Compose enables planning; staging defaults off. Code practice awaits M6 and full learning sessions await M7. See the [M5 index](docs/delivery/milestones/m5-index.md), [gate](docs/delivery/milestones/m5-gate.md), and [operations guide](docs/operations/m5-planning.md).

M6 adds a self-hosted CodeMirror 6 editor, autosave/resume, a durable signed execution broker, quotas, and separate gVisor-only Python/C++20/Java21 workers. Verified Submit results feed learning evidence and diagnostics; Run never changes mastery. Execution stays disabled until attested runtime images, dedicated-host security/load tests, and external review pass. See the [M6 index](docs/delivery/milestones/m6-index.md), [gate](docs/delivery/milestones/m6-gate.md), and [operations guide](docs/operations/m6-execution.md).

M7 implementation includes durable Today sessions, pinned language/track lessons, private objective checks, mixed Competitive timed/upsolve practice, configurable practice penalties, reviewed structural-repair mappings, saved history/local-day expiry, and owned participation/duration exports. Nine-cell inventory and fourteen-day planner audits gate publication of packs declaring session content. An [original limited-pilot draft](docs/operations/m7-limited-pilot.md) and policy proposal are prepared; independent reviews, calibration and deployed acceptance are owner-deferred. Local Compose enables sessions; staging defaults off. See the [M7 implementation status](docs/delivery/milestones/m7-index.md) and [gate](docs/delivery/milestones/m7-gate.md). Deferred M6 gVisor tests remain open.

M8 adds bounded tutoring, curated fallbacks, provider adapters, durable assistance at Submit, dependency fading, fresh-family planning safeguards and a shadow-only advisor. Models remain disabled by default; earlier external gates remain open. See the [M8 implementation](docs/delivery/milestones/m8-index.md), [gate](docs/delivery/milestones/m8-gate.md) and [operations](docs/operations/m8-assistance.md).

M9 adds protected baseline/weekly/final/retention forms, deterministic scoring, independent human review and disputes, atomic assessment evidence, and a reviewed spaced-scheduling policy. The owner authorized repository implementation while inherited release gates remain open. Local Compose enables assessment development; staging defaults off. See the [M9 implementation](docs/delivery/milestones/m9-index.md), [gate](docs/delivery/milestones/m9-gate.md), and [operations](docs/operations/m9-assessments.md).

M10 implements a Today-first evidence dashboard, reviewed schedule/recovery controls, consented in-app reminders with quiet hours, raw code/tutor retention, owned JSON export, and queued account erasure with private receipts and operator cleanup evidence. Local Compose enables the dashboard and reminders; staging defaults off. Independent accessibility and deployed storage/provider deletion acceptance remain pending. See the [M10 implementation](docs/delivery/milestones/m10-index.md) and [gate](docs/delivery/milestones/m10-gate.md).

## Repository map

```text
Socrat/
├── contracts/                 # Machine-readable product and interface contracts
│   ├── product/
│   └── schemas/
├── docs/
│   ├── architecture/          # System decisions, ADRs, dependency evaluation
│   ├── delivery/              # Milestone gates and execution status
│   ├── product/               # PRD, language, goals, policies, metrics, content rules
│   ├── research/              # User-research protocols and evidence
│   └── security/              # Threat models and security/privacy design
├── prototypes/
│   └── concierge/             # Disposable M0 learner-research prototype
├── apps/web/                  # Next.js learner-facing web application
├── services/api/              # FastAPI modular monolith and worker
├── tests/e2e/                 # Desktop/mobile browser acceptance journeys
├── infra/oci/                 # Validated OCI Hyderabad staging infrastructure
├── .github/                   # CI and dependency-maintenance policy
├── scripts/
│   ├── operations/            # Backup and restore smoke tooling
│   └── validation/            # Deterministic repository/contract checks
├── compose.yaml               # Reproducible local PostgreSQL topology
└── README.md
```

Future learning capabilities remain disabled until their milestone contracts and tests exist.

## Start here

1. [Documentation index](docs/README.md)
2. [V1 product requirements](docs/product/v1-product-requirements.md)
3. [M0 milestone index](docs/delivery/milestones/m0-index.md)
4. [M0 gate](docs/delivery/milestones/m0-gate.md)
5. [M1 platform foundation](docs/delivery/milestones/m1-index.md)
6. [M2 skill-pack kernel](docs/delivery/milestones/m2-index.md)
7. [M3 onboarding and routing](docs/delivery/milestones/m3-index.md)
8. [M4 diagnostic and learner-state implementation plan](docs/delivery/milestones/m4-index.md)

## Run the M1 foundation

With Docker available:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. The local login exists only in development/test. Staging and production settings fail closed unless HTTPS, PostgreSQL, managed OIDC, strong session/metrics secrets, and disabled developer login are configured.

## Validate M0

From the repository root:

```powershell
node --test prototypes/concierge/model.test.mjs
powershell -ExecutionPolicy Bypass -File scripts/validation/test-m0-contracts.ps1
```

Passing automated checks confirms document/contract consistency only. It does not substitute for learner pilots or accountable human sign-off.
