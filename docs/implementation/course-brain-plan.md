# The course brain: subject roots, reusable material, shared course versions

Written 2026-11-20 against `gbuild/main` at `1c42b949`. Planning only: nothing here is built, run or
measured. It extends `docs/implementation/lesson0-generation-plan.md` (the "previous plan": `Brief.plan`,
roadmap first, `view.start`, `session_minutes`, session-one adaptation) and follows
`docs/implementation/onboarding-handoff.md` (the "handoff") and `HANDOFF.md` for ownership and Git rules.

Labels: **[V]** verified by reading the code (path and symbol given); **[H]** reported by the handoff;
**[P]** proposed; **[?]** unverified assumption. Every number marked [P] is a target to measure, not a
measurement. Examples are illustrative unless they come from the handoff.

## Implementation status (2026-11-20)

**Update, later on 2026-11-20 (backlog section 3):** shadow mode (`course_brain_shadow`), the root backfill
(`scripts/dev/backfill_roots.py`), the served learner's overlay at delivery (minutes, Lesson 0 gaps -> worked example
first, Ladder start), a 76-pair gold set (0 false reuse), the scoper (`brain_scoper`), the stale-unit sweep
(`SOCRAT_BRAIN_REFRESH_SWEEP_SECONDS`) and the admin "Course brain" tab are built. Details and what is not built:
`course-generator-backlog.md` section 3. Ownerless shared courses (3.8) wait for the owner.

Owner decisions after review: (1) use the current Lesson 0 onboarding as it is; (2) roots are **not** a
fixed list: any subject a learner asks for gets a root on demand (`CANONICAL` in `brain/roots.py` only
folds synonyms such as math/maths/mathematics); (3) shared community courses **are** brain candidates.

Built (flag `course_brain`, default off), tested in `services/api/tests/test_course_brain.py`:

- Migration `0051_course_brain`: `subject_roots`, `subject_aliases`, `course_matches`; nullable
  `generated_courses.root_id/spec/spec_key/serve`; `enrollments.match_id/learner_plan`.
- `coursegen/brain/spec.py` (`CourseSpec`, `derive`, `is_private`, `overlay`), `roots.py` (`resolve`,
  on-demand roots, alias redirect), `route.py` (`compatible`, `decide`, `route`, `attach`, `granted`).
- `requests.begin` routes first; a served request becomes `matched` with no outline job. `publish` is a no-op
  for a matched request and stamps root/spec/serve on a newly built course. `POST /enrollments` admits a
  brain-served learner and copies their private overlay. `onboarding.claim` links the draft before `begin`
  so the profile is readable while routing.
- Community (public) courses made before the brain get a spec derived from their creating request on first
  sight, and are then candidates.

Built second (same flag): root units and the research job. Tables `root_units`, `sources`,
`unit_sources`, `concept_unit_pins` (in `0051`), `course_matches.units`; `brain/units.py` (one unit
per canonical topic and depth, `ensure` queues research once), `brain/researcher.py` (job kind
`research`, `extractor` role, code validation: every item cites a reachable source, exercise keys are
checked by the same math checker learners are graded with); the outline job waits for its units and
plans from `Brief.subject_material`; each lesson pins the unit revision it was written from;
`units.quarantine` makes courses written from a withdrawn unit ineligible for new learners. Outcomes
now distinguish `from_material` (no research) and `extend_and_new`. The learner-layer plug point is
`brain/learner.py`; its contract is in `generation-plug-points.md`.

Built third (same flag), tested in `test_course_brain.py` and `test_brain_units.py`:

