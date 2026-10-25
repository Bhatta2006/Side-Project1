# Content expansion plan

Branch: `content/syllabus-expansion` (cut from `redefined` at `741e1d0`). Target: [socrat-concept-syllabus.md](socrat-concept-syllabus.md), copied here unchanged from the owner's file. Nothing in this plan has been authored yet.

## 1. Baseline (23 Oct 2026, before any change)

| Command (run from the repo root) | Result |
|---|---|
| `.venv/Scripts/python scripts/content/build.py` | exit 0 · 3 courses, 61 concepts, 112 problems, 1223 cached tests |
| `.venv/Scripts/python scripts/content/validate_atoms.py` | exit 0 · 279 atoms, 99 adapters run in Python/C++/Java, 0 failures |
| `.venv/Scripts/python scripts/content/validate_quiz.py --check` | exit 0 · 900 bank items verified, manifest current |
| `.venv/Scripts/python scripts/content/lint_patterns.py` | exit 0 · 13 pattern packs, 0 problems |
| `.venv/Scripts/python scripts/content/validate_problems.py` | exit 0 · 112 problems: 29 pass, 83 warn (no brute force), 0 fail |
| `.venv/Scripts/python -m pytest services/api/tests` | 448 passed, 24 skipped |

Toolchains: Python 3.12 (venv), g++ (MinGW), JDK 21. Every validator must stay at exit 0, and the test suite must stay green, after every concept. CI also runs `ruff` and `mypy`; those only matter if code changes (see decision A).

**`content-status-report.md` is stale.** It describes branch `content-foundry` with 85 problems and 234 quiz items, while this branch has 112 problems and 900 bank items. It was produced by `.cache/generate_content_inventory.py`, which is untracked and git-ignored. `scripts/content/inventory.py` writes only the CSV. At each phase end I'll regenerate the report with the `.cache` script, unless you'd rather I promote it into `scripts/content/` first.

## 2. Schemas I will follow (with one real example each)

| File type | Path pattern | Real example | Contract (enforced by) |
|---|---|---|---|
| Course | `content/courses/<c>/course.yaml` | `content/courses/dsa/course.yaml` | `schema.Course`. `modules[].concepts` gives the order; every concept is in exactly one module; `levels[].start_concept` must exist (`registry.build`) |
| Concept | `content/courses/<c>/concepts/<id>.yaml` | `content/courses/dsa/concepts/dp-1d.yaml` | `schema.Concept`: id, title (≤100), summary (10–300), module, prerequisites (same-course id or `course:id`), difficulty 1–5, estimated_minutes 10–600, lesson (Markdown, ≥200 chars, fenced ` ```python/cpp/java `), key_points 2–8, pitfalls ≤8, **resources 2–8**, **quiz 2–10** (`QuizItem`: mcq/output/bug, options 2–6, answer index; authors write the correct option first), problems (native ids, same course), practice_links ≤10 |
| Pattern family | `content/patterns/<c>/<concept>/<family>.yaml` | `content/patterns/dsa/sliding-window/at-most-k-distinct.yaml` | `patterns.Pattern`: 3 recognition cues (≤60 words), state/transition/base_cases, complexity, templates in all 3 languages (≤25 lines each, complete programs run against `template_io`), variants with non-decreasing bands, external ids only `leetcode:`/`cf:`/`cses:` from `problems.jsonl` (checked at load), pitfalls = taxonomy ids, `provenance` required |
| Pattern atom pack | `content/atoms/<c>/<concept>/<family>.yaml` | `content/atoms/dsa/sliding-window/at-most-k-distinct.yaml` | `atoms.PatternAtomPack`, status `draft`, no review record |
| Concept atom pack | `content/atoms/<c>/<concept>.yaml` | `content/atoms/dsa/sliding-window.yaml` | Optional per concept; runnable adapters checked by `validate_atoms.py` |
| Quiz family | `content/quiz/<c>/<concept>/<family>.yaml` | `content/quiz/dsa/sliding-window/at-most-k-distinct.yaml` | `quizbank.QuizFamily`: id `quiz:<c>:<concept>:<family>`, format (`trace`, `output_prediction`, `bug_spot`, `classify`, …), static `items` (band 1–7, misconception per distractor) and/or a generator executed by `validate_quiz.py` |
| Contrast pair | `content/patterns/contrasts.yaml` | key `pattern-window-vs-prefix-sums` | Keyed by a misconception id; served by `learn/pattern_sessions.py`. Every new key also goes into `content/atoms/misconceptions.yaml` (141 ids today) |
| Native judge problem | `content/courses/<c>/problems/<id>.yaml` | `content/courses/dsa/problems/house-robber.yaml` | `schema.Problem`: statement, examples, 2–5 hints, approach, Python `reference`, `generator`; plus `brute`, `small_generator` and cpp/java `references` so `validate_problems.py` passes without warnings; tests built into `.cache/content-tests` by `build.py` |
| Project (capstone) | `content/projects/<c>/<id>.yaml` | none exist yet | `projects.Project`: milestones, rubric weights totalling 100, self-review |

**What `lint_patterns.py` adds (CI).** Every pattern file must have:
- 5–7 variants;
- all three templates passing on `template_io`;
- a draft atom pack with worked, faded, visualizer, micro (60–90 s, targeting the top pitfall) and classify (exactly 3 steps) atoms;
- a quiz family serving **≥12 items over ≥4 bands**, where every distractor is tagged with a misconception.

This is stricter than the brief's "≥3 quiz items, 3–8 variants". See decision B.

## 3. Rules for splits (learner progress safety)

1. **No id is deleted or renamed.** That covers concepts, native problems, patterns, quiz families and quiz item ids. A pattern id embeds its concept (`dsa:dp-1d/unbounded-coin-change`), so existing patterns stay under their current concept even when the family now belongs to a new concept. The new concept's lesson cross-links to it.
2. **The existing id keeps the foundational part**, for example: `dp-2d` → DP on grids, `dp-1d` → 1D DP, `binary-search` → search on sorted arrays, `stacks` → stack/queue fundamentals, `binary-trees` → traversals, `graph-traversal` → D18a, `union-find` → D18d. Exceptions are proposed in decision D.
3. **Existing native problems keep their `concepts:` list.** Changing `concepts[0]` would reroute future mastery evidence. Examples: `min-coins` stays on `dp-1d`, `next-greater` on `stacks`, `subset-sum-count` on `backtracking`. New concepts get practice through their own pattern variants and, where needed, new native problems.
4. **Existing quiz items stay** in their concept file. A split concept's lesson is rewritten to the narrower scope; any quiz item that no longer matches gets a "spot the bug in this item" review and is listed in the phase report rather than removed.
5. **Prerequisites are only ever added, never removed**, so every existing `course:id` reference still resolves and transitive closure only grows. The registry's topological sort rejects cycles at load.
6. **Effect on enrolled learners:** mastery stored on the old id stays valid. New split-off concepts start unmastered, so existing learners' plans grow. Seeding new concepts from the parent's mastery would need planner code and is out of scope; I'm flagging it, not doing it.
7. **Module moves** (a concept's `module:` changes) don't rename anything. A checkpoint a learner already passed stays passed; new concepts join the module's checkpoint pool.

## 4. Concept list

`●` existing id (extended or narrowed) · `+` new id · Tag = syllabus tag of the concept. Prereqs list only what's added or new; existing prereqs stay. Difficulty is 1–5.

### 4.1 Programming from Zero: 18 → 29 concepts (mini-projects become projects, decision E)

| Module | Concept | Syllabus | Tag | Prerequisites | Diff |
|---|---|---|---|---|---|
| first-steps | + `how-code-runs` | Z1 | CORE NEW | — | 1 |
| | ● `programs-and-output` | Z2 (output) | CORE | **+** how-code-runs | 1 |
| | ● `variables-and-types` | Z2 | CORE | (programs-and-output) | 1 |
| | ● `input-and-arithmetic` | Z4 + basic arithmetic | CORE | (variables-and-types) | 1 |
| | + `operators-and-expressions` | Z3 | CORE SPLIT | input-and-arithmetic | 2 |
| control-flow | ● `conditionals` | Z5 | CORE | (input-and-arithmetic) | 2 |
| | ● `boolean-logic` | Z5 | CORE | **+** operators-and-expressions | 2 |
| | ● `while-loops`, ● `for-loops`, ● `nested-loops` | Z6 | CORE | unchanged | 2 |
| | + `pattern-printing` | Z6 | CORE NEW | nested-loops | 2 |
| number-math (new module "Math on numbers") | + `math-on-numbers` | Z7 | CORE NEW | while-loops, operators-and-expressions | 2 |
| | + `number-systems` | Z15 | CORE NEW | math-on-numbers | 3 |
| collections | ● `lists`, ● `strings`, ● `maps`, ● `grids` | Z9–Z12 | CORE | unchanged | 2–3 |
| functions-module | ● `functions` | Z8 | CORE | unchanged | 2 |
| | ● `scope-and-mutation` | Z8 (scope) | CORE | unchanged | 3 |
| | + `memory-and-references` | Z16 | CORE SPLIT | scope-and-mutation | 3 |
| | ● `recursion` | Z13 | CORE | unchanged | 3 |
| algorithms-basics (new module) | + `searching-and-sorting` | Z14 | CORE NEW | lists, functions | 3 |
| | + `complexity-intuition` | Z21 | CORE NEW | nested-loops, searching-and-sorting | 3 |
| craft | ● `debugging`, ● `problem-solving` | Z22 | CORE | unchanged | 2–3 |
| | ● `classes-and-objects` | Z17 | CORE | unchanged | 3 |
| | + `exceptions` | Z18 | CORE NEW | functions | 3 |
| | + `files-and-modules` | Z19 | CORE NEW | strings, exceptions | 3 |
| | + `standard-library` | Z20 | CORE NEW | maps, searching-and-sorting | 3 |

### 4.2 DSA for Interviews: 23 → 46 concepts

| Module | Concept | Syllabus | Tag | New prerequisites | Diff |
|---|---|---|---|---|---|
| foundations | ● `complexity` | D1 | CORE | — | 2 |
| | ● `arrays-hashing` → Arrays | D2 | CORE | — | 2 |
| | ● `prefix-sums` | D6 | CORE | — | 2 |
| | + `hashing` | D3 | CORE SPLIT | arrays-hashing, prefix-sums | 3 |
| linear-patterns | ● `two-pointers`, ● `sliding-window` | D4, D5 | CORE | sliding-window **+** hashing | 3 |
| | ● `stacks` → fundamentals | D11a | CORE | — | 3 |
| | + `monotonic-stack` | D11b | CORE SPLIT | stacks, sliding-window | 4 |
| searching (new module) | ● `binary-search` → sorted arrays (moved module) | D7a | CORE | — | 3 |
| | + `binary-search-on-answer` | D7b | CORE SPLIT | binary-search | 4 |
| | + `binary-search-2d` | D7c | CORE SPLIT | binary-search, zero:grids | 3 |
| ordering | ● `sorting`, ● `intervals`, ● `greedy` | D8, D15, D14 | CORE | — | 3 |
| recursive-structures | ● `linked-lists` | D12 | CORE | — | 3 |
| | + `recursion-patterns` | D9 | CORE NEW | zero:recursion, complexity | 3 |
| | ● `backtracking` | D10 | CORE | **+** recursion-patterns | 4 |
| trees | ● `binary-trees` → traversals | D16a | CORE | — | 3 |
| | + `tree-patterns` | D16b | CORE SPLIT | binary-trees | 4 |
| | + `tree-construction` | D16c | CORE SPLIT | tree-patterns | 4 |
| | ● `bst` | D17 | CORE | **+** tree-patterns | 4 |
| | ● `heaps`, ● `tries` | D13, D20 | CORE | — | 3–4 |
| graphs | ● `graph-traversal` | D18a | CORE | — | 3 |
| | ● `topological-sort`, ● `shortest-paths` | D18b, D18c | CORE | — | 4 |
| | ● `union-find` → DSU + MST | D18d | CORE | **+** sorting | 4 |
| dynamic-programming | + `dp-introduction` | D19.0 | CORE NEW | zero:recursion, complexity | 3 |
| | ● `dp-1d` | D19.1 | CORE | **+** dp-introduction | 3 |
| | ● `dp-2d` → DP on grids | D19.2 | CORE | (dp-1d) | 4 |
| | + `knapsack-01` | D19.3 | CORE SPLIT | dp-2d | 4 |
| | + `knapsack-unbounded` | D19.4 | CORE SPLIT | knapsack-01 | 4 |
| | + `dp-lcs` | D19.5 | CORE SPLIT | dp-2d, zero:strings | 4 |
| | + `dp-edit-distance` | D19.6 | CORE NEW | dp-lcs | 5 |
| | + `dp-stocks` | D19.7 | CORE NEW | dp-2d | 4 |
| | + `dp-lis` | D19.8 | CORE NEW | dp-1d, binary-search | 4 |
| | + `dp-partition` | D19.9 | CORE NEW | dp-2d | 5 |
| | + `dp-squares` | D19.10 | CORE NEW | dp-2d, monotonic-stack | 4 |
| | + `dp-on-trees` | D19.11 | CORE NEW | dp-1d, tree-patterns | 5 |
| | + `dp-advanced-patterns` | D19.12 | STD | knapsack-01, dp-partition, bit-manipulation | 5 |
| math-and-bits (new module) | ● `bit-manipulation` (moved from DP module) | D21 | CORE | — | 3 |
| | + `interview-math` | D22 | CORE NEW | complexity, zero:math-on-numbers | 3 |
| strings-and-design (new module) | + `string-algorithms` | D23 | CORE NEW | hashing, interview-math | 4 |
| | + `design-data-structures` | D24 | CORE NEW | linked-lists, hashing, heaps, binary-search | 4 |
| | + `advanced-data-structures` | D25 | STD NEW | binary-trees, prefix-sums, bit-manipulation | 5 |
| | + `interview-skills` | D26 | CORE NEW | complexity, sliding-window, graph-traversal, dp-1d | 3 |

### 4.3 Competitive Programming: 20 → 50 concepts

| Module | Concept | Syllabus | Tag | New prerequisites | Diff |
|---|---|---|---|---|---|
| contest-basics (Level 0) | ● `fast-io` | C0.1 | CORE | — | 1 |
| | + `stress-testing` | C0.2 | CORE NEW | fast-io | 2 |
| | ● `simulation` | C0.3 | CORE | — | 2 |
| | + `ad-hoc` | C0.4 | CORE NEW | simulation | 3 |
| | + `constructive` | C0.5 | CORE NEW | ad-hoc | 3 |
| | + `math-basics` | C0.6 | CORE (see D) | fast-io, zero:math-on-numbers | 2 |
| | + `stl-mastery` | C0.7 | CORE NEW | fast-io, dsa:sorting | 2 |
| techniques (Level 1) | ● `complete-search` (moved here) | C1.1 | CORE | — | 3 |
| | ● `prefix-difference` | C1.2 | CORE | — | 3 |
| | + `two-pointers-cp` | C1.3 | CORE | dsa:two-pointers, dsa:sliding-window, fast-io | 3 |
| | ● `binary-search-answer`, ● `greedy-cp`, ● `bitmasks` | C1.4, C1.5, C1.8 | CORE | — | 3–4 |
| math | ● `number-theory` → sieve, SPF, divisors | C1.6 | CORE | **+** math-basics | 3 |
| | ● `modular-arithmetic` (+ extended Euclid) | C1.6 | CORE | — | 3 |
| | ● `combinatorics` | C1.7 | CORE | — | 4 |
| graph-module | ● `graph-techniques` → graph basics | C1.9 | CORE | — | 3 |
| | + `shortest-paths-cp` | C2.3 | CORE | graph-techniques, dsa:shortest-paths | 4 |
| | ● `mst` | C2.3 | CORE | — | 4 |
| | + `dsu-advanced` | C2.2 | CORE | dsa:union-find | 4 |
| | + `dag-dp` | C2.3 | CORE | dsa:topological-sort, dp-classics | 4 |
| | + `scc` (+ 2-SAT section, STD) | C2.3 | CORE NEW | graph-techniques, dsa:topological-sort | 5 |
| | + `bridges-articulation` | C2.3 | CORE NEW | graph-techniques | 5 |
| | + `euler-path` | C2.3 | STD NEW | graph-techniques | 5 |
| dp-module | ● `dp-classics` (AtCoder A–H/CSES selection) | C1.10 | CORE | — | 4 |
| | + `dp-counting` | C1.10 | CORE SPLIT | dp-classics, prefix-difference | 4 |
| | + `interval-dp` | C2.10 | CORE NEW | dp-classics | 5 |
| | ● `bitmask-dp` (+ SOS DP section) | C2.10 | CORE | — | 5 |
| | + `digit-dp` | C2.10 | CORE NEW | dp-classics | 5 |
| | + `dp-data-structures` | C2.10 | CORE NEW | dp-classics, fenwick-tree | 5 |
| | + `dp-optimisations` | C2.10 | STD NEW | dp-data-structures | 5 |
| range-structures | ● `fenwick-tree` (+ offline queries) | C2.1 | CORE | — | 4 |
| | + `sparse-table` | C2.1 | CORE NEW | prefix-difference, dsa:bit-manipulation | 4 |
| | ● `segment-tree` → build/query/update, merge nodes | C2.1 | CORE | — | 4 |
| | + `lazy-segment-tree` (lazy + walk) | C2.1 | CORE SPLIT | segment-tree | 5 |
| | + `sqrt-decomposition` (+ Mo's) | C2.1 | STD NEW | prefix-difference | 5 |
| tree-module (new module) | ● `tree-techniques` → tree DP (+ small-to-large, STD) (moved) | C2.4 | CORE | — | 4 |
| | ● `lca` (moved) | C2.4 | CORE | — | 4 |
| | + `rerooting` | C2.4 | CORE NEW | tree-techniques | 5 |
| | + `euler-tour` | C2.4 | CORE NEW | lca, fenwick-tree | 5 |
| strings-module | ● `string-hashing`, ● `kmp` | C2.5 | CORE | — | 4 |
| | + `z-function` (+ Manacher, STD) | C2.5 | CORE NEW | kmp | 5 |
| math-2 (new module) | + `number-theory-2` (+ Möbius, STD) | C2.6 | CORE | modular-arithmetic | 5 |
| | + `expected-value` | C2.7 | CORE NEW | combinatorics, modular-arithmetic | 5 |
| | + `advanced-counting` | C2.7 | CORE | combinatorics | 5 |
| | + `game-theory` | C2.8 | CORE NEW | dp-classics, bitmasks | 4 |
| | + `matrix-exponentiation` | C2.9 | CORE NEW | modular-arithmetic | 4 |
| | + `geometry` | C2.11 | CORE NEW | math-basics | 4 |
| contest-craft (new module) | + `contest-craft` | C-cross | CORE NEW | stress-testing, complete-search | 3 |

Level 3 and every bullet tagged [ADV] (suffix array, Aho–Corasick, flows, HLD, centroid, persistent and Li Chao trees, Lucas, XOR basis, …) wait until Phase 8 and your go-ahead. **Totals: 29 + 46 + 50 = 125 concepts**, against the syllabus's estimate of ≈113.

### 4.3a Phase 1 changes to the tables above (approved layout rule)

**Rule.** A module stays locked until its checkpoint is passed or all its concepts are mastered. A new module inserted mid-course would re-lock later modules for learners already past it, and moving a concept into a later module would lock work they had open. So:
- new modules are only **appended** at the end of a course;
- new mid-course concepts join **existing** modules;
- no existing concept changes module.

What changed from §4.1–4.3:
- **Zero:**
  - `math-on-numbers`, `number-systems` and `pattern-printing` → `control-flow`.
  - `memory-and-references`, `searching-and-sorting` and `complexity-intuition` → `functions-module`.
  - `exceptions`, `files-and-modules` and `standard-library` → `craft`.
  - No new Zero modules.
- **DSA:**
  - `binary-search` stays in `linear-patterns`, joined there by `monotonic-stack`, `binary-search-on-answer` and `binary-search-2d` (no `searching` module).
  - `bit-manipulation` stays in `dynamic-programming`.
  - Appended modules: `math-and-strings` (interview-math, string-algorithms) and `design-and-practice` (design-data-structures, advanced-data-structures, interview-skills).
  - `recursive-structures` is retitled "Linked structures, recursion and backtracking".
- **CP:**
  - `complete-search` stays in `contest-basics`.
  - `tree-techniques` and `lca` stay in `graph-module`, joined by `rerooting`.
  - `euler-tour` → `range-structures` (it needs a Fenwick tree).
  - `dp-data-structures` and `dp-optimisations` go into the appended module `dp-advanced`.
  - Appended modules: `dp-advanced`, `math-2` and `contest-craft` (no `tree-module`).

**Edges deferred to each concept's go-live commit.** A live concept can't depend on a draft, so these edges are added when the draft goes live:
- `zero:programs-and-output` ← `how-code-runs`
- `zero:boolean-logic` ← `operators-and-expressions`
- `dsa:sliding-window` ← `hashing`
- `dsa:backtracking` ← `recursion-patterns`
- `dsa:bst` ← `tree-patterns`
- `dsa:dp-1d` ← `dp-introduction`
- `cp:number-theory` ← `math-basics`

The live-to-live edge `dsa:union-find` ← `sorting` is added with union-find's expansion in Phase 3.

## 4.4 Pattern families per concept, all three tracks

Splitting into families applies to **every** concept that teaches more than one named template, not just DP. Each family below gets the full treatment in §5: recognition cues, a 3-language template, an anchor with a wrong first attempt and a dry-run table, variants, a contrast pair, mistakes and quiz items. Family slugs become `content/patterns/<course>/<concept>/<family>.yaml` and `content/quiz/<course>/<concept>/<family>.yaml`. The 13 existing pattern packs are kept and counted where they fit.

**Programming from Zero (29 concepts, ~70 families)**

| Concept | Families |
|---|---|
| how-code-runs | compile-vs-interpret, error-types |
| programs-and-output | print-separators, formatted-output |
| variables-and-types | overflow-and-ranges, type-conversion, float-precision, chars-as-numbers |
| input-and-arithmetic | read-one-line, read-n-values, read-until-eof, test-case-loop |
| operators-and-expressions | division-and-modulo, precedence, compound-and-increment, short-circuit, math-library |
| conditionals | if-chains, switch-match, classification-problems |
| boolean-logic | de-morgan, truthiness, guard-clauses |
| while-loops / for-loops | counter, accumulator *(existing pack)*, running-extreme, search-and-stop, flag-loop |
| nested-loops | dependent-inner-loop, iteration-count |
| pattern-printing | solid-and-hollow, triangles, pyramids-and-diamonds, number-and-alphabet, symmetric (butterfly, crown) |
| math-on-numbers | digit-extraction, digit-properties (Armstrong/perfect/strong), divisors-sqrt, primality, gcd-euclid, iterative-sequences |
| number-systems | base-conversion, bit-operators, bit-tricks |
| lists | traverse-and-filter *(existing)*, in-place-shift (rotate/move zeros), sorted-merge, frequency-by-loop, copy-vs-alias |
| strings | frequency-count *(existing)*, reverse-and-palindrome, split-join-build, anagram-check, prefix-and-rotation |
| maps | frequency-map, set-operations, grouping |
| grids | row-col-diagonal, transpose-rotate, spiral, direction-arrays |
| functions | decompose, pass-by-reference-effects, overloading-defaults |
| scope-and-mutation / memory-and-references | shadowing, alias-mutation, shallow-vs-deep-copy |
| recursion | print-ranges, functional-recursion, recursion-on-arrays |
| searching-and-sorting | linear-search, iterative-binary-search, simple-sorts, key-sort |
| complexity-intuition | count-operations, constraint-budget |
| debugging / problem-solving | trace-table, edge-case-checklist, brute-force-checker |
| classes-and-objects | encapsulation, inheritance-override, polymorphism, equality-and-hash |
| exceptions / files-and-modules / standard-library | try-catch-finally, input-validation, read-process-write, collections-toolkit (per language) |

**DSA for Interviews (46 concepts, ~190 families)**

| Concept | Families |
|---|---|
| complexity | loop-analysis, recurrence-tree, amortised, constraint-table |
| arrays-hashing (Arrays) | in-place-manipulation, kadane, dutch-flag, boyer-moore, next-permutation, leaders-suffix-max, rearrangement, cyclic-sort |
| hashing | complement-lookup, group-by-key, prefix-sum-hashmap, set-sequences |
| prefix-sums | range-sum-1d, prefix-2d, difference-array, prefix-suffix |
| two-pointers | opposite-ends, k-sum, read-write, fast-slow, merge-two-arrays |
| sliding-window | fixed-size, variable-size *(existing)*, at-most-k-distinct *(existing)*, shortest-valid, exactly-k |
| stacks | implement-stack-queue, balanced-brackets, min-stack, expression-evaluation |
| monotonic-stack | next-greater-family, span-and-temperatures, histogram-area, contribution-technique, monotonic-deque |
| binary-search | lower-upper-bound *(existing)*, rotated-array, parity-and-peak, real-root |
| binary-search-on-answer | answer-monotonic-predicate *(existing)*, min-max-split, max-min-distance, kth-of-two-sorted |
| binary-search-2d | staircase, flattened-matrix, row-search |
| sorting | merge-sort, quick-sort, counting-radix, comparator-sort, merge-sort-counting, quickselect |
| intervals | merge-insert, intersection, rooms, line-sweep |
| greedy | interval-scheduling, sort-then-pick, reach-jump, local-balance |
| linked-lists | basic-ops, reversal, fast-slow-list, merge-lists, rearrange, random-pointer-flatten |
| recursion-patterns | pick-not-pick, string-generation, recursive-stack-ops, divide-reduce (Hanoi, Josephus, k-th symbol), fast-power |
| backtracking | subsets, combinations, permutations, partitioning, board-search |
| binary-trees | dfs-orders, iterative-traversal, bfs-levels, size-and-height |
| tree-patterns | return-info-from-children, views-and-columns, root-paths, lca-binary-tree, distance-k, width-and-indexing |
| tree-construction | from-two-traversals, serialize |
| bst | search-insert-delete, validate-and-order, successor-iterator, bst-construction |
| heaps | heap-implementation, top-k *(existing)*, two-heaps, k-way-merge, heap-scheduling |
| tries | basic-trie, counting-trie, trie-backtracking, bitwise-trie |
| graph-traversal | bfs-dfs-components, grid-flood, multi-source-bfs, bipartite, cycle-detection, implicit-graph |
| topological-sort | kahn, dfs-topo, ordering-constraints |
| shortest-paths | bfs-unweighted, dijkstra, dijkstra-variants, bellman-ford, floyd-warshall, zero-one-bfs |
| union-find | dsu-template, dsu-applications, kruskal, prim |
| dp-introduction | fibonacci-four-ways, identify-dp, reconstruct-choice |
| dp-1d | climbing-stairs, house-robber, string-split |
| dp-2d | grid-paths, variable-start-end, two-walkers |
| knapsack-01 | knapsack-01, subset-sum, partition-difference, count-subsets, two-capacity |
| knapsack-unbounded | unbounded-knapsack, coin-change-min, combinations-vs-permutations (existing `dsa:dp-1d/unbounded-coin-change` linked) |
| dp-lcs | lcs, longest-common-substring, supersequence, palindromic-subsequence, subsequence-match |
| dp-edit-distance | edit-distance, distinct-subsequences, wildcard-regex, interleaving, palindromic-substrings |
| dp-stocks | stock-state-machine |
| dp-lis | lis-quadratic, lis-patience, lis-variants |
| dp-partition | mcm, cut-or-burst, boolean-ways, front-partition |
| dp-squares | maximal-square, histogram-rectangle |
| dp-on-trees | rob-or-skip, path-through-node, cover-states |
| dp-advanced-patterns | bitmask-subsets, game-minimax, state-machine-count, digit-dp-intro |
| bit-manipulation | bit-ops, xor-tricks, single-number-family, mask-enumeration |
| interview-math | sieve-and-factor, mod-power, ncr-catalan, random-sampling |
| string-algorithms | string-manipulation, rabin-karp, kmp-lps, z-function |
| design-data-structures | lru-lfu, design-with-hashing, design-with-ordering, iterator-design |
| advanced-data-structures | fenwick-intro, segment-tree-intro, ordered-set |
| interview-skills | umpire-walkthrough, pattern-identification |

**Competitive Programming (50 concepts, ~150 families)**

| Concept | Families |
|---|---|
| fast-io | cpp-template, multi-test-reset, overflow-guards, verdict-debugging |
| stress-testing | brute-gen-checker, sanitizers |
| simulation | grid-simulation, casework |
| ad-hoc | small-cases, invariants, parity-pigeonhole, work-backwards |
| constructive | alternating, extremes-first, permutation-build, grow-from-base |
| math-basics | divisibility-gcd, floor-ceil, sums-and-ap |
| stl-mastery | ordered-containers, coordinate-compression, pbds |
| complete-search | subset-enumeration *(existing)*, permutation-search, pruned-search, meet-in-the-middle |
| prefix-difference | difference-array *(existing)*, prefix-2d-cp, prefix-counts-map, ap-on-ranges |
| two-pointers-cp | monotone-segments, two-arrays-count |
| binary-search-answer | integer-answer, real-answer, kth-by-counting, average-median-transform, ternary-search |
| greedy-cp | exchange-key, regret-heap, deadline-scheduling, bitwise-greedy |
| number-theory | sieve, spf-factorisation, divisor-functions, harmonic-loops |
| modular-arithmetic | fast-power *(existing)*, modular-inverse, extended-euclid |
| combinatorics | ncr-factorials, stars-and-bars, inclusion-exclusion, contribution |
| bitmasks | xor-properties, per-bit-contribution, builtins-bitset |
| graph-techniques | bfs-dfs-cp, tree-basics, functional-graph, state-space-bfs |
| shortest-paths-cp | dijkstra-with-state, count-and-reconstruct, zero-one-bfs, negative-cycles |
| mst | kruskal-cp, mst-properties |
| dsu-advanced | dsu-with-data, offline-reverse, parity-dsu |
| dag-dp | longest-path, count-paths, game-on-dag |
| scc / bridges-articulation / euler-path | kosaraju-tarjan, condensation-dp, two-sat, low-link, hierholzer |
| dp-classics | selection-state, knapsack-swap-dimension, lcs-reconstruct, grid-dp, projects-dp |
| dp-counting | ordered-vs-unordered, prefix-sum-transitions, profile-counting |
| interval-dp | merge-interval, removal-game |
| bitmask-dp | tsp-hamiltonian, assignment, submask-enumeration, sos |
| digit-dp | digit-state |
| dp-data-structures | lis-bit, range-transition-segtree, deque-window |
| dp-optimisations | cht, divide-conquer, knuth |
| fenwick-tree | point-range, range-point, two-bits, order-statistics, offline-queries |
| sparse-table | idempotent-rmq |
| segment-tree | point-update-range-query, custom-merge-node |
| lazy-segment-tree | range-add, range-assign, segment-walk |
| sqrt-decomposition | blocks, mos |
| tree-techniques | subtree-dp, tree-matching, small-to-large |
| lca | binary-lifting, euler-rmq, path-queries |
| rerooting | reroot-sum, reroot-max |
| euler-tour | subtree-as-range |
| string-hashing / kmp / z-function | polynomial-hash, hash-binary-search, prefix-function, kmp-automaton, z-matching, manacher |
| number-theory-2 | crt, euler-theorem, coprime-counting, mobius |
| expected-value / advanced-counting | linearity-indicators, expectation-dp, modular-probability, obstacle-paths, bijections |
| game-theory | win-lose-dp, nim, sprague-grundy |
| matrix-exponentiation | linear-recurrence, walks-of-length-k |
| geometry | cross-orientation, segment-intersection, polygon-area, convex-hull |
| contest-craft | interactive, technique-from-constraints |

**About 410 families in total**, against the syllabus's estimate of ~350. Phases 2–7 author these concept by concept in Appendix B order. Each phase report lists families done, and families still waiting, per concept. Decision B decides which families become full CI-linted pattern packs.

## 5. How one concept is authored (Phases 2–7)

1. **Lesson** (`concept.lesson`). Each pattern family is one `##` section following syllabus §0.2:
   - recognition cues;
   - a template in all three languages;
   - the anchor: brute force → a wrong first attempt and why it fails → optimal, with a dry-run table;
   - variants (1 line each, pointing to the pattern ladder);
   - the contrast pair;
   - common mistakes.
   
   DP anchors show recursion → memoization → tabulation → space optimisation.
2. **Code check.** Every snippet goes into the scratchpad and runs (`python`, `g++ -std=c++20`, `javac`/`java`) on the dry-run input, and the output must match the table before the YAML is written.
3. **Per family.** A pattern file (templates also run by `lint_patterns.py`) whose variants are mapped only to ids found in `problems.jsonl`, plus a quiz family (trace / output_prediction / classify / bug_spot) and one contrast card with its misconception id. Atoms and item counts are per decision B.
4. **Concept quiz** (≤10 items): placement/check items for the concept as a whole.
5. **Unseen check.** Two variant problems per family are marked held-out (never linked from the lesson text); a native problem is added only when no external problem fits.
6. **Resources.** Only URLs I fetch and confirm. Unverified gaps are listed in the report (decision A covers the schema minimum of 2).
7. **Gate.** Run `build.py`, `validate_atoms.py`, `validate_quiz.py` (writes the manifest), `lint_patterns.py`, `validate_problems.py <new ids>` and `pytest`. Then commit `content(<course>): <concept-id>: <summary>`.

## 5a. Standards settled during Phase 2 (apply to every later concept)

- **Main family** of each concept: a full pattern pack at the CI bar, plus a quiz generator in `content/quiz/generators/`, so its items come from executed code and are verified in all three languages. New mutation defects go into `content/quiz/defects.yaml`.
- **Secondary families:** a static quiz family with at least 3 items, every distractor tagged with a misconception, and no pattern. These stay unreviewed, so they're practice-only and never count as mastery evidence. `test_quizbank` enforces this split.
- **Two held-out native judge problems per concept.** The planner only schedules native problems, and the syllabus's unseen check needs problems that can be judged. They are original, never shown in the lesson, and each changes one thing from the families taught. Each must pass every `validate_problems.py` gate: examples, brute force, timing, C++/Java references, originality, difficulty.
- **Every live concept needs an entry in `content/learning-resources.json`.** Reuse an existing concept's already-recorded links; never add an unverified URL.
- **Lessons end with** "Worked walkthrough", "Why this works", "Boundary cases and cost" and "Check your understanding". `test_learning_scope` enforces these for every concept. For Zero, the cost heading is "Things to watch for".
- **Every new misconception id must be used** by a quiz item, distractor, pitfall or micro atom (`test_quiz_generators`).
- **Gates that caught authoring slips:** concept quiz item ids are unique across a whole module (`test_gates`); pattern templates are at most 25 lines per language; one generated judge test is at most 2 000 000 characters; YAML options such as `No`, `false` or `6` must be quoted so they stay strings.
- **New resource URLs** are confirmed with an HTTP 200 and a matching page title before use.

### Phase 2 status (DSA dynamic-programming module)

Live, the whole module: `dp-introduction`, `knapsack-01`, `knapsack-unbounded`, `dp-lcs`, `dp-edit-distance`, `dp-stocks`, `dp-lis`, `dp-partition`, `dp-squares`, `dp-on-trees`, `dp-advanced-patterns`.

Pulled forward from Phase 3 to unblock `dp-squares` and `dp-on-trees`: `monotonic-stack` (D11b) and `tree-patterns` (D16b) are live, and the deferred edge `dsa:bst` ← `tree-patterns` is in place. Phase 3 skips them.

`monotonic-stack` now sits among the DSA course's first ten concepts. The starter-pack test (`test_learning_sessions`) therefore checks only the pre-expansion concepts in that range; new concepts carry draft pattern packs, and a released concept pack needs a human review record.

### Core subset status (24 Oct 2026)

Scope was narrowed to the seven concepts with no live coverage that interviews and beginners need most. All seven are live, each at the §5a standard: one full pattern pack with a generator, static families for the rest, and two held-out judge problems.

| Course | Live | Main family (generator) |
|---|---|---|
| DSA | `hashing` | prefix-sum-hashmap (`longest_sum_k`) |
| DSA | `binary-search-on-answer` | min-max-split (`min_max_split`) |
| DSA | `recursion-patterns` | pick-not-pick (`pick_not_pick`) |
| DSA | `design-data-structures` | lru-lfu (`lru_behaviour`) |
| Zero | `operators-and-expressions` | division-and-modulo (`split_units`) |
| Zero | `math-on-numbers` | divisors-sqrt (`divisor_pairs`) |
| Zero | `searching-and-sorting` | simple-sorts (`bubble_passes`) |

Deferred edges now in place: `dsa:sliding-window` ← `hashing`, `dsa:backtracking` ← `recursion-patterns`, `zero:boolean-logic` ← `operators-and-expressions`.

Two code changes came with them:
- **Pattern planner.** It gated patterns only by module locks, so a pattern pack early in an unlocked module (hashing, operators-and-expressions) would have jumped ahead of the concepts it builds on. A pattern now also waits for its same-course prerequisites to be mastered or placed as known (`learn/pattern_sessions.py`).
- **Tests.** The starter-pack test checks the first ten pre-expansion concepts, and the library-scope test counts Zero's live concepts instead of a fixed 18.

Still drafts, by decision (not blocked): the other 44 concepts. These are DSA `binary-search-2d`, `tree-construction`, `interview-math`, `string-algorithms`, `advanced-data-structures` and `interview-skills`; Zero `how-code-runs`, `pattern-printing`, `number-systems`, `memory-and-references`, `complexity-intuition`, `exceptions`, `files-and-modules` and `standard-library`; and all 30 CP drafts. Drafts are never served. The deferred edges `zero:programs-and-output` ← `how-code-runs` and `cp:number-theory` ← `math-basics` wait with them.

Not fixed here: `mypy services/api/src` reports one error in `learn/views.py:344`, already present before this work.

## 6. Decisions I need from you before Phase 1

**A. Stubs can't be valid and can't be hidden today.** `Concept` requires ≥2 resources, ≥2 quiz items, ≥2 key points and a 200-character lesson. Any concept in `course.yaml` is immediately in learners' paths, placement and plans. The options:
1. *(Recommended)* Add `status: draft | live` to `Concept`, default `live`. A draft relaxes the resource and quiz minimums, and is left out of course paths, placement and planning until it's flipped to live (registry plus `course_concepts`, with tests). Stubs can then merge safely, and each concept goes live in its own commit.
2. Keep all stubs on this branch and don't merge until each module is authored. Stubs would carry 2 real resources and 2 placeholder quiz items to satisfy the schema, and those placeholders would be live if merged early.

**B. Per-family bar.** CI lint requires, for every pattern file:
- 5–7 variants;
- 5 draft atoms;
- a quiz family of ≥12 items over ≥4 bands.

Your brief asks for ≥3 quiz items and 3–8 variants. With about 350 families, the CI bar is roughly 4× the quiz work. The options:
1. Every family is a full pattern pack at the CI bar (slowest, most consistent).
2. *(Recommended)* Full packs only for each concept's anchor family. Secondary families live as lesson sections plus a pattern-less quiz family of ≥3 items (pattern-less families aren't linted by `lint_patterns.py`), with their variant mappings in `practice_links` (max 10 per concept).
3. Add a tiered lint (code change).