- **Privacy for shared courses** (`brain/privacy.py`). A course the brain may share is generated
  from `shared_intent(intent)`: the Lesson 0 door sentence, the "patch these gaps" sentence, age,
  deadline and hours per week are removed (they stay in the learner's own request and overlay). The
  leakage gate `leaks(db, course_id)` compares everything a learner of the course can read (outline,
  lessons, problems) with its maker's request text, material and onboarding draft (8-word runs), their
  email and their full display name (two words or more). It runs in `attach` (at publish) and again
  in `decide` before a shared course is served, because lessons are added after publish; a hit sets
  `serve="private"` and records why.
- **In-flight joining** (family ids). A shareable request is built under a deterministic id
  `<topic slug>-<spec key[:8]>` (`-v2`, `-v3` for later versions). A second request with the same
  spec, arriving while that course's outline or first lesson is still being written, is `joined`
  (a served outcome, request status `matched`) instead of building a second course. A request that
  loses the race at enqueue (`AlreadyQueued`, or the id already taken) also joins. A joined learner
  may publish a course still in review (it was built for their exact spec). A course whose first
  lesson failed, was withdrawn or kept private is not joined: the next version is built. The maker
  can no longer cancel a course other learners were given (`409 course_shared`).
- **Correction path** (`units.correct`, `POST /api/v1/admin/brain/units/{id}/correct`). Withdraws the
  unit revision, queues research for a new revision with the reason in the extractor prompt, and
  sends every live lesson pinned to it back to planned through the existing `quality.quarantine`
  rewrite. The rewrite (`run_package`) and new outlines wait for the corrected revision (bounded by
  `UNIT_WAIT_SECONDS`); a routine refresh of a still-valid unit is never waited for. Re-pinning to
  the new revision drops the old pin, so the course becomes servable again.
- **Owner views**: `GET /api/v1/admin/brain/roots`, `/units?root=`, `/matches/{request_id}` (the
  decision with every candidate and check; the learner-only overlay is listed by field name only).

Still not built: a scoper that splits a topic into several units; a scheduled refresh of stale units
(a stale unit is refreshed only when a later request needs it); an admin web page for the endpoints
above; ownerless shared courses.

Deliberate deviation from the plan below: a shared child keeps the first learner as `owner_id` (so every
existing ownership path keeps working) instead of being ownerless; owner-only actions that would affect
other learners (cancel) are refused once the course is shared. `regenerate` is still owner-only and
only acts on courses in review, before anyone else can be enrolled.

---

## 0. Decisions in one page

1. **A course is already a stored, shareable, resumable object; the brain adds identity and lookup around it,
   not a second content store.** `GeneratedCourse` + `GeneratedConcept` + `ConceptVersion` + `Enrollment`
   exist [V `models.py`]. We add: a subject root, scoped root units, a spec on the course row, a pin table and
   an audit table. A *child course version is one `GeneratedCourse` row*; an enrollment already pins it by
   `course_id`, so "resume a stable version after a better one is published" costs nothing new.
2. **Reuse is decided by code over enumerated fields, never by text similarity.** Wording is normalised into a
   `CourseSpec` (canonical topic path, depth, frame kind, assessment kind, prerequisites, languages, register).
   Similarity (token overlap now, embeddings later) may only *find* candidates; `compatible()` decides.
3. **Hard requirements shape the shared course. Everything a learner's own session can absorb is enrollment-only.**
   The test: could a different learner use these exact lessons unchanged? (Section 3.)
4. **Shared courses are generated from a sanitized spec, never from a learner's words.** If a request contains
   private context (uploaded material, a personal project) the course stays private (today's flow), may still
   *read* shared root material, and is excluded from shared matching.
5. **Research is per unit and per subject, not per request.** Creating "Mathematics" creates an empty root. Units
   are researched on demand, committed before generation starts, and de-duplicated by a database key.
6. **Every decision is written to `course_matches`** (one row per request, unique on `request_id`): outcome,
   per-candidate check results, what was reused, what was generated, models avoided. The audit question in
   Section 7 is answered by one query.
7. **Flag-gated, additive, shadow first.** New flag `course_brain` (default off). PR order lets us record
   decisions for real traffic before anything is served from them.

---

## 1. Current repo flow, and where the brain plugs in

### 1.1 What exists [V]

| Concept | Existing equivalent | Notes |
|---|---|---|
| A course | `GeneratedCourse` (id PK, `payload`, `brief`, `status` review/published, `owner_id`, `visibility` private/public, `moderation`) | `owner_id` set = learner-requested; NULL = owner's. `updated_at` bumps invalidate the catalog cache |
| A lesson | `GeneratedConcept` (PK course_id, concept_id; `payload`, `atoms`, `problems`, `job_id`) | `Concept.status` live / planned / draft. Planned = outline only, held by the planner |
| Past versions of a lesson | `ConceptVersion` (digest, version, payload) via `generated.store_concept` and `catalog/revisions.carry` | Quiz ids of replaced versions stay resolvable (`retired_quiz`) |
| The request | `LearningRequest` (unique `(user_id, key)`, `text`, `intent`, `material`, `status`, `course_id`) | statuses include `matched` |
| The job queue | `GenerationJob` + partial unique index `uq_generation_jobs_one_open (course_id, kind, target)` where state in queued/running | `jobs.enqueue` turns an IntegrityError into `AlreadyQueued` inside a savepoint; `claim` orders by `priority, created_at` |
| Enrollment | `Enrollment` (`course_id`, `level_id`, `goal` JSON, `minutes_per_day`, `adaptive` JSON); no DB unique on (user, course) | `POST /enrollments` returns the earlier enrollment for a learner-made course (`learn/routes.py:493`) |
| Match before build | `coursegen/match.py` (`find`, `fit`, `subject_key`) + `GET /{id}/matches`, `POST /{id}/take`; flag `request_matching` (default off) | Compares owner's `intent` by stemmed subject words, language, register, exact-lowercase style string. Only public or own courses. Sets `status="matched"` |
| Sources | `catalog/sources.py` registry + `coursegen/research.py` (`RESEARCHER`, `screen`, `ground`, `credit`) + `search.gather` / `fetch.read` | Researcher runs per lesson inside `run_package`; its sources land in the job log and in `Concept.resources` / `citations`; nothing is stored per subject |
| Whole-outline reuse | `jobs.design_key` + `reusable_outline` (identical `Brief`, critic passed, `moderation ok`, last 200 jobs) | Matches only byte-identical briefs, so it almost never fires for learner wording |

Verified gaps that matter for the brain:

- **G1.** No subject identity anywhere. `Intent.subject` is free text (2-120 chars); `Intent.domain` and
  `Intent.adapter` are coarse [V `coursegen/intent.py:Intent`].
- **G2.** `match.fit` says "Taught in its own style, not the one you described" for any style difference, because
  it compares lowercase strings, so "detective cases" vs "mystery investigations" is a miss (and a request with no
  style never matches a themed course silently, which is right) [V `match.py:fit`].
- **G3.** Course ids are per learner and request: `intents.slug(subject, user_id, key)` [V `requests.py:378`].
  Two learners can never share an in-flight outline today.
- **G4.** A learner-requested course is private to its owner until the owner shares it with credit and perks
  (`requests.share`, `community.py`). `private_courses()` blocks enrolling in anyone else's private course
  [V `learn/routes.py:446,497`]. The brain's shared children must not go through that community path.
- **G5.** Enrollment for a course with `owner_id` NULL takes the "one course at a time" branch and returns
  `409 already_enrolled` for an unfinished active course [V `learn/routes.py:507-516`]. A second press of
  **Start** on a brain child would hit it unless the branch condition is extended (Section 5, case 3).
- **G6.** Course content changes in place (`store_concept` replaces the concept; the old payload goes to
  `ConceptVersion`). There is no immutable course snapshot. A lesson rewrite reaches every enrollee at once.
- **G7.** `view()` already renders a matched, published request with no job: `published`, `enroll`, `blueprint`,
  `ready/total` come from the stored course [V `requests.py:view`]. An immediate reuse hit needs no new screen
  state and no fake wait.
- **G8.** Researcher output is not persisted as reusable material: only the per-lesson `Concept.resources`,
  `citations` and the job log keep it [V `package.py`, `research.py`].

### 1.2 Where the new steps run

`begin(db, settings, user_id, row, parsed)` is the one place both entry points create the outline job (the
onboarding claim calls it at `onboarding.py:665`; `requests.confirm` calls it too) [V]. Keep its signature. The
brain adds a code-only `brain.route(...)` as the first statement of `begin`:

```
claim / confirm
  -> begin(db, settings, user_id, row, parsed)            signature unchanged
       0. brain.route(db, settings, user_id, row, parsed)   NEW; flag course_brain; one transaction
            requirements = derive(row.text, parsed, onboarding.profile_for(db, row.id))
            root         = resolve_root(requirements)       alias tables; one fast model call only on a miss
            decision     = decide(db, root, requirements)   candidates -> hard checks -> outcome + reason
            writes course_matches (unique request_id)
            if reuse*: row.course_id = child, row.status = "matched"; return (no outline job)
            else:       course_id = child family id (deterministic) ; fall through to the existing code
       1. existing: slug id, to_brief, enqueue "outline"        now with brain context in the job input
```

No model call is made on the request path except the optional root-resolution call (Section 2, step B), which uses
the same provider mechanism and timeout style as `intent` parsing. [?] Whether `begin` is allowed to await a model
is to be checked in PR B; if not, resolution moves into the preceding parse step and `begin` stays code-only.

---

## 2. Storage: four records (+ two support tables)

Names are proposals. All migrations are additive with a tested downgrade (next is `0051`, after
`0050_onboarding_drafts`) [V `migrations/versions`]; `schema_revision.py` and the table-existence tests change
with it.

### 2.1 Subject root: `subject_roots`, `subject_aliases`

```
subject_roots(
  id            str(64) PK              -- canonical slug: "mathematics", "physics", "software-engineering"
  title         str(120)
  status        "curated" | "provisional" | "merged"
  merged_into   str(64) NULL FK roots.id
  created_by    str(36) NULL            -- request id that created it
  created_at    int
)
subject_aliases(
  alias         str(120) PK             -- normalised: lowercase, ascii, punctuation stripped, plural-stemmed
  root_id       FK subject_roots.id
  topic_path    str(160) NULL           -- e.g. "algebra.linear-equations" for "first-degree equations"
  source        "curated" | "model" | "admin"
  confidence    float
)
```

| | Value |
|---|---|
| Existing equivalent | none for a root. `match.subject_key` is the nearest idea (a stemmed word set) |
| Owner | Generation (new module `coursegen/brain/`). The curated seed list is reviewed by the owner (content owner), not generated |
| Writer | seed migration/script (curated roots, about 30 [P]); `resolve_root` for provisional roots and model aliases; admin merge endpoint |
| Reader | `brain.route`, admin screens, matching |
| Identity key | `subject_roots.id`; `subject_aliases.alias` (so an alias resolves to exactly one root) |
| Versioning | none. A merge sets `status="merged"`, `merged_into`; lookups follow the redirect once. Aliases are repointed, never deleted |

**Alias policy.** Normalise (lowercase, NFKD to ascii, strip punctuation, collapse spaces, stem plurals with the
same `_stem` rule `match.py` uses). Lookup order: (1) exact normalised alias; (2) exact `topic_path` aliases within
a root ("first-degree equations", "linear equations", "solving for x" all map to `algebra.linear-equations`);
(3) one fast model call, `subject` role, which must answer from the list of root ids and a free `topic_path`
(never invent a root id outside `^[a-z][a-z0-9-]{1,63}$`); (4) miss: create a `provisional` root named from the
normalised subject, and mark the child private until an admin confirms or merges the root. Model-proposed aliases
enter with `source="model"` and `confidence`, and are used for *routing* only after they have served at least 2
requests [P], so a bad alias cannot silently capture a subject. "math", "maths" and "mathematics" are curated seeds.

**Scope is not lost.** The root is broad; the request keeps its scope in the `CourseSpec`: `topic_path` list
(canonical), `purpose` ("machine learning"), `depth`. "Linear algebra for machine learning" resolves to root
`mathematics`, `topic_path ["linear-algebra"]`, `purpose "machine-learning"`, depth practitioner. `purpose` is a
spec field (hard when it changes which concepts and examples are taught: eigenvectors for PCA vs for physics) and
selects units tagged with it. Nothing about "machine learning" is stored on the root.

**Ambiguity ("learn vectors").** `vectors` aliases to several `(root, topic_path)` pairs: `mathematics/linear-algebra`,
`physics/mechanics`, `software-engineering/data-structures` (arrays), `graphics`. Resolution order: (1) the goal and
`intended_use` in the request ("for my game", "for ML", "for physics class") plus Lesson 0 `learner_goal` pick one
if exactly one candidate's keyword set matches (code, via the alias table's `purpose` hints); (2) if the Lesson 0
door or `core_deliverable` mentions a domain term, same rule; (3) otherwise ask **one** clarification, using the
existing `Intent.clarifications` (max 2) and `needs_clarification` status [V `intent.py`], worded by code from the
candidate list ("Vectors in maths, in physics, or in programming?"). Ask only when candidates differ in at least
one hard field (topic path or root). If they would produce the same course, do not ask.

### 2.2 Root material: `root_units`, `sources`, `unit_sources`

A unit is the smallest reusable block of teaching material: one narrow topic at one depth.

```
root_units(
  id            str(36) PK
  root_id       FK
  unit_key      str(120)               -- "algebra.linear-equations.one-step", unique per root
  revision      int                    -- 1,2,3...
  is_current    bool                   -- partial unique (root_id, unit_key) WHERE is_current
  topic_path    str(160)
  purpose       str(60) NULL           -- "machine-learning" etc; NULL = general
  depth         "overview" | "practitioner" | "mastery"
  concepts      JSON                   -- [{key, title, summary, objectives[], misconceptions[]}] (Outline-shaped)
  prerequisites JSON                   -- [unit_key]; inside the same root only
  content       JSON                   -- retained material (2.2.2)
  quality       JSON                   -- gate results, reviewer verdicts, version of the validator
  status        "researching" | "validated" | "quarantined" | "superseded"
  retrieved_at  int; review_after int NULL   -- staleness
  job_id        FK-ish                 -- the research job that produced it
  digest        str(64)                -- hash of concepts+content, like ConceptVersion.digest
  created_at    int
)
sources(
  id            str(64) PK             -- sha256 of canonical URL
  url, title, publisher, license_class ("open"|"restricted"|"unknown"), registry_id NULL
  retrieved_at, content_hash, status ("ok"|"gone"|"changed")
)
unit_sources(unit_id, source_id, role ("explain"|"examples"|"visual"|"practice"), supports str(400),
             retained "none"|"paraphrase"|"excerpt", PRIMARY KEY (unit_id, source_id))
```

| | Value |
|---|---|
| Existing equivalent | partial: `catalog/sources.py` registry (licence info), `Citation` (n, url, claim, passage, basis, overlap, supported) [V `catalog/schema.py`], `Concept.outline` (objectives, misconceptions, assessment) for the concepts block |
| Owner | Generation |
| Writer | new job kind `research` only (never a learner request path, never a lesson author) |
| Reader | `decide()` (coverage), architect and detailer (concept list and prerequisites), lesson author (`material`), quiz/exercise authoring (seeds), correction tooling |
| Identity key | `(root_id, unit_key, revision)`; `is_current` partial unique index for "the live one" |
| Versioning | a correction or refresh writes revision N+1 as `researching`, then flips `is_current` in one transaction when it validates. Old revisions are kept (`superseded`); children pin `(unit_key, revision)` so nothing changes under an existing child |

**2.2.1 A reference to a source versus retained content.** `sources` is a *reference* (URL, title, licence,
retrieval time, content hash). Socrat retains only what the existing policy already permits: our own paraphrase
and, at most, a short passage of at most 400 characters stored with the claim it supports (the `Citation.passage`
bound) [V `research.py` docstring: "read and paraphrased, never copied"]. `unit_sources.retained` records which.
Licence class decides whether an excerpt may be kept (open registry sources only). A unit whose content is not
traceable to at least one `ok` source with `supports` text fails validation.

**2.2.2 What a unit retains** (`content`):

```
{ "explanations": [{id, text, level, supports:[source_id...]}],          # paraphrased, our wording
  "worked_examples": [{id, problem, steps[], answer, difficulty, supports}],
  "exercise_seeds":  [{id, statement, answer, check ("equation"|"numeric"|"equivalent"|"steps"),
                       difficulty, error_tags[], hint_ladder[]}],        # story-free, key included
  "misconceptions":  [{id, wrong_belief, symptom, fix}],
  "probes":          [{id, targets_misconception, item, key}],           # for gap-driven first tasks
  "glossary": [...] , "limits": ["what this unit does not cover"] }
```

Exercise seeds are **plain mathematics with a checkable key** (`3x + 4 = 19`, `x = 5`). A child may wrap a seed in
a story or a timer; the key and error tags stay the same. The `check` values are exactly the existing `Exercise.check`
set the math workbench grades with code [V `catalog/schema.py:Exercise`, `package.py:EXERCISES`].

### 2.3 Child course version: columns on `GeneratedCourse`, `concept_unit_pins`

Additive nullable columns on `generated_courses` (no new course table):

```
root_id        str(64) NULL FK subject_roots.id, index
family_id      str(80) NULL              -- stable id of the "child" across versions
version        int NULL                  -- 1,2,...; the row id is "<family>-v<version>"
spec           JSON NULL                 -- CourseSpec (2.3.1): the reusable, hard requirements
spec_key       str(64) NULL, index       -- sha256 of the normalised hard-field subset
serve          "private" | "shared" NULL -- NULL = legacy. shared = the brain may serve it to others
supersedes     str(80) NULL              -- previous version's course id
quality_gate   JSON NULL                 -- {passed_at, checks[], validator_version}
```

`concept_unit_pins(course_id, concept_id, unit_key, unit_revision)`, PK all four, index `(unit_key, unit_revision)`:
which unit revisions each lesson was written from. This is the only way to answer "which children does this
correction touch" without scanning JSON.

| | Value |
|---|---|
| Existing equivalent | `GeneratedCourse` is the course; `Course.modules/levels/shape/languages` + `Outline` per concept + `Brief` are the blueprint. `owner_id`, `visibility`, `moderation` are access fields |
| Owner | Generation (rows), Platform/owner for moderation |
| Writer | `run_outline` and `run_package` (spec, pins, quality gate); `brain.route` (reads only); admin (moderation, supersede) |
| Reader | `decide()`, `view`, enrollment, planner (unchanged), admin |
| Identity key | `id = "<family_id>-v<version>"`; `family_id = "brain-" + root_id + "-" + spec_key[:12]` (deterministic, which is what lets the database collapse concurrent identical requests, Section 5.1) |
| Versioning | a *version* is immutable in structure (modules, concept ids, spec, pins). Planned concepts may be filled in (the existing lazy generation, shared by design: "the first learner to approach a concept pays for it" [V `prefetch.py`]). A changed lesson that learners have already used is a correction (Section 5.5), which keeps `ConceptVersion` and quiz ids resolvable. A structural improvement is **version N+1**, a new row; existing enrollments stay on N |

**2.3.1 `CourseSpec`** (what makes a course a distinct reusable experience), and what can be derived from the
existing blueprint [V = already in `Brief`/`Course`/`Intent`; P = new]:

| Field | Meaning | Derived from existing |
|---|---|---|
| `root`, `topic_path[]`, `purpose` | scope | new (`Intent.subject/domain` give hints) |
| `covers` | set of `unit_key` the course teaches | new; computed from concept to unit pins |
| `outcome` | enumerated outcome kind + canonical deliverable id (e.g. `solve:linear-equations`) | `Brief.outcome` is free text; the kind is new |
| `entry` | prerequisite band: `none` / `numeracy` / `algebra-1`... plus `starting_level` band | `Intent.starting_level`, `levels[]` |
| `depth` | `overview` / `practitioner` / `mastery` | `Outline.depth` [V] |
| `rigor` | `intuitive` / `balanced` / `rigorous` | `StyleSpec.rigor` [V] |
| `frame_kind` | `none` / `investigation` / `game` / `story` / `case-study`... (themes inside a kind are soft) | `StyleSpec.frame` free text; kind is new, from a curated map |
| `assessment_kind` | `quiz` / `drill` / `proof` / `project` / `explain` | `Outline.assessment` [V] aggregated |
| `session_band` | `bite` (units <= 12 min) / `standard` / `long` | `styles.for_session`, `Brief.session_minutes` [V] |
| `human_language`, `register` | course language and age/formality | `Intent.language`, `Intent.register` [V] |
| `code_languages`, `tools` | explicit language or tool requirement | `Intent.code_languages`, `Brief.languages` [V] |
| `access` | accessibility flags that change content (no audio-only, etc.) | `Intent.accessibility` |
| `studio_needs` | graders the course needs (math workbench, runner) | `shape.effective(course)` [V] |

Fields not in the spec, because they are enrollment-only: Section 3.

### 2.4 Enrollment and adaptation: `Enrollment` (+ two additive columns)

```
enrollments.learner_plan   JSON NULL   -- private overlay (2.4.1); never copied into any shared record
enrollments.match_id       str(36) NULL FK course_matches.id
```

| | Value |
|---|---|
| Existing equivalent | `Enrollment` (+ `ConceptState`, `Evidence`, `PlanDay`, `adaptive`) [V] |
| Owner | Learning (existing) |
| Writer | `placement.enroll` (start point, minutes), `brain.route` (overlay, match id), planner and adaptive code (progress, adjustments) |
| Reader | planner (`build_plan`), tutor (`assistant/service.py`), `today_view`, the first-session adaptation of the previous plan |
| Identity key | `Enrollment.id`; (user, course) is not unique in the DB [V], so idempotency is application-level (5.3) |
| Versioning | pins `course_id` = a specific child version row. Moving to version N+1 is an explicit, learner-visible action (a proposal, like `evolve`), never automatic |

**2.4.1 `learner_plan`** holds what must never be shared: the raw request, the door, Lesson 0 calibration
(`concept_probed`, `detected_gaps`, `outcome`), the resolved probe, the true `session_minutes`, the learner's
constraints that are satisfied at delivery. It replaces the previous plan's use of `Brief.plan` **for shared
courses**; for a private course `Brief.plan` is unchanged. Hints, answers, progress remain where they are
(`Evidence`, `ConceptState`, `QuizResponse`, tutor threads).

### 2.5 Audit: `course_matches`

```
course_matches(
  id str(36) PK, request_id str(36) UNIQUE FK learning_requests.id, user_id, created_at,
  root_id, requirements JSON,              -- the derived CourseSpec + overlay, hashed fields listed
  outcome  "reuse" | "reuse_adapted" | "new_from_material" | "extend_and_new" | "clarify" | "private_new" | "legacy",
  course_id NULL,                          -- what was served or created
  candidates JSON,                         -- every candidate considered, with per-check pass/fail/unknown and reasons
  reason str(500),                         -- one human-readable line
  reused JSON, generated JSON, private JSON,   -- unit ids, concept ids, spec fields, overlay fields
  models_avoided JSON, cost_usd float,
  matcher_version str(16)
)
```

The `UNIQUE(request_id)` makes the routing decision idempotent (5.3) and gives the audit answer in one row.

---

## 3. What "similar enough to reuse" means

### 3.1 Request fields to criteria (full matrix)

Question for each: *could a different learner use the same lessons and assessments unchanged?* If no, the field
is **hard** (in `CourseSpec`, changes `spec_key`). If yes, it is **overlay** (in `Enrollment.learner_plan`, or a
plain enrollment column).

| Field (source) | Where | Why | Delivery-time component |
|---|---|---|---|
| Subject, scope, `topic_path` (Intent, alias tables) | **spec** | different concepts | none |
| Purpose ("for machine learning") | **spec** | different examples, unit selection | none |
| `core_deliverable` / `Brief.outcome` | **spec** as `outcome` kind; wording is overlay | different capability = different course | none |
| `desired_level` / depth | **spec** | content depth | none |
| Prerequisite band / entry level | **spec** `entry` (range) | a lesson that assumes algebra cannot serve a beginner | placement can start later in the course (overlay) |
| Explicit rigor ("derivations", "proofs") | **spec** `rigor` | different lessons and assessments | none |
| Explicit frame ("as detective cases") | **spec** `frame_kind` | the experience is the request; headings with a theme do not count | none |
| Assessment ("timed drills", "no quizzes", "only hints until I try") | **spec** `assessment_kind`; help policy is overlay | assessments are content; hint timing is the tutor's | tutor `Ladder` ceiling (overlay) |
| Human language, register/age | **spec** | text of lessons | none |
| Explicit code language or tool | **spec** | different examples and graders | none |
| Accessibility needs that change content | **spec** | content | none |
| `session_minutes` (10/25/60) | **overlay**, except `session_band` is **spec** | a bite course serves larger budgets by packing several lessons; a `standard` course cannot serve a 10-minute learner without splitting | planner packing [V]; splitting a lesson by its `## ` sections is **proposed** (no component today): MVP treats a 10-minute learner as incompatible with a `standard` child |
| Weekdays, deadline, `minutes_per_day` | **overlay** | scheduling | planner [V] |
| Starting point ("I already solve one-step equations") | **overlay** | where to begin | `levels[].start_concept`, `prefetch.initial_slice(start)`, placement probes [V]; mapping the claim to a concept is **proposed** (token match against unit concept titles, 4.A) |
| Lesson 0 calibration, `used_hint`, `pace_level` | **overlay** | prior for the opening only | opening-task choice, `Ladder` start (previous plan 2.4) |
| `detected_gaps` / `concept_probed` | **overlay** | picks a stored probe item from the unit | probe insertion into `/today` (**proposed**; MVP: tutor context line) |
| Door (analogy domain) | **overlay** | personal scenario | tutor context [V `tutor_block`]; a private intro card generated per enrollment is **proposed**; MVP: not applied to shared lessons |
| Tone, explanation length | **overlay** | wording default | tutor only in MVP; lessons are generated once |
| Raw request text, uploaded `material`, project details | **private**, never shared | privacy | forces `serve="private"` for course content derived from them |

A single onboarding snag (`or_overrides_all`) therefore never creates a variant: it chooses which stored probe is
the learner's first task. A *specific request* ("use C++", "university-level derivations") changes the spec and,
if no child has it, creates a new child.

### 3.2 Hard compatibility checks (all must pass; any `unknown` blocks serving)

1. `root` equal after redirect.
2. **Coverage:** `request.requires` (set of unit keys) is a subset of `child.covers`, and `child.covers` has no
   more than `1.25 x` the required units [P] (so a learner who asked for linear equations is not served a 40-lesson
   algebra course). Superset service through a path override is **proposed** (the enrollment's `adaptive`
   roadmap override exists [V comment on `Enrollment.adaptive`], its use here is [?]).
3. `depth` equal in the MVP (a deeper child is not served to a shallower request until we can show it does not overwhelm).
4. `entry`: the child's prerequisite band is not above what the learner states. Unknown learner level counts as
   `unknown`, which passes only against children with `entry = none` or a diagnostic-first start.
5. `rigor`, `frame_kind`, `assessment_kind`: equal when the learner constrained the field. When the learner did
   **not** constrain it, the child must have the default (`rigor balanced`, `frame_kind none`,
   `assessment_kind quiz`); a themed child never serves a learner who did not opt into the theme.
6. `human_language`, `register` (children never mix with adult courses, as in `match.fit` [V]), `code_languages`,
   `tools`, `access`: set equality on constrained fields.
7. `session_band` compatible: child `bite` serves budgets of any size; child `standard` serves >= 25 minutes only.
8. **Eligibility to serve** (2.3 table, Section 4.C): published, moderation ok, serve `shared`, quality gate passed,
   first playable content ready, schema and studios supported, every pinned unit revision still `validated`.

### 3.3 Decision examples

| Request | Existing child | Verdict | Reason |
|---|---|---|---|
| "linear equations through detective cases, 10 min" | spec: algebra.linear-equations, investigation, quiz, bite | accept | all hard fields equal; minutes overlay |
| "first-degree equations as short mystery investigations" | same child | accept | topic alias, frame kind `investigation` equal; theme word (detective/mystery) is soft |
| "same mystery algebra, 25 min, I know one-step" | same child | accept, adapted | bite serves 25; start moved by placement |
| "linear equations for an exam through timed drills" | detective child | **reject** | `assessment_kind` drill != quiz; `frame_kind none` != investigation (the child would be a themed course for a learner who asked for drills) |
| "linear equations, detective style, prove each step formally" | detective child (balanced) | reject | `rigor rigorous` != balanced |
| "linear equations" with no style | detective child | reject | unconstrained learner must not get a themed child (check 5) |
| "algebra" (whole course) | linear-equations child | reject | coverage: requires more units than the child covers |
| "linear equations" | whole algebra-1 child (14 units) | reject (MVP) | exceeds the `1.25x` ceiling |
| "linear equations, in French" | English child | reject | `human_language` |
| "conditional probability, detective cases" | algebra detective child | reject | coverage; the *frame* is the only thing in common |
| "linear equations, only hints until I try" | detective child | accept | help policy is overlay (Ladder ceiling) |
| "linear equations, I like football" | detective child | accept | door is overlay; MVP does not retheme the lesson, and says so in the match reason |
| "linear equations for my startup's pricing model" (private details) | any | no shared match for the personal part | private context: course is private; root units may still be read |

Rule against both failure modes: wording differences never reach `spec_key` (it hashes canonical enumerated fields
only), and a request's *explicit* frame, rigor or assessment is compared as a kind, so "detective-themed headings
on a conventional course" has `frame_kind none` and is rejected.

### 3.4 Retrieval versus decision; ranking; uncertainty

- **Retrieval (finds candidates).** `SELECT ... FROM generated_courses WHERE root_id = ? AND serve='shared' AND
  status='published' AND moderation='ok'`. At the expected size (tens to hundreds of children per root [?]) read all
  and filter in Python. `spec_key` equality is an index shortcut for the exact case. Alias and topic alias tables
  do the word work. Token overlap (the `match.subject_key` idea) is allowed only to propose candidates when the
  topic alias misses.
- **Decision.** `compatible(child.spec, requirements)` returns per-check `pass | fail | unknown` plus a reason;
  no score authorizes serving. Only all-`pass` serves.
- **Several pass:** exact `spec_key` first; then fewest overlay adaptations; then most concepts `live`; then
  fewest open reports; then the latest version. Tie: oldest family (stability).
- **Closest child covers only part of the goal:** not a hit. It is recorded in `candidates` with
  `partial: {covers_units, missing_units}`. Its **units** (not its lessons) are already in the root, so the new child
  reuses them; its pins show which. Its modules may be copied into the new child as a starting outline only if their
  concepts' unit pins validate (**proposed**, PR F).
- **Uncertain** (`unknown` on a hard check, e.g. the model did not classify `frame_kind`): treated as a miss for
  serving; `course_matches.reason` says which field. The learner is not asked, except through the one clarification
  rule above.
- **Simplest lookup that fits.** Exact SQL plus code checks. **Embeddings are justified only by evidence:** after
  PR D, measured missed-reuse rate on the gold set (Section 8) above 15% [P] where misses are due to *topic
  wording that the alias table cannot cover*, or a root with more than about 500 children, or alias-table misses
  above 20% of requests for two weeks. Then add an embedding column used for **retrieval only**; `compatible()` stays
  the decision. A separate search service is not justified at this size.

### 3.5 Pseudocode

```python
def route(db, settings, user_id, row, parsed) -> Decision:
    prof, status = learner_profile.load(db, row.id)                    # previous plan 2.1
    req = derive(row.text, parsed, prof, status)                       # Requirements(spec, overlay, private, requires)
    root = resolve_root(db, req)                                       # alias tables; fast model call only on miss
    if root is AMBIGUOUS: return clarify(req, root.options)            # reuses Intent.clarifications
    covered, missing = coverage(db, root, req.spec.requires)           # root_units current+validated+depth ok

    cands = candidates(db, root, req)                                  # shared, published, ok, same root
    audit = []
    best = []
    for c in cands:
        checks = compatible(c.spec, req.spec)                          # dict[field] -> pass|fail|unknown, reason
        elig   = eligible(db, c)                                       # published, gate, first playable, schema, pins valid
        audit.append(record(c, checks, elig))
        if all_pass(checks) and elig.ok: best.append(c)

    if best:
        child = rank(best)
        adaptation = overlay_diff(child, req)                          # minutes, start, probe, hints
        outcome = "reuse" if not adaptation else "reuse_adapted"
        return serve(db, row, child, outcome, adaptation, audit)       # no outline job

    if req.private_context:                                            # cannot be generalised safely
        return build_private(db, row, req, covered, missing, audit)    # may still read root units

    family = family_id(root.id, req.spec_key)                          # deterministic
    if not missing:
        return generate_child(db, row, family, req, outcome="new_from_material", audit)
    for unit in missing:
        enqueue_research_once(db, root, unit)                          # (course_id="root:<id>", kind research, target=unit_key)
    return generate_child(db, row, family, req, outcome="extend_and_new", audit)  # outline waits on units
```

`serve` and `generate_child` both write the `course_matches` row in the same transaction as the request update.
`audit` entries look like
`{"course": "brain-mathematics-9f2c-v1", "checks": {"frame_kind": ["fail", "request: none, child: investigation"]}, "eligible": true}`.

---

## 4. Researcher, validation, and the privacy boundary

### 4.A The root-extension job (`research`)

**Trigger.** `decide()` found `missing` unit keys. **Input** (never raw learner text): root id and title,
`unit_key`, canonical `topic_path`, `purpose`, `depth`, `entry` band, `human_language`, `register`, existing unit
keys of the root (for prerequisites and de-duplication), source registry ids allowed for this subject
(`GENERAL_SOURCES` plus subject-appropriate entries [V `research.py`]), and the previous revision when refreshing.

**Scoper (fast model).** Maps a topic path to the units needed: a list of `{unit_key, title, depth, prerequisites}`
validated by code (slug format, prerequisites exist or are in the same list, acyclic, same root). It is only called
when the topic alias table does not already name the units. [P]

**Source selection (per unit).** Existing machinery: `search.gather` (Wikipedia, Wikibooks, MIT OCW, OpenStax,
OpenAlex, optional web) ranked by `search.rank`, `RESEARCHER` prompt with fit >= 3, `research.screen` (public https,
reachable, `links`), `fetch.read` (robots allowed). Level and subject drive the choice: `depth` and `register` are in
the prompt; registry entries that are about computing are only offered to software subjects (`GENERAL_SOURCES`)
[V]. At least two independent sources per unit, one of them a registry (authority) source when one exists. [P]

**Extraction.** An extractor call (strong tier, once per unit) reads the fetched passages and writes the
`content` block in our own words, each item carrying `supports: [source_id]`. Worked examples and exercise
seeds carry an **answer key computed by code** where the studio can check it (`equation`/`numeric`/`equivalent`
through the existing math checkers); a seed whose key the checker cannot verify is dropped. [P, using V checkers]

**Validation before reuse** (all in code unless noted; a unit stays `researching` until every item passes):

1. Schema valid; slug rules; objectives are observable verbs (the existing rule for outlines).
2. Every retained claim has a source in `unit_sources` with status `ok`; `research.ground` overlap >= the existing
   threshold; `basis` recorded.
3. Licence: no `excerpt` from a source whose `license_class != "open"`.
4. Seeds and worked examples: answer keys verified by the grader; each seed has at least one `error_tag`.
5. Conflict check (below).
6. Independent review by the critic role: coverage of the unit's stated concepts and level fit, structured verdict
   (model opinion is advisory; items 1-5 are the gate).
7. `quality.validator_version` recorded so a stricter validator can later re-validate old units.

**Conflicting sources.** Compare claims by `unit_key`: when two sources disagree on a fact that has a checkable key
(numbers, algebraic results), the grader decides; otherwise prefer the registry/authoritative source, record both
in `quality.conflicts`, drop the disputed item, and never retain a claim that rests on one disputed source only. A
disagreement the validator cannot settle makes the unit `quarantined` with a reason and the research job `failed`
for review (it is not retried automatically).

**Failed retrieval.** Per source: record `sources.status="gone"` and continue with others. If fewer than two usable
sources remain, the unit does not validate; the job retries with the existing backoff (`retry_or_bury`) and then
stops in `failed`, which the existing admin retry already handles [V]. A request that needed it falls back to a
**private** course built through today's per-lesson researcher (no worse than today).

**Later correction.** A learner report, a link-check failure (`maintain`, `links`), or an admin correction creates
revision N+1 of the unit; the correction flow is Section 5.5.

**Freshness.** `review_after` is set per `depth` and subject class (e.g. a year for stable mathematics, shorter for
software) [P]. Past it, the unit is still served but is queued for a background refresh by `maintain`.

### 4.B Cost control

Creating a root creates no units. One unit costs one scoper-share, one search/fetch pass and one extractor call
(plus a critic call). Units are pulled by requests, so cost follows demand, and the unique key on the unit row
keeps two requests from paying twice (5.1).

### 4.C Child eligibility to serve (and what a partial child advertises)

A child serves a *new* learner only when all hold: `status='published'`, `moderation='ok'`, `serve='shared'`,
`quality_gate.passed_at` set; **first playable content ready** (the first concept in `levels[0]` order is `live`,
has at least one graded exercise or quiz item with a key, and its `ConceptVersion` is the released one); the stored
payload validates against the current schema and the renderer supports every studio in `spec.studio_needs`; every
`concept_unit_pins` row for the *first module* points at a `validated` unit revision.

A partially generated child **advertises exactly what is ready**, derived at read time (not stored, so it cannot
drift): `ready_concepts = [c for c in concepts if status == "live"]`, `planned = [...]`, and
`readiness ∈ {outline, first_ready, module1_ready, complete}` computed from them. `view.ready/total` already carry
the counts [V]; the previous plan's `view.start` carries the first-lesson state. Learners are served at
`first_ready`; later modules are filled by the existing prefetch (`AHEAD`, `INITIAL_CONCEPTS`) [V].

### 4.D What a shared child may and may not contain

May contain: a detective storyline, case files, characters, worked examples, exercises generated from the spec and
root units; the frame text comes from a **curated frame catalog** keyed by `frame_kind` (for `investigation`: "each
lesson is a short case; clues are the given facts; the answer closes the case"). **Must not** contain: the learner's
raw text, `material`, door, calibration, answers, names, project details, anything from `learner_plan`.

How a personal request uses shared material while keeping private elements private:

1. **Derive in two parts.** `req.spec` (shared-safe, canonical enums and ids) and `req.private` (raw text, door,
   material, calibration). Only `req.spec` and root units go into shared generation prompts; `Brief` for a shared
   child is built from `spec` (title from canonical topic and frame kind, `outcome` from the canonical deliverable,
   `style_request` from the frame catalog, `plan=None`).
2. **Overlay stays in `Enrollment.learner_plan`.**
3. **Private flag (code, conservative).** `private_context = bool(row.material) or intent flag "personal project"
   (new boolean from the parse step) or the request names an identifiable person, employer, school or file`. [P]
   `private_context` forces `serve="private"`; the course follows today's path, may read shared root units, and is
   never a match candidate (`serve` is not `shared`).
4. **Leakage gate before `serve='shared'` is set** (and again on every concept release): 8-word shingle overlap
   between the shared child's payload/unit content and *any* `LearningRequest.text`, `material`, `OnboardingDraft`
   text of the creating learner must be zero; stray tokens like the creator's display name or email fail it. A
   failure keeps the course `private`.
5. **Where safe generalisation is impossible** (the lesson's point is the learner's own data), the course stays
   private and excluded from matching, and `course_matches.outcome="private_new"` says why.

---

## 5. Failures that cost money or trust

### 5.1 Two learners request the first Mathematics course at once

| Step | Guarantee | Key |
|---|---|---|
| Root | one row | `subject_roots.id` PK. Insert with `ON CONFLICT DO NOTHING` (SQLAlchemy `insert().on_conflict_do_nothing()`, supported by SQLite and Postgres [?] on the deployed dialect); the loser re-reads |
| Child family | one course row | deterministic `family_id`/`id` from `(root_id, spec_key)`; `generated_courses.id` PK |
| Outline job | one open job | existing `uq_generation_jobs_one_open (course_id, kind, target)`: the second `enqueue` raises `AlreadyQueued`, caught like the existing duplicate handling; the second request sets `row.course_id = family id` and follows the same job. The first request is *not* the owner of the shared row |
| Research | one per unit | job kind `research`, `course_id = "root:<root_id>"`, `target = unit_key`: same index; plus the `root_units (root_id, unit_key) WHERE is_current` partial unique so a second inserted `researching` row for the same unit is refused |
| Both requests | each gets its own `LearningRequest`, `course_matches`, enrollment | `uq_learning_request_user_key`; `course_matches.request_id UNIQUE` |

Compatible requests share the in-flight generation because they resolve to the same deterministic family; two
incompatible requests (different `spec_key`) share only the research jobs through the unit key.

### 5.2 Researcher finishes, then the worker crashes

The unit is committed (`status='validated'`, `is_current=true`) in its own transaction before the outline job
reads it, and the research job's `output` records `{unit_id, revision}` (existing `_note(..., output=...)` [V]).
The outline job's first phase reads units from the database. After a crash the orphaned job is re-claimed
(`STALE_SECONDS`, which the previous plan shortens for waiting learners), re-runs step 0, sees the unit already
`validated`, skips research and resumes. The previous plan's "resume from the stored architect reply" (its 5.2.6)
covers the outline phase. Money spent on research is therefore paid once. An outline job waiting on a unit that
another job is researching does not poll the model: it sets `state='queued'`, `not_before = now + 10`,
`stage='waiting-research'` and does not increment `attempts` (**proposed**, small change in `jobs.py`).

### 5.3 Refresh, double claim, double Start

| Action | Why it is safe | Key / code |
|---|---|---|
| Refresh | `view()` is read-only | [V] |
| Claim twice | returns the same request; `begin` is skipped for a row already `confirmed` | `uq_learning_request_user_key`, `draft.request_id` [V handoff]; `course_matches.request_id UNIQUE` |
| Reuse hit twice | `route` is a no-op once the match row exists | `course_matches.request_id` |
| Start twice (`POST /enrollments`) | learner-made courses reuse the earlier enrollment (`learn/routes.py:507-516`). Brain children have `owner_id` NULL, so they would take the other branch and could return `409 already_enrolled` | **[P] change** the condition to `community is not None and (community.owner_id is not None or community.family_id is not None)`; also add a DB guard `UNIQUE(user_id, course_id) WHERE active` as a partial index [?] after checking existing data for duplicates |
| Publish twice | `requests.publish` is idempotent (status check, `enqueue_once` for the initial slice) [V] | extend authorization: for a brain child, any requester whose `LearningRequest.course_id == course.id` may call it |

### 5.4 A child has a roadmap but no playable first exercise

State `readiness = outline`. **Another learner cannot be served it** (4.C): `decide()` records the child as
`eligible=false, reason="first lesson not ready"`. What they can do: a compatible request arriving *while* the first
lesson is being written maps to the same family, shows the roadmap (blueprint) and `view.start.state =
roadmap_ready` from the previous plan, and enrolls when `first_ready`. If generation fails: `view.start.state =
first_lesson_failed` with `retry` (the existing `regenerate` path); the job is auto-retried once (`AUTO_RETRIES`)
[V]. If it dies, the second learner is not stranded: after `X` minutes [P] without `first_ready`, `decide()` for a
**new** request treats the family as unavailable, and the request's own `route` creates the next version row
(`-v2`, `supersedes` the stuck one) with a fresh outline job, never deleting the failed row. The stuck family stays
visible to the owner in the existing admin view.

### 5.5 A source correction invalidates an exercise used by several children

```
1. Quarantine:   root_units(unit_key, rev r).status = 'quarantined'  (reason, correction id)          one transaction
2. Find users:   SELECT course_id, concept_id FROM concept_unit_pins
                 WHERE unit_key = ? AND unit_revision = ?                                       -- indexed
3. Stop serving: eligible() joins pins to unit status; a child whose *first module* has a
                 quarantined pin is ineligible for new learners immediately (no code deploy).
                 A later-module pin makes only those concepts unavailable (the planner already holds planned/draft).
4. Existing enrollments: they stay on their version. Affected activities show a notice ("this item was
                 corrected"); the defective item stays resolvable (existing `retired_quiz`/`revisions.carry`
                 behaviour keeps stored attempts valid) but is no longer offered.
5. Repair:       research writes revision r+1 (validated); a `package` job re-writes each affected concept from
                 r+1 (reason "source-correction"); `store_concept` keeps the old payload in ConceptVersion;
                 pins are repointed to r+1; the exercise id is retired, the replacement has a new id.
6. Evidence:     answers on the defective item are not deleted. Excluding them from mastery is **[P]** (an
                 `evidence.voided` flag read by `engine`); until then a notice says that item did not count
                 correctly [?]. Honest boundary: Evidence is append-only today.
```

### 5.6 Existing requests and courses with no root

All new columns are nullable; `root_id IS NULL` means *legacy*. Legacy rows keep working unchanged (every read path
ignores the new columns). Rollout: (1) migration only; (2) **shadow mode**: `route` runs, writes `course_matches`
with `outcome` and `would_serve`, and changes nothing the learner sees; (3) a backfill script assigns `root_id`
to existing learner courses by running `resolve_root` on stored `LearningRequest.intent` (alias tables only, no
model), always with `serve='private'` (never auto-shared); (4) existing *public community* courses remain matchable
only through the old `match.find` (flag `request_matching`), unchanged; they are not brain candidates until an
admin gives them a `spec` (they have no pins and no sanitization guarantee); (5) turn on serving for fresh
requests only.

---

## 6. Five requests, in order

Illustrative root state at the start: empty. Unit counts and costs are illustrative; the previous plan's
modelling of generation applies (roadmap first, Module 1 detailed). `Q` = model calls avoided or needed.

### Request 1: "Teach me to solve linear equations through detective cases. I have ten minutes a day."

| | |
|---|---|
| Root | `mathematics` (alias "linear equations" hits the topic alias `algebra.linear-equations`; root created from the seed list, status curated, empty) |
| Spec | `topic_path [algebra.linear-equations]`, `depth practitioner`, `entry numeracy`, `frame_kind investigation` (explicit), `assessment_kind quiz`, `rigor balanced`, `session_band bite`, `en`, `general`, `private_context false` |
| Coverage | required `algebra.linear-equations.{one-step, two-step, both-sides}` [illustrative 3 units]; root has 0 |
| Candidates | none (no child) |
| Decision | `extend_and_new`. Reason: "root exists; no unit covers linear equations; no child; frame investigation requested" |
| New records | 3 `root_units` (researched), `sources` and `unit_sources`, child `brain-mathematics-<key>-v1` (`serve shared`), `concept_unit_pins`, `course_matches`, enrollment with `learner_plan` (raw text, 10 minutes) |
| Q required | `subject` (only on alias miss; here avoided by seed), scoper (avoided: topic alias names the units), research+extractor+critic for 3 units, stylist (frame from catalog: avoided), architect (roadmap + Module 1), critic, first-lesson package (author, quiz, atoms, reviewer). Baseline for scale only: the handoff's SQL cold run was 7 min 17 s and $1.70 [H]; no claim that this request matches it |
| First activity in `/today` | Lesson "Case 1: The Vault Code", about 9 minutes (bite) |

First exercise as the learner sees it:

> **Case 1: The Vault Code** (about 9 minutes)
> *Scene.* A bank vault opens with a secret number, the code. The night guard left a note on the desk.
> *Idea.* An equation is a balance. Whatever you do to one side, do to the other, and the balance holds.
> *Worked clue.* "The code plus 7 is 12." Subtract 7 from both sides: the code is 5.
> **Your turn.** The note says: *"Three times the code, plus 4, makes 19."* Write the equation and solve it. Type your answer as `x = …`.
> *Hint 1 (after one attempt):* What was done to the code **last**? Undo that first.
> *Expected:* `x = 5` (the math workbench's `equation` check accepts any equivalent form) from seed `3x + 4 = 19`.
> *Then:* two short check questions; if you answered without a hint, Case 2 is next.

### Request 2: "Help me solve first-degree equations as short mystery investigations. Ten minutes daily."

| | |
|---|---|
| Root / spec | `mathematics`; "first-degree equations" = topic alias of the same `topic_path`; "mystery investigations" maps to `frame_kind investigation`; same other fields. `spec_key` equal to Request 1's |
| Candidates | `brain-...-v1` (one) |
| Checks | all `pass` (root, coverage 3/3 = ratio 1.0, depth, entry, frame, assessment, session_band) |
| Eligibility | published, gate passed, first concept `live` with a keyed exercise, units `validated`: yes |
| Decision | `reuse`. Reason: "exact spec_key; wording difference (mystery vs detective) is a soft theme" |
| New records | `course_matches`, enrollment pinned to `-v1`, `learner_plan` (raw text, 10 minutes) |
| Q | required: none beyond the parse step that already ran. **Avoided:** scoper, research, extractor, stylist, architect, critic, all package jobs for written concepts. Prefetch may still queue concepts ahead (`AHEAD = 3`), a cost shared by all learners of the child [V] |
| Plan screen | `view`: `status matched`, `published true`, `blueprint` from the stored course, `job` null, `ready/total` from concepts, `enroll` present [V `requests.view`]. The screen shows the roadmap and **Start learning** immediately; no "generating" state because there is no job |
| First activity | the same Case 1 as Request 1 (shared lesson, unchanged). Overlay: the learner's raw request and 10-minute budget are in their `learner_plan` |

### Request 3: "I want the same mystery-style algebra course, but I have 25 minutes a day and already solve one-step equations."

| | |
|---|---|
| Spec | identical `spec_key` (25 minutes and a prior skill are overlay) |
| Decision | `reuse_adapted`. Reason: "child session_band bite serves 25; start moved by placement; no hard field differs" |
| Adaptation | (a) `Enrollment.learner_plan.session_minutes = 25`; the planner packs several bite lessons per day (previous plan PR 4 supplies the true budget; without it the 25 becomes 30 and packing still works) [V `ENROLL_MINUTES`]. (b) Start: the claim "one-step equations" is matched by code to concept `one-step` (token overlap with unit concept titles); a **probe item from the unit** (`probes` for one-step) is the learner's first task; pass moves the start to `two-step`. The existing mechanics are `levels[].start_concept`, `prefetch.initial_slice(start)` and placement probing of non-planned concepts [V]; the claim-to-concept mapping and the probe-in-`/today` insertion are **proposed**; MVP: start at the course's second-level start concept when the learner says they already know the basics, no probe (the child must provide `levels` with such a start) [?] |
| Q | avoided: everything in Request 2. Required: if `two-step` is `planned`, `prefetch.initial(start)` queues its package job (one lesson, from unit material, so no research) |
| First activity | "Case 2: The Locked Drawer", `two-step`: *"Twice the drawer number, plus 3, is 17"* style item, after one probe if the placement mapping is implemented |

### Request 4: "Teach me linear equations for an exam through timed drills."

| | |
|---|---|
| Root / spec | `mathematics`; same `topic_path`; `frame_kind none`; `assessment_kind drill`; `rigor balanced`; `purpose exam`; `session_band` from the learner's profile |
| Coverage | `one-step`, `two-step`, `both-sides` all `validated` in the root: **covered** |
| Candidates | the detective child: `frame_kind investigation != none` fail, `assessment_kind quiz != drill` fail |
| Decision | `new_from_material`. Reason: "root covers the topic; no child with drill assessment; detective child rejected on frame and assessment" |
| Reused | 3 units; their `exercise_seeds`, `worked_examples`, `misconceptions`, `error_tags`, hint ladders, source list; nothing from the detective child's lessons |
| Generated | child `brain-mathematics-<other key>-v1`: roadmap (drill rounds per unit), Module 1 detail, first drill lesson (strong tier), the drill assessments, scoring and error-tag feedback text |
| Q avoided | scoper, subject, research, extractor, critic of units |
| Q required | architect (smaller: concepts come from units), critic, first-lesson package without the per-lesson researcher (the unit is the `material`) |
| New records | child row, pins, `course_matches`, enrollment, `learner_plan` |
| First activity | Drill set |

First exercise as the learner sees it (same seed `3x + 4 = 19` and keys as the detective case, different experience):

> **Drill 1: One- and two-step equations** (8 minutes)
> *Warm-up (untimed, 2 items)* with worked solution shown after each.
> **Round 1: 4 items, 3 minutes, no hints.** Solve for x:
> (a) `x + 9 = 15` (b) `4x = 36` (c) `3x − 5 = 16` (d) `3x + 4 = 19`
> Expected: `x = 6`, `x = 9`, `x = 7`, `x = 5`.
> *After the round:* score, time, and the error tag for each miss, for example *"sign error: you added 5 instead of subtracting"* (from the unit's `error_tags`).
> *Note:* a countdown timer is not a supported renderer feature today. MVP records `elapsed_seconds` per item (the `Evidence` column exists [V]) and shows a "3-minute round" instruction; the learner is told the timer is self-run. A client timer is **proposed**.

### Request 5: "Teach me conditional probability through detective cases."

| | |
|---|---|
| Root | `mathematics` (alias "conditional probability" hits `probability.conditional`) |
| Spec | `topic_path [probability.conditional]`, `frame_kind investigation`, `assessment_kind quiz`, `entry` algebra and counting basics |
| Coverage | required `probability.basics`, `probability.conditional.bayes-intro`..., root has only `algebra.*`: **missing** |
| Candidates | the detective algebra child: root and frame match; coverage fails (`covers` has no probability unit) |
| Decision | `extend_and_new`. Reason: "root exists, algebra units cannot teach this; the nearest child shares only frame_kind (partial: 0 of 3 units)" |
| Reused | root record; the `investigation` frame from the catalog; the stylist `Frame` of the algebra child by `spec` frame text (saves one call); the validated algebra units only as prerequisite context ("solving for an unknown") |
| Research | targeted: 3 units [illustrative] (`probability.basics`, `probability.conditional`, `probability.bayes-intro`), under the root. The algebra units are not touched |
| New records | 3 `root_units`, sources, child `-v1` (new family key), pins, match row, enrollment |
| Q | scoper (the topic alias names only some units), research + extractor + critic per unit, architect, critic, first-lesson package |
| First activity | "Case 1: The Missing Witness" (a conditional probability: "of the 40 people in the building, 10 had keys; 4 of those with keys were seen near the door; given someone had a key, what is the chance they were near the door?"; expected `4/10`, `numeric` check) |

---

## 7. Answering the audit question

Query: `SELECT * FROM course_matches WHERE request_id = ?`, joined to `enrollments.match_id`.

| Question | Where |
|---|---|
| Why was this course served? | `outcome`, `reason`, `candidates[...].checks` |
| Why was another rejected? | the same JSON: `{"course": ..., "checks": {"assessment_kind": ["fail", "request drill, child quiz"]}}` |
| What did it reuse? | `reused`: unit ids and revisions, concept ids, frame text id, `models_avoided` |
| What was generated? | `generated`: course id, job ids, `cost_usd` (sum of `GenerationJob.cost_usd` for those jobs) |
| What belongs only to this learner? | `enrollments.learner_plan` keys listed in `private`; `Evidence`, `QuizResponse`, tutor threads |
| Which version is the learner on? | `enrollments.course_id` (an id with `-vN`) |
| Which sources back this lesson? | `concept_unit_pins` -> `root_units` -> `unit_sources` -> `sources` |

---

## 8. PR plan

Branch from `feat/onboarding-lesson0` (or `1c42b949`), no merging `main`, specific paths only, never
`apps/web/next-env.d.ts`; tests from the repo root with `--basetemp`; flag `course_brain` default off; migrations
additive with a tested downgrade. Shared contracts (`requests.begin`, `requests.view`, intent, roles, config,
migrations) need a note to the onboarding owner before merge, as in the handoff. Dependencies on the previous
plan are noted.

| PR | Owner | Files | Depends on | Observable acceptance |
|---|---|---|---|---|
| **A Schema** | Generation | `models.py`, `migrations/versions/0051_course_brain.py`, `schema_revision.py` and its tests | none | upgrade and downgrade round-trip; every legacy test green; new columns nullable |
| **B Spec, root, audit, shadow** | Generation | new `coursegen/brain/{spec,roots,compat,decide}.py`, `requests.begin` (one call), `config.py` flag, `tests/test_brain_*.py` | A, previous PR 0 (profile loader) | with the flag on and serving off, every claim writes one `course_matches` row with `would_serve`; gold set (3.3 table) reproduces its verdicts; claim twice writes one row |
| **C First milestone: a second learner reuses a working child** | Generation | `brain/serve.py`, `requests.begin` (reuse branch), `learn/routes.py` enrollment branch (G5), `run_outline`/`run_package` (sanitized Brief for `serve=shared`, family id), `generated.py` (stamp `quality_gate` and `serve='shared'` when first playable lesson is released and the leakage gate passes), `tests/test_brain_reuse.py` | B, previous PR 1 and 2 helpful, not blocking | a scripted-provider test: learner A claims (cold, no root units, existing per-lesson researcher); once the first lesson is `live`, learner B claims a compatible request (different wording); B's request settles as `matched`, **zero** outline, package, researcher, or architect calls for B (asserted on the provider script and on `GenerationJob` rows), B's `/today` `next` is A's first lesson, and `course_matches.reason` names the checks. A third incompatible request (drill) gets its own child |
| D Root material and research job | Generation | `root_units`, `sources`, `unit_sources` writers, `coursegen/brain/research.py` (job kind `research`), `jobs.py` (dispatch, priority, `waiting-research`), `package.context` reads units as `material`, pins | C | research for a unit commits before the outline job; killing the worker after research and restarting does not call research again; two concurrent requests research a unit once (job count, source calls); validation rules reject a unit with an unsupported claim |
| E New child from existing material | Generation | `outline.py` (architect receives unit concept lists; smaller prompt), `package.py` (author reads unit seeds and keys) | D | Request 4 trace: no research calls; the first drill's items come from unit seeds with keys; cost lower than Request 1's cold run in the same harness |
| F Corrections and supersede | Generation, Platform | `brain/corrections.py`, admin endpoint, `eligible()` joins pins, `store_concept` repoint | D | quarantining a unit makes its children ineligible for the next request at once; existing enrollments keep working and see the notice; replacement lesson ids retire the old item |
| G Backfill and rollout | Generation + owner | `scripts/dev/backfill_roots.py`, docs | C | backfill assigns roots with `serve='private'`; no behaviour change for existing learners (snapshot test of `view` for legacy rows) |
| H Delivery-time adaptation | Generation + Learning | planner, `Enrollment.learner_plan`, probe insertion, tutor `Ladder` | previous PRs 4 and 6 | Request 3 trace: 25-minute packing and a probe item driven by the overlay |
| I Retrieval upgrade (only on evidence) | Generation | embeddings for candidate retrieval | measurements from Section 9 | missed reuse drops without raising false reuse |

**Smallest first milestone** is PR C. It deliberately needs **no** root material: the first learner's child is
generated by today's pipeline from a sanitized spec, and the second learner reuses it. That already removes the
repeated outline, researcher and first-lesson cost for the common case and proves the decision, audit, privacy and
enrollment contracts before research is moved to the root in PR D.

Required small changes outside `coursegen/brain/` (for review): `learn/routes.py` enrollment branch condition,
`requests.py` (`begin`, authorization on `publish` for brain children), `jobs.py` (`research` kind, priority map,
`waiting-research`), `models.py`, `config.py`, `intent.py` (two additive booleans/fields: `private_context`,
`topic_path`, only if the derive step cannot compute them in code). The last item touches the onboarding contract
and needs the onboarding owner's agreement first.

---

## 9. Tests and measurements

| Area | Test | Fails if |
|---|---|---|
| False reuse | `test_brain_compat.py::near_misses_rejected`: the Section 3.3 reject rows plus 40 more authored pairs (depth, rigor, language, register, tools, assessment, coverage, themed vs unthemed) | any hard-field difference is served |
| Missed reuse | `::wording_variants_accepted`: alias and theme variations ("first-degree", "mystery", "maths") | an acceptable pair misses |
| Gold set | a labelled set of at least 60 request pairs [P] for precision and recall; **false reuse must be 0 on the gold set**, missed reuse reported | |
| Duplicate generation | `::concurrent_first_requests`: N=8 threads claim compatible requests against a fresh database | more than one root, family row, outline job, or per-unit research job; or total provider calls > one cold run's |
| Crash safety | `::resume_after_research_crash`, `::resume_after_outline_crash` | committed units re-researched; a second architect call |
| Idempotency | claim twice, publish twice, Start twice (`POST /enrollments` twice) | duplicate request, match row, job or enrollment, or `409` on the second Start |
| Leakage | `::shared_child_has_no_private_text`: a learner request with a name, a project, `material`, a door; shingle scan of the shared child and units; the child with private context is `serve='private'`, absent from every other learner's candidates | any overlap, or a private child in `candidates` |
| Data separation | `::overlay_never_in_shared_rows`: `learner_plan` keys absent from `GeneratedCourse`, `GeneratedConcept`, `root_units` | |
| Eligibility | roadmap-only child is ineligible; `first_ready` serves; stuck family triggers `-v2` | |
| Corrections | quarantine -> ineligible for new learners, existing enrollment still opens its lesson | |
| Legacy | `root_id IS NULL` courses behave as before; `view` snapshot for old requests unchanged | |
| Claim to Today | extends the previous plan's acceptance test: B's `/today` `next` is the shared first lesson and the match row explains it | |

**Measurements** (script `scripts/dev/bench_brain.py` [P], same harness as the previous plan's 5.4; per path, report
separately, never blended):

| Path | What is timed from the claim | Cost source | Target [P] |
|---|---|---|---|
| Cold (no root units, no child) | T1 first roadmap, T2 first usable exercise, outline end | `GenerationJob.cost_usd` by kind, `AIUsage` cross-check, `/api/v1/admin/engine-costs` | measured first; observed baseline is the handoff's single SQL run, 7 min 17 s and $1.70 for 8 modules and 36 lessons [H] and nothing more |
| New child from existing material | same | same | T2 well under cold; cost excludes research (the claim to be demonstrated, not assumed) |
| Direct reuse | claim to `view.enroll` present; claim to `/today` first activity | model calls on the request path = 0 apart from the parse | seconds, not minutes |

Plus: false-reuse and missed-reuse rates on the gold set, duplicate-generation count under N concurrent claims,
leakage count (must be 0), and the share of requests by outcome from `course_matches` once serving is on.
`ai_usage` has no course or role column [V `models.py:AIUsage`], so per-path cost uses `GenerationJob.cost_usd`
and the match row's job ids.

---

## 10. Not verified

- Nothing was run: no migration, no model call, no worker, no measurement. All targets are proposals.
- [?] Whether `begin` may await a model call (PR B checks). [?] The deployed database dialect and `ON CONFLICT DO NOTHING` support (SQLite for dev is assumed to work; confirm for production).
- [?] `Enrollment` duplicates already in production data (needed before adding the partial unique index).
- [?] Whether the enrollment's `adaptive` roadmap override can express "serve a subset of a larger child" (kept out of the MVP).
- [?] Evidence exclusion for corrected items does not exist; the plan states the boundary.
- Root seed list, `review_after` periods, size ceilings (`1.25x`), the 8-word shingle gate and the "2 served requests" alias promotion rule are proposals.
- Catalog size assumptions (tens to hundreds of children per root) come from the current absence of built-in courses, not from data.
- Intent schema additions (`topic_path`, `private_context`) touch the onboarding contract and are to be agreed with its owner.