**C. Concept quiz cap.** `Concept.quiz` holds at most 10 items, so the per-family items go into `content/quiz/…` families, not the concept file. That's assumed in §5; flagging it so it's no surprise.

**D. Split directions that differ from "existing id keeps the first part":**
- `cp:number-theory` already teaches sieve and divisors (and its problems are sieve problems), so it stays C1.6, and C0.6 becomes the new `math-basics`.
- `zero:input-and-arithmetic` already holds input plus basic arithmetic, so the new `operators-and-expressions` comes *after* it, although the syllabus orders Z3 before Z4.
- `how-code-runs` becomes the first Zero concept, which adds a prerequisite to `programs-and-output`.

**E. Z23 mini-projects** become `content/projects/zero/*.yaml` (the project schema exists, 0 projects today) instead of a concept, because they have no quiz or mastery semantics.

**F. Regenerating the status report** uses the git-ignored `.cache/generate_content_inventory.py` (see §1). Keep it there, or move it into `scripts/content/`?

## 7. Where I think the syllabus needs a correction (not changed)

- **C1.10 anchors are AtCoder DP A–Z, but `problems.jsonl` has no AtCoder ids** (only LeetCode, Codeforces, CSES), and pattern external ids allow only `leetcode`/`cf`/`cses`. AtCoder families will map to CSES/Codeforces equivalents, or get a native problem, never an invented id.
- **Overlaps:**
  - the C1.10 anchors Stones, Deque, Slimes, Coins and Sushi are interval/game/probability DP, which C2.10 and C2.7 cover again; I put them in `interval-dp` and `expected-value`;
  - D19.12 bitmask DP duplicates CP C2.10;
  - D24 repeats D11a's min stack / queue-from-stacks;
  - D5 and D11b both list sliding-window maximum.
  
  Each is taught once, with a cross-link.
- **D18d calls MST "NEW to DSA"** while `cp:mst` exists. DSA teaches it inside `union-find`, and `cp:mst` keeps its contest depth.
- **Practice is thin for some Zero families:** pattern printing, Armstrong/strong numbers, files and exceptions have almost no LeetCode/Codeforces/CSES equivalents. They'll need native problems, which is allowed when no good external mapping exists.
- **D3 vs D5:** the "sliding window fails with negatives → prefix sum + hashmap" contrast already exists as `pattern-window-vs-prefix-sums`, so I'll reuse it.

## 8. Checked so far

- 75 of 75 DP family ids I sampled (D19.1–D19.12 anchors and variants) exist in `problems.jsonl`.
- Things currently attached to concepts that will narrow: `dsa:dp-1d` has the `unbounded-coin-change` pattern and the `min-coins` problem (a D19.4 family); `dsa:dp-2d` has `lcs-length` (D19.5); `dsa:stacks` has `next-greater` and `next-taller-building` (D11b); `dsa:backtracking` has `subset-sum-count` (D9/D19.3). These stay where they are (§3), and the new concepts' lessons link to them.
