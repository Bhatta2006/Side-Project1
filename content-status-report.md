# Socrat: current content status and complete inventory

**Snapshot:** 2026-10-24T17:30:25+05:30 (Asia/Calcutta). **Branch:** `content/syllabus-expansion`. **Inspected commit:** `f972ef4111a1fbffa3c8f359aaa5cb685eb53f05`.

This report inventories the checked-out repository and its existing generated test cache. It does not measure a deployed production database, student-generated content, private uploads or external websites. Counts below come from files and the executable catalog schema, not older roadmap totals. No course content was edited or downloaded for this audit.

The companion [complete CSV inventory](<D:/Socrat/content-inventory.csv>) contains **18,092 records**, including every external problem, implementation link, local lesson/quiz/problem/atom, lesson section, book reference, additional resource and company index. These are different record types and include nested sections and link mappings; **do not treat their combined row count as a number of independent lessons**.

## 1. What actually exists

| Layer | Quantity | What the quantity means |
| --- | --- | --- |
| Courses | 3 | Programming from Zero; DSA for Interviews; Competitive Programming |
| Modules / subject areas | 20 | Authored groups inside courses |
| Concepts / taught topics | 81 | One local YAML lesson per concept |
| Lesson sections / subtopics | 1240 | Actual Markdown headings, including recurring walkthrough/check headings; not separate lesson files |
| Lesson text size | 124,773 whitespace words | Includes code/Markdown tokens; not a pure-prose reading-time estimate |
| Prerequisite edges | 131 | Includes cross-course bridges |
| Local concept quiz items | 455 | One reusable bank; not an additional bank per placement/review/assessment mode |
| Local judge problems | 152 | Full statements, examples, hints, Python references and generators stored locally |
| Generated judge test cases | 1778 | Cached cases for the 152 problems, not new exercises |
| Released teaching-atom packs | 30 | 30 of 81 concepts; all have recorded release/review metadata |
| Teaching-atom instances | 279 | 279 instances; repeated/template bodies occur across packs |
| Checks inside atoms | 107 | Separate authored interactive steps, not added to the 455 concept-quiz count |
| Curated course-resource mappings | 274 | 165 exact unique URLs; external links, not stored articles/videos |
| Authored external practice mappings | 310 | 267 exact unique URLs; can overlap the imported practice index |
| Imported external problem records | 13889 | Metadata/links only; no local statement/editorial/solution corpus |
| Reference implementation links | 538 | TheAlgorithms links; not 538 locally stored code lessons |
| Company groups | 637 | Company/problem frequency metadata, not company-authored courses |
| Company/problem associations | 16933 | Many-to-many; not extra distinct problems |
| Additional roadmap-link mappings | 132 | Developer Roadmap metadata/links |
| Additional Python exercise mappings | 35 | Links/guidance; external exercise text not stored here |
| Handbook references | 47 | One externally linked book, mapped to 39 concepts |
| Controlled misconception IDs | 338 | Repair taxonomy, not standalone lessons |
| Problem drafts in content/drafts | 0 | Directory currently has its workflow README only |

**Hierarchy used in this report:** course → authored module (subject area) → concept (topic) → lesson heading (subtopic/section). The current schema does not define a separate universal subject/subtopic taxonomy. Python, C++ and Java are supported languages of the same courses; they are not three copies of each curriculum. Course prose is English; no separate translated course tree is present.

**Important distinction:** the active catalog has 152 locally judgeable authored problems and 13,889 external problem links. The links expand practice selection, but do not supply 13,889 local explanations, answer keys, hidden-test suites or independently calibrated assessment items.

## 2. Course totals and quantity definitions

| Course | Version | Modules | Concepts | Lesson words | Quiz items | Local problems | Atoms | Atom-pack coverage | External unique mapped | External primary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Programming from Zero | 1.0.1 | 5 | 21 | 22023 | 126 | 45 | 93 | 10/21 | 1523 | 329 |
| DSA for Interviews | 1.0.0 | 8 | 40 | 91083 | 250 | 79 | 93 | 10/40 | 6268 | 4575 |
| Competitive Programming | 1.0.0 | 7 | 20 | 11667 | 79 | 28 | 93 | 10/20 | 11287 | 8985 |

`External unique mapped` counts a problem once within that course if any of its up-to-three concept mappings belongs to the course. `External primary` uses only its first concept and partitions the global bank. External counts across concepts/modules/courses overlap; their sum is not the unique global count. Local problem totals use unique IDs; one concept (`zero:scope-and-mutation`) has no linked native problem.

| Course | Owned estimated learning minutes | Full prerequisite closure | Cross-course concepts in closure | Language support |
| --- | --- | --- | --- | --- |
| Programming from Zero | 915 | 21 | none | python, cpp, java |
| DSA for Interviews | 2545 | 57 | zero: 17 | python, cpp, java |
| Competitive Programming | 1045 | 57 | dsa: 20, zero: 17 | python, cpp, java |

Estimated learning minutes are authored concept estimates that include learning/practice intent. They are not measured completion times or the runtime planner's promise for any learner. Prerequisite closure adds existing concepts from other courses rather than creating more owned lessons.

### Local text volume by course

| Course | Lesson words | Quiz-prompt words | Native-statement words | Hint words | Solution-approach words | Atom-body words (instances) |
| --- | --- | --- | --- | --- | --- | --- |
| Programming from Zero | 22023 | 1364 | 1932 | 2196 | 1810 | 1913 |
| DSA for Interviews | 91083 | 3206 | 3914 | 4884 | 4368 | 2008 |
| Competitive Programming | 11667 | 944 | 1036 | 1571 | 1033 | 2009 |

These are separate field-level text measurements, not an additive unique-word corpus: atom templates repeat, quizzes can refer to code outside their prompt, and lessons include Markdown/code. Reference/generator code and test input/output bytes are not counted as explanatory prose. Every lesson section below has its own body word count; inclusive counts overlap when headings nest.

## 3. Storage, sources, provenance and current serving behavior

| Content type | Stored where | Stored body or link? | Source / review evidence |
| --- | --- | --- | --- |
| Courses/modules/lessons/quizzes | `content/courses/<course>/course.yaml` and `concepts/*.yaml` | Local curriculum/lesson/code/quiz bodies | No per-lesson/per-quiz author, license or review field in active schema; linked reading is not proof of where the prose originated |
| Native problems | `content/courses/<course>/problems/*.yaml` | Local statements, examples, hints, references/generators | 2/152 have explicit review blocks; the other 150 have no review block in current files, which does not prove whether review happened elsewhere |
| Teaching atoms | `content/atoms/<course>/<concept>.yaml` | Local teaching/check/code bodies | All 30 packs declare original Socrat examples, owner Socrat learning content, status released, review by Owner on 2026-10-13; declarations are recorded evidence, not an independent rights audit |
| Curated reading/video/docs/visualizers | concept.resources | Titles, URLs, type, duration, level/language | Publisher labels exist; item licenses, robots snapshots, fetch timestamps and content hashes do not |
| External practice index | content/practice/problems.jsonl | Titles/URLs/tags/difficulty/ratings/company metadata | Aggregate source manifest has pinned Git revisions for several imports, but no per-record import timestamp or license evidence |
| Company metadata | content/practice/companies.json | Problem ID/frequency/recency associations | Importer reads snehasishroy company CSVs; no verification against employers in this audit |
| Implementation references | content/practice/implementations.jsonl | GitHub code-file links only | TheAlgorithms repository revisions pinned in URLs/manifest; importer describes MIT repos, not per-file proof |
| Book chapters | content/practice/book.json | External PDF/page links only | CC BY-NC-SA 4.0 (linked, not reproduced) (manifest declaration; not verified online) |
| Roadmap/exercise supplements | content/learning-resources.json | Metadata/links plus local short guidance | Roadmap URLs pin a revision; Python exercise links point at mutable master |
| Judge test cache | `.cache/content-tests/<problem>.json` + `.sha256` | Generated input/expected-output cases | 152 current caches match source YAML hashes; correctness was not re-executed in this audit |

The active loader is [services/api/src/socrat/catalog/registry.py](<D:/Socrat/services/api/src/socrat/catalog/registry.py>); authoring contracts are in [services/api/src/socrat/catalog/schema.py](<D:/Socrat/services/api/src/socrat/catalog/schema.py>) and [services/api/src/socrat/catalog/atoms.py](<D:/Socrat/services/api/src/socrat/catalog/atoms.py>). The report treats repository lessons/problems as stored authoring material; it does not infer that they were scraped from their recommended links. No tracked LICENSE/NOTICE file was found by the audit; that absence is not a legal conclusion about ownership.

**What learners can be served by current code:** normal concept views expose local lesson text, key points, pitfalls, native problems, filtered reading and external practice links. Resource ranking picks three preferred entries and returns the ranked list; implementations are filtered by learner language (default up to three), and handbook references are page links. Roadmap links appear in the course roadmap; extra exercises are language-filtered. Released atom packs are used by session composition. A concept without a pack still has its standard lesson and quiz, but the atom composer has no authored atom sequence for it. These are code-path observations, not a live deployment/UI audit.

**Assessment content is reused:** placement/review/checkpoint/assessment services draw from the concept quiz/native problem banks. No separate, independently calibrated unseen assessment corpus was identified. Schema validity and generated test counts do not establish independent-solve calibration or teaching quality.

### 3.1 Curated resource publishers and formats

| Publisher label in YAML | Link mappings | Courses using it |
| --- | --- | --- |
| USACO Guide | 35 | cp, dsa, zero |
| Tech Interview Handbook | 29 | dsa, zero |
| CSES | 29 | cp, dsa |
| NeetCode | 28 | cp, dsa |
| VisuAlgo | 22 | cp, dsa, zero |
| CP-Algorithms | 22 | cp, dsa |
| Antti Laaksonen | 20 | cp, dsa, zero |
| Python docs | 17 | dsa, zero |
| Harvard CS50 | 12 | dsa, zero |
| freeCodeCamp | 12 | cp, dsa, zero |
| Python Tutor | 10 | zero |
| LearnCpp | 9 | zero |
| Oracle | 8 | zero |
| Programming with Mosh | 3 | zero |
| cppreference | 3 | zero |
| Wikipedia | 3 | dsa |
| YouTube | 2 | zero |
| Oracle dev.java | 2 | zero |
| Programiz | 1 | zero |
| Fireship | 1 | dsa |
| Michael Sambol | 1 | dsa |
| CS Dojo | 1 | dsa |
| bigocheatsheet.com | 1 | dsa |
| HackerRank | 1 | dsa |
| WilliamFiset | 1 | dsa |
| Tushar Roy | 1 | cp |

| Resource kind | Mappings |
| --- | --- |
| article | 100 |
| video | 51 |
| visualizer | 32 |
| interactive | 29 |
| docs | 28 |
| book | 20 |
| course | 14 |

Publisher names above are stored labels (for example Oracle and Oracle dev.java remain distinct labels). Repeated links are counted as mappings. No resource was fetched, re-licensed or link-health checked for this report.

### 3.2 Imported-source ledger

| Source | Role | Recorded revision |
| --- | --- | --- |
| [liquidslr](<https://github.com/liquidslr/leetcode-company-wise-problems>) | LeetCode titles/topics/difficulty metadata | `03850eb5d16892514491cf1381c32ec0330a2719` |
| [companywise](<https://github.com/snehasishroy/leetcode-companywise-interview-questions>) | Company problem frequency and recency | `e095c259cfd036e3ddb6886e84d7075c2faac477` |
| [striver](<https://github.com/Codensity30/Strivers-A2Z-DSA-Sheet>) | Title matching to flag A2Z membership; 74 flagged problems, not a full imported A2Z course | `c42ee6ecac700e1171e99d2d3e2b0cb27c2f597d` |
| [thealgorithms-cpp](<https://github.com/TheAlgorithms/C-Plus-Plus>) | 139 C++ implementation links | `fdcc29b0ac2848e9d1a8d926e171cc5b39f97759` |
| [thealgorithms-python](<https://github.com/TheAlgorithms/Python>) | 212 Python implementation links | `215c1f0710f610aaf5ebaeab04edacec3f5308cd` |
| [thealgorithms-java](<https://github.com/TheAlgorithms/Java>) | 187 Java implementation links | `5eb9d6634cfe84b1d53daf83187f8d11eca0bbb8` |

Other recorded import sources: Codeforces problemset API (`https://codeforces.com/api/problemset.problems`), CSES problemset index (`https://cses.fi/problemset/`), and [Developer Roadmap](<https://github.com/nilbuild/developer-roadmap>) at `8e62a35a8c113d9b52267046941b49f52e3f621e`. The exercise source is [zhiwehu/Python-programming-exercises](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md>).

`learning-resources.json` also records `anatomy_revision=e6600ffc4e8e6620eeb45bf49bcdbd5e4b84163f`, but 0 emitted supplement URLs reference that revision and every roadmap entry is labelled Developer Roadmap. Treat it as manifest metadata, not evidence of an additional imported course/book. The source manifest records takeuforward.org as excluded because of its automated-access policy; the A2Z flag comes from the GitHub title source. These are repository declarations, not fresh website/terms checks.

The older practice importer uses tag/section/title/filename rules and up to three concept matches. CSES difficulty uses section/solver heuristics, Codeforces labels use rating thresholds (easy ≤1200, medium ≤1700), and other library rating bands are software mappings. No per-problem pedagogical review, live difficulty calibration, or company-claim verification was found in these records. The practice importer predates Foundry and is not evidence that these links passed Foundry's newer domain/license/robots checks.

## 4. Complete course, module, topic and subtopic breakdown

In course tables, `Native` means concept-linked local judge problems; `EP` is imported external primary matches and `EA` all matches; `Impl P/C/J` counts Python/C++/Java implementation links. Zero means no record in that specific layer, not that the concept has no lesson. Lesson subtopics are actual authored heading labels; recurring pedagogical headings are included. `Own words` counts body text from that heading to the next heading, excluding its title; `Including children` extends to the next same/higher-level heading and can overlap child counts. Resources/quizzes/problems are mapped to concepts, not individual headings, so no per-section resource assignments are invented. All full individual links and local quiz prompts are also indexed in the CSV.

### 4.1 Programming from Zero — `zero`

A patient, practice-first path for complete beginners. You will learn how programs think, write and debug real code in Python, C++ or Java, and build the problem-solving habits every later skill depends on. No prior experience assumed.

**Course file:** [content/courses/zero/course.yaml](<D:/Socrat/content/courses/zero/course.yaml>). **Version:** 1.0.1. **Languages:** python, cpp, java.

| Module / subject area | Topics | Lesson words | Quiz | Native | Atoms | Reading links | External unique mapped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| First steps | 4 | 5182 | 29 | 9 | 30 | 17 | 675 |
| Making decisions and repeating | 6 | 6954 | 40 | 16 | 45 | 21 | 0 |
| Working with data | 4 | 2671 | 24 | 11 | 18 | 17 | 816 |
| Functions and structure | 4 | 5271 | 21 | 6 | 0 | 14 | 44 |
| The programmer's craft | 3 | 1945 | 12 | 3 | 0 | 9 | 0 |

**Topic-level local coverage**

| Concept ID | Topic | Words | Sections | Quiz | Native | Atom pack / atoms | Estimated minutes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| zero:programs-and-output | Programs and output | 723 | 10 | 6 | 2 | released / 9 | 25 |
| zero:variables-and-types | Variables and types | 613 | 9 | 7 | 2 | released / 12 | 35 |
| zero:input-and-arithmetic | Input and arithmetic | 653 | 10 | 7 | 3 | released / 9 | 40 |
| zero:operators-and-expressions | Operators and expressions | 3193 | 40 | 9 | 2 | missing / 0 | 45 |
| zero:conditionals | Making decisions with if | 591 | 9 | 6 | 3 | released / 9 | 40 |
| zero:boolean-logic | Combining conditions | 628 | 10 | 6 | 2 | released / 9 | 35 |
| zero:while-loops | While loops | 664 | 8 | 6 | 3 | released / 9 | 40 |
| zero:for-loops | For loops | 655 | 9 | 6 | 3 | released / 9 | 40 |
| zero:nested-loops | Nested loops | 607 | 9 | 6 | 3 | released / 9 | 40 |
| zero:math-on-numbers | Math on numbers | 3809 | 47 | 10 | 2 | missing / 0 | 60 |
| zero:lists | Lists and arrays | 661 | 8 | 6 | 3 | released / 9 | 50 |
| zero:strings | Strings | 681 | 9 | 6 | 3 | released / 9 | 45 |
| zero:maps | Dictionaries and maps | 600 | 9 | 6 | 3 | missing / 0 | 45 |
| zero:grids | Grids and 2D lists | 729 | 8 | 6 | 2 | missing / 0 | 45 |
| zero:functions | Functions | 722 | 9 | 4 | 2 | missing / 0 | 45 |
| zero:scope-and-mutation | Scope, references and mutation | 695 | 9 | 4 | 0 | missing / 0 | 40 |
| zero:recursion | Recursion | 727 | 9 | 4 | 2 | missing / 0 | 55 |
| zero:searching-and-sorting | Searching and sorting basics | 3127 | 33 | 9 | 2 | missing / 0 | 60 |
| zero:debugging | Debugging calmly | 632 | 10 | 4 | 1 | missing / 0 | 35 |
| zero:problem-solving | Solving unfamiliar problems | 662 | 9 | 4 | 1 | missing / 0 | 45 |
| zero:classes-and-objects | Classes and objects | 651 | 9 | 4 | 1 | missing / 0 | 50 |

**Topic-level external coverage**

| Concept ID | Reading | Authored practice links | EP | EA | Impl P/C/J | Roadmap | Python exercises | Book refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zero:programs-and-output | 5 | 1 | 0 | 0 | 0/0/0 | 3 | 0 | 0 |
| zero:variables-and-types | 4 | 0 | 0 | 0 | 0/0/0 | 3 | 0 | 0 |
| zero:input-and-arithmetic | 4 | 1 | 139 | 675 | 0/0/0 | 6 | 1 | 0 |
| zero:operators-and-expressions | 4 | 7 | 0 | 0 | 0/0/0 | 6 | 0 | 0 |
| zero:conditionals | 4 | 1 | 0 | 0 | 0/0/0 | 3 | 1 | 0 |
| zero:boolean-logic | 3 | 0 | 0 | 0 | 0/0/0 | 3 | 1 | 0 |
| zero:while-loops | 4 | 1 | 0 | 0 | 0/0/0 | 3 | 0 | 0 |
| zero:for-loops | 4 | 1 | 0 | 0 | 0/0/0 | 3 | 1 | 0 |
| zero:nested-loops | 3 | 1 | 0 | 0 | 0/0/0 | 3 | 3 | 0 |
| zero:math-on-numbers | 3 | 8 | 0 | 0 | 0/0/0 | 3 | 0 | 0 |
| zero:lists | 5 | 2 | 0 | 0 | 0/0/0 | 3 | 3 | 0 |
| zero:strings | 4 | 2 | 158 | 610 | 0/0/0 | 2 | 3 | 0 |
| zero:maps | 4 | 2 | 0 | 0 | 0/0/0 | 3 | 2 | 0 |
| zero:grids | 4 | 1 | 24 | 206 | 0/0/0 | 3 | 2 | 0 |
| zero:functions | 4 | 1 | 0 | 0 | 0/0/0 | 3 | 2 | 0 |
| zero:scope-and-mutation | 3 | 0 | 0 | 0 | 0/0/0 | 4 | 1 | 0 |
| zero:recursion | 4 | 1 | 8 | 44 | 0/0/0 | 2 | 2 | 0 |
| zero:searching-and-sorting | 3 | 7 | 0 | 0 | 0/0/0 | 3 | 0 | 0 |
| zero:debugging | 3 | 0 | 0 | 0 | 0/0/0 | 3 | 1 | 0 |
| zero:problem-solving | 3 | 2 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| zero:classes-and-objects | 3 | 0 | 0 | 0 | 0/0/0 | 3 | 1 | 0 |

#### First steps — `first-steps`

What a program is, how it runs, and how it stores and computes values.

##### Programs and output — `zero:programs-and-output`

- **Scope:** A program is a precise list of instructions the computer runs top to bottom. Printing is how it talks back.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/programs-and-output.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/programs-and-output.yaml>)
- **Prerequisites:** none
- **Key points:** A program runs its instructions in order, top to bottom.; Printing shows output; the order of print statements is the order of output.; Quotes make text (a string); without quotes, expressions are calculated.; Comments are ignored by the computer and explain code to people.
- **Pitfalls:** Forgetting the closing quote or bracket — the program will not run at all.; Expecting the computer to "understand what you meant". It does exactly what you wrote.
- **Local judge problems:** [Echo a reading](<D:/Socrat/content/courses/zero/problems/echo-reading.yaml>) (`echo-reading`, easy); [Print a ticket stub](<D:/Socrat/content/courses/zero/problems/ticket-stub.yaml>) (`ticket-stub`, easy)
- **Quiz items:** `order-of-output` (output, difficulty 1/5); `quotes-vs-math` (output, difficulty 1/5); `comment-ignored` (mcq, difficulty 1/5); `precise-instructions` (mcq, difficulty 2/5); `print-sep-end` (output, difficulty 4/5); `print-order` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 92 | 92 |
| Your first program | H2 | 80 | 80 |
| Text versus numbers | H2 | 97 | 97 |
| How Python, C++ and Java differ here | H2 | 74 | 74 |
| Several values in one print | H2 | 74 | 74 |
| Comments | H2 | 24 | 24 |
| Worked walkthrough | H2 | 93 | 251 |
| Worked walkthrough > Why this works | H3 | 41 | 41 |
| Worked walkthrough > Things to watch for | H3 | 44 | 44 |
| Worked walkthrough > Check your understanding | H3 | 60 | 60 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [CS50x Week 0: Computational thinking and Scratch](<https://cs50.harvard.edu/x/2024/weeks/0/>) | Harvard CS50 | course / intro | 90 | neutral |
| [An Informal Introduction to Python](<https://docs.python.org/3/tutorial/introduction.html>) | Python docs | docs / core | 20 | python |
| [Learn C++: Introduction to objects and variables (start of the tutorial)](<https://www.learncpp.com/cpp-tutorial/introduction-to-objects-and-variables/>) | LearnCpp | article / core | 15 | cpp |
| [Learn Java on dev.java](<https://dev.java/learn/>) | Oracle dev.java | course / core | 30 | java |
| [Learn Python – Full Course for Beginners](<https://www.youtube.com/watch?v=rfscVS0vtbw>) | freeCodeCamp | video / intro | 270 | python |

**Other authored/supplemental links**

- Practice — [Hello World (try printing different messages)](<https://pythontutor.com/>) (Python Tutor, easy)
- Roadmap — [Basic Syntax](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/basic-syntax@6xRncUs3_vxVbDur567QA.md>)
- Roadmap — [Running Your First Program](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/running-your-first-program@SEq0D2Zg5WTsIDtd1hW9f.md>)
- Roadmap — [Lifecycle Of A Program](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/lifecycle-of-a-program@QgWalJLIb6Fw0HhN1wb02.md>)

##### Variables and types — `zero:variables-and-types`

- **Scope:** Variables are named boxes that hold values; every value has a type that decides what you can do with it.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/variables-and-types.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/variables-and-types.yaml>)
- **Prerequisites:** `zero:programs-and-output`
- **Key points:** A variable is a named place that stores one value at a time.; `=` evaluates the right side, then stores the result on the left.; Every value has a type (whole number, decimal, text, true/false).; C++ and Java require declaring a variable's type; Python infers it.; Trace code by tracking each variable's value line by line.
- **Pitfalls:** Reading `x = x + 1` as a false equation instead of an update.; Using a variable before giving it a value.; Mixing text and numbers without converting (e.g. "5" + 3).
- **Local judge problems:** [One more visitor](<D:/Socrat/content/courses/zero/problems/next-counter.yaml>) (`next-counter`, easy); [Celsius to Fahrenheit](<D:/Socrat/content/courses/zero/problems/temperature-converter.yaml>) (`temperature-converter`, easy)
- **Quiz items:** `reassign` (output, difficulty 1/5); `swap-trace` (output, difficulty 2/5); `type-of-text` (mcq, difficulty 1/5); `declared-type` (mcq, difficulty 1/5); `equals-meaning` (mcq, difficulty 1/5); `int-division-types` (mcq, difficulty 4/5); `rebinding` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral); `trace` (trace, 1 checks, adapters python,cpp,java); `predict` (predict, 1 checks, adapters python,cpp,java); `debug` (debug, 1 checks, adapters python,cpp,java)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 80 | 80 |
| `=` means "store", not "equals" | H2 | 120 | 120 |
| Types | H2 | 101 | 101 |
| Naming | H2 | 27 | 27 |
| Tracing | H2 | 42 | 42 |
| Worked walkthrough | H2 | 70 | 224 |
| Worked walkthrough > Why this works | H3 | 37 | 37 |
| Worked walkthrough > Things to watch for | H3 | 50 | 50 |
| Worked walkthrough > Check your understanding | H3 | 54 | 54 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Python Tutor – watch variables change step by step](<https://pythontutor.com/>) | Python Tutor | visualizer / intro | 15 | neutral |
| [Built-in types (numbers, strings, booleans)](<https://docs.python.org/3/library/stdtypes.html>) | Python docs | docs / deep | 20 | python |
| [Learn C++: Introduction to objects and variables](<https://www.learncpp.com/cpp-tutorial/introduction-to-objects-and-variables/>) | LearnCpp | article / core | 15 | cpp |
| [Java Tutorials: Variables](<https://docs.oracle.com/javase/tutorial/java/nutsandbolts/variables.html>) | Oracle | docs / core | 15 | java |

**Other authored/supplemental links**

- Roadmap — [Variables And Data Types](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/variables-and-data-types@dEFLBGpiH6nbSMeR7ecaT.md>)
- Roadmap — [Data Types](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/data-types@MwznA4qfpNlv6sqSNjPZi.md>)
- Roadmap — [Data Types](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/data-types@5g9mmi01WeZ4aDqNzwx_V.md>)

##### Input and arithmetic — `zero:input-and-arithmetic`

- **Scope:** Read values the user gives your program, convert them to numbers, and compute with + - * / and remainder.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/input-and-arithmetic.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/input-and-arithmetic.yaml>)
- **Prerequisites:** `zero:variables-and-types`
- **Key points:** Input arrives as text; convert it before doing arithmetic.; Whole-number division: `//` in Python, `/` between ints in C++ and Java.; `%` gives the remainder: great for even/odd, last digit and unit conversions.; Multiplication and division happen before addition and subtraction.
- **Pitfalls:** Forgetting to convert input in Python, then adding text instead of numbers.; Using `/` in Python when you wanted a whole number.; Integer overflow in C++/Java when results exceed about 2.1 billion.
- **Local judge problems:** [Personal greeting](<D:/Socrat/content/courses/zero/problems/greeting.yaml>) (`greeting`, easy); [Minutes to hours](<D:/Socrat/content/courses/zero/problems/time-convert.yaml>) (`time-convert`, easy); [Split the bill](<D:/Socrat/content/courses/zero/problems/split-the-bill.yaml>) (`split-the-bill`, easy)
- **Quiz items:** `int-division` (output, difficulty 1/5); `precedence` (output, difficulty 1/5); `last-digit` (mcq, difficulty 2/5); `input-is-text` (mcq, difficulty 2/5); `even-check` (mcq, difficulty 1/5); `string-plus` (mcq, difficulty 4/5); `negative-mod` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 31 | 31 |
| Reading input | H2 | 144 | 144 |
| Arithmetic | H2 | 124 | 124 |
| Worked example: minutes to hours | H2 | 52 | 52 |
| Order of operations | H2 | 35 | 35 |
| Very large numbers | H2 | 30 | 30 |
| Worked walkthrough | H2 | 65 | 211 |
| Worked walkthrough > Why this works | H3 | 39 | 39 |
| Worked walkthrough > Things to watch for | H3 | 48 | 48 |
| Worked walkthrough > Check your understanding | H3 | 46 | 46 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Input and Output](<https://docs.python.org/3/tutorial/inputoutput.html>) | Python docs | docs / core | 20 | python |
| [Python Tutor – step through arithmetic](<https://pythontutor.com/>) | Python Tutor | visualizer / intro | 10 | neutral |
| [CS50x Week 1: C, types, operators and input](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / core | 120 | cpp |
| [Java Full Course for Beginners](<https://www.youtube.com/watch?v=eIrMbAQSU34>) | Programming with Mosh | video / core | 150 | java |

**Other authored/supplemental links**

- Practice — [Watermelon (even split)](<https://codeforces.com/problemset/problem/4/A>) (Codeforces, easy)
- Roadmap — [Type Casting](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/type-casting@R9DQNc0AyAQ2HLpP4HOk6.md>)
- Roadmap — [Operators](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/operators@so95CO6Qw3I0S98ISENS-.md>)
- Roadmap — [Iostream](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/iostream@VeVxZ230xkesQsIDig8zQ.md>)
- Roadmap — [Arithmetic Operators](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/arithmetic-operators@8aOSpZLWwZv_BEYiurhyR.md>)
- Roadmap — [Io Operations](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/io-operations@M0ybgK1JCycXhZ1dEpCFo.md>)
- Roadmap — [Math Operations](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/math-operations@ziD_XwzJSFQP_3iLjq9pA.md>)
- Python exercise 15 — [Digit-based arithmetic](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-15>)

##### Operators and expressions — `zero:operators-and-expressions`

- **Scope:** Division and modulo in each language, precedence, compound assignment, short-circuit logic and the math library.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/operators-and-expressions.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:input-and-arithmetic`
- **Key points:** `//` counts whole groups and `%` gives what is left over; together they split a quantity into units.; Take each smaller unit from the remainder of the bigger one.; Python rounds negative division down; C++ and Java round towards zero.; `*`, `/`, `//`, `%` run before `+` and `-`; use brackets for averages.; `+=` updates a variable from its old value; `=+` is a different, legal statement.; Put the guard first in an `and`, so the risky test never runs when it would crash.; Prefer whole-number formulas to decimals for big whole answers.
- **Pitfalls:** Taking the minutes from the whole total instead of the remainder.; Writing an average without brackets.; Writing `=+` instead of `+=`.; Putting the zero check after the division.; Trusting the decimal square root for big numbers.
- **Local judge problems:** [Party packs](<D:/Socrat/content/courses/zero/problems/party-packs.yaml>) (`party-packs`, easy); [The clock after a wait](<D:/Socrat/content/courses/zero/problems/clock-after.yaml>) (`clock-after`, easy)
- **Quiz items:** `split-seconds` (mcq, difficulty 1/5); `minutes-from-total` (mcq, difficulty 2/5); `negative-floor` (mcq, difficulty 3/5); `average-brackets` (mcq, difficulty 2/5); `plus-equals` (mcq, difficulty 2/5); `guard-first` (mcq, difficulty 3/5); `round-up` (mcq, difficulty 3/5); `round-up-trap` (mcq, difficulty 4/5); `float-root` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 93 | 93 |
| Division and modulo | H2 | 0 | 1110 |
| Division and modulo > Recognition cues | H3 | 54 | 54 |
| Division and modulo > Template | H3 | 203 | 203 |
| Division and modulo > Anchor problem: 3725 seconds | H3 | 668 | 668 |
| Division and modulo > Variants | H3 | 85 | 85 |
| Division and modulo > Contrast | H3 | 39 | 39 |
| Division and modulo > Common mistakes | H3 | 44 | 44 |
| Precedence | H2 | 0 | 404 |
| Precedence > Recognition cues | H3 | 29 | 29 |
| Precedence > Template | H3 | 122 | 122 |
| Precedence > Anchor problem: average of 4, 5 and 9 | H3 | 114 | 114 |
| Precedence > Variants | H3 | 34 | 34 |
| Precedence > Contrast | H3 | 31 | 31 |
| Precedence > Common mistakes | H3 | 53 | 53 |
| Compound and increment | H2 | 0 | 413 |
| Compound and increment > Recognition cues | H3 | 24 | 24 |
| Compound and increment > Template | H3 | 205 | 205 |
| Compound and increment > Anchor problem: 3 8 5 2 | H3 | 84 | 84 |
| Compound and increment > Variants | H3 | 31 | 31 |
| Compound and increment > Contrast | H3 | 26 | 26 |
| Compound and increment > Common mistakes | H3 | 24 | 24 |
| Short circuit | H2 | 0 | 393 |
| Short circuit > Recognition cues | H3 | 39 | 39 |
| Short circuit > Template | H3 | 148 | 148 |
| Short circuit > Anchor problem: 10 and 0 | H3 | 74 | 74 |
| Short circuit > Variants | H3 | 38 | 38 |
| Short circuit > Contrast | H3 | 39 | 39 |
| Short circuit > Common mistakes | H3 | 37 | 37 |
| Math library | H2 | 0 | 471 |
| Math library > Recognition cues | H3 | 23 | 23 |
| Math library > Template | H3 | 234 | 234 |
| Math library > Anchor problem: rounding up and a big square root | H3 | 83 | 83 |
| Math library > Variants | H3 | 30 | 30 |
| Math library > Contrast | H3 | 42 | 42 |
| Math library > Common mistakes | H3 | 37 | 37 |
| Worked walkthrough | H2 | 82 | 286 |
| Worked walkthrough > Why this works | H3 | 92 | 92 |
| Worked walkthrough > Things to watch for | H3 | 44 | 44 |
| Worked walkthrough > Check your understanding | H3 | 55 | 55 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Python Tutor – step through arithmetic](<https://pythontutor.com/>) | Python Tutor | visualizer / intro | 10 | neutral |
| [Input and Output](<https://docs.python.org/3/tutorial/inputoutput.html>) | Python docs | docs / core | 20 | python |
| [CS50x Week 1: C, types, operators and input](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / core | 120 | cpp |
| [Java Full Course for Beginners](<https://www.youtube.com/watch?v=eIrMbAQSU34>) | Programming with Mosh | video / core | 150 | java |

**Other authored/supplemental links**

- Practice — [Watermelon](<https://codeforces.com/problemset/problem/4/A>) (Codeforces, easy)
- Practice — [Theatre Square](<https://codeforces.com/problemset/problem/1/A>) (Codeforces, easy)
- Practice — [Coins](<https://codeforces.com/problemset/problem/1061/A>) (Codeforces, easy)
- Practice — [Count of Matches in Tournament](<https://leetcode.com/problems/count-of-matches-in-tournament/>) (LeetCode, easy)
- Practice — [Water Bottles](<https://leetcode.com/problems/water-bottles/>) (LeetCode, easy)
- Practice — [Convert the Temperature](<https://leetcode.com/problems/convert-the-temperature/>) (LeetCode, easy)
- Practice — [Count the Digits That Divide a Number](<https://leetcode.com/problems/count-the-digits-that-divide-a-number/>) (LeetCode, easy)
- Roadmap — [Type Casting](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/type-casting@R9DQNc0AyAQ2HLpP4HOk6.md>)
- Roadmap — [Operators](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/operators@so95CO6Qw3I0S98ISENS-.md>)
- Roadmap — [Iostream](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/iostream@VeVxZ230xkesQsIDig8zQ.md>)
- Roadmap — [Arithmetic Operators](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/arithmetic-operators@8aOSpZLWwZv_BEYiurhyR.md>)
- Roadmap — [Io Operations](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/io-operations@M0ybgK1JCycXhZ1dEpCFo.md>)
- Roadmap — [Math Operations](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/math-operations@ziD_XwzJSFQP_3iLjq9pA.md>)

#### Making decisions and repeating — `control-flow`

Branches and loops — the two ideas that make programs powerful.

##### Making decisions with if — `zero:conditionals`

- **Scope:** Use if, else if and else to run different code depending on the situation.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/conditionals.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/conditionals.yaml>)
- **Prerequisites:** `zero:input-and-arithmetic`
- **Key points:** `if` runs a block only when its condition is true.; In an if / else-if / else chain, only the first true branch runs.; `==` compares; `=` assigns.; Test boundary values — exactly at each threshold.
- **Pitfalls:** Writing `=` instead of `==` inside a condition.; Putting a broad condition before a narrow one so the narrow branch never runs.; Forgetting braces (C++/Java) or indentation (Python), so the wrong lines are inside the if.
- **Local judge problems:** [Letter grade](<D:/Socrat/content/courses/zero/problems/grade-letter.yaml>) (`grade-letter`, easy); [Largest of three](<D:/Socrat/content/courses/zero/problems/max-of-three.yaml>) (`max-of-three`, easy); [Museum ticket price](<D:/Socrat/content/courses/zero/problems/museum-ticket.yaml>) (`museum-ticket`, easy)
- **Quiz items:** `first-true-branch` (output, difficulty 2/5); `equals-operator` (mcq, difficulty 1/5); `boundary` (mcq, difficulty 1/5); `else-meaning` (mcq, difficulty 1/5); `elif-order` (output, difficulty 4/5); `dangling-if` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 128 | 128 |
| How the chain is checked | H2 | 55 | 55 |
| Comparison operators | H2 | 54 | 54 |
| Blocks | H2 | 32 | 32 |
| Worked example: the larger of two numbers | H2 | 83 | 83 |
| Worked walkthrough | H2 | 58 | 213 |
| Worked walkthrough > Why this works | H3 | 39 | 39 |
| Worked walkthrough > Things to watch for | H3 | 57 | 57 |
| Worked walkthrough > Check your understanding | H3 | 46 | 46 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [More control flow tools: if statements](<https://docs.python.org/3/tutorial/controlflow.html>) | Python docs | docs / core | 15 | python |
| [Learn C++: If statements and blocks](<https://www.learncpp.com/cpp-tutorial/if-statements-and-blocks/>) | LearnCpp | article / core | 15 | cpp |
| [Java Tutorials: The if-then and if-then-else statements](<https://docs.oracle.com/javase/tutorial/java/nutsandbolts/if.html>) | Oracle | docs / core | 10 | java |
| [CS50x Week 1: Conditionals](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / intro | 120 | neutral |

**Other authored/supplemental links**

- Practice — [Watermelon](<https://codeforces.com/problemset/problem/4/A>) (Codeforces, easy)
- Roadmap — [Conditionals](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/conditionals@NP1kjSk0ujU0Gx-ajNHlR.md>)
- Roadmap — [If Else / Switch / Goto](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/if-else--switch--goto@bjpFWxiCKGz28E-ukhZBp.md>)
- Roadmap — [Conditionals](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/conditionals@sG_3ZQIE1-FQXQkk-OduQ.md>)
- Python exercise 44 — [Recognize accepted strings](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-44>)

##### Combining conditions — `zero:boolean-logic`

- **Scope:** Use and, or and not to express exact rules, and reason about them precisely.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/boolean-logic.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/boolean-logic.yaml>)
- **Prerequisites:** `zero:conditionals`, `zero:operators-and-expressions`
- **Key points:** and/&& needs both sides true; or/\|\| needs at least one; not/! flips.; Express ranges as two comparisons joined by and.; Short-circuiting skips the right side when the answer is already known.; De Morgan: not (A and B) = not A or not B, and vice versa.
- **Pitfalls:** Writing `1 <= x <= 10` in C++ or Java.; Negating a compound condition without flipping and/or.; Writing `x == 1 or 2` instead of `x == 1 or x == 2`.
- **Local judge problems:** [Leap year](<D:/Socrat/content/courses/zero/problems/leap-year.yaml>) (`leap-year`, easy); [Who may join the coding club?](<D:/Socrat/content/courses/zero/problems/club-entry.yaml>) (`club-entry`, easy)
- **Quiz items:** `and-or` (mcq, difficulty 1/5); `de-morgan` (mcq, difficulty 3/5); `range-check` (mcq, difficulty 2/5); `short-circuit` (mcq, difficulty 2/5); `negate-both` (mcq, difficulty 4/5); `guard-first` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 142 | 142 |
| Truth tables | H2 | 31 | 31 |
| Ranges | H2 | 48 | 48 |
| Short-circuiting | H2 | 61 | 61 |
| De Morgan's laws | H2 | 58 | 58 |
| Worked example: leap years | H2 | 54 | 54 |
| Worked walkthrough | H2 | 49 | 211 |
| Worked walkthrough > Why this works | H3 | 40 | 40 |
| Worked walkthrough > Things to watch for | H3 | 53 | 53 |
| Worked walkthrough > Check your understanding | H3 | 56 | 56 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Boolean operations: and, or, not](<https://docs.python.org/3/library/stdtypes.html>) | Python docs | docs / core | 10 | python |
| [CS50x Week 1: Boolean expressions](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / intro | 120 | neutral |
| [Java Tutorials: The if-then and if-then-else statements](<https://docs.oracle.com/javase/tutorial/java/nutsandbolts/if.html>) | Oracle | docs / core | 10 | java |

**Other authored/supplemental links**

- Roadmap — [Operators](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/operators@so95CO6Qw3I0S98ISENS-.md>)
- Roadmap — [Logical Operators](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/logical-operators@Y9gq8WkDA_XGe68JkY2UZ.md>)
- Roadmap — [Conditionals](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/conditionals@sG_3ZQIE1-FQXQkk-OduQ.md>)
- Python exercise 1 — [Divisibility filters](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-1>)

##### While loops — `zero:while-loops`

- **Scope:** Repeat a block for as long as a condition stays true — the tool for "keep going until...".
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/while-loops.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/while-loops.yaml>)
- **Prerequisites:** `zero:boolean-logic`
- **Key points:** while repeats its body as long as the condition is true, checking before each round.; Every loop needs a start, a condition, and progress toward stopping.; Missing progress causes an infinite loop.; The accumulator pattern builds an answer one round at a time.
- **Pitfalls:** Forgetting to update the loop variable (infinite loop).; Off-by-one conditions — `>` versus `>=` changes the number of rounds.; Special input like 0 that skips the loop entirely; make sure the answer is still right.
- **Local judge problems:** [Sum of digits](<D:/Socrat/content/courses/zero/problems/digit-sum.yaml>) (`digit-sum`, easy); [Collatz steps](<D:/Socrat/content/courses/zero/problems/collatz-steps.yaml>) (`collatz-steps`, medium); [Reverse the digits](<D:/Socrat/content/courses/zero/problems/reverse-the-digits.yaml>) (`reverse-the-digits`, easy)
- **Quiz items:** `rounds` (output, difficulty 2/5); `infinite` (mcq, difficulty 1/5); `zero-input` (mcq, difficulty 2/5); `accumulator` (output, difficulty 2/5); `loop-count` (output, difficulty 4/5); `infinite-loop` (bug, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 124 | 124 |
| The three parts of every loop | H2 | 61 | 61 |
| When to use while | H2 | 42 | 42 |
| Worked example: sum of digits | H2 | 187 | 187 |
| Worked walkthrough | H2 | 58 | 225 |
| Worked walkthrough > Why this works | H3 | 43 | 43 |
| Worked walkthrough > Things to watch for | H3 | 50 | 50 |
| Worked walkthrough > Check your understanding | H3 | 61 | 61 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Learn C++: Introduction to loops and while statements](<https://www.learncpp.com/cpp-tutorial/introduction-to-loops-and-while-statements/>) | LearnCpp | article / core | 15 | cpp |
| [Python Tutor – watch a while loop run round by round](<https://pythontutor.com/>) | Python Tutor | visualizer / intro | 10 | neutral |
| [More control flow tools](<https://docs.python.org/3/tutorial/controlflow.html>) | Python docs | docs / core | 15 | python |
| [CS50x Week 1: Loops](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / core | 120 | neutral |

**Other authored/supplemental links**

- Practice — [Weird Algorithm](<https://cses.fi/problemset/task/1068>) (CSES, easy)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/loops@Dvy7BnNzK55qbh_SgOk8m.md>)
- Roadmap — [For / While / Do While Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/for--while--do-while-loops@_IP_e1K9LhNHilYTDh7L5.md>)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/loops@JHUhVEjWFXTn6-wKcKevg.md>)

##### For loops — `zero:for-loops`

- **Scope:** Repeat a block a known number of times, or once for each item — the everyday loop.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/for-loops.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/for-loops.yaml>)
- **Prerequisites:** `zero:while-loops`
- **Key points:** A for loop bundles start, condition and progress for counting loops.; Python's range(a, b) stops before b; C++/Java conditions decide inclusion explicitly.; Use for when the number of rounds is known, while when it is not.; Trace the first and last round to catch off-by-one errors.
- **Pitfalls:** Writing range(1, n) when you meant 1..n inclusive.; Modifying the loop counter inside the body.; Using int for sums that can exceed about 2.1 billion in C++/Java.
- **Local judge problems:** [FizzBuzz](<D:/Socrat/content/courses/zero/problems/fizzbuzz.yaml>) (`fizzbuzz`, easy); [Sum of multiples](<D:/Socrat/content/courses/zero/problems/sum-of-multiples.yaml>) (`sum-of-multiples`, medium); [A times table](<D:/Socrat/content/courses/zero/problems/times-table.yaml>) (`times-table`, easy)
- **Quiz items:** `range-end` (mcq, difficulty 1/5); `count-rounds` (output, difficulty 2/5); `for-vs-while` (mcq, difficulty 1/5); `break-meaning` (mcq, difficulty 1/5); `range-step` (output, difficulty 4/5); `modify-loop-var` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 107 | 107 |
| Reading the header | H2 | 109 | 109 |
| for or while? | H2 | 22 | 22 |
| Worked example: sum of 1 to n | H2 | 125 | 125 |
| Skipping and stopping | H2 | 26 | 26 |
| Worked walkthrough | H2 | 65 | 239 |
| Worked walkthrough > Why this works | H3 | 47 | 47 |
| Worked walkthrough > Things to watch for | H3 | 56 | 56 |
| Worked walkthrough > Check your understanding | H3 | 58 | 58 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Learn C++: For statements](<https://www.learncpp.com/cpp-tutorial/for-statements/>) | LearnCpp | article / core | 15 | cpp |
| [Java Tutorials: The for statement](<https://docs.oracle.com/javase/tutorial/java/nutsandbolts/for.html>) | Oracle | docs / core | 10 | java |
| [for statements and range()](<https://docs.python.org/3/tutorial/controlflow.html>) | Python docs | docs / core | 15 | python |
| [Python Tutor – step through a for loop](<https://pythontutor.com/>) | Python Tutor | visualizer / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Way Too Long Words](<https://codeforces.com/problemset/problem/71/A>) (Codeforces, easy)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/loops@Dvy7BnNzK55qbh_SgOk8m.md>)
- Roadmap — [For / While / Do While Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/for--while--do-while-loops@_IP_e1K9LhNHilYTDh7L5.md>)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/loops@JHUhVEjWFXTn6-wKcKevg.md>)
- Python exercise 1 — [Divisibility filters](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-1>)

##### Nested loops — `zero:nested-loops`

- **Scope:** Put a loop inside a loop to handle rows and columns, pairs, and patterns.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/nested-loops.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/nested-loops.yaml>)
- **Prerequisites:** `zero:for-loops`
- **Key points:** For every outer round, the inner loop runs completely.; Total work is the product of the loop sizes.; Inner bounds may depend on the outer counter (triangles, pairs with i < j).; break exits only the innermost loop.
- **Pitfalls:** Putting the newline inside the inner loop instead of after it.; Reusing the same counter name for both loops.; Not noticing that nested loops over large inputs are slow.
- **Local judge problems:** [Right-aligned staircase](<D:/Socrat/content/courses/zero/problems/staircase.yaml>) (`staircase`, easy); [Pairs that sum to a target](<D:/Socrat/content/courses/zero/problems/pair-count.yaml>) (`pair-count`, medium); [Number triangle](<D:/Socrat/content/courses/zero/problems/number-triangle.yaml>) (`number-triangle`, easy)
- **Quiz items:** `body-count` (mcq, difficulty 1/5); `triangle` (output, difficulty 2/5); `pairs` (mcq, difficulty 2/5); `break-inner` (mcq, difficulty 2/5); `inner-body-runs` (mcq, difficulty 4/5); `break-only-inner` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 145 | 145 |
| Counting the work | H2 | 54 | 54 |
| The inner loop can depend on the outer | H2 | 93 | 93 |
| Pairs | H2 | 40 | 40 |
| Tips | H2 | 34 | 34 |
| Worked walkthrough | H2 | 54 | 217 |
| Worked walkthrough > Why this works | H3 | 33 | 33 |
| Worked walkthrough > Things to watch for | H3 | 63 | 63 |
| Worked walkthrough > Check your understanding | H3 | 54 | 54 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Learn C++: For statements (nested loops section)](<https://www.learncpp.com/cpp-tutorial/for-statements/>) | LearnCpp | article / core | 15 | cpp |
| [Python Tutor – visualize nested loops](<https://pythontutor.com/>) | Python Tutor | visualizer / core | 10 | neutral |
| [CS50x Week 1: Loops and nested loops (Mario)](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / core | 120 | neutral |

**Other authored/supplemental links**

- Practice — [Beautiful Matrix](<https://codeforces.com/problemset/problem/263/A>) (Codeforces, easy)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/loops@Dvy7BnNzK55qbh_SgOk8m.md>)
- Roadmap — [For / While / Do While Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/for--while--do-while-loops@_IP_e1K9LhNHilYTDh7L5.md>)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/loops@JHUhVEjWFXTn6-wKcKevg.md>)
- Python exercise 7 — [Multiplication grid](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-7>)
- Python exercise 12 — [Filter digit patterns](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-12>)
- Python exercise 86 — [Enumerate a Cartesian product](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-86>)

##### Math on numbers — `zero:math-on-numbers`

- **Scope:** Digit tricks with % 10 and // 10, divisors and primes in O(sqrt n), Euclid's GCD and simple sequences.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/math-on-numbers.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:while-loops`, `zero:operators-and-expressions`
- **Key points:** `n % 10` is the last digit and `n // 10` drops it; loop while n > 0.; 0 has one digit, which the loop alone does not count.; Digit rules often need the digit count first, then a second pass.; Divisors pair up as i and n // i, so loop while i · i ≤ n.; A perfect square's root is its own partner; count it once.; A prime is at least 2 and has no divisor from 2 to its square root.; Euclid: gcd(x, y) = gcd(y, x % y); lcm = a // gcd · b.; Update sequence variables from the old values, all at once.
- **Pitfalls:** Stopping digit loops at n > 9.; Hard-coding the power in Armstrong numbers.; Counting the square root of a perfect square twice.; Calling 1 prime.; Overflowing a · b when computing the LCM.; Updating Fibonacci variables one at a time.
- **Local judge problems:** [Number mood](<D:/Socrat/content/courses/zero/problems/number-mood.yaml>) (`number-mood`, easy); [Tiling the floor](<D:/Socrat/content/courses/zero/problems/square-tiles.yaml>) (`square-tiles`, easy)
- **Quiz items:** `digit-count-zero` (mcq, difficulty 1/5); `reverse-trace` (mcq, difficulty 2/5); `armstrong` (mcq, difficulty 2/5); `divisor-pairs` (mcq, difficulty 2/5); `square-root-once` (mcq, difficulty 3/5); `sqrt-cost` (mcq, difficulty 3/5); `prime-one` (mcq, difficulty 3/5); `euclid-step` (mcq, difficulty 4/5); `lcm-order` (mcq, difficulty 4/5); `fib-update` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 81 | 81 |
| Digit extraction | H2 | 0 | 504 |
| Digit extraction > Recognition cues | H3 | 30 | 30 |
| Digit extraction > Template | H3 | 277 | 277 |
| Digit extraction > Anchor problem: 4729 | H3 | 74 | 74 |
| Digit extraction > Variants | H3 | 42 | 42 |
| Digit extraction > Contrast | H3 | 35 | 35 |
| Digit extraction > Common mistakes | H3 | 30 | 30 |
| Digit properties | H2 | 0 | 467 |
| Digit properties > Recognition cues | H3 | 37 | 37 |
| Digit properties > Template | H3 | 255 | 255 |
| Digit properties > Anchor problem: 153 and 1634 | H3 | 62 | 62 |
| Digit properties > Variants | H3 | 32 | 32 |
| Digit properties > Contrast | H3 | 26 | 26 |
| Digit properties > Common mistakes | H3 | 37 | 37 |
| Divisors up to the square root | H2 | 0 | 1096 |
| Divisors up to the square root > Recognition cues | H3 | 37 | 37 |
| Divisors up to the square root > Template | H3 | 265 | 265 |
| Divisors up to the square root > Anchor problem: the divisors of 36 | H3 | 607 | 607 |
| Divisors up to the square root > Variants | H3 | 72 | 72 |
| Divisors up to the square root > Contrast | H3 | 37 | 37 |
| Divisors up to the square root > Common mistakes | H3 | 59 | 59 |
| Primality | H2 | 0 | 458 |
| Primality > Recognition cues | H3 | 25 | 25 |
| Primality > Template | H3 | 236 | 236 |
| Primality > Anchor problem: 97 and 1 | H3 | 75 | 75 |
| Primality > Variants | H3 | 46 | 46 |
| Primality > Contrast | H3 | 29 | 29 |
| Primality > Common mistakes | H3 | 29 | 29 |
| Euclid's GCD | H2 | 0 | 462 |
| Euclid's GCD > Recognition cues | H3 | 26 | 26 |
| Euclid's GCD > Template | H3 | 217 | 217 |
| Euclid's GCD > Anchor problem: 12 and 18 | H3 | 99 | 99 |
| Euclid's GCD > Variants | H3 | 37 | 37 |
| Euclid's GCD > Contrast | H3 | 28 | 28 |
| Euclid's GCD > Common mistakes | H3 | 37 | 37 |
| Iterative sequences | H2 | 0 | 408 |
| Iterative sequences > Recognition cues | H3 | 31 | 31 |
| Iterative sequences > Template | H3 | 194 | 194 |
| Iterative sequences > Anchor problem: seven terms | H3 | 69 | 69 |
| Iterative sequences > Variants | H3 | 29 | 29 |
| Iterative sequences > Contrast | H3 | 35 | 35 |
| Iterative sequences > Common mistakes | H3 | 33 | 33 |
| Worked walkthrough | H2 | 68 | 305 |
| Worked walkthrough > Why this works | H3 | 106 | 106 |
| Worked walkthrough > Things to watch for | H3 | 54 | 54 |
| Worked walkthrough > Check your understanding | H3 | 64 | 64 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Python Tutor – step through arithmetic](<https://pythontutor.com/>) | Python Tutor | visualizer / intro | 10 | neutral |
| [CS50x Week 1: C, types, operators and input](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / core | 120 | cpp |
| [Competitive Programmer's Handbook, chapter 21: Number theory](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [Palindrome Number](<https://leetcode.com/problems/palindrome-number/>) (LeetCode, easy)
- Practice — [Armstrong Number](<https://leetcode.com/problems/armstrong-number/>) (LeetCode, easy)
- Practice — [Three Divisors](<https://leetcode.com/problems/three-divisors/>) (LeetCode, easy)
- Practice — [The kth Factor of n](<https://leetcode.com/problems/the-kth-factor-of-n/>) (LeetCode, medium)
- Practice — [Perfect Number](<https://leetcode.com/problems/perfect-number/>) (LeetCode, easy)
- Practice — [T-primes](<https://codeforces.com/problemset/problem/230/B>) (Codeforces, easy)
- Practice — [Find Greatest Common Divisor of Array](<https://leetcode.com/problems/find-greatest-common-divisor-of-array/>) (LeetCode, easy)
- Practice — [Fibonacci Number](<https://leetcode.com/problems/fibonacci-number/>) (LeetCode, easy)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/loops@Dvy7BnNzK55qbh_SgOk8m.md>)
- Roadmap — [For / While / Do While Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/for--while--do-while-loops@_IP_e1K9LhNHilYTDh7L5.md>)
- Roadmap — [Loops](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/loops@JHUhVEjWFXTn6-wKcKevg.md>)

#### Working with data — `collections`

Store many values and look them up quickly.

##### Lists and arrays — `zero:lists`

- **Scope:** Store many values in order under one name, and process them with loops.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/lists.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/lists.yaml>)
- **Prerequisites:** `zero:for-loops`
- **Key points:** Lists keep values in order; indexes run from 0 to n − 1.; Loop over values for items, over indexes when position matters.; Out-of-range indexes are errors (and silent bugs in C++).; Most list problems are accumulators, best-so-far, or neighbour comparisons.
- **Pitfalls:** Using 1-based indexes and skipping the first element or overrunning the last.; Comparing a[i] with a[i - 1] starting from i = 0.; Changing a list's length while looping over it.
- **Local judge problems:** [Above the average](<D:/Socrat/content/courses/zero/problems/above-average.yaml>) (`above-average`, easy); [Longest rising streak](<D:/Socrat/content/courses/zero/problems/increasing-steps.yaml>) (`increasing-steps`, medium); [Runner-up score](<D:/Socrat/content/courses/zero/problems/runner-up-score.yaml>) (`runner-up-score`, easy)
- **Quiz items:** `last-index` (mcq, difficulty 1/5); `list-neighbours` (mcq, difficulty 2/5); `list-output` (output, difficulty 1/5); `best-so-far` (mcq, difficulty 2/5); `alias` (output, difficulty 4/5); `slice-reverse` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 178 | 178 |
| Looping over a list | H2 | 122 | 122 |
| Reading a list from input | H2 | 57 | 57 |
| Classic patterns | H2 | 43 | 43 |
| Worked walkthrough | H2 | 60 | 240 |
| Worked walkthrough > Why this works | H3 | 43 | 43 |
| Worked walkthrough > Things to watch for | H3 | 68 | 68 |
| Worked walkthrough > Check your understanding | H3 | 56 | 56 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Data Structures: more on lists](<https://docs.python.org/3/tutorial/datastructures.html>) | Python docs | docs / core | 20 | python |
| [Learn C++: Introduction to std::vector](<https://www.learncpp.com/cpp-tutorial/introduction-to-stdvector-and-list-constructors/>) | LearnCpp | article / core | 20 | cpp |
| [std::vector reference](<https://en.cppreference.com/w/cpp/container/vector>) | cppreference | docs / deep | 10 | cpp |
| [Java Tutorials: Arrays](<https://docs.oracle.com/javase/tutorial/java/nutsandbolts/arrays.html>) | Oracle | docs / core | 15 | java |
| [Introduction to Data Structures](<https://www.youtube.com/watch?v=xLetJpcjHS0>) | YouTube | video / intro | 15 | neutral |

**Other authored/supplemental links**

- Practice — [Missing Number](<https://cses.fi/problemset/task/1083>) (CSES, easy)
- Practice — [Increasing Array](<https://cses.fi/problemset/task/1094>) (CSES, easy)
- Roadmap — [Lists](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/lists@UT_SR7G-LYtzqooWrEtF1.md>)
- Roadmap — [Containers](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/containers@1pydf-SR0QUfVNuBEyvzc.md>)
- Roadmap — [Array Vs Arraylist](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/array-vs-arraylist@a-EQiBUlSgdZba1mW36op.md>)
- Python exercise 16 — [Filter odd values](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-16>)
- Python exercise 38 — [Generate and slice squares](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-38>)
- Python exercise 87 — [Filter a collection safely](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-87>)

##### Strings — `zero:strings`

- **Scope:** Text is a sequence of characters — index it, loop over it, compare it and build new text.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/strings.yaml>); [released atom pack](<D:/Socrat/content/atoms/zero/strings.yaml>)
- **Prerequisites:** `zero:lists`
- **Key points:** Strings behave like lists of characters with indexes from 0.; Python and Java strings are immutable; build text with join or StringBuilder.; Characters have numeric codes; 'c' - 'a' gives a letter's position.; In Java compare strings with equals, not ==.
- **Pitfalls:** Using == for strings in Java.; Building long strings with repeated + in a loop (slow in Python/Java).; Forgetting that input lines may carry trailing spaces or newlines.
- **Local judge problems:** [Count the vowels](<D:/Socrat/content/courses/zero/problems/vowel-count.yaml>) (`vowel-count`, easy); [Caesar cipher](<D:/Socrat/content/courses/zero/problems/caesar-shift.yaml>) (`caesar-shift`, medium); [Mirror phrase](<D:/Socrat/content/courses/zero/problems/mirror-phrase.yaml>) (`mirror-phrase`, easy)
- **Quiz items:** `char-math` (mcq, difficulty 2/5); `java-equals` (mcq, difficulty 1/5); `immutability` (mcq, difficulty 2/5); `string-index` (output, difficulty 1/5); `immutable` (mcq, difficulty 4/5); `split-join` (output, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 112 | 112 |
| Strings are (usually) immutable | H2 | 81 | 81 |
| Characters are numbers underneath | H2 | 54 | 54 |
| Comparing strings | H2 | 30 | 30 |
| Worked example: is it a palindrome? | H2 | 161 | 161 |
| Worked walkthrough | H2 | 47 | 216 |
| Worked walkthrough > Why this works | H3 | 37 | 37 |
| Worked walkthrough > Things to watch for | H3 | 66 | 66 |
| Worked walkthrough > Check your understanding | H3 | 53 | 53 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Text sequence type: str methods](<https://docs.python.org/3/library/stdtypes.html>) | Python docs | docs / core | 20 | python |
| [std::basic_string reference](<https://en.cppreference.com/w/cpp/string/basic_string>) | cppreference | docs / core | 15 | cpp |
| [Learn Java on dev.java (Strings and StringBuilder)](<https://dev.java/learn/>) | Oracle dev.java | course / core | 20 | java |
| [Tech Interview Handbook: String cheatsheet](<https://www.techinterviewhandbook.org/algorithms/string/>) | Tech Interview Handbook | article / deep | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Petya and Strings](<https://codeforces.com/problemset/problem/112/A>) (Codeforces, easy)
- Practice — [Repetitions](<https://cses.fi/problemset/task/1069>) (CSES, easy)
- Roadmap — [Working With Strings](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/working-with-strings@Sg5w8zO2Ji-uDJKEoWey9.md>)
- Roadmap — [Strings And Methods](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/strings-and-methods@aEaBobzFWv0mJHGAbgxKY.md>)
- Python exercise 13 — [Count letters and digits](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-13>)
- Python exercise 96 — [Character frequencies](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-96>)
- Python exercise 97 — [Reverse text](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-97>)

##### Dictionaries and maps — `zero:maps`

- **Scope:** Store key → value pairs and look values up instantly by key instead of searching.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/maps.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:strings`
- **Key points:** Maps store key → value pairs; keys are unique.; Lookup, insert and update by key are fast on average, regardless of size.; Counting occurrences is the classic map pattern.; Hash maps are unordered; use a sorted map or sort keys when order matters.; A set stores unique keys for fast "seen before?" checks.
- **Pitfalls:** Reading a missing key (Python KeyError; C++ [] silently inserts 0).; Printing results in hash order when sorted order was required.; Using a list and searching it repeatedly when a map would be instant.
- **Local judge problems:** [Word frequency](<D:/Socrat/content/courses/zero/problems/word-frequency.yaml>) (`word-frequency`, easy); [First repeated number](<D:/Socrat/content/courses/zero/problems/first-repeat.yaml>) (`first-repeat`, medium); [Class election](<D:/Socrat/content/courses/zero/problems/class-election.yaml>) (`class-election`, easy)
- **Quiz items:** `unique-keys` (output, difficulty 2/5); `which-structure` (mcq, difficulty 1/5); `set-use` (mcq, difficulty 1/5); `order` (mcq, difficulty 2/5); `get-default` (output, difficulty 4/5); `key-types` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 194 | 194 |
| Counting with a map | H2 | 61 | 61 |
| Ordered vs unordered | H2 | 44 | 44 |
| Sets | H2 | 22 | 22 |
| Why it matters | H2 | 35 | 35 |
| Worked walkthrough | H2 | 50 | 222 |
| Worked walkthrough > Why this works | H3 | 39 | 39 |
| Worked walkthrough > Things to watch for | H3 | 64 | 64 |
| Worked walkthrough > Check your understanding | H3 | 56 | 56 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Data Structures: dictionaries and sets](<https://docs.python.org/3/tutorial/datastructures.html>) | Python docs | docs / core | 15 | python |
| [std::unordered_map reference](<https://en.cppreference.com/w/cpp/container/unordered_map>) | cppreference | docs / core | 10 | cpp |
| [Java Tutorials: The Map interface](<https://docs.oracle.com/javase/tutorial/collections/interfaces/map.html>) | Oracle | docs / core | 15 | java |
| [Hash tables visualized](<https://visualgo.net/en/hashtable>) | VisuAlgo | visualizer / deep | 15 | neutral |

**Other authored/supplemental links**

- Practice — [Distinct Numbers](<https://cses.fi/problemset/task/1621>) (CSES, easy)
- Practice — [Two Sum](<https://leetcode.com/problems/two-sum/>) (LeetCode, easy)
- Roadmap — [Dictionaries](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/dictionaries@bc9CL_HMT-R6nXO1eR-gP.md>)
- Roadmap — [Containers](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/containers@1pydf-SR0QUfVNuBEyvzc.md>)
- Roadmap — [Map](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/map@eKtdDtiJygKQ4PuEylFQY.md>)
- Python exercise 3 — [Square lookup table](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-3>)
- Python exercise 96 — [Character frequencies](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-96>)

##### Grids and 2D lists — `zero:grids`

- **Scope:** Represent boards, maps and tables as lists of rows, and move around them safely.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/grids.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:nested-loops`, `zero:lists`
- **Key points:** A grid is a list of rows; access cells as grid[row][col].; In Python, build rows in a loop — never multiply a list of lists.; Direction arrays make neighbour loops short and uniform.; Check bounds before touching any neighbour.
- **Pitfalls:** Swapping row and column (grid[c][r]).; Reading neighbours outside the grid on edge cells.; Python's shared-row bug from [[0] * cols] * rows.
- **Local judge problems:** [Minesweeper numbers](<D:/Socrat/content/courses/zero/problems/minesweeper-counts.yaml>) (`minesweeper-counts`, medium); [Row and column totals](<D:/Socrat/content/courses/zero/problems/row-and-column-sums.yaml>) (`row-and-column-sums`, easy)
- **Quiz items:** `index-order` (mcq, difficulty 1/5); `corner-neighbours` (mcq, difficulty 2/5); `python-shared-rows` (mcq, difficulty 3/5); `work` (mcq, difficulty 2/5); `grid-trap` (output, difficulty 4/5); `neighbours` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 202 | 202 |
| Character grids | H2 | 20 | 20 |
| Neighbours and bounds | H2 | 224 | 224 |
| Worked idea: counting around each cell | H2 | 51 | 51 |
| Worked walkthrough | H2 | 43 | 211 |
| Worked walkthrough > Why this works | H3 | 38 | 38 |
| Worked walkthrough > Things to watch for | H3 | 60 | 60 |
| Worked walkthrough > Check your understanding | H3 | 57 | 57 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Data Structures: nested list comprehensions](<https://docs.python.org/3/tutorial/datastructures.html>) | Python docs | docs / core | 10 | python |
| [Java Tutorials: Arrays (multidimensional)](<https://docs.oracle.com/javase/tutorial/java/nutsandbolts/arrays.html>) | Oracle | docs / core | 10 | java |
| [Tech Interview Handbook: Matrix cheatsheet](<https://www.techinterviewhandbook.org/algorithms/matrix/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [USACO Guide: Simulation](<https://usaco.guide/bronze/simulation>) | USACO Guide | article / deep | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Number Spiral](<https://cses.fi/problemset/task/1071>) (CSES, medium)
- Roadmap — [Lists](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/lists@UT_SR7G-LYtzqooWrEtF1.md>)
- Roadmap — [Containers](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/containers@1pydf-SR0QUfVNuBEyvzc.md>)
- Roadmap — [Arrays](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/arrays@5khApwg1FZ-0qorsLyH-F.md>)
- Python exercise 7 — [Multiplication grid](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-7>)
- Python exercise 90 — [Independent nested lists](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-90>)

#### Functions and structure — `functions-module`

Break programs into reusable, testable pieces.

##### Functions — `zero:functions`

- **Scope:** Package a piece of logic under a name, give it inputs, and get a result back.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/functions.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:lists`
- **Key points:** Functions take parameters, run their body, and return a value.; return ends the function immediately and hands back a value.; print shows output; return gives a value to the caller — prefer return.; Small, single-purpose, well-named functions make programs readable and testable.
- **Pitfalls:** Printing inside a function when the caller needed the value.; Forgetting to return on every path (C++ may return garbage; Java will not compile).; Calling a function without using its returned value.
- **Local judge problems:** [Prime or not](<D:/Socrat/content/courses/zero/problems/prime-check.yaml>) (`prime-check`, easy); [Greatest common divisor](<D:/Socrat/content/courses/zero/problems/gcd-function.yaml>) (`gcd-function`, medium)
- **Quiz items:** `return-ends` (output, difficulty 1/5); `print-vs-return` (mcq, difficulty 2/5); `sqrt-bound` (mcq, difficulty 3/5); `call-value` (output, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 149 | 149 |
| What happens on a call | H2 | 72 | 72 |
| print versus return | H2 | 46 | 46 |
| Early return | H2 | 148 | 148 |
| Designing good functions | H2 | 36 | 36 |
| Worked walkthrough | H2 | 61 | 247 |
| Worked walkthrough > Why this works | H3 | 39 | 39 |
| Worked walkthrough > Things to watch for | H3 | 69 | 69 |
| Worked walkthrough > Check your understanding | H3 | 65 | 65 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Defining functions](<https://docs.python.org/3/tutorial/controlflow.html>) | Python docs | docs / core | 15 | python |
| [Learn C++: Introduction to functions](<https://www.learncpp.com/cpp-tutorial/introduction-to-functions/>) | LearnCpp | article / core | 15 | cpp |
| [Java Full Course for Beginners (methods section)](<https://www.youtube.com/watch?v=eIrMbAQSU34>) | Programming with Mosh | video / core | 30 | java |
| [CS50x Week 1: Functions and abstraction](<https://cs50.harvard.edu/x/2024/weeks/1/>) | Harvard CS50 | course / core | 120 | neutral |

**Other authored/supplemental links**

- Practice — [Team](<https://codeforces.com/problemset/problem/231/A>) (Codeforces, easy)
- Roadmap — [Functions Builtin Functions](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/functions-builtin-functions@-DJgS6l2qngfwurExlmmT.md>)
- Roadmap — [Functions](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/functions@oYi3YOc1GC2Nfp71VOkJt.md>)
- Roadmap — [Attributes And Methods](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/attributes-and-methods@xTwJYcA6ldgaw3yGmbDEd.md>)
- Python exercise 23 — [Square a function argument](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-23>)
- Python exercise 30 — [Combine function inputs](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-30>)

##### Scope, references and mutation — `zero:scope-and-mutation`

- **Scope:** Know where a variable lives, and when passing a list to a function lets it change the original.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/scope-and-mutation.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:functions`
- **Key points:** Local variables exist only inside their function or block.; Pass data in as parameters and send results out with return.; In Python and Java, functions receive references to lists/arrays and can mutate them.; C++ copies by default; & passes the original, const & avoids copies safely.; b = a aliases a list in Python/Java; copy explicitly when you need independence.
- **Pitfalls:** Expecting a function to change a number variable of the caller.; Accidentally mutating a list passed in, surprising the caller.; Copying large vectors on every call in C++.
- **Local judge problems:** none
- **Quiz items:** `number-param` (output, difficulty 2/5); `list-param` (mcq, difficulty 2/5); `cpp-ref` (mcq, difficulty 2/5); `alias` (output, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 33 | 33 |
| Scope | H2 | 147 | 147 |
| Mutation: numbers vs. lists | H2 | 188 | 188 |
| Aliasing | H2 | 39 | 39 |
| Rule of thumb | H2 | 26 | 26 |
| Worked walkthrough | H2 | 61 | 242 |
| Worked walkthrough > Why this works | H3 | 37 | 37 |
| Worked walkthrough > Things to watch for | H3 | 70 | 70 |
| Worked walkthrough > Check your understanding | H3 | 61 | 61 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Python Tutor – see references and aliasing visually](<https://pythontutor.com/>) | Python Tutor | visualizer / core | 15 | neutral |
| [Classes: a word about names and objects](<https://docs.python.org/3/tutorial/classes.html>) | Python docs | docs / core | 10 | python |
| [Learn C++: Introduction to functions (parameters)](<https://www.learncpp.com/cpp-tutorial/introduction-to-functions/>) | LearnCpp | article / core | 15 | cpp |

**Other authored/supplemental links**

- Roadmap — [Variable Scope](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/variable-scope@3RNy7Sp28d-NMx0Yh4bdx.md>)
- Roadmap — [Scope](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/scope@dKCYmxDNZubCVcR5rf8b-.md>)
- Roadmap — [References](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/references@uUzRKa9wGzdUwwmAg3FWr.md>)
- Roadmap — [Pass By Value / Pass By Reference](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/pass-by-value--pass-by-reference@3r0Er9XZHovIZz3gNyj4A.md>)
- Python exercise 90 — [Independent nested lists](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-90>)

##### Recursion — `zero:recursion`

- **Scope:** Solve a problem by having a function call itself on a smaller version, until a simple base case.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/recursion.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:functions`
- **Key points:** Every recursive function needs a base case and a step toward it.; Each call gets its own frame on the call stack; frames finish in reverse order.; Trust the recursive call on smaller input (the leap of faith).; Branching recursion can repeat work; memoization remembers answers.
- **Pitfalls:** Missing or unreachable base case — infinite recursion and stack overflow.; Recursing on input that does not get smaller.; Exponential time from naive branching recursion without memoization.
- **Local judge problems:** [Fast power](<D:/Socrat/content/courses/zero/problems/power-recursive.yaml>) (`power-recursive`, medium); [Ways to climb](<D:/Socrat/content/courses/zero/problems/stairs-ways.yaml>) (`stairs-ways`, medium)
- **Quiz items:** `base-case` (mcq, difficulty 1/5); `trace` (output, difficulty 2/5); `order` (output, difficulty 3/5); `memo` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 133 | 133 |
| How it actually runs: the call stack | H2 | 87 | 87 |
| The leap of faith | H2 | 61 | 61 |
| Branching recursion | H2 | 152 | 152 |
| When to use recursion | H2 | 32 | 32 |
| Worked walkthrough | H2 | 48 | 234 |
| Worked walkthrough > Why this works | H3 | 46 | 46 |
| Worked walkthrough > Things to watch for | H3 | 72 | 72 |
| Worked walkthrough > Check your understanding | H3 | 55 | 55 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Recursion in Programming – Full Course](<https://www.youtube.com/watch?v=IJDJ0kBx2LM>) | freeCodeCamp | video / core | 110 | neutral |
| [Recursion trees visualized](<https://visualgo.net/en/recursion>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Python Recursion (Recursive Function)](<https://www.programiz.com/python-programming/recursion>) | Programiz | article / core | 10 | python |
| [Tech Interview Handbook: Recursion cheatsheet](<https://www.techinterviewhandbook.org/algorithms/recursion/>) | Tech Interview Handbook | article / deep | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Climbing Stairs](<https://leetcode.com/problems/climbing-stairs/>) (LeetCode, easy)
- Roadmap — [Recursion](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/recursion@kLBgy_nxxjE8SxdVi04bq.md>)
- Roadmap — [Recursion](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/recursion@4ZAzcwP0oPGZ9Rw042V8-.md>)
- Python exercise 2 — [Factorial by recursion](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-2>)
- Python exercise 66 — [Fibonacci recurrence](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-66>)

##### Searching and sorting basics — `zero:searching-and-sorting`

- **Scope:** Linear and binary search, selection, bubble and insertion sort traced by hand, and sorting by a key with the built-in sort.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/searching-and-sorting.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:lists`, `zero:functions`
- **Key points:** Linear search checks every element; "not found" is only known after the loop.; Binary search needs a sorted list and halves the candidates each step, O(log n).; Move lo to mid + 1 and hi to mid − 1, and loop while lo ≤ hi.; One bubble pass carries the largest unsorted value to the end; repeat until no swaps.; Selection picks the smallest remaining value; insertion slides values into a sorted front.; Simple sorts are O(n²); the built-in sort is O(n log n).; Sort by a key, and include the tie rule in it.
- **Pitfalls:** Deciding "not found" inside the loop.; Binary searching an unsorted list, or using lo = mid.; Expecting one pass of swaps to sort the list.; Copying instead of swapping.; Leaving ties to chance in a key sort.
- **Local judge problems:** [Exam ranking](<D:/Socrat/content/courses/zero/problems/exam-ranking.yaml>) (`exam-ranking`, easy); [Counting the swaps](<D:/Socrat/content/courses/zero/problems/swap-count.yaml>) (`swap-count`, medium)
- **Quiz items:** `lin-not-found` (mcq, difficulty 1/5); `lin-first` (mcq, difficulty 1/5); `bin-needs-sorted` (mcq, difficulty 2/5); `bin-looks` (mcq, difficulty 2/5); `bin-lo-mid` (mcq, difficulty 3/5); `one-pass` (mcq, difficulty 3/5); `two-passes` (mcq, difficulty 4/5); `sort-cost` (mcq, difficulty 4/5); `key-tie` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 102 | 102 |
| Linear search | H2 | 0 | 380 |
| Linear search > Recognition cues | H3 | 21 | 21 |
| Linear search > Template | H3 | 191 | 191 |
| Linear search > Anchor problem: find 2 | H3 | 76 | 76 |
| Linear search > Variants | H3 | 30 | 30 |
| Linear search > Contrast | H3 | 19 | 19 |
| Linear search > Common mistakes | H3 | 26 | 26 |
| Iterative binary search | H2 | 0 | 624 |
| Iterative binary search > Recognition cues | H3 | 30 | 30 |
| Iterative binary search > Template | H3 | 362 | 362 |
| Iterative binary search > Anchor problem: find 7 | H3 | 98 | 98 |
| Iterative binary search > Variants | H3 | 46 | 46 |
| Iterative binary search > Contrast | H3 | 42 | 42 |
| Iterative binary search > Common mistakes | H3 | 29 | 29 |
| Simple sorts | H2 | 0 | 1288 |
| Simple sorts > Recognition cues | H3 | 34 | 34 |
| Simple sorts > Template | H3 | 380 | 380 |
| Simple sorts > Anchor problem: 5 1 4 2 8 | H3 | 708 | 708 |
| Simple sorts > Variants | H3 | 60 | 60 |
| Simple sorts > Contrast | H3 | 37 | 37 |
| Simple sorts > Common mistakes | H3 | 49 | 49 |
| Key sort | H2 | 0 | 395 |
| Key sort > Recognition cues | H3 | 24 | 24 |
| Key sort > Template | H3 | 169 | 169 |
| Key sort > Anchor problem: five fruits | H3 | 67 | 67 |
| Key sort > Variants | H3 | 43 | 43 |
| Key sort > Contrast | H3 | 43 | 43 |
| Key sort > Common mistakes | H3 | 32 | 32 |
| Worked walkthrough | H2 | 83 | 318 |
| Worked walkthrough > Why this works | H3 | 98 | 98 |
| Worked walkthrough > Things to watch for | H3 | 53 | 53 |
| Worked walkthrough > Check your understanding | H3 | 71 | 71 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Sorting visualized](<https://visualgo.net/en/sorting>) | VisuAlgo | visualizer / core | 20 | neutral |
| [Python Tutor – step through arithmetic](<https://pythontutor.com/>) | Python Tutor | visualizer / intro | 10 | neutral |
| [Tech Interview Handbook: Sorting and searching](<https://www.techinterviewhandbook.org/algorithms/sorting-searching/>) | Tech Interview Handbook | article / deep | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Binary Search](<https://leetcode.com/problems/binary-search/>) (LeetCode, easy)
- Practice — [Search Insert Position](<https://leetcode.com/problems/search-insert-position/>) (LeetCode, easy)
- Practice — [Height Checker](<https://leetcode.com/problems/height-checker/>) (LeetCode, easy)
- Practice — [Gravity Flip](<https://codeforces.com/problemset/problem/405/A>) (Codeforces, easy)
- Practice — [Helpful Maths](<https://codeforces.com/problemset/problem/339/A>) (Codeforces, easy)
- Practice — [Sort the People](<https://leetcode.com/problems/sort-the-people/>) (LeetCode, easy)
- Practice — [Sort Integers by The Number of 1 Bits](<https://leetcode.com/problems/sort-integers-by-the-number-of-1-bits/>) (LeetCode, easy)
- Roadmap — [Lists](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/lists@UT_SR7G-LYtzqooWrEtF1.md>)
- Roadmap — [Containers](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/containers@1pydf-SR0QUfVNuBEyvzc.md>)
- Roadmap — [Array Vs Arraylist](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/array-vs-arraylist@a-EQiBUlSgdZba1mW36op.md>)

#### The programmer's craft — `craft`

Debug calmly, solve unfamiliar problems, and model the world with objects.

##### Debugging calmly — `zero:debugging`

- **Scope:** Read error messages, reproduce the bug, find the first wrong value, and fix the cause — not the symptom.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/debugging.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:functions`
- **Key points:** Compile, runtime and logic errors need different responses.; Read the first error message carefully — it gives the line and the kind of problem.; Reproduce with the smallest failing input, predict, observe, and find the first wrong value.; Test edge cases before submitting; remove debug output.
- **Pitfalls:** Changing code randomly until the output looks right.; Fixing the line where the crash appears instead of the reason the value was wrong.; Leaving debug prints in a submission.
- **Local judge problems:** [Fix the average](<D:/Socrat/content/courses/zero/problems/fix-the-average.yaml>) (`fix-the-average`, easy)
- **Quiz items:** `first-error` (mcq, difficulty 1/5); `smallest-case` (mcq, difficulty 1/5); `logic-bug` (mcq, difficulty 1/5); `edge-cases` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 25 | 25 |
| Three kinds of errors | H2 | 90 | 90 |
| Read the error message | H2 | 48 | 48 |
| The debugging method | H2 | 144 | 144 |
| Test the edges | H2 | 42 | 42 |
| Rubber duck | H2 | 48 | 48 |
| Worked walkthrough | H2 | 53 | 207 |
| Worked walkthrough > Why this works | H3 | 38 | 38 |
| Worked walkthrough > Things to watch for | H3 | 53 | 53 |
| Worked walkthrough > Check your understanding | H3 | 50 | 50 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Errors and exceptions](<https://docs.python.org/3/tutorial/errors.html>) | Python docs | docs / core | 20 | python |
| [Python Tutor – step through code to find the first wrong value](<https://pythontutor.com/>) | Python Tutor | visualizer / core | 15 | neutral |
| [CS50x Week 2: Debugging](<https://cs50.harvard.edu/x/2024/weeks/2/>) | Harvard CS50 | course / core | 60 | neutral |

**Other authored/supplemental links**

- Roadmap — [Exceptions](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/exceptions@fNTb9y3zs1HPYclAmu_Wv.md>)
- Roadmap — [Debuggers](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/debuggers@qmHs6_BzND_xpMmls5YUH.md>)
- Roadmap — [Exception Handling](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/exception-handling@g9P3548F38tYGjevBc42w.md>)
- Python exercise 70 — [Assert a list invariant](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-70>)

##### Solving unfamiliar problems — `zero:problem-solving`

- **Scope:** A repeatable process for turning a problem statement you have never seen into working code.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/problem-solving.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:debugging`, `zero:maps`
- **Key points:** Understand the input, output, examples and constraints before coding.; Solve small examples by hand and turn your own steps into an algorithm.; Write pseudocode, then code, then test edge cases.; A correct simple solution first; optimize after.; Reflect on the key insight so each problem teaches a reusable pattern.
- **Pitfalls:** Coding before understanding the examples.; Never testing beyond the given examples.; Watching the solution immediately instead of struggling productively for a while.
- **Local judge problems:** [Does a pair exist?](<D:/Socrat/content/courses/zero/problems/two-sum-exists.yaml>) (`two-sum-exists`, medium)
- **Quiz items:** `first-step` (mcq, difficulty 1/5); `constraints` (mcq, difficulty 2/5); `brute-force` (mcq, difficulty 1/5); `reflect` (mcq, difficulty 1/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 43 | 43 |
| The process | H2 | 236 | 236 |
| Common moves when stuck | H2 | 65 | 65 |
| Reading constraints | H2 | 50 | 50 |
| Asking for help well | H2 | 30 | 30 |
| Worked walkthrough | H2 | 50 | 215 |
| Worked walkthrough > Why this works | H3 | 37 | 37 |
| Worked walkthrough > Things to watch for | H3 | 58 | 58 |
| Worked walkthrough > Check your understanding | H3 | 57 | 57 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [CS50x Week 0: Computational thinking](<https://cs50.harvard.edu/x/2024/weeks/0/>) | Harvard CS50 | course / intro | 90 | neutral |
| [Google Coding Interview With A College Student (watch the process)](<https://www.youtube.com/watch?v=3Q_oYDQ2whs>) | YouTube | video / core | 45 | neutral |
| [USACO Guide: Simulation (turning a statement into steps)](<https://usaco.guide/bronze/simulation>) | USACO Guide | article / core | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Next Round](<https://codeforces.com/problemset/problem/158/A>) (Codeforces, easy)
- Practice — [Distinct Numbers](<https://cses.fi/problemset/task/1621>) (CSES, easy)
- Roadmap — [Problem Solving Techniques](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/problem-solving-techniques@Y1Uz6XRbR1YqFtO4akiPA.md>)

##### Classes and objects — `zero:classes-and-objects`

- **Scope:** Bundle related data and the operations on it into your own types.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/zero/concepts/classes-and-objects.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:scope-and-mutation`
- **Key points:** A class defines a type with data (attributes) and behaviour (methods).; An object is an instance with its own copy of the attributes.; Constructors initialise objects; self/this refers to the current object.; Encapsulation keeps data and its rules together, preventing invalid states.
- **Pitfalls:** Forgetting self in Python method definitions or attribute access.; Sharing one mutable default (like a list) between all Python objects.; Huge classes that do everything instead of one clear job.
- **Local judge problems:** [Bank ledger](<D:/Socrat/content/courses/zero/problems/bank-ledger.yaml>) (`bank-ledger`, medium)
- **Quiz items:** `own-copy` (mcq, difficulty 1/5); `constructor` (mcq, difficulty 1/5); `encapsulation` (mcq, difficulty 2/5); `self-this` (mcq, difficulty 1/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 212 | 212 |
| Key vocabulary | H2 | 67 | 67 |
| Why bother? | H2 | 52 | 52 |
| In data structures | H2 | 48 | 48 |
| Keep classes small | H2 | 31 | 31 |
| Worked walkthrough | H2 | 53 | 220 |
| Worked walkthrough > Why this works | H3 | 45 | 45 |
| Worked walkthrough > Things to watch for | H3 | 54 | 54 |
| Worked walkthrough > Check your understanding | H3 | 55 | 55 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Classes](<https://docs.python.org/3/tutorial/classes.html>) | Python docs | docs / core | 30 | python |
| [Java Tutorials: Classes](<https://docs.oracle.com/javase/tutorial/java/javaOO/classes.html>) | Oracle | docs / core | 20 | java |
| [C++ Tutorial for Beginners – Full Course (classes section)](<https://www.youtube.com/watch?v=vLnPwxZdW4Y>) | freeCodeCamp | video / core | 40 | cpp |

**Other authored/supplemental links**

- Roadmap — [Classes](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/python/content/classes@AqwzR8dZKLQIoj_6KKZ3t.md>)
- Roadmap — [Object Oriented Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/cpp/content/object-oriented-programming@b3-QYKNcW3LYCNOza3Olf.md>)
- Roadmap — [Classes And Objects](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/java/content/classes-and-objects@LenPrQwxFsE1UVbXO_dE7.md>)
- Python exercise 52 — [Encapsulate circle dimensions](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-52>)

### 4.2 DSA for Interviews — `dsa`

The data structures and algorithm patterns that coding interviews actually test, taught as reusable patterns rather than memorised answers. Each topic ends with unseen problems you solve on your own, so you walk into interviews knowing you can do it.

**Course file:** [content/courses/dsa/course.yaml](<D:/Socrat/content/courses/dsa/course.yaml>). **Version:** 1.0.0. **Languages:** python, cpp, java.

| Module / subject area | Topics | Lesson words | Quiz | Native | Atoms | Reading links | External unique mapped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Foundations | 4 | 5712 | 29 | 11 | 30 | 15 | 2415 |
| Linear patterns | 6 | 11395 | 41 | 17 | 36 | 20 | 1422 |
| Sorting and greedy | 3 | 1759 | 12 | 5 | 27 | 10 | 1767 |
| Linked structures, recursion and backtracking | 3 | 5401 | 17 | 5 | 0 | 10 | 182 |
| Trees and heaps | 5 | 8335 | 25 | 7 | 0 | 16 | 488 |
| Graphs | 4 | 2444 | 16 | 5 | 0 | 15 | 1870 |
| Dynamic programming and bits | 14 | 51098 | 101 | 27 | 0 | 46 | 853 |
| Design and interview practice | 1 | 4939 | 9 | 2 | 0 | 3 | 0 |

**Topic-level local coverage**

| Concept ID | Topic | Words | Sections | Quiz | Native | Atom pack / atoms | Estimated minutes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dsa:complexity | Time and space complexity | 679 | 9 | 7 | 2 | released / 9 | 45 |
| dsa:arrays-hashing | Arrays and hashing | 606 | 11 | 6 | 3 | released / 9 | 60 |
| dsa:prefix-sums | Prefix sums | 619 | 7 | 6 | 4 | released / 12 | 50 |
| dsa:hashing | Hashing patterns | 3808 | 32 | 10 | 2 | missing / 0 | 60 |
| dsa:two-pointers | Two pointers | 637 | 10 | 6 | 4 | released / 9 | 50 |
| dsa:sliding-window | Sliding window | 694 | 9 | 6 | 3 | released / 9 | 55 |
| dsa:stacks | Stacks, queues and monotonic stacks | 710 | 8 | 6 | 3 | released / 9 | 55 |
| dsa:monotonic-stack | Monotonic stack and deque | 4664 | 44 | 8 | 2 | missing / 0 | 90 |
| dsa:binary-search | Binary search | 680 | 8 | 6 | 3 | released / 9 | 60 |
| dsa:binary-search-on-answer | Binary search on the answer | 4010 | 25 | 9 | 2 | missing / 0 | 60 |
| dsa:sorting | Sorting | 670 | 9 | 4 | 2 | released / 9 | 60 |
| dsa:intervals | Intervals | 521 | 9 | 4 | 1 | released / 9 | 45 |
| dsa:greedy | Greedy algorithms | 568 | 10 | 4 | 2 | released / 9 | 55 |
| dsa:linked-lists | Linked lists | 622 | 10 | 4 | 1 | missing / 0 | 55 |
| dsa:recursion-patterns | Recursion patterns | 4199 | 39 | 9 | 2 | missing / 0 | 70 |
| dsa:backtracking | Backtracking | 580 | 8 | 4 | 2 | missing / 0 | 60 |
| dsa:binary-trees | Binary trees | 590 | 9 | 4 | 2 | missing / 0 | 60 |
| dsa:tree-patterns | Binary tree patterns | 6093 | 52 | 9 | 2 | missing / 0 | 90 |
| dsa:bst | Binary search trees | 537 | 9 | 4 | 1 | missing / 0 | 50 |
| dsa:heaps | Heaps and priority queues | 520 | 9 | 4 | 1 | missing / 0 | 50 |
| dsa:tries | Tries (prefix trees) | 595 | 8 | 4 | 1 | missing / 0 | 45 |
| dsa:graph-traversal | Graphs, BFS and DFS | 659 | 11 | 4 | 2 | missing / 0 | 70 |
| dsa:topological-sort | Topological sort | 629 | 9 | 4 | 1 | missing / 0 | 45 |
| dsa:union-find | Union-Find (Disjoint Set Union) | 575 | 8 | 4 | 1 | missing / 0 | 50 |
| dsa:shortest-paths | Weighted shortest paths | 581 | 8 | 4 | 1 | missing / 0 | 55 |
| dsa:dp-introduction | Dynamic programming: the idea | 4188 | 28 | 7 | 2 | missing / 0 | 60 |
| dsa:dp-1d | Dynamic programming (1D) | 618 | 10 | 4 | 2 | missing / 0 | 70 |
| dsa:dp-2d | Dynamic programming (2D) | 630 | 10 | 4 | 2 | missing / 0 | 70 |
| dsa:knapsack-01 | 0/1 knapsack family | 6001 | 44 | 8 | 2 | missing / 0 | 90 |
| dsa:knapsack-unbounded | Unbounded knapsack family | 4669 | 28 | 9 | 2 | missing / 0 | 75 |
| dsa:dp-lcs | Strings DP: the LCS family | 4934 | 44 | 8 | 2 | missing / 0 | 85 |
| dsa:dp-edit-distance | Strings DP: edits and matching | 5164 | 44 | 8 | 2 | missing / 0 | 90 |
| dsa:dp-stocks | Stock trading DP | 3031 | 12 | 8 | 2 | missing / 0 | 60 |
| dsa:dp-lis | Longest increasing subsequence family | 3508 | 28 | 8 | 2 | missing / 0 | 75 |
| dsa:dp-partition | Partition DP (matrix chain) | 4823 | 36 | 9 | 2 | missing / 0 | 90 |
| dsa:dp-squares | DP on squares and rectangles | 3491 | 20 | 7 | 2 | missing / 0 | 60 |
| dsa:dp-on-trees | DP on trees | 4625 | 28 | 8 | 2 | missing / 0 | 75 |
| dsa:bit-manipulation | Bit manipulation | 569 | 9 | 4 | 1 | missing / 0 | 40 |
| dsa:dp-advanced-patterns | More interview DP patterns | 4847 | 36 | 9 | 2 | missing / 0 | 90 |
| dsa:design-data-structures | Designing data structures | 4939 | 32 | 9 | 2 | missing / 0 | 70 |

**Topic-level external coverage**

| Concept ID | Reading | Authored practice links | EP | EA | Impl P/C/J | Roadmap | Python exercises | Book refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dsa:complexity | 4 | 2 | 0 | 0 | 0/0/0 | 3 | 0 | 1 |
| dsa:arrays-hashing | 4 | 4 | 541 | 2334 | 0/0/0 | 2 | 3 | 1 |
| dsa:prefix-sums | 3 | 3 | 166 | 220 | 1/1/3 | 1 | 0 | 1 |
| dsa:hashing | 4 | 8 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:two-pointers | 3 | 4 | 392 | 839 | 1/0/1 | 1 | 0 | 1 |
| dsa:sliding-window | 3 | 3 | 130 | 156 | 3/0/3 | 1 | 0 | 1 |
| dsa:stacks | 4 | 3 | 135 | 204 | 8/5/8 | 1 | 0 | 2 |
| dsa:monotonic-stack | 3 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:binary-search | 4 | 3 | 144 | 355 | 4/3/11 | 1 | 1 | 1 |
| dsa:binary-search-on-answer | 3 | 8 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:sorting | 4 | 3 | 619 | 1478 | 17/19/17 | 1 | 1 | 1 |
| dsa:intervals | 3 | 4 | 19 | 19 | 0/0/0 | 1 | 0 | 0 |
| dsa:greedy | 3 | 4 | 207 | 406 | 3/1/4 | 1 | 0 | 1 |
| dsa:linked-lists | 3 | 4 | 49 | 75 | 14/12/18 | 1 | 0 | 0 |
| dsa:recursion-patterns | 4 | 9 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:backtracking | 3 | 4 | 81 | 107 | 14/5/11 | 1 | 1 | 1 |
| dsa:binary-trees | 4 | 4 | 166 | 236 | 14/5/8 | 2 | 0 | 1 |
| dsa:tree-patterns | 3 | 10 | 0 | 0 | 0/0/0 | 2 | 0 | 0 |
| dsa:bst | 3 | 3 | 39 | 40 | 5/3/3 | 1 | 0 | 0 |
| dsa:heaps | 3 | 3 | 155 | 201 | 12/2/13 | 1 | 0 | 1 |
| dsa:tries | 3 | 2 | 56 | 56 | 1/4/2 | 1 | 0 | 1 |
| dsa:graph-traversal | 4 | 4 | 367 | 1384 | 7/4/2 | 2 | 0 | 2 |
| dsa:topological-sort | 3 | 3 | 42 | 42 | 2/2/1 | 1 | 0 | 1 |
| dsa:union-find | 4 | 3 | 402 | 492 | 2/4/3 | 1 | 0 | 1 |
| dsa:shortest-paths | 4 | 3 | 327 | 331 | 13/5/5 | 2 | 0 | 1 |
| dsa:dp-introduction | 4 | 6 | 0 | 0 | 0/0/0 | 1 | 1 | 0 |
| dsa:dp-1d | 4 | 4 | 358 | 547 | 8/10/10 | 1 | 1 | 1 |
| dsa:dp-2d | 4 | 4 | 90 | 136 | 0/0/0 | 1 | 0 | 2 |
| dsa:knapsack-01 | 3 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:knapsack-unbounded | 3 | 9 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-lcs | 3 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-edit-distance | 4 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-stocks | 3 | 6 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-lis | 3 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-partition | 3 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-squares | 3 | 6 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:dp-on-trees | 3 | 6 | 0 | 0 | 0/0/0 | 2 | 0 | 0 |
| dsa:bit-manipulation | 3 | 4 | 90 | 206 | 15/7/19 | 0 | 1 | 1 |
| dsa:dp-advanced-patterns | 3 | 10 | 0 | 0 | 0/0/0 | 1 | 0 | 0 |
| dsa:design-data-structures | 3 | 8 | 0 | 0 | 0/0/0 | 2 | 0 | 0 |

#### Foundations — `foundations`

Measure efficiency and master the array and hash map toolkit.

##### Time and space complexity — `dsa:complexity`

- **Scope:** Predict how running time and memory grow with input size using Big-O, before you write a line.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/complexity.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/complexity.yaml>)
- **Prerequisites:** `zero:nested-loops`, `zero:functions`
- **Key points:** Big-O describes growth with input size, ignoring constants and lower terms.; Sequential code adds, nested loops multiply, halving gives log n.; About 10^8 simple operations per second — check your plan against the constraints.; Trading memory for time (hash sets/maps) is the most common optimisation.; Know the hidden cost of library operations (list membership, slicing, string concat).
- **Pitfalls:** Calling an O(n) operation (like list membership) inside a loop, making O(n²).; Ignoring recursion depth as a space cost.; Optimising constant factors before fixing the complexity class.
- **Local judge problems:** [Triangle number queries](<D:/Socrat/content/courses/dsa/problems/sum-queries.yaml>) (`sum-queries`, easy); [Matching sock pairs](<D:/Socrat/content/courses/dsa/problems/matching-pairs.yaml>) (`matching-pairs`, easy)
- **Quiz items:** `nested-cost` (mcq, difficulty 1/5); `halving` (mcq, difficulty 2/5); `constraint-fit` (mcq, difficulty 2/5); `hidden-cost` (mcq, difficulty 3/5); `drop-terms` (mcq, difficulty 1/5); `halving-loop` (mcq, difficulty 4/5); `amortised` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 158 | 158 |
| Counting steps | H2 | 176 | 176 |
| Space complexity | H2 | 28 | 28 |
| Reading constraints like an expert | H2 | 88 | 88 |
| Hidden costs | H2 | 40 | 40 |
| Worked walkthrough | H2 | 51 | 167 |
| Worked walkthrough > Why this works | H3 | 27 | 27 |
| Worked walkthrough > Boundary cases and cost | H3 | 38 | 38 |
| Worked walkthrough > Check your understanding | H3 | 38 | 38 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Big-O notation in 5 minutes](<https://www.youtube.com/watch?v=__vX2sjlpXU>) | Michael Sambol | video / intro | 5 | neutral |
| [Introduction to Big O Notation and Time Complexity](<https://www.youtube.com/watch?v=D6xkbGLQesk>) | CS Dojo | video / core | 36 | neutral |
| [Big-O Algorithm Complexity Cheat Sheet](<https://www.bigocheatsheet.com/>) | bigocheatsheet.com | article / core | 10 | neutral |
| [USACO Guide: Time complexity](<https://usaco.guide/bronze/time-comp>) | USACO Guide | article / deep | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Contains Duplicate](<https://leetcode.com/problems/contains-duplicate/>) (LeetCode, easy)
- Practice — [Missing Number](<https://cses.fi/problemset/task/1083>) (CSES, easy)
- Roadmap — [Algorithmic Complexity](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/algorithmic-complexity@VotdHk0_bI3CeoIf-KoKu.md>)
- Roadmap — [Big O Notation](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/big-o-notation@oylTfop_JDPHJ3jYuA2Nq.md>)
- Roadmap — [Time Vs Space Complexity](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/time-vs-space-complexity@unaYmPzK761Eh_iZMLeRC.md>)
- Handbook §2, printed page 17 — [Time complexity](<https://cses.fi/book/book.pdf#page=27>)

##### Arrays and hashing — `dsa:arrays-hashing`

- **Scope:** Use hash maps and sets to turn repeated searching into instant lookups — the
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/arrays-hashing.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/arrays-hashing.yaml>)
- **Prerequisites:** `dsa:complexity`, `zero:maps`
- **Key points:** Hash maps/sets give O(1) average lookup, turning repeated searches into one pass.; Complement lookup — store what you've seen, look for target − x.; Frequency counting solves anagram, majority and top-k style questions.; Canonical keys group equivalent items.; For small known ranges, a counting array beats a hash map.
- **Pitfalls:** Inserting before checking, and pairing an element with itself.; Forgetting that hash maps are unordered when output order matters.; Using mutable lists as Python dict keys (use tuples or strings).
- **Local judge problems:** [Anagram check](<D:/Socrat/content/courses/dsa/problems/valid-anagram.yaml>) (`valid-anagram`, easy); [Top K frequent](<D:/Socrat/content/courses/dsa/problems/top-k-frequent.yaml>) (`top-k-frequent`, medium); [Longest unbroken run of values](<D:/Socrat/content/courses/dsa/problems/consecutive-run.yaml>) (`consecutive-run`, medium)
- **Quiz items:** `two-sum-complexity` (mcq, difficulty 1/5); `anagram-key` (mcq, difficulty 2/5); `check-before-insert` (mcq, difficulty 2/5); `counting-array` (mcq, difficulty 2/5); `hash-worst-case` (mcq, difficulty 4/5); `two-sum-one-pass` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 40 | 40 |
| How hashing works (just enough) | H2 | 44 | 44 |
| Pattern 1 — complement lookup (Two Sum) | H2 | 150 | 150 |
| Pattern 2 — frequency counting | H2 | 18 | 18 |
| Pattern 3 — canonical keys (grouping) | H2 | 41 | 41 |
| Arrays: the in-place toolkit | H2 | 63 | 63 |
| Interview checklist | H2 | 36 | 36 |
| Worked walkthrough | H2 | 48 | 172 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 38 | 38 |
| Worked walkthrough > Check your understanding | H3 | 47 | 47 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Two Sum – HashMap](<https://www.youtube.com/watch?v=KLlXCFG5TnA>) | NeetCode | video / core | 8 | neutral |
| [Tech Interview Handbook: Hash table cheatsheet](<https://www.techinterviewhandbook.org/algorithms/hash-table/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Hash tables visualized](<https://visualgo.net/en/hashtable>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Product of Array Except Self](<https://www.youtube.com/watch?v=bNvIQI2wAjk>) | NeetCode | video / deep | 11 | neutral |

**Other authored/supplemental links**

- Practice — [Two Sum](<https://leetcode.com/problems/two-sum/>) (LeetCode, easy)
- Practice — [Group Anagrams](<https://leetcode.com/problems/group-anagrams/>) (LeetCode, medium)
- Practice — [Product of Array Except Self](<https://leetcode.com/problems/product-of-array-except-self/>) (LeetCode, medium)
- Practice — [Sum of Two Values](<https://cses.fi/problemset/task/1640>) (CSES, easy)
- Roadmap — [Array](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/array@lxY3ErxJ_D3zkSAXIBUpv.md>)
- Roadmap — [Hash Tables](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/hash-tables@kSy-8ubESdmIX4Fyl8TSu.md>)
- Python exercise 10 — [Distinct words in sorted order](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-10>)
- Python exercise 93 — [Set intersection](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-93>)
- Python exercise 94 — [Deduplicate while preserving order](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-94>)
- Handbook §4, printed page 35 — [Data structures: sets and maps](<https://cses.fi/book/book.pdf#page=45>)

##### Prefix sums — `dsa:prefix-sums`

- **Scope:** Precompute running totals once so any range sum costs O(1), and count subarrays with hash maps.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/prefix-sums.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/prefix-sums.yaml>)
- **Prerequisites:** `dsa:arrays-hashing`
- **Key points:** p[i] holds the sum of the first i elements; sum(l..r) = p[r+1] − p[l].; One O(n) precomputation makes every range query O(1).; Subarrays summing to k ⇔ earlier prefix equal to current − k; count with a hash map.; Prefix ideas extend to 2D, XOR, counts and difference arrays.
- **Pitfalls:** Off-by-one between p indexes and array indexes.; Forgetting to seed the map with prefix 0 (count 1).; 32-bit overflow on large sums.
- **Local judge problems:** [Range sum queries](<D:/Socrat/content/courses/dsa/problems/range-sum-queries.yaml>) (`range-sum-queries`, easy); [Subarrays summing to K](<D:/Socrat/content/courses/dsa/problems/subarray-sum-k.yaml>) (`subarray-sum-k`, medium); [Balance point](<D:/Socrat/content/courses/dsa/problems/balance-point.yaml>) (`balance-point`, easy); [Profits that split evenly](<D:/Socrat/content/courses/dsa/problems/divisible-subarrays.yaml>) (`divisible-subarrays`, medium)
- **Quiz items:** `range-formula` (mcq, difficulty 2/5); `seed` (mcq, difficulty 3/5); `query-cost` (mcq, difficulty 1/5); `negatives` (mcq, difficulty 3/5); `count-k` (mcq, difficulty 5/5); `inclusive-range` (mcq, difficulty 4/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral); `trace` (trace, 1 checks, adapters python,cpp,java); `predict` (predict, 1 checks, adapters python,cpp,java); `debug` (debug, 1 checks, adapters python,cpp,java)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 183 | 183 |
| Counting subarrays with a given sum | H2 | 211 | 211 |
| Variations you will meet | H2 | 50 | 50 |
| Worked walkthrough | H2 | 38 | 156 |
| Worked walkthrough > Why this works | H3 | 32 | 32 |
| Worked walkthrough > Boundary cases and cost | H3 | 36 | 36 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Introduction to prefix sums](<https://usaco.guide/silver/prefix-sums>) | USACO Guide | article / core | 30 | neutral |
| [Static Range Sum Queries](<https://cses.fi/problemset/task/1646>) | CSES | interactive / core | 15 | neutral |
| [Tech Interview Handbook: Array cheatsheet (prefix sums)](<https://www.techinterviewhandbook.org/algorithms/array/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Subarray Sum Equals K](<https://leetcode.com/problems/subarray-sum-equals-k/>) (LeetCode, medium)
- Practice — [Range Sum Query - Immutable](<https://leetcode.com/problems/range-sum-query-immutable/>) (LeetCode, easy)
- Practice — [Subarray Sums II](<https://cses.fi/problemset/task/1661>) (CSES, medium)
- Roadmap — [Array](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/array@lxY3ErxJ_D3zkSAXIBUpv.md>)
- Handbook §9.1, printed page 84 — [Static array queries: prefix sums](<https://cses.fi/book/book.pdf#page=94>)

##### Hashing patterns — `dsa:hashing`

- **Scope:** Complement lookups, grouping by a key, prefix sums with a hash map for subarray counts, and set-based sequence problems.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/hashing.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:arrays-hashing`, `dsa:prefix-sums`
- **Key points:** A hash map answers "have I seen this, and what did I store with it?" in O(1) on average.; Choose the key (what you look up) and the value (a count, a first index, a list).; Complement lookup: look up k − x before inserting x, so no element pairs with itself.; Group by key: a canonical key equal exactly when two items belong together.; Prefix state: a subarray sums to k when an earlier prefix equals total − k; seed the empty prefix.; Longest keeps the first index, shortest keeps the last, a count keeps how many.; Set sequences: only walk from run starts, where x − 1 is missing.
- **Pitfalls:** Inserting before looking up, so x pairs with itself.; A grouping key that collides, such as the sum of the letter codes.; Forgetting the empty prefix at index −1.; Overwriting the first index when the longest subarray is wanted.; A sliding window on an array with negative numbers.; Walking a run from every element instead of only from its start.
- **Local judge problems:** [Longest evenly shared run](<D:/Socrat/content/courses/dsa/problems/longest-divisible-run.yaml>) (`longest-divisible-run`, medium); [Balanced shifts](<D:/Socrat/content/courses/dsa/problems/balanced-segments.yaml>) (`balanced-segments`, medium)
- **Quiz items:** `lookup-first` (mcq, difficulty 1/5); `pairs-of-three` (mcq, difficulty 2/5); `canonical` (mcq, difficulty 2/5); `empty-prefix` (mcq, difficulty 2/5); `first-index` (mcq, difficulty 3/5); `longest-trace` (mcq, difficulty 3/5); `window-negatives` (mcq, difficulty 3/5); `remainder-key` (mcq, difficulty 4/5); `run-start` (mcq, difficulty 4/5); `shortest-last` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Complement lookup | H2 | 0 | 595 |
| Complement lookup > Recognition cues | H3 | 49 | 49 |
| Complement lookup > Template | H3 | 259 | 259 |
| Complement lookup > Anchor problem: pairs that sum to k | H3 | 101 | 101 |
| Complement lookup > Variants | H3 | 89 | 89 |
| Complement lookup > Contrast | H3 | 44 | 44 |
| Complement lookup > Common mistakes | H3 | 33 | 33 |
| Group by key | H2 | 0 | 532 |
| Group by key > Recognition cues | H3 | 35 | 35 |
| Group by key > Template | H3 | 251 | 251 |
| Group by key > Anchor problem: group anagrams | H3 | 86 | 86 |
| Group by key > Variants | H3 | 55 | 55 |
| Group by key > Contrast | H3 | 45 | 45 |
| Group by key > Common mistakes | H3 | 43 | 43 |
| Prefix state hash map | H2 | 0 | 1630 |
| Prefix state hash map > Recognition cues | H3 | 56 | 56 |
| Prefix state hash map > Template | H3 | 394 | 394 |
| Prefix state hash map > Anchor problem: longest subarray with sum k | H3 | 895 | 895 |
| Prefix state hash map > Variants | H3 | 122 | 122 |
| Prefix state hash map > Contrast | H3 | 76 | 76 |
| Prefix state hash map > Common mistakes | H3 | 67 | 67 |
| Set sequences | H2 | 0 | 534 |
| Set sequences > Recognition cues | H3 | 45 | 45 |
| Set sequences > Template | H3 | 247 | 247 |
| Set sequences > Anchor problem: longest consecutive sequence | H3 | 94 | 94 |
| Set sequences > Variants | H3 | 56 | 56 |
| Set sequences > Contrast | H3 | 37 | 37 |
| Set sequences > Common mistakes | H3 | 37 | 37 |
| Worked walkthrough | H2 | 138 | 392 |
| Worked walkthrough > Why this works | H3 | 87 | 87 |
| Worked walkthrough > Boundary cases and cost | H3 | 76 | 76 |
| Worked walkthrough > Check your understanding | H3 | 78 | 78 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Tech Interview Handbook: Hash table cheatsheet](<https://www.techinterviewhandbook.org/algorithms/hash-table/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Two Sum – HashMap](<https://www.youtube.com/watch?v=KLlXCFG5TnA>) | NeetCode | video / core | 8 | neutral |
| [USACO Guide: Introduction to prefix sums](<https://usaco.guide/silver/prefix-sums>) | USACO Guide | article / core | 30 | neutral |
| [Hash tables visualized](<https://visualgo.net/en/hashtable>) | VisuAlgo | visualizer / deep | 15 | neutral |

**Other authored/supplemental links**

- Practice — [Maximum Size Subarray Sum Equals k](<https://leetcode.com/problems/maximum-size-subarray-sum-equals-k/>) (LeetCode, medium)
- Practice — [Contiguous Array](<https://leetcode.com/problems/contiguous-array/>) (LeetCode, medium)
- Practice — [Subarray Sums Divisible by K](<https://leetcode.com/problems/subarray-sums-divisible-by-k/>) (LeetCode, medium)
- Practice — [Count Number of Nice Subarrays](<https://leetcode.com/problems/count-number-of-nice-subarrays/>) (LeetCode, medium)
- Practice — [4Sum II](<https://leetcode.com/problems/4sum-ii/>) (LeetCode, medium)
- Practice — [Isomorphic Strings](<https://leetcode.com/problems/isomorphic-strings/>) (LeetCode, easy)
- Practice — [Longest Consecutive Sequence](<https://leetcode.com/problems/longest-consecutive-sequence/>) (LeetCode, medium)
- Practice — [Subarray Divisibility](<https://cses.fi/problemset/task/1662>) (CSES, medium)
- Roadmap — [Hash Tables](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/hash-tables@kSy-8ubESdmIX4Fyl8TSu.md>)

#### Linear patterns — `linear-patterns`

Two pointers, sliding windows, stacks and binary search.

##### Two pointers — `dsa:two-pointers`

- **Scope:** Move two indexes through sorted or structured data to replace an O(n²) pair search with one O(n) sweep.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/two-pointers.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/two-pointers.yaml>)
- **Prerequisites:** `dsa:arrays-hashing`
- **Key points:** Two indexes, each moving at most n times, give an O(n) sweep.; Opposite ends on sorted data — move the pointer that cannot be part of an answer.; Read/write pointers filter or partition in place with O(1) space.; Sort, fix one element, two-pointer the rest for triples (3Sum).; Always be able to justify why a discarded element can never be in the answer.
- **Pitfalls:** Using opposite-end pointers on unsorted data.; Infinite loops when neither pointer moves in some branch.; Producing duplicate triples by not skipping equal values.
- **Local judge problems:** [Pair sum in a sorted array](<D:/Socrat/content/courses/dsa/problems/pair-sum-sorted.yaml>) (`pair-sum-sorted`, easy); [Container with most water](<D:/Socrat/content/courses/dsa/problems/container-water.yaml>) (`container-water`, medium); [Pairs with a fixed gap](<D:/Socrat/content/courses/dsa/problems/difference-pairs.yaml>) (`difference-pairs`, medium); [Squares in order](<D:/Socrat/content/courses/dsa/problems/sorted-squares.yaml>) (`sorted-squares`, easy)
- **Quiz items:** `which-moves` (mcq, difficulty 1/5); `correctness` (mcq, difficulty 3/5); `container` (mcq, difficulty 2/5); `three-sum` (mcq, difficulty 2/5); `dedupe-in-place` (mcq, difficulty 4/5); `pointer-invariant` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 46 | 46 |
| Shape 1 — opposite ends | H2 | 236 | 236 |
| Shape 2 — same direction (fast/slow) | H2 | 61 | 61 |
| Shape 3 — fix one, two-pointer the rest | H2 | 28 | 28 |
| Container With Most Water | H2 | 28 | 28 |
| When to reach for two pointers | H2 | 36 | 36 |
| Worked walkthrough | H2 | 42 | 161 |
| Worked walkthrough > Why this works | H3 | 31 | 31 |
| Worked walkthrough > Boundary cases and cost | H3 | 38 | 38 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Container With Most Water](<https://www.youtube.com/watch?v=UuiTKBwPgAo>) | NeetCode | video / core | 12 | neutral |
| [USACO Guide: Two pointers](<https://usaco.guide/silver/two-pointers>) | USACO Guide | article / core | 25 | neutral |
| [Tech Interview Handbook: Array cheatsheet (two pointers)](<https://www.techinterviewhandbook.org/algorithms/array/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Valid Palindrome](<https://leetcode.com/problems/valid-palindrome/>) (LeetCode, easy)
- Practice — [3Sum](<https://leetcode.com/problems/3sum/>) (LeetCode, medium)
- Practice — [Container With Most Water](<https://leetcode.com/problems/container-with-most-water/>) (LeetCode, medium)
- Practice — [Ferris Wheel](<https://cses.fi/problemset/task/1090>) (CSES, medium)
- Roadmap — [Two Pointer Technique](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/two-pointer-technique@itvhUXbe9dr9JN5ga2jYy.md>)
- Handbook §8.1, printed page 77 — [Two pointers method](<https://cses.fi/book/book.pdf#page=87>)

##### Sliding window — `dsa:sliding-window`

- **Scope:** Maintain a contiguous window and its summary as it slides, instead of recomputing every subarray.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/sliding-window.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/sliding-window.yaml>)
- **Prerequisites:** `dsa:two-pointers`, `dsa:hashing`
- **Key points:** A window [left, right] plus a running summary avoids recomputing every subarray.; Fixed-size windows add the entering element and remove the leaving one.; Variable windows expand right, shrink left while invalid, then record.; Requires monotonic validity; with negative sums use prefix sums instead.; Exactly-k counts can be atMost(k) − atMost(k − 1).
- **Pitfalls:** Applying a window to sums with negative numbers.; Recording the answer before restoring validity.; Moving left past a stale "last seen" position (check last[ch] ≥ left).
- **Local judge problems:** [Longest substring without repeats](<D:/Socrat/content/courses/dsa/problems/longest-unique-substring.yaml>) (`longest-unique-substring`, medium); [Best k-day streak](<D:/Socrat/content/courses/dsa/problems/max-window-sum.yaml>) (`max-window-sum`, easy); [Shortest stretch to reach a goal](<D:/Socrat/content/courses/dsa/problems/shortest-fundraiser.yaml>) (`shortest-fundraiser`, medium)
- **Quiz items:** `fixed-update` (mcq, difficulty 1/5); `negatives-fail` (mcq, difficulty 3/5); `complexity` (mcq, difficulty 2/5); `unique-trace` (mcq, difficulty 1/5); `negatives-break` (mcq, difficulty 4/5); `window-complexity` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 63 | 63 |
| Fixed-size window | H2 | 156 | 156 |
| Variable-size window: expand, then shrink | H2 | 205 | 205 |
| When does a sliding window work? | H2 | 52 | 52 |
| Interview tips | H2 | 38 | 38 |
| Worked walkthrough | H2 | 42 | 154 |
| Worked walkthrough > Why this works | H3 | 27 | 27 |
| Worked walkthrough > Boundary cases and cost | H3 | 35 | 35 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Longest Substring Without Repeating Characters](<https://www.youtube.com/watch?v=wiGpQwVHdE0>) | NeetCode | video / core | 7 | neutral |
| [Tech Interview Handbook: String cheatsheet (sliding window)](<https://www.techinterviewhandbook.org/algorithms/string/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [USACO Guide: Two pointers (windows)](<https://usaco.guide/silver/two-pointers>) | USACO Guide | article / deep | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Longest Substring Without Repeating Characters](<https://leetcode.com/problems/longest-substring-without-repeating-characters/>) (LeetCode, medium)
- Practice — [Minimum Window Substring](<https://leetcode.com/problems/minimum-window-substring/>) (LeetCode, hard)
- Practice — [Best Time to Buy and Sell Stock](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock/>) (LeetCode, easy)
- Roadmap — [Sliding Window Technique](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/sliding-window-technique@gbHVR-ojRxv9I0E5eSlWy.md>)
- Handbook §8.3, printed page 81 — [Sliding window minimum](<https://cses.fi/book/book.pdf#page=91>)

##### Stacks, queues and monotonic stacks — `dsa:stacks`

- **Scope:** Last-in-first-out and first-in-first-out containers, and the monotonic stack trick for "next greater" questions.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/stacks.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/stacks.yaml>)
- **Prerequisites:** `dsa:arrays-hashing`
- **Key points:** Stack = LIFO, queue = FIFO; both O(1) per operation with the right container.; A stack holds the most recent unfinished item — perfect for matching brackets.; Monotonic stacks answer next/previous greater/smaller in O(n) total.; Amortised analysis — each element is pushed and popped at most once.; Use deque for queues in Python, never list.pop(0).
- **Pitfalls:** Popping from an empty stack (check first).; Forgetting to check that the stack is empty at the end (unmatched openers).; Storing values instead of indexes when you need positions or distances.
- **Local judge problems:** [Balanced brackets](<D:/Socrat/content/courses/dsa/problems/balanced-brackets.yaml>) (`balanced-brackets`, easy); [Days until warmer](<D:/Socrat/content/courses/dsa/problems/next-greater.yaml>) (`next-greater`, medium); [Next taller building](<D:/Socrat/content/courses/dsa/problems/next-taller-building.yaml>) (`next-taller-building`, medium)
- **Quiz items:** `lifo` (mcq, difficulty 1/5); `queue-structure` (mcq, difficulty 1/5); `amortized` (mcq, difficulty 3/5); `brackets` (mcq, difficulty 2/5); `monotonic-direction` (mcq, difficulty 4/5); `largest-rectangle` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 97 | 97 |
| Stacks match "most recent unfinished thing" | H2 | 199 | 199 |
| The monotonic stack | H2 | 218 | 218 |
| Queues | H2 | 20 | 20 |
| Worked walkthrough | H2 | 38 | 156 |
| Worked walkthrough > Why this works | H3 | 27 | 27 |
| Worked walkthrough > Boundary cases and cost | H3 | 38 | 38 |
| Worked walkthrough > Check your understanding | H3 | 40 | 40 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Valid Parentheses – Stack](<https://www.youtube.com/watch?v=WTzjTskDFMg>) | NeetCode | video / core | 10 | neutral |
| [Daily Temperatures – Monotonic Stack](<https://www.youtube.com/watch?v=cTBiBSnjO3c>) | NeetCode | video / core | 13 | neutral |
| [Stacks and queues visualized](<https://visualgo.net/en/list>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Tech Interview Handbook: Stack cheatsheet](<https://www.techinterviewhandbook.org/algorithms/stack/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Valid Parentheses](<https://leetcode.com/problems/valid-parentheses/>) (LeetCode, easy)
- Practice — [Min Stack](<https://leetcode.com/problems/min-stack/>) (LeetCode, medium)
- Practice — [Daily Temperatures](<https://leetcode.com/problems/daily-temperatures/>) (LeetCode, medium)
- Roadmap — [Stacks](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/stacks@jvKRykGNy140FlquF2fcK.md>)
- Handbook §4.5, printed page 42 — [Other structures: stack, queue and deque](<https://cses.fi/book/book.pdf#page=52>)
- Handbook §8.2, printed page 79 — [Nearest smaller elements](<https://cses.fi/book/book.pdf#page=89>)

##### Monotonic stack and deque — `dsa:monotonic-stack`

- **Scope:** Next greater and smaller elements, spans, histogram areas, contribution counting and the sliding-window maximum deque.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/monotonic-stack.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:stacks`, `dsa:sliding-window`
- **Key points:** A monotonic stack keeps the indexes still waiting for an answer, in sorted value order.; An element is answered at the moment it is popped; each index is pushed and popped once, so O(n).; Scan direction and pop comparison pick next/previous and greater/smaller.; Store indexes when the answer is a distance or position.; Histogram: pop on a lower bar; area = height × (i − left − 1); end with a 0 bar.; Contribution: Σ a[i] · left[i] · right[i], strict on one side and non-strict on the other.; Monotonic deque: pop worse values from the back, expired ones from the front.
- **Pitfalls:** Taking the maximum to the right instead of the nearest greater.; Popping on <= versus < without thinking about equal values.; Pushing values when distances or expiry need indexes.; Forgetting the 0 sentinel bar in the histogram.; Using the same tie rule on both sides when counting subarrays.
- **Local judge problems:** [Nearest taller neighbour](<D:/Socrat/content/courses/dsa/problems/nearest-taller-either-side.yaml>) (`nearest-taller-either-side`, medium); [Peak totals](<D:/Socrat/content/courses/dsa/problems/peak-totals.yaml>) (`peak-totals`, medium)
- **Quiz items:** `nge-value` (mcq, difficulty 1/5); `amortised` (mcq, difficulty 2/5); `indexes` (mcq, difficulty 2/5); `histogram` (mcq, difficulty 3/5); `sentinel` (mcq, difficulty 3/5); `ties` (mcq, difficulty 4/5); `deque-why` (mcq, difficulty 4/5); `window-output` (output, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Next greater family | H2 | 0 | 1488 |
| Next greater family > Recognition cues | H3 | 55 | 55 |
| Next greater family > State, transition, base cases, answer, loop order | H3 | 128 | 128 |
| Next greater family > Template | H3 | 294 | 294 |
| Next greater family > Anchor problem: 2 1 2 4 3 | H3 | 776 | 776 |
| Next greater family > Variants | H3 | 109 | 109 |
| Next greater family > Contrast | H3 | 39 | 39 |
| Next greater family > Common mistakes | H3 | 59 | 59 |
| Spans and waiting times | H2 | 0 | 562 |
| Spans and waiting times > Recognition cues | H3 | 47 | 47 |
| Spans and waiting times > State, transition, base cases, answer, loop order | H3 | 44 | 44 |
| Spans and waiting times > Template | H3 | 282 | 282 |
| Spans and waiting times > Anchor problem: temperatures 73 74 75 71 69 72 76 73 | H3 | 51 | 51 |
| Spans and waiting times > Variants | H3 | 45 | 45 |
| Spans and waiting times > Contrast | H3 | 28 | 28 |
| Spans and waiting times > Common mistakes | H3 | 33 | 33 |
| Histogram area | H2 | 0 | 689 |
| Histogram area > Recognition cues | H3 | 30 | 30 |
| Histogram area > State, transition, base cases, answer, loop order | H3 | 75 | 75 |
| Histogram area > Template | H3 | 328 | 328 |
| Histogram area > Anchor problem: 2 1 5 6 2 3 | H3 | 83 | 83 |
| Histogram area > Variants | H3 | 59 | 59 |
| Histogram area > Contrast | H3 | 44 | 44 |
| Histogram area > Common mistakes | H3 | 41 | 41 |
| Contribution technique | H2 | 0 | 716 |
| Contribution technique > Recognition cues | H3 | 31 | 31 |
| Contribution technique > State, transition, base cases, answer, loop order | H3 | 78 | 78 |
| Contribution technique > Template | H3 | 408 | 408 |
| Contribution technique > Anchor problem: 3 1 2 4 | H3 | 86 | 86 |
| Contribution technique > Variants | H3 | 29 | 29 |
| Contribution technique > Contrast | H3 | 36 | 36 |
| Contribution technique > Common mistakes | H3 | 21 | 21 |
| Monotonic deque | H2 | 0 | 706 |
| Monotonic deque > Recognition cues | H3 | 34 | 34 |
| Monotonic deque > State, transition, base cases, answer, loop order | H3 | 60 | 60 |
| Monotonic deque > Template | H3 | 314 | 314 |
| Monotonic deque > Anchor problem: 1 3 −1 −3 5 3 6 7, k = 3 | H3 | 121 | 121 |
| Monotonic deque > Variants | H3 | 65 | 65 |
| Monotonic deque > Contrast | H3 | 38 | 38 |
| Monotonic deque > Common mistakes | H3 | 40 | 40 |
| Worked walkthrough | H2 | 144 | 355 |
| Worked walkthrough > Why this works | H3 | 70 | 70 |
| Worked walkthrough > Boundary cases and cost | H3 | 53 | 53 |
| Worked walkthrough > Check your understanding | H3 | 75 | 75 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Stack](<https://www.techinterviewhandbook.org/algorithms/stack/>) | Tech Interview Handbook | article / core | 15 | neutral |
| [Minimum stack / Minimum queue](<https://cp-algorithms.com/data_structures/stack_queue_modification.html>) | CP-Algorithms | article / deep | 20 | neutral |
| [Competitive Programmer's Handbook, chapter 8: Amortized analysis](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 30 | neutral |

**Other authored/supplemental links**

- Practice — [Next Greater Element II](<https://leetcode.com/problems/next-greater-element-ii/>) (LeetCode, medium)
- Practice — [Nearest Smaller Values](<https://cses.fi/problemset/task/1645>) (CSES, medium)
- Practice — [Daily Temperatures](<https://leetcode.com/problems/daily-temperatures/>) (LeetCode, medium)
- Practice — [Online Stock Span](<https://leetcode.com/problems/online-stock-span/>) (LeetCode, medium)
- Practice — [Largest Rectangle in Histogram](<https://leetcode.com/problems/largest-rectangle-in-histogram/>) (LeetCode, hard)
- Practice — [Sum of Subarray Minimums](<https://leetcode.com/problems/sum-of-subarray-minimums/>) (LeetCode, medium)
- Practice — [Sliding Window Maximum](<https://leetcode.com/problems/sliding-window-maximum/>) (LeetCode, hard)
- Practice — [Trapping Rain Water](<https://leetcode.com/problems/trapping-rain-water/>) (LeetCode, hard)
- Practice — [132 Pattern](<https://leetcode.com/problems/132-pattern/>) (LeetCode, medium)
- Practice — [Remove K Digits](<https://leetcode.com/problems/remove-k-digits/>) (LeetCode, medium)
- Roadmap — [Stacks](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/stacks@jvKRykGNy140FlquF2fcK.md>)

##### Binary search — `dsa:binary-search`

- **Scope:** Halve the search space each step — on sorted arrays and on the answer itself.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/binary-search.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/binary-search.yaml>)
- **Prerequisites:** `dsa:complexity`, `dsa:arrays-hashing`
- **Key points:** Binary search halves the range each step — O(log n).; Use one template - the first index where a monotonic condition becomes true.; Lower/upper bounds give existence, counts and insertion positions.; Binary search on the answer when feasibility is monotonic.; mid = lo + (hi − lo) / 2 avoids overflow.
- **Pitfalls:** Infinite loops from lo = mid instead of mid + 1.; Using it on unsorted data, or on a non-monotonic condition.; Forgetting the "not found" case (index n).
- **Local judge problems:** [Count in range](<D:/Socrat/content/courses/dsa/problems/lower-bound-queries.yaml>) (`lower-bound-queries`, medium); [Minimum reading speed](<D:/Socrat/content/courses/dsa/problems/koko-speed.yaml>) (`koko-speed`, medium); [Whole-number square root](<D:/Socrat/content/courses/dsa/problems/whole-square-root.yaml>) (`whole-square-root`, medium)
- **Quiz items:** `steps` (mcq, difficulty 1/5); `count-x` (mcq, difficulty 2/5); `answer-search` (mcq, difficulty 2/5); `overflow` (mcq, difficulty 2/5); `midpoint-overflow` (mcq, difficulty 4/5); `infinite-search` (bug, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 4 checks, adapters neutral); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 41 | 41 |
| The one template to rely on | H2 | 316 | 316 |
| Binary search on the answer | H2 | 101 | 101 |
| Rotated arrays | H2 | 33 | 33 |
| Worked walkthrough | H2 | 37 | 166 |
| Worked walkthrough > Why this works | H3 | 36 | 36 |
| Worked walkthrough > Boundary cases and cost | H3 | 45 | 45 |
| Worked walkthrough > Check your understanding | H3 | 35 | 35 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Binary Search Algorithm in 100 Seconds](<https://www.youtube.com/watch?v=MFhxShGxHWc>) | Fireship | video / intro | 2 | neutral |
| [Binary Search – Leetcode 704](<https://www.youtube.com/watch?v=s4DPM8ct1pI>) | NeetCode | video / core | 9 | neutral |
| [USACO Guide: Binary search (including on the answer)](<https://usaco.guide/silver/binary-search>) | USACO Guide | article / deep | 40 | neutral |
| [Tech Interview Handbook: Sorting and searching](<https://www.techinterviewhandbook.org/algorithms/sorting-searching/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Search in Rotated Sorted Array](<https://leetcode.com/problems/search-in-rotated-sorted-array/>) (LeetCode, medium)
- Practice — [Koko Eating Bananas](<https://leetcode.com/problems/koko-eating-bananas/>) (LeetCode, medium)
- Practice — [Factory Machines](<https://cses.fi/problemset/task/1620>) (CSES, medium)
- Roadmap — [Binary Search](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-search@Wt74MRKaZcs8lYvfqjffT.md>)
- Python exercise 72 — [Search a sorted list](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-72>)
- Handbook §3.3, printed page 31 — [Binary search](<https://cses.fi/book/book.pdf#page=41>)

##### Binary search on the answer — `dsa:binary-search-on-answer`

- **Scope:** Minimise the maximum or maximise the minimum by binary searching over answers with a monotone yes/no check.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/binary-search-on-answer.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:binary-search`
- **Key points:** Three parts: a range, a monotone check, and a direction.; Min max problems search for the first cap that works; keep hi = mid on success.; Max min problems search for the last value that works; round mid up and keep lo = mid.; The check is usually one greedy O(n) pass.; Start min max split at max(a); below it the greedy count is wrong.; Using exactly k parts is allowed, so accept parts ≤ k.; Kth of two sorted: search how many come from a; the rest come from b.
- **Pitfalls:** Cutting near the average instead of searching the cap.; Starting the search below the largest element.; Accepting only parts < k.; Rounding mid down while searching for the last value that works.; Forgetting to sort positions before the greedy gap check.; A split range that lets the other array's count go out of bounds.
- **Local judge problems:** [Courier vans](<D:/Socrat/content/courses/dsa/problems/courier-vans.yaml>) (`courier-vans`, medium); [The k-th cheapest meal](<D:/Socrat/content/courses/dsa/problems/kth-cheapest-meal.yaml>) (`kth-cheapest-meal`, medium)
- **Quiz items:** `answer-shape` (mcq, difficulty 1/5); `split-range` (mcq, difficulty 2/5); `split-check` (mcq, difficulty 2/5); `average-trap` (mcq, difficulty 3/5); `exactly-k` (mcq, difficulty 3/5); `round-up` (mcq, difficulty 3/5); `gap-trace` (mcq, difficulty 4/5); `kth-split` (mcq, difficulty 4/5); `kth-value` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Min max split | H2 | 0 | 1767 |
| Min max split > Recognition cues | H3 | 41 | 41 |
| Min max split > Template | H3 | 470 | 470 |
| Min max split > Anchor problem: split into three parts | H3 | 1024 | 1024 |
| Min max split > Variants | H3 | 92 | 92 |
| Min max split > Contrast | H3 | 44 | 44 |
| Min max split > Common mistakes | H3 | 77 | 77 |
| Max min distance | H2 | 0 | 749 |
| Max min distance > Recognition cues | H3 | 50 | 50 |
| Max min distance > Template | H3 | 457 | 457 |
| Max min distance > Anchor problem: three stalls | H3 | 104 | 104 |
| Max min distance > Variants | H3 | 49 | 49 |
| Max min distance > Contrast | H3 | 45 | 45 |
| Max min distance > Common mistakes | H3 | 27 | 27 |
| Kth of two sorted | H2 | 0 | 928 |
| Kth of two sorted > Recognition cues | H3 | 46 | 46 |
| Kth of two sorted > Template | H3 | 472 | 472 |
| Kth of two sorted > Anchor problem: the 6th smallest | H3 | 206 | 206 |
| Kth of two sorted > Variants | H3 | 69 | 69 |
| Kth of two sorted > Contrast | H3 | 54 | 54 |
| Kth of two sorted > Common mistakes | H3 | 63 | 63 |
| Worked walkthrough | H2 | 99 | 384 |
| Worked walkthrough > Why this works | H3 | 121 | 121 |
| Worked walkthrough > Boundary cases and cost | H3 | 74 | 74 |
| Worked walkthrough > Check your understanding | H3 | 77 | 77 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Binary search (on the answer)](<https://usaco.guide/silver/binary-search>) | USACO Guide | article / core | 40 | neutral |
| [Tech Interview Handbook: Sorting and searching](<https://www.techinterviewhandbook.org/algorithms/sorting-searching/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Array Division](<https://cses.fi/problemset/task/1085>) | CSES | interactive / deep | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Split Array Largest Sum](<https://leetcode.com/problems/split-array-largest-sum/>) (LeetCode, hard)
- Practice — [Capacity To Ship Packages Within D Days](<https://leetcode.com/problems/capacity-to-ship-packages-within-d-days/>) (LeetCode, medium)
- Practice — [Minimum Number of Days to Make m Bouquets](<https://leetcode.com/problems/minimum-number-of-days-to-make-m-bouquets/>) (LeetCode, medium)
- Practice — [Magnetic Force Between Two Balls](<https://leetcode.com/problems/magnetic-force-between-two-balls/>) (LeetCode, medium)
- Practice — [Maximum Tastiness of Candy Basket](<https://leetcode.com/problems/maximum-tastiness-of-candy-basket/>) (LeetCode, medium)
- Practice — [Median of Two Sorted Arrays](<https://leetcode.com/problems/median-of-two-sorted-arrays/>) (LeetCode, hard)
- Practice — [Kth Smallest Element in a Sorted Matrix](<https://leetcode.com/problems/kth-smallest-element-in-a-sorted-matrix/>) (LeetCode, medium)
- Practice — [Array Division](<https://cses.fi/problemset/task/1085>) (CSES, medium)
- Roadmap — [Binary Search](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-search@Wt74MRKaZcs8lYvfqjffT.md>)

#### Sorting and greedy — `ordering`

Sort to reveal structure, then make provably safe greedy choices.

##### Sorting — `dsa:sorting`

- **Scope:** How merge sort and quicksort reach O(n log n), how to sort by custom rules, and why sorting first simplifies problems.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/sorting.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/sorting.yaml>)
- **Prerequisites:** `dsa:complexity`, `zero:recursion`
- **Key points:** Comparison sorting is O(n log n) at best; library sorts already achieve it.; Merge sort - split, recurse, merge — stable, O(n log n), O(n) space; counts inversions.; Quicksort is fast on average; quickselect finds the k-th element in O(n) average.; Sort by tuples / comparators for multi-key ordering.; Sorting first often turns hard problems into easy scans.
- **Pitfalls:** Non-strict comparators in C++ (using <=).; Forgetting tie-breaking rules required by the problem.; Sorting inside a loop, accidentally making O(n² log n).
- **Local judge problems:** [Leaderboard](<D:/Socrat/content/courses/dsa/problems/rank-students.yaml>) (`rank-students`, easy); [Count inversions](<D:/Socrat/content/courses/dsa/problems/count-inversions.yaml>) (`count-inversions`, hard)
- **Quiz items:** `merge-complexity` (mcq, difficulty 2/5); `stable` (mcq, difficulty 2/5); `quicksort-worst` (mcq, difficulty 3/5); `counting` (mcq, difficulty 2/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 60 | 60 |
| Merge sort: divide and conquer | H2 | 312 | 312 |
| Quicksort and quickselect | H2 | 40 | 40 |
| Sorting by your own rules | H2 | 64 | 64 |
| Counting sort | H2 | 21 | 21 |
| Worked walkthrough | H2 | 32 | 147 |
| Worked walkthrough > Why this works | H3 | 28 | 28 |
| Worked walkthrough > Boundary cases and cost | H3 | 41 | 41 |
| Worked walkthrough > Check your understanding | H3 | 33 | 33 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Sorting algorithms visualized](<https://visualgo.net/en/sorting>) | VisuAlgo | visualizer / core | 20 | neutral |
| [CS50x Week 3: Algorithms (searching, sorting, recursion)](<https://cs50.harvard.edu/x/2024/weeks/3/>) | Harvard CS50 | course / core | 120 | neutral |
| [Kth Largest Element in an Array – Quick Select](<https://www.youtube.com/watch?v=XEmy13g1Qxc>) | NeetCode | video / deep | 15 | neutral |
| [Tech Interview Handbook: Sorting and searching](<https://www.techinterviewhandbook.org/algorithms/sorting-searching/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Sort an Array](<https://leetcode.com/problems/sort-an-array/>) (LeetCode, medium)
- Practice — [Kth Largest Element in an Array](<https://leetcode.com/problems/kth-largest-element-in-an-array/>) (LeetCode, medium)
- Practice — [Stick Lengths](<https://cses.fi/problemset/task/1074>) (CSES, easy)
- Roadmap — [Sorting Algorithms](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/sorting-algorithms@WzFkdkcbL8ea9DBkjfSwa.md>)
- Python exercise 8 — [Sort a sequence of words](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-8>)
- Handbook §3, printed page 25 — [Sorting](<https://cses.fi/book/book.pdf#page=35>)

##### Intervals — `dsa:intervals`

- **Scope:** Sort intervals by start, then sweep once to merge, insert, or detect overlaps.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/intervals.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/intervals.yaml>)
- **Prerequisites:** `dsa:sorting`
- **Key points:** Sort by start; then overlaps involve only neighbours in the sweep.; Overlap of [a, b] and [c, d] ⇔ a ≤ d and c ≤ b — clarify whether touching counts.; Merge by extending the last block with max(end).; Sweep line - +1/−1 events sorted by time give concurrent counts.; Sorting by end time enables greedy selection.
- **Pitfalls:** Forgetting max() when merging nested intervals.; Mis-ordering events at equal times (end before start or vice versa).; Not clarifying whether touching intervals overlap.
- **Local judge problems:** [Merge study sessions](<D:/Socrat/content/courses/dsa/problems/merge-intervals.yaml>) (`merge-intervals`, medium)
- **Quiz items:** `overlap` (mcq, difficulty 1/5); `nested` (mcq, difficulty 2/5); `rooms` (mcq, difficulty 2/5); `first-step` (mcq, difficulty 1/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 42 | 42 |
| Overlap test | H2 | 40 | 40 |
| Merge overlapping intervals | H2 | 144 | 144 |
| Other classic interval questions | H2 | 103 | 103 |
| Sweep line in one sentence | H2 | 22 | 22 |
| Worked walkthrough | H2 | 34 | 145 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 35 | 35 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Merge Intervals – Sorting](<https://www.youtube.com/watch?v=44H3cEC2fFM>) | NeetCode | video / core | 9 | neutral |
| [Tech Interview Handbook: Interval cheatsheet](<https://www.techinterviewhandbook.org/algorithms/interval/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Restaurant Customers (sweep line practice)](<https://cses.fi/problemset/task/1619>) | CSES | interactive / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Merge Intervals](<https://leetcode.com/problems/merge-intervals/>) (LeetCode, medium)
- Practice — [Insert Interval](<https://leetcode.com/problems/insert-interval/>) (LeetCode, medium)
- Practice — [Non-overlapping Intervals](<https://leetcode.com/problems/non-overlapping-intervals/>) (LeetCode, medium)
- Practice — [Restaurant Customers](<https://cses.fi/problemset/task/1619>) (CSES, easy)
- Roadmap — [Merge Intervals](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/merge-intervals@S2mBvlFTd673XcXxisD5P.md>)

##### Greedy algorithms — `dsa:greedy`

- **Scope:** Make the locally best choice at each step — and learn to prove when that is globally optimal.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/greedy.yaml>); [released atom pack](<D:/Socrat/content/atoms/dsa/greedy.yaml>)
- **Prerequisites:** `dsa:sorting`, `dsa:intervals`
- **Key points:** Greedy takes the locally best choice and never reconsiders.; Usually - sort by the right key, then one pass.; Justify with an exchange argument — swapping into the greedy choice never hurts.; Test greedy ideas against brute force on small cases; if it fails, think DP.
- **Pitfalls:** Picking an intuitive but wrong ordering (shortest, earliest start).; Assuming greedy works for general coin systems.; Skipping the proof and missing a counterexample.
- **Local judge problems:** [Most mentoring sessions](<D:/Socrat/content/courses/dsa/problems/max-meetings.yaml>) (`max-meetings`, medium); [Jump to the end](<D:/Socrat/content/courses/dsa/problems/can-reach-end.yaml>) (`can-reach-end`, medium)
- **Quiz items:** `activity-key` (mcq, difficulty 2/5); `coins-fail` (mcq, difficulty 3/5); `exchange` (mcq, difficulty 3/5); `jump` (mcq, difficulty 2/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 52 | 52 |
| Example: activity selection | H2 | 171 | 171 |
| Proving it: the exchange argument | H2 | 55 | 55 |
| Example: can you reach the end? | H2 | 29 | 29 |
| When greedy fails | H2 | 52 | 52 |
| Signals that greedy might work | H2 | 31 | 31 |
| Worked walkthrough | H2 | 37 | 144 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 33 | 33 |
| Worked walkthrough > Check your understanding | H3 | 35 | 35 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Jump Game – Greedy](<https://www.youtube.com/watch?v=Yan0cv2cLy8>) | NeetCode | video / core | 10 | neutral |
| [USACO Guide: Greedy algorithms with sorting](<https://usaco.guide/silver/greedy-sorting>) | USACO Guide | article / core | 35 | neutral |
| [Movie Festival (activity selection)](<https://cses.fi/problemset/task/1629>) | CSES | interactive / core | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Jump Game](<https://leetcode.com/problems/jump-game/>) (LeetCode, medium)
- Practice — [Gas Station](<https://leetcode.com/problems/gas-station/>) (LeetCode, medium)
- Practice — [Movie Festival](<https://cses.fi/problemset/task/1629>) (CSES, easy)
- Practice — [Apartments](<https://cses.fi/problemset/task/1084>) (CSES, easy)
- Roadmap — [Greedy Algorithms](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/greedy-algorithms@qUlqyTjk3XKF9DEm6Lsgb.md>)
- Handbook §6, printed page 57 — [Greedy algorithms](<https://cses.fi/book/book.pdf#page=67>)

#### Linked structures, recursion and backtracking — `recursive-structures`

Pointers and nodes, recursion patterns, and exhaustive search done cleanly.

##### Linked lists — `dsa:linked-lists`

- **Scope:** Nodes connected by pointers — O(1) insertion and removal anywhere, and the pointer-juggling interviewers love.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/linked-lists.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:complexity`, `zero:classes-and-objects`
- **Key points:** Nodes hold a value and a pointer to the next node; no random access.; Insert/delete next to a known node in O(1); finding a node is O(n).; Rewire pointers in the right order; a dummy head removes edge cases.; Reverse in place with prev/curr/next in one pass.; Fast/slow pointers find the middle and detect cycles in O(1) space.
- **Pitfalls:** Losing the rest of the list by overwriting next too early.; Null pointer access at the end of the list.; Forgetting to update head when the first node changes.
- **Local judge problems:** [Playlist editor](<D:/Socrat/content/courses/dsa/problems/playlist-editor.yaml>) (`playlist-editor`, medium)
- **Quiz items:** `insert-order` (mcq, difficulty 2/5); `access-cost` (mcq, difficulty 1/5); `cycle` (mcq, difficulty 2/5); `dummy` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 187 | 187 |
| Core operations | H2 | 58 | 58 |
| Reverse a list (the classic) | H2 | 99 | 99 |
| Fast and slow pointers | H2 | 38 | 38 |
| Doubly linked lists | H2 | 36 | 36 |
| Simulating linked lists with arrays | H2 | 33 | 33 |
| Worked walkthrough | H2 | 32 | 140 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 34 | 34 |
| Worked walkthrough > Check your understanding | H3 | 35 | 35 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Reverse Linked List – Iterative and Recursive](<https://www.youtube.com/watch?v=G0_I-ZF0S38>) | NeetCode | video / core | 8 | neutral |
| [Linked lists visualized](<https://visualgo.net/en/list>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Tech Interview Handbook: Linked list cheatsheet](<https://www.techinterviewhandbook.org/algorithms/linked-list/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Reverse Linked List](<https://leetcode.com/problems/reverse-linked-list/>) (LeetCode, easy)
- Practice — [Merge Two Sorted Lists](<https://leetcode.com/problems/merge-two-sorted-lists/>) (LeetCode, easy)
- Practice — [Linked List Cycle](<https://leetcode.com/problems/linked-list-cycle/>) (LeetCode, easy)
- Practice — [Reorder List](<https://leetcode.com/problems/reorder-list/>) (LeetCode, medium)
- Roadmap — [Linked Lists](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/linked-lists@bRu9u8pEAQ1TmKygjIjyI.md>)

##### Recursion patterns — `dsa:recursion-patterns`

- **Scope:** Trust the function: pick or not pick, generate strings, recurse on stacks, divide and reduce, and fast power.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/recursion-patterns.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:recursion`, `dsa:complexity`
- **Key points:** Name the state, the choices and the base case; trust the smaller call.; Pick or not pick: two branches per index; a choice is finished only when every index is decided.; Carry the running total in the call, so each leaf costs O(1).; String generation: only extend valid prefixes, such as ")" only when closed < opened.; Recursive stack ops: each call holds one popped element; reverse needs insert-at-bottom.; Divide and reduce: answer for n from the answer for a smaller n, shifted back (Josephus).; Fast power: compute the half once and square it, O(log n).
- **Pitfalls:** Returning as soon as the sum is reached, before every index is decided.; A base case that counts every choice.; Allowing ")" whenever fewer than n have been used.; Pushing the held element back on top when reversing a stack.; Forgetting to shift the smaller Josephus answer.; Calling the half power twice.
- **Local judge problems:** [Squad selection](<D:/Socrat/content/courses/dsa/problems/squad-selection.yaml>) (`squad-selection`, medium); [Seating plans](<D:/Socrat/content/courses/dsa/problems/seating-plans.yaml>) (`seating-plans`, medium)
- **Quiz items:** `two-branches` (mcq, difficulty 1/5); `leaves` (mcq, difficulty 2/5); `early-stop` (mcq, difficulty 2/5); `close-rule` (mcq, difficulty 2/5); `catalan-three` (mcq, difficulty 3/5); `stack-bottom` (mcq, difficulty 3/5); `josephus` (mcq, difficulty 4/5); `half-twice` (mcq, difficulty 4/5); `memo-link` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Pick or not pick | H2 | 0 | 1367 |
| Pick or not pick > Recognition cues | H3 | 44 | 44 |
| Pick or not pick > Template | H3 | 340 | 340 |
| Pick or not pick > Anchor problem: subsequences with sum k | H3 | 795 | 795 |
| Pick or not pick > Variants | H3 | 70 | 70 |
| Pick or not pick > Contrast | H3 | 41 | 41 |
| Pick or not pick > Common mistakes | H3 | 58 | 58 |
| String generation | H2 | 0 | 569 |
| String generation > Recognition cues | H3 | 51 | 51 |
| String generation > Template | H3 | 270 | 270 |
| String generation > Anchor problem: three pairs | H3 | 86 | 86 |
| String generation > Variants | H3 | 64 | 64 |
| String generation > Contrast | H3 | 42 | 42 |
| String generation > Common mistakes | H3 | 39 | 39 |
| Recursive stack ops | H2 | 0 | 622 |
| Recursive stack ops > Recognition cues | H3 | 40 | 40 |
| Recursive stack ops > Template | H3 | 387 | 387 |
| Recursive stack ops > Anchor problem: reverse 1 2 3 4 | H3 | 75 | 75 |
| Recursive stack ops > Variants | H3 | 35 | 35 |
| Recursive stack ops > Contrast | H3 | 31 | 31 |
| Recursive stack ops > Common mistakes | H3 | 34 | 34 |
| Divide and reduce | H2 | 0 | 553 |
| Divide and reduce > Recognition cues | H3 | 49 | 49 |
| Divide and reduce > Template | H3 | 201 | 201 |
| Divide and reduce > Anchor problem: five people, every second one | H3 | 123 | 123 |
| Divide and reduce > Variants | H3 | 81 | 81 |
| Divide and reduce > Contrast | H3 | 38 | 38 |
| Divide and reduce > Common mistakes | H3 | 41 | 41 |
| Fast power | H2 | 0 | 511 |
| Fast power > Recognition cues | H3 | 25 | 25 |
| Fast power > Template | H3 | 258 | 258 |
| Fast power > Anchor problem: 3¹³ mod 1000 | H3 | 89 | 89 |
| Fast power > Variants | H3 | 50 | 50 |
| Fast power > Contrast | H3 | 32 | 32 |
| Fast power > Common mistakes | H3 | 39 | 39 |
| Worked walkthrough | H2 | 121 | 369 |
| Worked walkthrough > Why this works | H3 | 85 | 85 |
| Worked walkthrough > Boundary cases and cost | H3 | 78 | 78 |
| Worked walkthrough > Check your understanding | H3 | 72 | 72 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Recursion in Programming – Full Course](<https://www.youtube.com/watch?v=IJDJ0kBx2LM>) | freeCodeCamp | video / core | 110 | neutral |
| [Tech Interview Handbook: Recursion cheatsheet](<https://www.techinterviewhandbook.org/algorithms/recursion/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Recursion trees visualized](<https://visualgo.net/en/recursion>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Subsets – Backtracking](<https://www.youtube.com/watch?v=REOH22Xwdkk>) | NeetCode | video / deep | 9 | neutral |

**Other authored/supplemental links**

- Practice — [Subsets](<https://leetcode.com/problems/subsets/>) (LeetCode, medium)
- Practice — [Target Sum](<https://leetcode.com/problems/target-sum/>) (LeetCode, medium)
- Practice — [Combination Sum](<https://leetcode.com/problems/combination-sum/>) (LeetCode, medium)
- Practice — [Generate Parentheses](<https://leetcode.com/problems/generate-parentheses/>) (LeetCode, medium)
- Practice — [Letter Combinations of a Phone Number](<https://leetcode.com/problems/letter-combinations-of-a-phone-number/>) (LeetCode, medium)
- Practice — [Find the Winner of the Circular Game](<https://leetcode.com/problems/find-the-winner-of-the-circular-game/>) (LeetCode, medium)
- Practice — [K-th Symbol in Grammar](<https://leetcode.com/problems/k-th-symbol-in-grammar/>) (LeetCode, medium)
- Practice — [Pow(x, n)](<https://leetcode.com/problems/powx-n/>) (LeetCode, medium)
- Practice — [Tower of Hanoi](<https://cses.fi/problemset/task/2165>) (CSES, easy)
- Roadmap — [Backtracking](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/backtracking@mKoC5o__gLSTjAlq8iXkV.md>)

##### Backtracking — `dsa:backtracking`

- **Scope:** Explore every choice recursively — choose, explore, un-choose — and prune branches that cannot succeed.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/backtracking.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:recursion`, `dsa:complexity`, `dsa:recursion-patterns`
- **Key points:** Backtracking explores a decision tree - choose, explore, un-choose.; Record copies of the current state, never the shared object.; Prune branches that can no longer succeed — this is what makes it fast enough.; Expect exponential growth; check n is small (≤ ~20 subsets, ≤ ~10 permutations).
- **Pitfalls:** Saving a reference to the mutable current list instead of a copy.; Missing the un-choose step.; Generating duplicate results from duplicate input values.
- **Local judge problems:** [Subsets with target sum](<D:/Socrat/content/courses/dsa/problems/subset-sum-count.yaml>) (`subset-sum-count`, medium); [N-Queens](<D:/Socrat/content/courses/dsa/problems/n-queens-count.yaml>) (`n-queens-count`, hard)
- **Quiz items:** `template` (mcq, difficulty 1/5); `subset-count` (mcq, difficulty 1/5); `copy-bug` (mcq, difficulty 2/5); `queens-prune` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 53 | 53 |
| The template: choose → explore → un-choose | H2 | 169 | 169 |
| Pruning: cut dead branches early | H2 | 146 | 146 |
| Bugs to watch for | H2 | 41 | 41 |
| Worked walkthrough | H2 | 35 | 145 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 32 | 32 |
| Worked walkthrough > Check your understanding | H3 | 39 | 39 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Subsets – Backtracking](<https://www.youtube.com/watch?v=REOH22Xwdkk>) | NeetCode | video / core | 9 | neutral |
| [Recursion in Programming – Full Course (backtracking section)](<https://www.youtube.com/watch?v=IJDJ0kBx2LM>) | freeCodeCamp | video / core | 40 | neutral |
| [Chessboard and Queens](<https://cses.fi/problemset/task/1624>) | CSES | interactive / deep | 30 | neutral |

**Other authored/supplemental links**

- Practice — [Subsets](<https://leetcode.com/problems/subsets/>) (LeetCode, medium)
- Practice — [Permutations](<https://leetcode.com/problems/permutations/>) (LeetCode, medium)
- Practice — [Combination Sum](<https://leetcode.com/problems/combination-sum/>) (LeetCode, medium)
- Practice — [Word Search](<https://leetcode.com/problems/word-search/>) (LeetCode, medium)
- Roadmap — [Backtracking](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/backtracking@mKoC5o__gLSTjAlq8iXkV.md>)
- Python exercise 99 — [Enumerate permutations](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-99>)
- Handbook §5.3, printed page 50 — [Backtracking and pruning](<https://cses.fi/book/book.pdf#page=60>)

#### Trees and heaps — `trees`

Recursive data, ordered trees, priority queues and prefix trees.

##### Binary trees — `dsa:binary-trees`

- **Scope:** Recursive data where each node has up to two children — traverse depth-first and breadth-first, and solve with recursion.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/binary-trees.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:linked-lists`, `zero:recursion`
- **Key points:** A tree is a root plus left and right subtrees — solve recursively.; Pre-, in- and post-order are depth-first; level order uses a queue.; Return values up (height, size) or pass state down (depth, range).; Deep trees can overflow recursion; iterate with an explicit stack or reverse BFS order.
- **Pitfalls:** Forgetting the empty-tree (null) base case.; Confusing height in nodes vs. height in edges — confirm the definition.; Stack overflow on degenerate (chain-shaped) trees.
- **Local judge problems:** [Level sums](<D:/Socrat/content/courses/dsa/problems/tree-levels.yaml>) (`tree-levels`, easy); [Binary tree diameter](<D:/Socrat/content/courses/dsa/problems/tree-diameter.yaml>) (`tree-diameter`, medium)
- **Quiz items:** `inorder` (mcq, difficulty 1/5); `bfs-structure` (mcq, difficulty 1/5); `height-trace` (mcq, difficulty 1/5); `postorder-use` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 191 | 191 |
| Depth-first traversals | H2 | 52 | 52 |
| Breadth-first (level order) | H2 | 67 | 67 |
| Two kinds of recursive answers | H2 | 56 | 56 |
| Trees in input | H2 | 54 | 54 |
| Worked walkthrough | H2 | 36 | 146 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 33 | 33 |
| Worked walkthrough > Check your understanding | H3 | 38 | 38 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Invert Binary Tree – DFS](<https://www.youtube.com/watch?v=OnSn2XEQ4MY>) | NeetCode | video / core | 4 | neutral |
| [Maximum Depth of Binary Tree – 3 Solutions](<https://www.youtube.com/watch?v=hTM3phVI6YQ>) | NeetCode | video / core | 12 | neutral |
| [Tech Interview Handbook: Tree cheatsheet](<https://www.techinterviewhandbook.org/algorithms/tree/>) | Tech Interview Handbook | article / core | 12 | neutral |
| [Data Structures Easy to Advanced (trees section)](<https://www.youtube.com/watch?v=RBSGKlAvoiM>) | freeCodeCamp | video / deep | 60 | neutral |

**Other authored/supplemental links**

- Practice — [Invert Binary Tree](<https://leetcode.com/problems/invert-binary-tree/>) (LeetCode, easy)
- Practice — [Maximum Depth of Binary Tree](<https://leetcode.com/problems/maximum-depth-of-binary-tree/>) (LeetCode, easy)
- Practice — [Binary Tree Level Order Traversal](<https://leetcode.com/problems/binary-tree-level-order-traversal/>) (LeetCode, medium)
- Practice — [Tree Diameter](<https://cses.fi/problemset/task/1131>) (CSES, medium)
- Roadmap — [Binary Trees](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-trees@RPU5CGp2Li5lk0UB-zNHT.md>)
- Roadmap — [Tree Traversal](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/tree-traversal@2Od5lNc6fCM6Gyj_axj4n.md>)
- Handbook §14, printed page 133 — [Tree algorithms](<https://cses.fi/book/book.pdf#page=143>)

##### Binary tree patterns — `dsa:tree-patterns`

- **Scope:** Return information from children, views and columns, root paths, lowest common ancestor, distance K and width.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/tree-patterns.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:binary-trees`
- **Key points:** Return info: a node returns what its parent can extend and records the full answer in a global.; For path sums, return one branch (val + max(gl, gr)) but record both (val + gl + gr).; Process children before parents with reverse BFS order to avoid deep recursion.; Views and levels: BFS level by level; take the first or last node of each level.; Root paths: pass the running sum, maximum or number down; check at leaves.; LCA: equalise depths, then lift both until they meet.; Distance K and width: add parent edges for BFS; number positions 2p and 2p + 1, renumbered per level.
- **Pitfalls:** Returning a two-sided path to the parent.; Not dropping negative branches, or starting the best at 0.; Following only right children for the right view.; Treating a node with one child as a leaf.; Lifting both nodes before their depths are equal.; Searching only downwards for distance K.
- **Local judge problems:** [Balanced splits](<D:/Socrat/content/courses/dsa/problems/balanced-splits.yaml>) (`balanced-splits`, medium); [Shortest walk to a leaf](<D:/Socrat/content/courses/dsa/problems/nearest-leaf.yaml>) (`nearest-leaf`, medium)
- **Quiz items:** `return-vs-record` (mcq, difficulty 2/5); `bent-path` (mcq, difficulty 3/5); `right-view` (mcq, difficulty 1/5); `leaf` (mcq, difficulty 2/5); `lca-self` (mcq, difficulty 3/5); `lca-lift` (mcq, difficulty 3/5); `distance-up` (mcq, difficulty 4/5); `width` (mcq, difficulty 4/5); `good-nodes` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Return info from children | H2 | 0 | 1982 |
| Return info from children > Recognition cues | H3 | 64 | 64 |
| Return info from children > State, transition, base cases, answer, loop order | H3 | 142 | 142 |
| Return info from children > Template | H3 | 526 | 526 |
| Return info from children > Anchor problem: values 1 2 3 4 5 | H3 | 1058 | 1058 |
| Return info from children > Variants | H3 | 76 | 76 |
| Return info from children > Contrast | H3 | 40 | 40 |
| Return info from children > Common mistakes | H3 | 47 | 47 |
| Views and columns | H2 | 0 | 618 |
| Views and columns > Recognition cues | H3 | 30 | 30 |
| Views and columns > State, transition, base cases, answer, loop order | H3 | 56 | 56 |
| Views and columns > Template | H3 | 329 | 329 |
| Views and columns > Anchor problem: the right side view | H3 | 80 | 80 |
| Views and columns > Variants | H3 | 45 | 45 |
| Views and columns > Contrast | H3 | 33 | 33 |
| Views and columns > Common mistakes | H3 | 18 | 18 |
| Root paths | H2 | 0 | 714 |
| Root paths > Recognition cues | H3 | 31 | 31 |
| Root paths > State, transition, base cases, answer, loop order | H3 | 37 | 37 |
| Root paths > Template | H3 | 414 | 414 |
| Root paths > Anchor problem: paths summing to 22 | H3 | 81 | 81 |
| Root paths > Variants | H3 | 56 | 56 |
| Root paths > Contrast | H3 | 35 | 35 |
| Root paths > Common mistakes | H3 | 33 | 33 |
| Lowest common ancestor | H2 | 0 | 777 |
| Lowest common ancestor > Recognition cues | H3 | 30 | 30 |
| Lowest common ancestor > State, transition, base cases, answer, loop order | H3 | 47 | 47 |
| Lowest common ancestor > Template | H3 | 471 | 471 |
| Lowest common ancestor > Anchor problem: nodes 4 and 9 | H3 | 102 | 102 |
| Lowest common ancestor > Variants | H3 | 51 | 51 |
| Lowest common ancestor > Contrast | H3 | 28 | 28 |
| Lowest common ancestor > Common mistakes | H3 | 21 | 21 |
| Distance K | H2 | 0 | 770 |
| Distance K > Recognition cues | H3 | 30 | 30 |
| Distance K > State, transition, base cases, answer, loop order | H3 | 31 | 31 |
| Distance K > Template | H3 | 525 | 525 |
| Distance K > Anchor problem: target 2, K = 2 | H3 | 64 | 64 |
| Distance K > Variants | H3 | 41 | 41 |
| Distance K > Contrast | H3 | 29 | 29 |
| Distance K > Common mistakes | H3 | 22 | 22 |
| Width and indexing | H2 | 0 | 640 |
| Width and indexing > Recognition cues | H3 | 23 | 23 |
| Width and indexing > State, transition, base cases, answer, loop order | H3 | 57 | 57 |
| Width and indexing > Template | H3 | 408 | 408 |
| Width and indexing > Anchor problem: width 4 | H3 | 68 | 68 |
| Width and indexing > Variants | H3 | 26 | 26 |
| Width and indexing > Contrast | H3 | 18 | 18 |
| Width and indexing > Common mistakes | H3 | 15 | 15 |
| Worked walkthrough | H2 | 117 | 363 |
| Worked walkthrough > Why this works | H3 | 80 | 80 |
| Worked walkthrough > Boundary cases and cost | H3 | 54 | 54 |
| Worked walkthrough > Check your understanding | H3 | 99 | 99 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Tree](<https://www.techinterviewhandbook.org/algorithms/tree/>) | Tech Interview Handbook | article / core | 15 | neutral |
| [Lowest Common Ancestor](<https://cp-algorithms.com/graph/lca.html>) | CP-Algorithms | article / deep | 25 | neutral |
| [Competitive Programmer's Handbook, chapter 14: Tree algorithms](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [Binary Tree Maximum Path Sum](<https://leetcode.com/problems/binary-tree-maximum-path-sum/>) (LeetCode, hard)
- Practice — [Balanced Binary Tree](<https://leetcode.com/problems/balanced-binary-tree/>) (LeetCode, easy)
- Practice — [Binary Tree Right Side View](<https://leetcode.com/problems/binary-tree-right-side-view/>) (LeetCode, medium)
- Practice — [Vertical Order Traversal of a Binary Tree](<https://leetcode.com/problems/vertical-order-traversal-of-a-binary-tree/>) (LeetCode, hard)
- Practice — [Path Sum II](<https://leetcode.com/problems/path-sum-ii/>) (LeetCode, medium)
- Practice — [Count Good Nodes in Binary Tree](<https://leetcode.com/problems/count-good-nodes-in-binary-tree/>) (LeetCode, medium)
- Practice — [Lowest Common Ancestor of a Binary Tree](<https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/>) (LeetCode, medium)
- Practice — [All Nodes Distance K in Binary Tree](<https://leetcode.com/problems/all-nodes-distance-k-in-binary-tree/>) (LeetCode, medium)
- Practice — [Maximum Width of Binary Tree](<https://leetcode.com/problems/maximum-width-of-binary-tree/>) (LeetCode, medium)
- Practice — [Subordinates](<https://cses.fi/problemset/task/1674>) (CSES, easy)
- Roadmap — [Binary Trees](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-trees@RPU5CGp2Li5lk0UB-zNHT.md>)
- Roadmap — [Tree Traversal](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/tree-traversal@2Od5lNc6fCM6Gyj_axj4n.md>)

##### Binary search trees — `dsa:bst`

- **Scope:** Keep keys ordered in a tree so search, insert and delete follow one root-to-leaf path.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/bst.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:binary-trees`, `dsa:binary-search`, `dsa:tree-patterns`
- **Key points:** BST rule - left subtree keys < node < right subtree keys.; Search, insert and delete walk one path, costing O(height).; Inorder traversal of a BST yields sorted keys.; Validate with a (low, high) range passed down, not just parent-child checks.; Unbalanced BSTs degrade to O(n); library ordered sets/maps stay O(log n).
- **Pitfalls:** Validating only against the immediate parent.; Assuming O(log n) without balance (sorted insertions make a chain).; Mishandling duplicate keys — define where equal keys go.
- **Local judge problems:** [Validate a BST](<D:/Socrat/content/courses/dsa/problems/bst-validate.yaml>) (`bst-validate`, medium)
- **Quiz items:** `inorder-sorted` (mcq, difficulty 1/5); `validate-trap` (mcq, difficulty 3/5); `sorted-insert` (mcq, difficulty 2/5); `lca` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 189 | 189 |
| The inorder property | H2 | 36 | 36 |
| Validate a BST — the classic trap | H2 | 46 | 46 |
| Height and balance | H2 | 76 | 76 |
| Lowest common ancestor in a BST | H2 | 27 | 27 |
| Worked walkthrough | H2 | 40 | 133 |
| Worked walkthrough > Why this works | H3 | 21 | 21 |
| Worked walkthrough > Boundary cases and cost | H3 | 29 | 29 |
| Worked walkthrough > Check your understanding | H3 | 30 | 30 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Validate Binary Search Tree](<https://www.youtube.com/watch?v=s6ATEkipzow>) | NeetCode | video / core | 10 | neutral |
| [BST and AVL trees visualized](<https://visualgo.net/en/bst>) | VisuAlgo | visualizer / core | 20 | neutral |
| [Tech Interview Handbook: Tree cheatsheet (BST section)](<https://www.techinterviewhandbook.org/algorithms/tree/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Validate Binary Search Tree](<https://leetcode.com/problems/validate-binary-search-tree/>) (LeetCode, medium)
- Practice — [Kth Smallest Element in a BST](<https://leetcode.com/problems/kth-smallest-element-in-a-bst/>) (LeetCode, medium)
- Practice — [Lowest Common Ancestor of a Binary Search Tree](<https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-search-tree/>) (LeetCode, medium)
- Roadmap — [Binary Search Trees](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-search-trees@UYm7unZfXd9Ge5EYV4odb.md>)

##### Heaps and priority queues — `dsa:heaps`

- **Scope:** Always get the smallest (or largest) item in O(log n) — the engine behind top-k, scheduling and Dijkstra.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/heaps.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:binary-trees`
- **Key points:** Heaps give O(1) peek and O(log n) push/pop of the min (or max).; Python and Java default to min-heaps; C++ priority_queue defaults to max.; Array layout - children at 2i+1, 2i+2; sift up on push, sift down on pop.; Top-k - keep a min-heap of size k for the k largest.; Two heaps maintain a running median.
- **Pitfalls:** Forgetting C++'s default max-heap behaviour.; Sorting everything when a size-k heap suffices.; Searching a heap for arbitrary elements (O(n)) — heaps only make the top fast.
- **Local judge problems:** [Live k-th best score](<D:/Socrat/content/courses/dsa/problems/kth-largest-stream.yaml>) (`kth-largest-stream`, medium)
- **Quiz items:** `pop-cost` (mcq, difficulty 1/5); `cpp-default` (mcq, difficulty 2/5); `topk` (mcq, difficulty 3/5); `children` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 82 | 82 |
| Using the library | H2 | 87 | 87 |
| How it works inside | H2 | 55 | 55 |
| Pattern: top-k with a size-k heap | H2 | 72 | 72 |
| More heap patterns | H2 | 54 | 54 |
| Worked walkthrough | H2 | 38 | 143 |
| Worked walkthrough > Why this works | H3 | 23 | 23 |
| Worked walkthrough > Boundary cases and cost | H3 | 32 | 32 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Data Structures: Heaps](<https://www.youtube.com/watch?v=t0Cq6tVNRBA>) | HackerRank | video / core | 10 | neutral |
| [Binary heap visualized](<https://visualgo.net/en/heap>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Tech Interview Handbook: Heap cheatsheet](<https://www.techinterviewhandbook.org/algorithms/heap/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Kth Largest Element in a Stream](<https://leetcode.com/problems/kth-largest-element-in-a-stream/>) (LeetCode, easy)
- Practice — [Last Stone Weight](<https://leetcode.com/problems/last-stone-weight/>) (LeetCode, easy)
- Practice — [Find Median from Data Stream](<https://leetcode.com/problems/find-median-from-data-stream/>) (LeetCode, hard)
- Roadmap — [Heap](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/heap@R3Coq0TG1_cSOXzXWgpuI.md>)
- Handbook §4.5, printed page 43 — [Other structures: priority queue](<https://cses.fi/book/book.pdf#page=53>)

##### Tries (prefix trees) — `dsa:tries`

- **Scope:** Store strings character by character in a tree so prefix questions cost O(length), not O(number of words).
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/tries.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:binary-trees`, `zero:strings`
- **Key points:** Each trie edge is a character; a root-to-node path spells a prefix.; Insert and prefix queries take O(length), independent of the number of words.; Node counts answer how many words share a prefix; end markers mark whole words.; Use a hash set instead when you only need exact lookups.
- **Pitfalls:** Confusing "prefix exists" with "word exists" (missing end markers).; Excess memory from allocating 26 children for every node with huge inputs.; Recursion depth when deleting or traversing very long words.
- **Local judge problems:** [Autocomplete counts](<D:/Socrat/content/courses/dsa/problems/prefix-counts.yaml>) (`prefix-counts`, medium)
- **Quiz items:** `prefix-cost` (mcq, difficulty 1/5); `end-marker` (mcq, difficulty 2/5); `counts` (mcq, difficulty 2/5); `when-not` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 299 | 299 |
| Design choices | H2 | 60 | 60 |
| Where tries shine | H2 | 43 | 43 |
| Cost | H2 | 31 | 31 |
| Worked walkthrough | H2 | 39 | 146 |
| Worked walkthrough > Why this works | H3 | 22 | 22 |
| Worked walkthrough > Boundary cases and cost | H3 | 33 | 33 |
| Worked walkthrough > Check your understanding | H3 | 39 | 39 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Implement Trie (Prefix Tree)](<https://www.youtube.com/watch?v=oobqoCJlHA0>) | NeetCode | video / core | 18 | neutral |
| [Tech Interview Handbook: Trie cheatsheet](<https://www.techinterviewhandbook.org/algorithms/trie/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Data Structures Easy to Advanced (full course)](<https://www.youtube.com/watch?v=RBSGKlAvoiM>) | freeCodeCamp | video / deep | 60 | neutral |

**Other authored/supplemental links**

- Practice — [Implement Trie (Prefix Tree)](<https://leetcode.com/problems/implement-trie-prefix-tree/>) (LeetCode, medium)
- Practice — [Word Search II](<https://leetcode.com/problems/word-search-ii/>) (LeetCode, hard)
- Roadmap — [Trie](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/trie@zy3wpb1MjizfUfx9_rZy2.md>)
- Handbook §26.2, printed page 244 — [Trie structure](<https://cses.fi/book/book.pdf#page=254>)

#### Graphs — `graphs`

Traverse, order, connect and find shortest paths.

##### Graphs, BFS and DFS — `dsa:graph-traversal`

- **Scope:** Model relationships as nodes and edges, then explore them depth-first or breadth-first.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/graph-traversal.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:stacks`, `zero:grids`
- **Key points:** Store graphs as adjacency lists — O(V + E) memory.; BFS (queue) gives shortest paths in unweighted graphs.; DFS (recursion/stack) explores deeply — components, cycles, flood fill.; Mark nodes visited when they are first discovered.; Both run in O(V + E); grids are implicit graphs.
- **Pitfalls:** Forgetting the reverse edge in undirected graphs.; Marking visited on dequeue, causing duplicate work.; Recursion depth limits for DFS on large graphs.
- **Local judge problems:** [Count the islands](<D:/Socrat/content/courses/dsa/problems/count-islands.yaml>) (`count-islands`, medium); [Fewest hops](<D:/Socrat/content/courses/dsa/problems/fewest-hops.yaml>) (`fewest-hops`, medium)
- **Quiz items:** `bfs-shortest` (mcq, difficulty 2/5); `complexity` (mcq, difficulty 1/5); `components` (mcq, difficulty 1/5); `mark-time` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 38 | 38 |
| Representation: adjacency lists | H2 | 141 | 141 |
| Breadth-first search (BFS) | H2 | 193 | 193 |
| Depth-first search (DFS) | H2 | 39 | 39 |
| Connected components / number of islands | H2 | 29 | 29 |
| Complexity | H2 | 18 | 18 |
| Choosing | H2 | 26 | 26 |
| Worked walkthrough | H2 | 37 | 145 |
| Worked walkthrough > Why this works | H3 | 24 | 24 |
| Worked walkthrough > Boundary cases and cost | H3 | 37 | 37 |
| Worked walkthrough > Check your understanding | H3 | 34 | 34 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Graph Algorithms for Technical Interviews – Full Course](<https://www.youtube.com/watch?v=tWVWeAqZ0WU>) | freeCodeCamp | video / core | 130 | neutral |
| [Number of Islands](<https://www.youtube.com/watch?v=pV2kpPD66nE>) | NeetCode | video / core | 11 | neutral |
| [Graph traversal visualized (DFS/BFS)](<https://visualgo.net/en/dfsbfs>) | VisuAlgo | visualizer / core | 20 | neutral |
| [Breadth First Search](<https://cp-algorithms.com/graph/breadth-first-search.html>) | CP-Algorithms | article / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Number of Islands](<https://leetcode.com/problems/number-of-islands/>) (LeetCode, medium)
- Practice — [Rotting Oranges](<https://leetcode.com/problems/rotting-oranges/>) (LeetCode, medium)
- Practice — [Counting Rooms](<https://cses.fi/problemset/task/1192>) (CSES, easy)
- Practice — [Message Route](<https://cses.fi/problemset/task/1667>) (CSES, easy)
- Roadmap — [Breadth First Search](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/breadth-first-search@c7LdXJPv-5M-NPKSCXYuB.md>)
- Roadmap — [Depth First Search](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/depth-first-search@NrPO7vF8Z1WzmA9Ca3Y_E.md>)
- Handbook §11, printed page 109 — [Basics of graphs](<https://cses.fi/book/book.pdf#page=119>)
- Handbook §12, printed page 117 — [Graph traversal](<https://cses.fi/book/book.pdf#page=127>)

##### Topological sort — `dsa:topological-sort`

- **Scope:** Order tasks so every prerequisite comes first — and detect impossible cycles.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/topological-sort.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:graph-traversal`
- **Key points:** A topological order puts every prerequisite before what depends on it.; It exists iff the directed graph has no cycle.; Kahn's algorithm repeatedly removes in-degree-0 nodes; leftovers indicate a cycle.; A min-heap instead of a queue yields the lexicographically smallest order.; Topological order enables DP on DAGs.
- **Pitfalls:** Reversing edge direction (a → b must mean a before b).; Forgetting to report cycles when the order is incomplete.; Using a plain queue when the smallest valid order is required.
- **Local judge problems:** [Course order](<D:/Socrat/content/courses/dsa/problems/course-order.yaml>) (`course-order`, medium)
- **Quiz items:** `exists` (mcq, difficulty 1/5); `start` (mcq, difficulty 1/5); `cycle-detect` (mcq, difficulty 2/5); `lexi` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 56 | 56 |
| Kahn's algorithm (BFS with in-degrees) | H2 | 315 | 315 |
| Choosing among valid orders | H2 | 31 | 31 |
| DFS alternative | H2 | 37 | 37 |
| Beyond ordering | H2 | 32 | 32 |
| Worked walkthrough | H2 | 38 | 134 |
| Worked walkthrough > Why this works | H3 | 18 | 18 |
| Worked walkthrough > Boundary cases and cost | H3 | 30 | 30 |
| Worked walkthrough > Check your understanding | H3 | 35 | 35 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Course Schedule – Graph Adjacency List](<https://www.youtube.com/watch?v=EgI5nU9etnU>) | NeetCode | video / core | 16 | neutral |
| [Topological Sorting](<https://cp-algorithms.com/graph/topological-sort.html>) | CP-Algorithms | article / core | 15 | neutral |
| [Course Schedule (CSES)](<https://cses.fi/problemset/task/1679>) | CSES | interactive / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Course Schedule](<https://leetcode.com/problems/course-schedule/>) (LeetCode, medium)
- Practice — [Course Schedule II](<https://leetcode.com/problems/course-schedule-ii/>) (LeetCode, medium)
- Practice — [Course Schedule](<https://cses.fi/problemset/task/1679>) (CSES, medium)
- Roadmap — [Directed Graph](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/directed-graph@XVw2_dL3uN0SOWmjH1Uao.md>)
- Handbook §16.1, printed page 149 — [Topological sorting](<https://cses.fi/book/book.pdf#page=159>)

##### Union-Find (Disjoint Set Union) — `dsa:union-find`

- **Scope:** Merge groups and ask "same group?" in near-constant time — connectivity, cycles and Kruskal's MST.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/union-find.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:graph-traversal`
- **Key points:** DSU keeps groups as trees; the root identifies the group.; Path compression + union by size give near-constant amortised operations.; union returns whether a merge happened — that detects cycles.; Track component count by decrementing on successful unions.; Kruskal's MST = sorted edges + DSU.
- **Pitfalls:** Comparing elements instead of their roots.; Skipping both optimisations, leading to O(n) chains.; Expecting DSU to support splitting groups.
- **Local judge problems:** [Growing friend groups](<D:/Socrat/content/courses/dsa/problems/online-components.yaml>) (`online-components`, medium)
- **Quiz items:** `same-group` (mcq, difficulty 1/5); `cycle` (mcq, difficulty 2/5); `union-components` (mcq, difficulty 1/5); `optimisations` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 64 | 64 |
| Two optimisations make it near O(1) | H2 | 286 | 286 |
| Classic uses | H2 | 51 | 51 |
| Limits | H2 | 20 | 20 |
| Worked walkthrough | H2 | 35 | 135 |
| Worked walkthrough > Why this works | H3 | 22 | 22 |
| Worked walkthrough > Boundary cases and cost | H3 | 33 | 33 |
| Worked walkthrough > Check your understanding | H3 | 32 | 32 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Union Find Introduction](<https://www.youtube.com/watch?v=ibjEGG7ylHk>) | WilliamFiset | video / core | 10 | neutral |
| [Redundant Connection – Union Find](<https://www.youtube.com/watch?v=FXWRE67PLL0>) | NeetCode | video / core | 12 | neutral |
| [Disjoint Set Union](<https://cp-algorithms.com/data_structures/disjoint_set_union.html>) | CP-Algorithms | article / deep | 25 | neutral |
| [Union-Find visualized](<https://visualgo.net/en/ufds>) | VisuAlgo | visualizer / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Redundant Connection](<https://leetcode.com/problems/redundant-connection/>) (LeetCode, medium)
- Practice — [Building Roads](<https://cses.fi/problemset/task/1666>) (CSES, easy)
- Practice — [Road Construction](<https://cses.fi/problemset/task/1676>) (CSES, medium)
- Roadmap — [Disjoint Set Union Find](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/disjoint-set-union-find@La8XAT0BWvqRCrvQxtZIp.md>)
- Handbook §15.2, printed page 145 — [Union-find structure](<https://cses.fi/book/book.pdf#page=155>)

##### Weighted shortest paths — `dsa:shortest-paths`

- **Scope:** Dijkstra's algorithm — always settle the closest unsettled node — for graphs with non-negative weights.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/shortest-paths.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:graph-traversal`, `dsa:heaps`
- **Key points:** Dijkstra = BFS with a min-heap on distance; works only with non-negative weights.; The first time a node is popped, its distance is final.; Skip stale heap entries with if d > dist[u]; continue.; O((V + E) log V); use 64-bit distances.; Negative edges → Bellman-Ford; all pairs → Floyd-Warshall; 0/1 weights → 0-1 BFS.
- **Pitfalls:** Running Dijkstra with negative weights.; Not skipping stale entries (still correct, but slow on dense updates).; Overflow from 32-bit distances or from INF + w.
- **Local judge problems:** [Cheapest routes](<D:/Socrat/content/courses/dsa/problems/cheapest-routes.yaml>) (`cheapest-routes`, medium)
- **Quiz items:** `negative` (mcq, difficulty 3/5); `structure` (mcq, difficulty 1/5); `stale` (mcq, difficulty 2/5); `unit-weights` (mcq, difficulty 1/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 47 | 47 |
| Why it works | H2 | 300 | 300 |
| Limits and alternatives | H2 | 51 | 51 |
| Use 64-bit distances | H2 | 16 | 16 |
| Worked walkthrough | H2 | 36 | 148 |
| Worked walkthrough > Why this works | H3 | 21 | 21 |
| Worked walkthrough > Boundary cases and cost | H3 | 37 | 37 |
| Worked walkthrough > Check your understanding | H3 | 41 | 41 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Network Delay Time – Dijkstra's algorithm](<https://www.youtube.com/watch?v=EaphyqKU4PQ>) | NeetCode | video / core | 19 | neutral |
| [Dijkstra — finding shortest paths from a given vertex](<https://cp-algorithms.com/graph/dijkstra.html>) | CP-Algorithms | article / core | 25 | neutral |
| [Single-source shortest paths visualized](<https://visualgo.net/en/sssp>) | VisuAlgo | visualizer / core | 15 | neutral |
| [USACO Guide: Shortest paths with non-negative edge weights](<https://usaco.guide/gold/shortest-paths>) | USACO Guide | article / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [Network Delay Time](<https://leetcode.com/problems/network-delay-time/>) (LeetCode, medium)
- Practice — [Cheapest Flights Within K Stops](<https://leetcode.com/problems/cheapest-flights-within-k-stops/>) (LeetCode, medium)
- Practice — [Shortest Routes I](<https://cses.fi/problemset/task/1671>) (CSES, medium)
- Roadmap — [Shortest Path Algorithms](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/shortest-path-algorithms@N-qvYirxpORcaTslvlOL0.md>)
- Roadmap — [Dijkstras Algorithm](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dijkstras-algorithm@87UugvReiywF0E7Acos9U.md>)
- Handbook §13, printed page 123 — [Shortest paths](<https://cses.fi/book/book.pdf#page=133>)

#### Dynamic programming and bits — `dynamic-programming`

Turn exponential search into polynomial tables; use bits as tools.

##### Dynamic programming: the idea — `dsa:dp-introduction`

- **Scope:** Overlapping subproblems and optimal substructure, Fibonacci four ways, spotting DP, and printing the choices behind an answer.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-introduction.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:recursion`, `dsa:complexity`
- **Key points:** DP stores answers to repeated subproblems so each is solved once.; Write the state as a sentence, then the transition, base cases, answer cell and loop order.; Derive with recursion, fix with memoization, scale with tabulation, compress space last.; Plain Fibonacci recursion makes 2·F(n+1) − 1 calls; memoization makes about 2n.; If a greedy rule has a small counterexample and situations repeat, use DP.; To print the choices, record which option won at every cell and walk back from the answer.
- **Pitfalls:** Recursing without a memo on inputs of 40 or more.; Computing a value in the memoized function but never storing it.; Base cases that make every answer zero, such as ways(0) = 0.; Compressing the table before checking whether the output needs the path.
- **Local judge problems:** [Colouring the posts](<D:/Socrat/content/courses/dsa/problems/fence-painting.yaml>) (`fence-painting`, medium); [Stepping stones](<D:/Socrat/content/courses/dsa/problems/stepping-stones-path.yaml>) (`stepping-stones-path`, medium)
- **Quiz items:** `two-properties` (mcq, difficulty 1/5); `naive-calls` (mcq, difficulty 2/5); `memo-missing-store` (bug, difficulty 2/5); `tab-output` (output, difficulty 2/5); `greedy-stairs` (mcq, difficulty 3/5); `reconstruct-needs` (mcq, difficulty 3/5); `space-when` (mcq, difficulty 4/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Fibonacci four ways | H2 | 0 | 1628 |
| Fibonacci four ways > Recognition cues | H3 | 66 | 66 |
| Fibonacci four ways > State, transition, base cases, answer, loop order | H3 | 90 | 90 |
| Fibonacci four ways > Template | H3 | 158 | 158 |
| Fibonacci four ways > Anchor problem: the n-th Fibonacci number | H3 | 1017 | 1017 |
| Fibonacci four ways > Variants | H3 | 95 | 95 |
| Fibonacci four ways > Contrast | H3 | 82 | 82 |
| Fibonacci four ways > Common mistakes | H3 | 93 | 93 |
| Spotting a DP problem | H2 | 0 | 1042 |
| Spotting a DP problem > Recognition cues | H3 | 65 | 65 |
| Spotting a DP problem > State, transition, base cases, answer, loop order | H3 | 69 | 69 |
| Spotting a DP problem > Template | H3 | 254 | 254 |
| Spotting a DP problem > Anchor problem: cheapest way up the stairs | H3 | 457 | 457 |
| Spotting a DP problem > Variants | H3 | 64 | 64 |
| Spotting a DP problem > Contrast | H3 | 57 | 57 |
| Spotting a DP problem > Common mistakes | H3 | 48 | 48 |
| Reconstructing the choice | H2 | 0 | 775 |
| Reconstructing the choice > Recognition cues | H3 | 51 | 51 |
| Reconstructing the choice > State, transition, base cases, answer, loop order | H3 | 44 | 44 |
| Reconstructing the choice > Template | H3 | 416 | 416 |
| Reconstructing the choice > Anchor problem: which stairs were used? | H3 | 119 | 119 |
| Reconstructing the choice > Variants | H3 | 41 | 41 |
| Reconstructing the choice > Contrast | H3 | 41 | 41 |
| Reconstructing the choice > Common mistakes | H3 | 36 | 36 |
| Worked walkthrough | H2 | 355 | 624 |
| Worked walkthrough > Why this works | H3 | 95 | 95 |
| Worked walkthrough > Boundary cases and cost | H3 | 81 | 81 |
| Worked walkthrough > Check your understanding | H3 | 80 | 80 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Introduction to Dynamic Programming](<https://cp-algorithms.com/dynamic_programming/intro-to-dp.html>) | CP-Algorithms | article / intro | 20 | neutral |
| [Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 30 | neutral |
| [Recursion Tree and DAG (Dynamic Programming)](<https://visualgo.net/en/recursion>) | VisuAlgo | visualizer / intro | 15 | neutral |
| [functools.cache and lru_cache](<https://docs.python.org/3/library/functools.html>) | Python docs | docs / core | 10 | python |

**Other authored/supplemental links**

- Practice — [Jump Game](<https://leetcode.com/problems/jump-game/>) (LeetCode, medium)
- Practice — [Coin Change](<https://leetcode.com/problems/coin-change/>) (LeetCode, medium)
- Practice — [Maximum Subarray](<https://leetcode.com/problems/maximum-subarray/>) (LeetCode, medium)
- Practice — [Coin Path](<https://leetcode.com/problems/coin-path/>) (LeetCode, hard)
- Practice — [Largest Divisible Subset](<https://leetcode.com/problems/largest-divisible-subset/>) (LeetCode, medium)
- Practice — [Longest Common Subsequence](<https://cses.fi/problemset/task/3403>) (CSES, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)
- Python exercise 66 — [Fibonacci recurrence](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-66>)

##### Dynamic programming (1D) — `dsa:dp-1d`

- **Scope:** Define a state, write the recurrence, fill a table — and turn exponential recursion into linear time.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-1d.yaml>); no teaching-atom pack
- **Prerequisites:** `zero:recursion`, `dsa:complexity`, `dsa:dp-introduction`
- **Key points:** DP = state + transition + base cases + answer.; Each state is computed once, so exponential recursion becomes polynomial.; Top-down (memo) to derive; bottom-up (table) to scale.; Often only the last few states are needed — reduce memory to O(1).; Counting DPs take results modulo 1e9+7.
- **Pitfalls:** A vague state definition — write it as a full sentence.; Wrong iteration order so a state is used before it's computed.; Forgetting unreachable states (∞ or −1) and printing them as answers.
- **Local judge problems:** [Non-adjacent picks](<D:/Socrat/content/courses/dsa/problems/house-robber.yaml>) (`house-robber`, medium); [Fewest coins](<D:/Socrat/content/courses/dsa/problems/min-coins.yaml>) (`min-coins`, medium)
- **Quiz items:** `components` (mcq, difficulty 1/5); `robber` (mcq, difficulty 2/5); `overlap` (mcq, difficulty 2/5); `coins` (mcq, difficulty 1/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 75 | 75 |
| Example: house robber | H2 | 170 | 170 |
| Example: coin change (minimum coins) | H2 | 101 | 101 |
| Top-down vs bottom-up | H2 | 40 | 40 |
| Recognising DP | H2 | 40 | 40 |
| Counting problems and modulo | H2 | 13 | 13 |
| Worked walkthrough | H2 | 39 | 150 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 32 | 32 |
| Worked walkthrough > Check your understanding | H3 | 40 | 40 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Dynamic Programming – Learn to Solve Algorithmic Problems](<https://www.youtube.com/watch?v=oBt53YbR9Kk>) | freeCodeCamp | video / core | 300 | neutral |
| [Climbing Stairs – Dynamic Programming](<https://www.youtube.com/watch?v=Y0lT9Fck7qI>) | NeetCode | video / intro | 18 | neutral |
| [House Robber](<https://www.youtube.com/watch?v=73r3KWiEvyk>) | NeetCode | video / core | 10 | neutral |
| [USACO Guide: Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [Climbing Stairs](<https://leetcode.com/problems/climbing-stairs/>) (LeetCode, easy)
- Practice — [House Robber](<https://leetcode.com/problems/house-robber/>) (LeetCode, medium)
- Practice — [Coin Change](<https://leetcode.com/problems/coin-change/>) (LeetCode, medium)
- Practice — [Dice Combinations](<https://cses.fi/problemset/task/1633>) (CSES, easy)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)
- Python exercise 66 — [Fibonacci recurrence](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-66>)
- Handbook §7, printed page 65 — [Dynamic programming](<https://cses.fi/book/book.pdf#page=75>)

##### Dynamic programming (2D) — `dsa:dp-2d`

- **Scope:** States with two indexes — grids, two strings, items × capacity — filled row by row.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-2d.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-1d`
- **Key points:** 2D states describe grid positions, prefix pairs of two strings, or items × capacity.; LCS - match → diagonal + 1, otherwise max of top and left.; Fill in dependency order; often only the previous row is needed.; 0/1 knapsack in 1D iterates capacity downwards.; Reconstruct solutions by walking back through the table.
- **Pitfalls:** Index offsets between dp (1-based prefixes) and strings (0-based).; Iterating knapsack capacity upwards (accidentally unbounded).; O(n·m) memory when only one previous row is needed.
- **Local judge problems:** [Longest common subsequence](<D:/Socrat/content/courses/dsa/problems/lcs-length.yaml>) (`lcs-length`, medium); [Grid paths with obstacles](<D:/Socrat/content/courses/dsa/problems/grid-paths.yaml>) (`grid-paths`, medium)
- **Quiz items:** `lcs-match` (mcq, difficulty 2/5); `lcs-value` (mcq, difficulty 1/5); `knapsack-direction` (mcq, difficulty 3/5); `grid-paths` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 45 | 45 |
| Grid paths | H2 | 48 | 48 |
| Longest common subsequence (LCS) | H2 | 260 | 260 |
| 0/1 knapsack | H2 | 46 | 46 |
| Getting the order right | H2 | 28 | 28 |
| Reconstructing the answer | H2 | 24 | 24 |
| Worked walkthrough | H2 | 37 | 152 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 36 | 36 |
| Worked walkthrough > Check your understanding | H3 | 40 | 40 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Longest Common Subsequence](<https://www.youtube.com/watch?v=Ua0GhsJSlWM>) | NeetCode | video / core | 18 | neutral |
| [Unique Paths](<https://www.youtube.com/watch?v=IlEsdxuD4lY>) | NeetCode | video / core | 10 | neutral |
| [Recursion trees and DP visualized](<https://visualgo.net/en/recursion>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Tech Interview Handbook: Dynamic programming cheatsheet](<https://www.techinterviewhandbook.org/algorithms/dynamic-programming/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Unique Paths](<https://leetcode.com/problems/unique-paths/>) (LeetCode, medium)
- Practice — [Longest Common Subsequence](<https://leetcode.com/problems/longest-common-subsequence/>) (LeetCode, medium)
- Practice — [Edit Distance](<https://leetcode.com/problems/edit-distance/>) (LeetCode, medium)
- Practice — [Book Shop](<https://cses.fi/problemset/task/1158>) (CSES, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)
- Handbook §7.3, printed page 71 — [Paths in a grid](<https://cses.fi/book/book.pdf#page=81>)
- Handbook §7.5, printed page 74 — [Edit distance](<https://cses.fi/book/book.pdf#page=84>)

##### 0/1 knapsack family — `dsa:knapsack-01`

- **Scope:** Take or skip each item once: knapsack, subset sum, equal partition, counting subsets, minimum difference and two capacities.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/knapsack-01.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-2d`
- **Key points:** 0/1 knapsack: each item is taken once or skipped; dp over (items, budget).; dp[i][c] = max(dp[i−1][c], dp[i−1][c−w] + v); base row all zeros.; One row is enough if capacity is filled from W down, so no item is reused.; Subset sum uses or; counting uses +; the best total uses max. Same table.; Count partitions with difference D by counting subsets with sum (total + D) / 2.; Two budgets give a 2D state; loop both budgets backwards.; Greedy by value per weight is only correct for the fractional knapsack.
- **Pitfalls:** Looping capacity forwards in the one-row version, which reuses items.; Greedy by value per weight on whole items.; can[0] or ways[0] left at false or 0, which makes nothing reachable.; An inner loop that stops before s == x, which silently ignores zeros when counting.; Missing the parity check when the target is (total + D) / 2.
- **Local judge problems:** [Exact change at the festival](<D:/Socrat/content/courses/dsa/problems/exact-change-festival.yaml>) (`exact-change-festival`, medium); [Fair teams](<D:/Socrat/content/courses/dsa/problems/fair-teams.yaml>) (`fair-teams`, medium)
- **Quiz items:** `take-or-skip` (mcq, difficulty 1/5); `greedy-ratio` (mcq, difficulty 2/5); `backwards-why` (mcq, difficulty 3/5); `forward-output` (output, difficulty 4/5); `subset-base` (mcq, difficulty 2/5); `equal-partition-odd` (mcq, difficulty 2/5); `count-zeros` (mcq, difficulty 4/5); `difference-transform` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| 0/1 knapsack | H2 | 0 | 2788 |
| 0/1 knapsack > Recognition cues | H3 | 63 | 63 |
| 0/1 knapsack > State, transition, base cases, answer, loop order | H3 | 87 | 87 |
| 0/1 knapsack > Template | H3 | 285 | 285 |
| 0/1 knapsack > Anchor problem: packing a bag | H3 | 2080 | 2080 |
| 0/1 knapsack > Variants | H3 | 100 | 100 |
| 0/1 knapsack > Contrast | H3 | 62 | 62 |
| 0/1 knapsack > Common mistakes | H3 | 85 | 85 |
| Subset sum | H2 | 0 | 646 |
| Subset sum > Recognition cues | H3 | 49 | 49 |
| Subset sum > State, transition, base cases, answer, loop order | H3 | 55 | 55 |
| Subset sum > Template | H3 | 246 | 246 |
| Subset sum > Anchor problem: is 9 reachable? | H3 | 169 | 169 |
| Subset sum > Variants | H3 | 42 | 42 |
| Subset sum > Contrast | H3 | 34 | 34 |
| Subset sum > Common mistakes | H3 | 25 | 25 |
| Minimum difference partition | H2 | 0 | 630 |
| Minimum difference partition > Recognition cues | H3 | 42 | 42 |
| Minimum difference partition > State, transition, base cases, answer, loop order | H3 | 45 | 45 |
| Minimum difference partition > Template | H3 | 286 | 286 |
| Minimum difference partition > Anchor problem: numbers 1 6 11 5 | H3 | 87 | 87 |
| Minimum difference partition > Variants | H3 | 67 | 67 |
| Minimum difference partition > Contrast | H3 | 44 | 44 |
| Minimum difference partition > Common mistakes | H3 | 31 | 31 |
| Counting subsets with a target sum | H2 | 0 | 742 |
| Counting subsets with a target sum > Recognition cues | H3 | 47 | 47 |
| Counting subsets with a target sum > State, transition, base cases, answer, loop order | H3 | 41 | 41 |
| Counting subsets with a target sum > Template | H3 | 271 | 271 |
| Counting subsets with a target sum > Anchor problem: numbers 1 2 3 3, target 6 | H3 | 238 | 238 |
| Counting subsets with a target sum > Variants | H3 | 42 | 42 |
| Counting subsets with a target sum > Contrast | H3 | 34 | 34 |
| Counting subsets with a target sum > Common mistakes | H3 | 39 | 39 |
| Two capacities | H2 | 0 | 628 |
| Two capacities > Recognition cues | H3 | 37 | 37 |
| Two capacities > State, transition, base cases, answer, loop order | H3 | 39 | 39 |
| Two capacities > Template | H3 | 299 | 299 |
| Two capacities > Anchor problem: ones and zeroes | H3 | 87 | 87 |
| Two capacities > Variants | H3 | 47 | 47 |
| Two capacities > Contrast | H3 | 62 | 62 |
| Two capacities > Common mistakes | H3 | 31 | 31 |
| Worked walkthrough | H2 | 151 | 456 |
| Worked walkthrough > Why this works | H3 | 93 | 93 |
| Worked walkthrough > Boundary cases and cost | H3 | 92 | 92 |
| Worked walkthrough > Check your understanding | H3 | 107 | 107 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Knapsack Problem](<https://cp-algorithms.com/dynamic_programming/knapsack.html>) | CP-Algorithms | article / core | 25 | neutral |
| [Knapsack DP](<https://usaco.guide/gold/knapsack>) | USACO Guide | article / core | 40 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Partition Equal Subset Sum](<https://leetcode.com/problems/partition-equal-subset-sum/>) (LeetCode, medium)
- Practice — [Money Sums](<https://cses.fi/problemset/task/1745>) (CSES, easy)
- Practice — [Baby Ehab Partitions Again](<https://codeforces.com/problemset/problem/1516/C>) (Codeforces, medium)
- Practice — [Last Stone Weight II](<https://leetcode.com/problems/last-stone-weight-ii/>) (LeetCode, medium)
- Practice — [Tallest Billboard](<https://leetcode.com/problems/tallest-billboard/>) (LeetCode, hard)
- Practice — [Minimize the Difference Between Target and Chosen Elements](<https://leetcode.com/problems/minimize-the-difference-between-target-and-chosen-elements/>) (LeetCode, medium)
- Practice — [Target Sum](<https://leetcode.com/problems/target-sum/>) (LeetCode, medium)
- Practice — [Two Sets II](<https://cses.fi/problemset/task/1093>) (CSES, medium)
- Practice — [Number of Great Partitions](<https://leetcode.com/problems/number-of-great-partitions/>) (LeetCode, hard)
- Practice — [Ones and Zeroes](<https://leetcode.com/problems/ones-and-zeroes/>) (LeetCode, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### Unbounded knapsack family — `dsa:knapsack-unbounded`

- **Scope:** Items you can reuse: unbounded knapsack, rod cutting, fewest coins, and why loop order separates combinations from permutations.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/knapsack-unbounded.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:knapsack-01`
- **Key points:** Unbounded knapsack: each item can be taken any number of times.; One row filled forwards (c from w up to W) reuses items on purpose.; In the 2D table, a take reads the same row dp[i][c − w], not the row above.; Fewest coins: dp[0] = 0, every other cell infinity; −1 if still infinity.; "Exactly W" needs unreachable markers; "at most W" can start from zeros.; Counting ways - coins outer counts combinations, amount outer counts permutations.; Greedy largest-first or best-ratio-first fails for many inputs.
- **Pitfalls:** Looping capacity backwards, which turns it into 0/1 knapsack.; Starting a minimum DP at 0 instead of infinity.; Swapping the two loops when counting ways.; Overflow from INF + 1 in C++ or Java.; Trusting greedy coin change because the examples pass.
- **Local judge problems:** [Ride tokens](<D:/Socrat/content/courses/dsa/problems/ride-tokens.yaml>) (`ride-tokens`, medium); [Bundles of stickers](<D:/Socrat/content/courses/dsa/problems/bundle-count.yaml>) (`bundle-count`, medium)
- **Quiz items:** `reuse-cue` (mcq, difficulty 1/5); `rod-greedy` (mcq, difficulty 2/5); `forward-why` (mcq, difficulty 3/5); `backward-output` (output, difficulty 4/5); `min-init` (mcq, difficulty 2/5); `greedy-coins` (mcq, difficulty 2/5); `loop-order-count` (mcq, difficulty 3/5); `orders-count` (mcq, difficulty 4/5); `exact-ribbon` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Unbounded knapsack | H2 | 0 | 2506 |
| Unbounded knapsack > Recognition cues | H3 | 56 | 56 |
| Unbounded knapsack > State, transition, base cases, answer, loop order | H3 | 87 | 87 |
| Unbounded knapsack > Template | H3 | 273 | 273 |
| Unbounded knapsack > Anchor problem: cutting a rod | H3 | 1863 | 1863 |
| Unbounded knapsack > Variants | H3 | 100 | 100 |
| Unbounded knapsack > Contrast | H3 | 47 | 47 |
| Unbounded knapsack > Common mistakes | H3 | 54 | 54 |
| Fewest coins | H2 | 48 | 785 |
| Fewest coins > Recognition cues | H3 | 38 | 38 |
| Fewest coins > State, transition, base cases, answer, loop order | H3 | 61 | 61 |
| Fewest coins > Template | H3 | 277 | 277 |
| Fewest coins > Anchor problem: coins 1 3 4, amount 6 | H3 | 166 | 166 |
| Fewest coins > Variants | H3 | 58 | 58 |
| Fewest coins > Contrast | H3 | 52 | 52 |
| Fewest coins > Common mistakes | H3 | 56 | 56 |
| Combinations or permutations | H2 | 0 | 858 |
| Combinations or permutations > Recognition cues | H3 | 49 | 49 |
| Combinations or permutations > State, transition, base cases, answer, loop order | H3 | 85 | 85 |
| Combinations or permutations > Template | H3 | 401 | 401 |
| Combinations or permutations > Anchor problem: coins 1 2 3, amount 4 | H3 | 189 | 189 |
| Combinations or permutations > Variants | H3 | 45 | 45 |
| Combinations or permutations > Contrast | H3 | 33 | 33 |
| Combinations or permutations > Common mistakes | H3 | 27 | 27 |
| Worked walkthrough | H2 | 127 | 413 |
| Worked walkthrough > Why this works | H3 | 114 | 114 |
| Worked walkthrough > Boundary cases and cost | H3 | 83 | 83 |
| Worked walkthrough > Check your understanding | H3 | 76 | 76 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Knapsack Problem](<https://cp-algorithms.com/dynamic_programming/knapsack.html>) | CP-Algorithms | article / core | 25 | neutral |
| [Knapsack DP](<https://usaco.guide/gold/knapsack>) | USACO Guide | article / core | 40 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Coin Change](<https://leetcode.com/problems/coin-change/>) (LeetCode, medium)
- Practice — [Minimizing Coins](<https://cses.fi/problemset/task/1634>) (CSES, easy)
- Practice — [Coin Change II](<https://leetcode.com/problems/coin-change-ii/>) (LeetCode, medium)
- Practice — [Coin Combinations II](<https://cses.fi/problemset/task/1636>) (CSES, medium)
- Practice — [Combination Sum IV](<https://leetcode.com/problems/combination-sum-iv/>) (LeetCode, medium)
- Practice — [Coin Combinations I](<https://cses.fi/problemset/task/1635>) (CSES, easy)
- Practice — [Perfect Squares](<https://leetcode.com/problems/perfect-squares/>) (LeetCode, medium)
- Practice — [Minimum Cost For Tickets](<https://leetcode.com/problems/minimum-cost-for-tickets/>) (LeetCode, medium)
- Practice — [Dice Combinations](<https://cses.fi/problemset/task/1633>) (CSES, easy)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### Strings DP: the LCS family — `dsa:dp-lcs`

- **Scope:** Longest common subsequence and its relatives: common substring, supersequence, palindromic subsequence and subsequence matching.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-lcs.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-2d`, `zero:strings`
- **Key points:** dp[i][j] compares the prefixes a[:i] and b[:j]; row 0 and column 0 are 0.; LCS: match → up-left + 1; mismatch → max(up, left).; Greedy matching is wrong for LCS but right for checking that s is a subsequence of t.; Common substring: mismatch resets to 0, and the answer is the largest cell.; Shortest common supersequence: n + m − LCS; print it by walking back.; Longest palindromic subsequence fills i from n − 1 down, because row i reads row i + 1.; Two rows give the length in O(m) memory; printing the answer needs the full table.
- **Pitfalls:** Taking up-left on a mismatch, which drops a character that might still match.; Confusing a[i] with a[i − 1] when the table is indexed by prefix length.; Printing dp[n][m] for longest common substring instead of the maximum cell.; Filling the palindrome table with i ascending.; Greedy pointer matching for LCS.
- **Local judge problems:** [Shared playlist](<D:/Socrat/content/courses/dsa/problems/weighted-common-playlist.yaml>) (`weighted-common-playlist`, medium); [Palindrome trimming](<D:/Socrat/content/courses/dsa/problems/palindrome-trim.yaml>) (`palindrome-trim`, medium)
- **Quiz items:** `subsequence-meaning` (mcq, difficulty 1/5); `mismatch-rule` (mcq, difficulty 2/5); `greedy-lcs` (mcq, difficulty 2/5); `substring-reset` (mcq, difficulty 3/5); `scs-length` (mcq, difficulty 3/5); `lps-order` (mcq, difficulty 4/5); `lps-value` (output, difficulty 4/5); `two-pointer-safe` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Longest common subsequence | H2 | 0 | 2058 |
| Longest common subsequence > Recognition cues | H3 | 47 | 47 |
| Longest common subsequence > State, transition, base cases, answer, loop order | H3 | 81 | 81 |
| Longest common subsequence > Template | H3 | 318 | 318 |
| Longest common subsequence > Anchor problem: zabcd and abczd | H3 | 1392 | 1392 |
| Longest common subsequence > Variants | H3 | 85 | 85 |
| Longest common subsequence > Contrast | H3 | 40 | 40 |
| Longest common subsequence > Common mistakes | H3 | 69 | 69 |
| Longest common substring | H2 | 0 | 586 |
| Longest common substring > Recognition cues | H3 | 17 | 17 |
| Longest common substring > State, transition, base cases, answer, loop order | H3 | 30 | 30 |
| Longest common substring > Template | H3 | 288 | 288 |
| Longest common substring > Anchor problem: abcde and abfde | H3 | 133 | 133 |
| Longest common substring > Variants | H3 | 43 | 43 |
| Longest common substring > Contrast | H3 | 27 | 27 |
| Longest common substring > Common mistakes | H3 | 22 | 22 |
| Shortest common supersequence | H2 | 0 | 787 |
| Shortest common supersequence > Recognition cues | H3 | 24 | 24 |
| Shortest common supersequence > State, transition, base cases, answer, loop order | H3 | 73 | 73 |
| Shortest common supersequence > Template | H3 | 492 | 492 |
| Shortest common supersequence > Anchor problem: abac and cab | H3 | 70 | 70 |
| Shortest common supersequence > Variants | H3 | 39 | 39 |
| Shortest common supersequence > Contrast | H3 | 29 | 29 |
| Shortest common supersequence > Common mistakes | H3 | 34 | 34 |
| Longest palindromic subsequence | H2 | 0 | 616 |
| Longest palindromic subsequence > Recognition cues | H3 | 21 | 21 |
| Longest palindromic subsequence > State, transition, base cases, answer, loop order | H3 | 58 | 58 |
| Longest palindromic subsequence > Template | H3 | 289 | 289 |
| Longest palindromic subsequence > Anchor problem: bbbab | H3 | 130 | 130 |
| Longest palindromic subsequence > Variants | H3 | 33 | 33 |
| Longest palindromic subsequence > Contrast | H3 | 37 | 37 |
| Longest palindromic subsequence > Common mistakes | H3 | 24 | 24 |
| Subsequence matching | H2 | 0 | 441 |
| Subsequence matching > Recognition cues | H3 | 29 | 29 |
| Subsequence matching > State, transition, base cases, answer, loop order | H3 | 72 | 72 |
| Subsequence matching > Template | H3 | 175 | 175 |
| Subsequence matching > Anchor problem: ace in abcde | H3 | 25 | 25 |
| Subsequence matching > Variants | H3 | 47 | 47 |
| Subsequence matching > Contrast | H3 | 45 | 45 |
| Subsequence matching > Common mistakes | H3 | 22 | 22 |
| Worked walkthrough | H2 | 82 | 323 |
| Worked walkthrough > Why this works | H3 | 81 | 81 |
| Worked walkthrough > Boundary cases and cost | H3 | 77 | 77 |
| Worked walkthrough > Check your understanding | H3 | 70 | 70 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 40 | neutral |
| [Longest common subsequence](<https://en.wikipedia.org/wiki/Longest_common_subsequence>) | Wikipedia | article / deep | 20 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Longest Common Subsequence](<https://leetcode.com/problems/longest-common-subsequence/>) (LeetCode, medium)
- Practice — [Delete Operation for Two Strings](<https://leetcode.com/problems/delete-operation-for-two-strings/>) (LeetCode, medium)
- Practice — [Uncrossed Lines](<https://leetcode.com/problems/uncrossed-lines/>) (LeetCode, medium)
- Practice — [Maximum Length of Repeated Subarray](<https://leetcode.com/problems/maximum-length-of-repeated-subarray/>) (LeetCode, medium)
- Practice — [Shortest Common Supersequence](<https://leetcode.com/problems/shortest-common-supersequence/>) (LeetCode, hard)
- Practice — [Longest Palindromic Subsequence](<https://leetcode.com/problems/longest-palindromic-subsequence/>) (LeetCode, medium)
- Practice — [Minimum Insertion Steps to Make a String Palindrome](<https://leetcode.com/problems/minimum-insertion-steps-to-make-a-string-palindrome/>) (LeetCode, hard)
- Practice — [Is Subsequence](<https://leetcode.com/problems/is-subsequence/>) (LeetCode, easy)
- Practice — [Number of Matching Subsequences](<https://leetcode.com/problems/number-of-matching-subsequences/>) (LeetCode, medium)
- Practice — [Longest Common Subsequence](<https://cses.fi/problemset/task/3403>) (CSES, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### Strings DP: edits and matching — `dsa:dp-edit-distance`

- **Scope:** Edit distance, distinct subsequences, wildcard and regex matching, interleaving strings and palindromic substrings.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-edit-distance.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-lcs`
- **Key points:** dp[i][j] turns a[:i] into b[:j]; the base row is j inserts, the base column i deletes.; Equal last characters cost nothing; otherwise 1 + min(delete, insert, replace).; n + m − 2·LCS is correct only when replace is not allowed.; Distinct subsequences: count with ways[0] = 1 and j backwards, like 0/1 knapsack.; Wildcard * is empty or eats one more character; regex x* skips the pair (j − 2).; Interleaving: the last character of s3[:i+j] came from s1 or from s2; check lengths first.; Palindromic substrings expand from 2n − 1 centres, odd and even.
- **Pitfalls:** Base row and column left at 0.; Adding 1 when the last characters are equal.; Dropping the replace option, or using the LCS shortcut when replace is allowed.; Looping j forwards when counting distinct subsequences.; Greedy pointers for interleaving or for wildcard stars.
- **Local judge problems:** [Priced typo fixes](<D:/Socrat/content/courses/dsa/problems/typo-costs.yaml>) (`typo-costs`, medium); [Wildcard sightings](<D:/Socrat/content/courses/dsa/problems/wildcard-sightings.yaml>) (`wildcard-sightings`, medium)
- **Quiz items:** `three-ops` (mcq, difficulty 1/5); `base-column` (mcq, difficulty 2/5); `horse` (mcq, difficulty 2/5); `equal-chars` (mcq, difficulty 3/5); `distinct-count` (mcq, difficulty 4/5); `wildcard-star` (mcq, difficulty 4/5); `interleave-greedy` (mcq, difficulty 5/5); `palindrome-count` (output, difficulty 4/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Edit distance | H2 | 0 | 2226 |
| Edit distance > Recognition cues | H3 | 42 | 42 |
| Edit distance > State, transition, base cases, answer, loop order | H3 | 75 | 75 |
| Edit distance > Template | H3 | 361 | 361 |
| Edit distance > Anchor problem: horse to ros | H3 | 1566 | 1566 |
| Edit distance > Variants | H3 | 72 | 72 |
| Edit distance > Contrast | H3 | 36 | 36 |
| Edit distance > Common mistakes | H3 | 48 | 48 |
| Distinct subsequences | H2 | 0 | 654 |
| Distinct subsequences > Recognition cues | H3 | 43 | 43 |
| Distinct subsequences > State, transition, base cases, answer, loop order | H3 | 56 | 56 |
| Distinct subsequences > Template | H3 | 263 | 263 |
| Distinct subsequences > Anchor problem: rabbit in rabbbit | H3 | 177 | 177 |
| Distinct subsequences > Variants | H3 | 34 | 34 |
| Distinct subsequences > Contrast | H3 | 27 | 27 |
| Distinct subsequences > Common mistakes | H3 | 28 | 28 |
| Wildcard and regex matching | H2 | 0 | 725 |
| Wildcard and regex matching > Recognition cues | H3 | 30 | 30 |
| Wildcard and regex matching > State, transition, base cases, answer, loop order | H3 | 76 | 76 |
| Wildcard and regex matching > Template | H3 | 390 | 390 |
| Wildcard and regex matching > Anchor problem: adceb against *a*b | H3 | 93 | 93 |
| Wildcard and regex matching > Variants | H3 | 38 | 38 |
| Wildcard and regex matching > Contrast | H3 | 39 | 39 |
| Wildcard and regex matching > Common mistakes | H3 | 33 | 33 |
| Interleaving strings | H2 | 0 | 695 |
| Interleaving strings > Recognition cues | H3 | 29 | 29 |
| Interleaving strings > State, transition, base cases, answer, loop order | H3 | 52 | 52 |
| Interleaving strings > Template | H3 | 435 | 435 |
| Interleaving strings > Anchor problem: aabcc, dbbca and aadbbcbcac | H3 | 79 | 79 |
| Interleaving strings > Variants | H3 | 18 | 18 |
| Interleaving strings > Contrast | H3 | 32 | 32 |
| Interleaving strings > Common mistakes | H3 | 23 | 23 |
| Palindromic substrings | H2 | 0 | 500 |
| Palindromic substrings > Recognition cues | H3 | 14 | 14 |
| Palindromic substrings > State, transition, base cases, answer, loop order | H3 | 62 | 62 |
| Palindromic substrings > Template | H3 | 287 | 287 |
| Palindromic substrings > Anchor problem: aaa | H3 | 38 | 38 |
| Palindromic substrings > Variants | H3 | 41 | 41 |
| Palindromic substrings > Contrast | H3 | 23 | 23 |
| Palindromic substrings > Common mistakes | H3 | 11 | 11 |
| Worked walkthrough | H2 | 94 | 289 |
| Worked walkthrough > Why this works | H3 | 71 | 71 |
| Worked walkthrough > Boundary cases and cost | H3 | 49 | 49 |
| Worked walkthrough > Check your understanding | H3 | 62 | 62 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Edit distance](<https://en.wikipedia.org/wiki/Edit_distance>) | Wikipedia | article / core | 15 | neutral |
| [Levenshtein distance](<https://en.wikipedia.org/wiki/Levenshtein_distance>) | Wikipedia | article / deep | 20 | neutral |
| [Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 40 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Edit Distance](<https://leetcode.com/problems/edit-distance/>) (LeetCode, medium)
- Practice — [Edit Distance](<https://cses.fi/problemset/task/1639>) (CSES, medium)
- Practice — [One Edit Distance](<https://leetcode.com/problems/one-edit-distance/>) (LeetCode, medium)
- Practice — [Distinct Subsequences](<https://leetcode.com/problems/distinct-subsequences/>) (LeetCode, hard)
- Practice — [Wildcard Matching](<https://leetcode.com/problems/wildcard-matching/>) (LeetCode, hard)
- Practice — [Regular Expression Matching](<https://leetcode.com/problems/regular-expression-matching/>) (LeetCode, hard)
- Practice — [Interleaving String](<https://leetcode.com/problems/interleaving-string/>) (LeetCode, medium)
- Practice — [Palindromic Substrings](<https://leetcode.com/problems/palindromic-substrings/>) (LeetCode, medium)
- Practice — [Longest Palindromic Substring](<https://leetcode.com/problems/longest-palindromic-substring/>) (LeetCode, medium)
- Practice — [Palindrome Partitioning II](<https://leetcode.com/problems/palindrome-partitioning-ii/>) (LeetCode, hard)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### Stock trading DP — `dsa:dp-stocks`

- **Scope:** One state machine, day by holding by transactions left, that solves all six buy-and-sell-stock problems.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-stocks.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-2d`
- **Key points:** States: holding a share or not, plus transactions left; moves: rest, buy, sell.; cash[t] = max(cash[t], hold[t] + p); hold[t] = max(hold[t], cash[t − 1] − p).; hold starts at −∞, cash at 0; the answer is cash[k].; Loop t from k down so a buy reads yesterday's cash[t − 1].; Unlimited trades - sum of every daily rise; greedy is correct only then.; Fee: subtract once when selling. Cooldown: buy from cash two days ago.; O(n·k) time, O(k) memory.
- **Pitfalls:** hold initialised to 0, which allows selling a share never bought.; Buying from cash[t] instead of cash[t − 1], which ignores the transaction limit.; Keeping the k largest rising runs instead of running the machine.; Charging the fee on both sides of a trade.; Cooldown buy reading yesterday's cash.
- **Local judge problems:** [Warehouse trading](<D:/Socrat/content/courses/dsa/problems/warehouse-trading.yaml>) (`warehouse-trading`, medium); [Trading with rest days](<D:/Socrat/content/courses/dsa/problems/rest-days.yaml>) (`rest-days`, medium)
- **Quiz items:** `states` (mcq, difficulty 1/5); `unlimited` (mcq, difficulty 2/5); `hold-init` (mcq, difficulty 2/5); `buy-index` (mcq, difficulty 3/5); `runs-greedy` (mcq, difficulty 4/5); `fee` (mcq, difficulty 3/5); `cooldown` (mcq, difficulty 4/5); `k-output` (output, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Stock state machine | H2 | 0 | 2618 |
| Stock state machine > Recognition cues | H3 | 59 | 59 |
| Stock state machine > State, transition, base cases, answer, loop order | H3 | 140 | 140 |
| Stock state machine > Template | H3 | 348 | 348 |
| Stock state machine > Anchor problem: at most two trades | H3 | 1812 | 1812 |
| Stock state machine > Variants | H3 | 121 | 121 |
| Stock state machine > Contrast | H3 | 38 | 38 |
| Stock state machine > Common mistakes | H3 | 73 | 73 |
| Worked walkthrough | H2 | 120 | 331 |
| Worked walkthrough > Why this works | H3 | 75 | 75 |
| Worked walkthrough > Boundary cases and cost | H3 | 66 | 66 |
| Worked walkthrough > Check your understanding | H3 | 57 | 57 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 40 | neutral |
| [Dynamic Programming](<https://www.techinterviewhandbook.org/algorithms/dynamic-programming/>) | Tech Interview Handbook | article / core | 15 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Best Time to Buy and Sell Stock](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock/>) (LeetCode, easy)
- Practice — [Best Time to Buy and Sell Stock II](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock-ii/>) (LeetCode, medium)
- Practice — [Best Time to Buy and Sell Stock III](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/>) (LeetCode, hard)
- Practice — [Best Time to Buy and Sell Stock IV](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iv/>) (LeetCode, hard)
- Practice — [Best Time to Buy and Sell Stock with Cooldown](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/>) (LeetCode, medium)
- Practice — [Best Time to Buy and Sell Stock with Transaction Fee](<https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-transaction-fee/>) (LeetCode, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### Longest increasing subsequence family — `dsa:dp-lis`

- **Scope:** LIS in O(n^2) and O(n log n), printing it, and variants: divisible subsets, chains, bitonic, counts and envelopes.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-lis.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-1d`, `dsa:binary-search`
- **Key points:** dp[i] is the longest increasing subsequence ending at a[i]; the answer is max(dp).; dp[i] = 1 + max dp[j] over earlier, smaller a[j]; O(n²).; Patience sorting: tails[L] is the smallest tail of a chain of length L + 1; O(n log n).; Strict LIS uses lower bound; non-decreasing uses upper bound.; tails gives the length only; print an LIS with parent pointers.; Unordered items - sort by one key (ties descending), then LIS on the other.; Fewest removals to make it increasing = n − LIS.
- **Pitfalls:** Printing dp[n − 1] instead of the maximum over all i.; Using <= or upper bound for a strictly increasing subsequence.; Treating tails as an actual subsequence.; Sorting a sequence whose order matters.; Envelopes sorted with equal widths in ascending height.
- **Local judge problems:** [Tidy shelf](<D:/Socrat/content/courses/dsa/problems/tidy-shelf.yaml>) (`tidy-shelf`, medium); [Heaviest rising chain](<D:/Socrat/content/courses/dsa/problems/heaviest-rise.yaml>) (`heaviest-rise`, medium)
- **Quiz items:** `state` (mcq, difficulty 1/5); `greedy` (mcq, difficulty 2/5); `answer-cell` (mcq, difficulty 2/5); `bound` (mcq, difficulty 3/5); `tails-trace` (output, difficulty 4/5); `envelopes` (mcq, difficulty 4/5); `removals` (mcq, difficulty 3/5); `non-decreasing` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| LIS in O(n²) | H2 | 0 | 1562 |
| LIS in O(n²) > Recognition cues | H3 | 63 | 63 |
| LIS in O(n²) > State, transition, base cases, answer, loop order | H3 | 91 | 91 |
| LIS in O(n²) > Template | H3 | 254 | 254 |
| LIS in O(n²) > Anchor problem: 10 9 2 5 3 7 101 18 | H3 | 985 | 985 |
| LIS in O(n²) > Variants | H3 | 76 | 76 |
| LIS in O(n²) > Contrast | H3 | 30 | 30 |
| LIS in O(n²) > Common mistakes | H3 | 32 | 32 |
| Patience sorting: LIS in O(n log n) | H2 | 0 | 701 |
| Patience sorting: LIS in O(n log n) > Recognition cues | H3 | 27 | 27 |
| Patience sorting: LIS in O(n log n) > State, transition, base cases, answer, loop order | H3 | 65 | 65 |
| Patience sorting: LIS in O(n log n) > Template | H3 | 277 | 277 |
| Patience sorting: LIS in O(n log n) > Anchor problem: the same numbers, faster | H3 | 167 | 167 |
| Patience sorting: LIS in O(n log n) > Variants | H3 | 64 | 64 |
| Patience sorting: LIS in O(n log n) > Contrast | H3 | 37 | 37 |
| Patience sorting: LIS in O(n log n) > Common mistakes | H3 | 37 | 37 |
| LIS variants: printing, counting, sorting first | H2 | 0 | 806 |
| LIS variants: printing, counting, sorting first > Recognition cues | H3 | 41 | 41 |
| LIS variants: printing, counting, sorting first > State, transition, base cases, answer, loop order | H3 | 67 | 67 |
| LIS variants: printing, counting, sorting first > Template | H3 | 386 | 386 |
| LIS variants: printing, counting, sorting first > Anchor problem: printing for 10 9 2 5 3 7 101 18 | H3 | 119 | 119 |
| LIS variants: printing, counting, sorting first > Variants | H3 | 66 | 66 |
| LIS variants: printing, counting, sorting first > Contrast | H3 | 53 | 53 |
| LIS variants: printing, counting, sorting first > Common mistakes | H3 | 41 | 41 |
| Worked walkthrough | H2 | 101 | 346 |
| Worked walkthrough > Why this works | H3 | 105 | 105 |
| Worked walkthrough > Boundary cases and cost | H3 | 47 | 47 |
| Worked walkthrough > Check your understanding | H3 | 80 | 80 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Longest increasing subsequence](<https://cp-algorithms.com/sequences/longest_increasing_subsequence.html>) | CP-Algorithms | article / core | 30 | neutral |
| [Longest Increasing Subsequence](<https://usaco.guide/gold/lis>) | USACO Guide | article / core | 30 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Longest Increasing Subsequence](<https://leetcode.com/problems/longest-increasing-subsequence/>) (LeetCode, medium)
- Practice — [Increasing Subsequence](<https://cses.fi/problemset/task/1145>) (CSES, medium)
- Practice — [Towers](<https://cses.fi/problemset/task/1073>) (CSES, medium)
- Practice — [Number of Longest Increasing Subsequence](<https://leetcode.com/problems/number-of-longest-increasing-subsequence/>) (LeetCode, medium)
- Practice — [Russian Doll Envelopes](<https://leetcode.com/problems/russian-doll-envelopes/>) (LeetCode, hard)
- Practice — [Largest Divisible Subset](<https://leetcode.com/problems/largest-divisible-subset/>) (LeetCode, medium)
- Practice — [Longest String Chain](<https://leetcode.com/problems/longest-string-chain/>) (LeetCode, medium)
- Practice — [Maximum Length of Pair Chain](<https://leetcode.com/problems/maximum-length-of-pair-chain/>) (LeetCode, medium)
- Practice — [Minimum Number of Removals to Make Mountain Array](<https://leetcode.com/problems/minimum-number-of-removals-to-make-mountain-array/>) (LeetCode, hard)
- Practice — [Longest Continuous Increasing Subsequence](<https://leetcode.com/problems/longest-continuous-increasing-subsequence/>) (LeetCode, easy)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### Partition DP (matrix chain) — `dsa:dp-partition`

- **Scope:** Try every split point between i and j: matrix chains, cutting sticks, bursting balloons, boolean ways and minimum cuts.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-partition.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-2d`
- **Key points:** dp[i][j] solves the range i..j by trying every split point k and combining two smaller ranges.; Fill by range length, so every part is ready before the range that reads it.; Matrix chain: dp[i][j] = min dp[i][k] + dp[k+1][j] + p[i]·p[k+1]·p[j+1].; Cut a stick: think about the first cut; burst balloons: think about the last burst.; Boolean ways: keep true and false counts for every range.; Front partition: if only the last piece matters, a prefix state gives O(n²).; Interval DP is O(n³) time and O(n²) memory.
- **Pitfalls:** Filling ranges row by row from the top instead of by length.; The wrong dimension product for the last multiplication.; Unsorted cut positions or missing sentinels.; Choosing the first balloon instead of the last.; Keeping only true counts in boolean ways.
- **Local judge problems:** [Merging crate stacks](<D:/Socrat/content/courses/dsa/problems/crate-merging.yaml>) (`crate-merging`, medium); [Signal splits](<D:/Socrat/content/courses/dsa/problems/signal-splits.yaml>) (`signal-splits`, medium)
- **Quiz items:** `recognise` (mcq, difficulty 1/5); `loop-order` (mcq, difficulty 2/5); `join-cost` (mcq, difficulty 3/5); `cheapest-pair-first` (mcq, difficulty 3/5); `three` (mcq, difficulty 2/5); `burst-last` (mcq, difficulty 4/5); `cut-stick` (mcq, difficulty 4/5); `front` (mcq, difficulty 3/5); `bool-false` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Matrix chain multiplication | H2 | 0 | 1981 |
| Matrix chain multiplication > Recognition cues | H3 | 49 | 49 |
| Matrix chain multiplication > State, transition, base cases, answer, loop order | H3 | 122 | 122 |
| Matrix chain multiplication > Template | H3 | 384 | 384 |
| Matrix chain multiplication > Anchor problem: four matrices | H3 | 1200 | 1200 |
| Matrix chain multiplication > Variants | H3 | 90 | 90 |
| Matrix chain multiplication > Contrast | H3 | 57 | 57 |
| Matrix chain multiplication > Common mistakes | H3 | 54 | 54 |
| Cut or burst | H2 | 0 | 768 |
| Cut or burst > Recognition cues | H3 | 38 | 38 |
| Cut or burst > State, transition, base cases, answer, loop order | H3 | 102 | 102 |
| Cut or burst > Template | H3 | 373 | 373 |
| Cut or burst > Anchor problem: a stick of length 7, cuts at 1 3 4 5 | H3 | 119 | 119 |
| Cut or burst > Variants | H3 | 30 | 30 |
| Cut or burst > Contrast | H3 | 39 | 39 |
| Cut or burst > Common mistakes | H3 | 33 | 33 |
| Boolean ways | H2 | 0 | 959 |
| Boolean ways > Recognition cues | H3 | 40 | 40 |
| Boolean ways > State, transition, base cases, answer, loop order | H3 | 93 | 93 |
| Boolean ways > Template | H3 | 662 | 662 |
| Boolean ways > Anchor problem: T\|T&F^T | H3 | 49 | 49 |
| Boolean ways > Variants | H3 | 34 | 34 |
| Boolean ways > Contrast | H3 | 32 | 32 |
| Boolean ways > Common mistakes | H3 | 25 | 25 |
| Front partition | H2 | 0 | 664 |
| Front partition > Recognition cues | H3 | 44 | 44 |
| Front partition > State, transition, base cases, answer, loop order | H3 | 48 | 48 |
| Front partition > Template | H3 | 381 | 381 |
| Front partition > Anchor problem: aab | H3 | 59 | 59 |
| Front partition > Variants | H3 | 46 | 46 |
| Front partition > Contrast | H3 | 32 | 32 |
| Front partition > Common mistakes | H3 | 30 | 30 |
| Worked walkthrough | H2 | 136 | 338 |
| Worked walkthrough > Why this works | H3 | 61 | 61 |
| Worked walkthrough > Boundary cases and cost | H3 | 71 | 71 |
| Worked walkthrough > Check your understanding | H3 | 57 | 57 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Range DP](<https://usaco.guide/gold/dp-ranges>) | USACO Guide | article / core | 40 | neutral |
| [Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 40 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Minimum Score Triangulation of Polygon](<https://leetcode.com/problems/minimum-score-triangulation-of-polygon/>) (LeetCode, medium)
- Practice — [Minimum Cost Tree From Leaf Values](<https://leetcode.com/problems/minimum-cost-tree-from-leaf-values/>) (LeetCode, medium)
- Practice — [Minimum Cost to Cut a Stick](<https://leetcode.com/problems/minimum-cost-to-cut-a-stick/>) (LeetCode, hard)
- Practice — [Burst Balloons](<https://leetcode.com/problems/burst-balloons/>) (LeetCode, hard)
- Practice — [Different Ways to Add Parentheses](<https://leetcode.com/problems/different-ways-to-add-parentheses/>) (LeetCode, medium)
- Practice — [Palindrome Partitioning II](<https://leetcode.com/problems/palindrome-partitioning-ii/>) (LeetCode, hard)
- Practice — [Word Break](<https://leetcode.com/problems/word-break/>) (LeetCode, medium)
- Practice — [Partition Array for Maximum Sum](<https://leetcode.com/problems/partition-array-for-maximum-sum/>) (LeetCode, medium)
- Practice — [Removal Game](<https://cses.fi/problemset/task/1097>) (CSES, medium)
- Practice — [Rectangle Cutting](<https://cses.fi/problemset/task/1744>) (CSES, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### DP on squares and rectangles — `dsa:dp-squares`

- **Scope:** Maximal square, counting all-ones squares and the maximal rectangle built from a histogram per row.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-squares.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-2d`, `dsa:monotonic-stack`
- **Key points:** dp[i][j] is the side of the largest all-ones square whose bottom-right corner is (i, j).; On a 1 cell, 1 + min(up, left, up-left); on a 0 cell, 0.; The diagonal is the only neighbour that checks the square's far corner.; One row is enough if the old dp[j] is saved as the next diagonal.; The sum of all dp values counts every all-ones square.; Rectangles: build a histogram per row and run the largest-rectangle stack on each.
- **Pitfalls:** Leaving out the diagonal neighbour.; Printing the side instead of the area.; Not resetting a height or a dp value to 0 on an empty cell.; Trying to store the largest rectangle per cell as one number.
- **Local judge problems:** [Solar panel plots](<D:/Socrat/content/courses/dsa/problems/solar-squares.yaml>) (`solar-squares`, medium); [Fence around the meadow](<D:/Socrat/content/courses/dsa/problems/meadow-fence.yaml>) (`meadow-fence`, medium)
- **Quiz items:** `square-state` (mcq, difficulty 1/5); `square-cell` (mcq, difficulty 2/5); `diagonal` (mcq, difficulty 3/5); `count` (mcq, difficulty 3/5); `histogram` (mcq, difficulty 2/5); `rectangle` (mcq, difficulty 4/5); `why-not-dp` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Maximal square | H2 | 0 | 2332 |
| Maximal square > Recognition cues | H3 | 43 | 43 |
| Maximal square > State, transition, base cases, answer, loop order | H3 | 141 | 141 |
| Maximal square > Template | H3 | 370 | 370 |
| Maximal square > Anchor problem: the largest square | H3 | 1601 | 1601 |
| Maximal square > Variants | H3 | 62 | 62 |
| Maximal square > Contrast | H3 | 44 | 44 |
| Maximal square > Common mistakes | H3 | 45 | 45 |
| Histogram rectangle | H2 | 0 | 718 |
| Histogram rectangle > Recognition cues | H3 | 23 | 23 |
| Histogram rectangle > State, transition, base cases, answer, loop order | H3 | 60 | 60 |
| Histogram rectangle > Template | H3 | 392 | 392 |
| Histogram rectangle > Anchor problem: the largest rectangle | H3 | 127 | 127 |
| Histogram rectangle > Variants | H3 | 30 | 30 |
| Histogram rectangle > Contrast | H3 | 22 | 22 |
| Histogram rectangle > Common mistakes | H3 | 38 | 38 |
| Worked walkthrough | H2 | 106 | 334 |
| Worked walkthrough > Why this works | H3 | 93 | 93 |
| Worked walkthrough > Boundary cases and cost | H3 | 52 | 52 |
| Worked walkthrough > Check your understanding | H3 | 70 | 70 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 40 | neutral |
| [Dynamic Programming](<https://www.techinterviewhandbook.org/algorithms/dynamic-programming/>) | Tech Interview Handbook | article / core | 15 | neutral |
| [Competitive Programmer's Handbook, chapter 7: Dynamic programming](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Maximal Square](<https://leetcode.com/problems/maximal-square/>) (LeetCode, medium)
- Practice — [Count Square Submatrices with All Ones](<https://leetcode.com/problems/count-square-submatrices-with-all-ones/>) (LeetCode, medium)
- Practice — [Largest 1-Bordered Square](<https://leetcode.com/problems/largest-1-bordered-square/>) (LeetCode, medium)
- Practice — [Maximal Rectangle](<https://leetcode.com/problems/maximal-rectangle/>) (LeetCode, hard)
- Practice — [Count Submatrices With All Ones](<https://leetcode.com/problems/count-submatrices-with-all-ones/>) (LeetCode, medium)
- Practice — [Largest Rectangle in Histogram](<https://leetcode.com/problems/largest-rectangle-in-histogram/>) (LeetCode, hard)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

##### DP on trees — `dsa:dp-on-trees`

- **Scope:** Post-order DP over tree nodes: rob or skip, best path through a node and camera-style cover states.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-on-trees.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-1d`, `dsa:tree-patterns`
- **Key points:** Subproblems are subtrees; fill children before parents (reverse BFS order).; Keep one answer per node state when the parent's choice depends on the child's.; Rob or skip: take = val + Σ skip(children); skip = Σ max(take, skip)(children).; Path through a node: record 1 + two best allowed arms, return 1 + the best arm.; A child that may not join is still solved on its own.; Cover states: camera here, covered by a child, waiting for the parent; the root cannot wait.; O(n) time and memory.
- **Pitfalls:** Alternating levels instead of deciding per node.; Adding take of a child when the parent is taken.; Dropping a blocked child's subtree in path problems.; Only two states for camera problems.; Deep recursion on long chains.
- **Local judge problems:** [Watchtowers on the trails](<D:/Socrat/content/courses/dsa/problems/watchtowers.yaml>) (`watchtowers`, medium); [Street lamps on a tree](<D:/Socrat/content/courses/dsa/problems/street-lamps.yaml>) (`street-lamps`, hard)
- **Quiz items:** `take-skip` (mcq, difficulty 1/5); `levels` (mcq, difficulty 2/5); `order` (mcq, difficulty 2/5); `chain` (mcq, difficulty 3/5); `blocked` (mcq, difficulty 3/5); `three-states` (mcq, difficulty 4/5); `cameras` (mcq, difficulty 4/5); `root` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Rob or skip | H2 | 0 | 2225 |
| Rob or skip > Recognition cues | H3 | 60 | 60 |
| Rob or skip > State, transition, base cases, answer, loop order | H3 | 80 | 80 |
| Rob or skip > Template | H3 | 489 | 489 |
| Rob or skip > Anchor problem: houses on a tree | H3 | 1427 | 1427 |
| Rob or skip > Variants | H3 | 57 | 57 |
| Rob or skip > Contrast | H3 | 41 | 41 |
| Rob or skip > Common mistakes | H3 | 44 | 44 |
| Path through a node | H2 | 0 | 900 |
| Path through a node > Recognition cues | H3 | 40 | 40 |
| Path through a node > State, transition, base cases, answer, loop order | H3 | 68 | 68 |
| Path through a node > Template | H3 | 552 | 552 |
| Path through a node > Anchor problem: neighbours must differ | H3 | 119 | 119 |
| Path through a node > Variants | H3 | 33 | 33 |
| Path through a node > Contrast | H3 | 37 | 37 |
| Path through a node > Common mistakes | H3 | 25 | 25 |
| Cover states | H2 | 0 | 1041 |
| Cover states > Recognition cues | H3 | 41 | 41 |
| Cover states > State, transition, base cases, answer, loop order | H3 | 120 | 120 |
| Cover states > Template | H3 | 649 | 649 |
| Cover states > Anchor problem: cameras | H3 | 99 | 99 |
| Cover states > Variants | H3 | 36 | 36 |
| Cover states > Contrast | H3 | 40 | 40 |
| Cover states > Common mistakes | H3 | 32 | 32 |
| Worked walkthrough | H2 | 122 | 334 |
| Worked walkthrough > Why this works | H3 | 78 | 78 |
| Worked walkthrough > Boundary cases and cost | H3 | 52 | 52 |
| Worked walkthrough > Check your understanding | H3 | 69 | 69 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [DP on Trees - Introduction](<https://usaco.guide/gold/dp-trees>) | USACO Guide | article / core | 40 | neutral |
| [Tree](<https://www.techinterviewhandbook.org/algorithms/tree/>) | Tech Interview Handbook | article / core | 15 | neutral |
| [Competitive Programmer's Handbook, chapter 14: Tree algorithms](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [House Robber III](<https://leetcode.com/problems/house-robber-iii/>) (LeetCode, medium)
- Practice — [Tree Matching](<https://cses.fi/problemset/task/1130>) (CSES, medium)
- Practice — [Binary Tree Cameras](<https://leetcode.com/problems/binary-tree-cameras/>) (LeetCode, hard)
- Practice — [Longest Univalue Path](<https://leetcode.com/problems/longest-univalue-path/>) (LeetCode, medium)
- Practice — [Binary Tree Maximum Path Sum](<https://leetcode.com/problems/binary-tree-maximum-path-sum/>) (LeetCode, hard)
- Practice — [Distribute Coins in Binary Tree](<https://leetcode.com/problems/distribute-coins-in-binary-tree/>) (LeetCode, medium)
- Roadmap — [Binary Trees](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-trees@RPU5CGp2Li5lk0UB-zNHT.md>)
- Roadmap — [Tree Traversal](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/tree-traversal@2Od5lNc6fCM6Gyj_axj4n.md>)

##### Bit manipulation — `dsa:bit-manipulation`

- **Scope:** Treat integers as arrays of bits — XOR tricks, masks, and counting set bits.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/bit-manipulation.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:complexity`
- **Key points:** AND, OR, XOR, NOT and shifts manipulate bits directly.; x & (x − 1) removes the lowest set bit; power of two ⇔ x > 0 and x & (x − 1) == 0.; XOR cancels pairs - a ^ a = 0, so XOR of all values finds the unpaired one.; Masks from 0 to 2^n − 1 enumerate all subsets.; Use 64-bit shifts (1LL, 1L) for large bit positions.
- **Pitfalls:** Operator precedence — wrap bit expressions in parentheses (in C++/Java & binds weaker than ==).; Overflow from 1 << k with 32-bit ints.; Python's ~ producing negative numbers unexpectedly.
- **Local judge problems:** [The unpaired badge](<D:/Socrat/content/courses/dsa/problems/single-number.yaml>) (`single-number`, easy)
- **Quiz items:** `xor-pairs` (mcq, difficulty 1/5); `power-two` (mcq, difficulty 2/5); `subsets` (mcq, difficulty 2/5); `and-value` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 104 | 104 |
| Essential tricks | H2 | 74 | 74 |
| XOR's superpower | H2 | 108 | 108 |
| Bitmasks as sets | H2 | 78 | 78 |
| Language notes | H2 | 43 | 43 |
| Worked walkthrough | H2 | 32 | 142 |
| Worked walkthrough > Why this works | H3 | 21 | 21 |
| Worked walkthrough > Boundary cases and cost | H3 | 39 | 39 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Counting Bits](<https://www.youtube.com/watch?v=RyBM56RIWrM>) | NeetCode | video / core | 13 | neutral |
| [Bitmask operations visualized](<https://visualgo.net/en/bitmask>) | VisuAlgo | visualizer / core | 10 | neutral |
| [Tech Interview Handbook: Binary cheatsheet](<https://www.techinterviewhandbook.org/algorithms/binary/>) | Tech Interview Handbook | article / core | 10 | neutral |

**Other authored/supplemental links**

- Practice — [Single Number](<https://leetcode.com/problems/single-number/>) (LeetCode, easy)
- Practice — [Number of 1 Bits](<https://leetcode.com/problems/number-of-1-bits/>) (LeetCode, easy)
- Practice — [Counting Bits](<https://leetcode.com/problems/counting-bits/>) (LeetCode, easy)
- Practice — [Missing Number](<https://leetcode.com/problems/missing-number/>) (LeetCode, easy)
- Python exercise 11 — [Binary divisibility](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-11>)
- Handbook §10, printed page 95 — [Bit manipulation](<https://cses.fi/book/book.pdf#page=105>)

##### More interview DP patterns — `dsa:dp-advanced-patterns`

- **Scope:** Bitmask DP on small sets, minimax games, state-machine counting and a first look at digit DP.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/dp-advanced-patterns.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:knapsack-01`, `dsa:dp-partition`, `dsa:bit-manipulation`
- **Key points:** The state is exactly what the future depends on - a set, a position, a recent history or a digit prefix.; Bitmask DP: dp[mask] over used items; the next worker is popcount(mask); O(2ⁿ · n).; Increasing mask order is a valid fill order, because adding a bit makes a larger number.; Games: store the best score difference for the player to move; mine = (sum + diff) / 2.; State-machine counting: remember only what the rules look back at; build the next day in a new table.; Digit DP: (position, property so far, tight); a range is count(B) − count(A − 1).
- **Pitfalls:** Greedy choices in assignment or in games.; Using a loop index instead of popcount(mask) for the current worker.; Adding the opponent's best instead of subtracting it.; A counting state that forgets part of a rule.; Forgetting the tight flag in digit DP.
- **Local judge problems:** [Lab partners](<D:/Socrat/content/courses/dsa/problems/lab-partners.yaml>) (`lab-partners`, medium); [Take one or two](<D:/Socrat/content/courses/dsa/problems/two-coin-take.yaml>) (`two-coin-take`, medium)
- **Quiz items:** `bitmask-size` (mcq, difficulty 1/5); `bitmask-order` (mcq, difficulty 2/5); `greedy-assign` (mcq, difficulty 3/5); `game-diff` (mcq, difficulty 3/5); `game-value` (mcq, difficulty 4/5); `state-machine` (mcq, difficulty 3/5); `records` (mcq, difficulty 2/5); `tight` (mcq, difficulty 4/5); `tight-count` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| Bitmask DP over subsets | H2 | 0 | 2038 |
| Bitmask DP over subsets > Recognition cues | H3 | 57 | 57 |
| Bitmask DP over subsets > State, transition, base cases, answer, loop order | H3 | 119 | 119 |
| Bitmask DP over subsets > Template | H3 | 420 | 420 |
| Bitmask DP over subsets > Anchor problem: three workers, three jobs | H3 | 1234 | 1234 |
| Bitmask DP over subsets > Variants | H3 | 73 | 73 |
| Bitmask DP over subsets > Contrast | H3 | 45 | 45 |
| Bitmask DP over subsets > Common mistakes | H3 | 63 | 63 |
| Game minimax | H2 | 0 | 641 |
| Game minimax > Recognition cues | H3 | 43 | 43 |
| Game minimax > State, transition, base cases, answer, loop order | H3 | 61 | 61 |
| Game minimax > Template | H3 | 326 | 326 |
| Game minimax > Anchor problem: 4 5 1 3 | H3 | 65 | 65 |
| Game minimax > Variants | H3 | 53 | 53 |
| Game minimax > Contrast | H3 | 35 | 35 |
| Game minimax > Common mistakes | H3 | 31 | 31 |
| State-machine counting | H2 | 0 | 834 |
| State-machine counting > Recognition cues | H3 | 47 | 47 |
| State-machine counting > State, transition, base cases, answer, loop order | H3 | 87 | 87 |
| State-machine counting > Template | H3 | 475 | 475 |
| State-machine counting > Anchor problem: records of length 2 | H3 | 62 | 62 |
| State-machine counting > Variants | H3 | 56 | 56 |
| State-machine counting > Contrast | H3 | 45 | 45 |
| State-machine counting > Common mistakes | H3 | 35 | 35 |
| Digit DP (a first look) | H2 | 0 | 784 |
| Digit DP (a first look) > Recognition cues | H3 | 46 | 46 |
| Digit DP (a first look) > State, transition, base cases, answer, loop order | H3 | 68 | 68 |
| Digit DP (a first look) > Template | H3 | 440 | 440 |
| Digit DP (a first look) > Anchor problem: N = 23, S = 5 | H3 | 64 | 64 |
| Digit DP (a first look) > Variants | H3 | 54 | 54 |
| Digit DP (a first look) > Contrast | H3 | 40 | 40 |
| Digit DP (a first look) > Common mistakes | H3 | 43 | 43 |
| Worked walkthrough | H2 | 151 | 438 |
| Worked walkthrough > Why this works | H3 | 82 | 82 |
| Worked walkthrough > Boundary cases and cost | H3 | 84 | 84 |
| Worked walkthrough > Check your understanding | H3 | 108 | 108 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Bitmask DP](<https://usaco.guide/gold/dp-bitmasks>) | USACO Guide | article / core | 40 | neutral |
| [Range DP](<https://usaco.guide/gold/dp-ranges>) | USACO Guide | article / core | 40 | neutral |
| [Competitive Programmer's Handbook, chapter 10: Bit manipulation](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 45 | neutral |

**Other authored/supplemental links**

- Practice — [Partition to K Equal Sum Subsets](<https://leetcode.com/problems/partition-to-k-equal-sum-subsets/>) (LeetCode, medium)
- Practice — [Elevator Rides](<https://cses.fi/problemset/task/1653>) (CSES, hard)
- Practice — [Hamiltonian Flights](<https://cses.fi/problemset/task/1690>) (CSES, hard)
- Practice — [Removal Game](<https://cses.fi/problemset/task/1097>) (CSES, medium)
- Practice — [Predict the Winner](<https://leetcode.com/problems/predict-the-winner/>) (LeetCode, medium)
- Practice — [Can I Win](<https://leetcode.com/problems/can-i-win/>) (LeetCode, medium)
- Practice — [Student Attendance Record II](<https://leetcode.com/problems/student-attendance-record-ii/>) (LeetCode, hard)
- Practice — [Knight Dialer](<https://leetcode.com/problems/knight-dialer/>) (LeetCode, medium)
- Practice — [Counting Numbers](<https://cses.fi/problemset/task/2220>) (CSES, hard)
- Practice — [Number of Digit One](<https://leetcode.com/problems/number-of-digit-one/>) (LeetCode, hard)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)

#### Design and interview practice — `design-and-practice`

Design data structures, meet advanced structures and practise running an interview.

##### Designing data structures — `dsa:design-data-structures`

- **Scope:** LRU and LFU caches, hash-based designs, ordered designs with binary search, and iterator design.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/dsa/concepts/design-data-structures.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:linked-lists`, `dsa:hashing`, `dsa:heaps`, `dsa:binary-search`
- **Key points:** List the operations and their costs, pick a structure per need, and state the invariant that ties them.; LRU: a hash map to find the node and a doubly linked list to move it, both O(1).; A get is a use; an update of an existing key evicts nothing.; LFU: one LRU list per frequency plus the smallest frequency in use.; Random set: array plus value → index map; delete by moving the last value into the hole.; Time-based store: append to a sorted history per key and binary search it.; Iterators: a cursor that is advanced past empty parts before every answer.
- **Pitfalls:** Evicting in arrival order, ignoring gets.; An update evicting another key.; Forgetting to update the index of the element moved into the hole.; Keeping only the latest value when queries ask about the past.; hasNext that does not skip empty rows.
- **Local judge problems:** [Thumbnail cache](<D:/Socrat/content/courses/dsa/problems/thumbnail-cache.yaml>) (`thumbnail-cache`, medium); [The popular shelf](<D:/Socrat/content/courses/dsa/problems/library-shelf.yaml>) (`library-shelf`, hard)
- **Quiz items:** `two-structures` (mcq, difficulty 1/5); `get-is-use` (mcq, difficulty 2/5); `update` (mcq, difficulty 2/5); `queue-fails` (mcq, difficulty 3/5); `sentinels` (mcq, difficulty 3/5); `swap-delete` (mcq, difficulty 3/5); `history` (mcq, difficulty 4/5); `lfu` (mcq, difficulty 4/5); `iterator-empty` (mcq, difficulty 5/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| LRU and LFU caches | H2 | 0 | 2296 |
| LRU and LFU caches > Recognition cues | H3 | 49 | 49 |
| LRU and LFU caches > Template | H3 | 385 | 385 |
| LRU and LFU caches > Anchor problem: capacity 2 | H3 | 1673 | 1673 |
| LRU and LFU caches > Variants | H3 | 58 | 58 |
| LRU and LFU caches > Contrast | H3 | 52 | 52 |
| LRU and LFU caches > Common mistakes | H3 | 62 | 62 |
| Design with hashing | H2 | 0 | 731 |
| Design with hashing > Recognition cues | H3 | 47 | 47 |
| Design with hashing > Template | H3 | 446 | 446 |
| Design with hashing > Anchor problem: insert, delete, get random | H3 | 92 | 92 |
| Design with hashing > Variants | H3 | 48 | 48 |
| Design with hashing > Contrast | H3 | 43 | 43 |
| Design with hashing > Common mistakes | H3 | 36 | 36 |
| Design with ordering | H2 | 0 | 674 |
| Design with ordering > Recognition cues | H3 | 47 | 47 |
| Design with ordering > Template | H3 | 391 | 391 |
| Design with ordering > Anchor problem: a price over time | H3 | 94 | 94 |
| Design with ordering > Variants | H3 | 48 | 48 |
| Design with ordering > Contrast | H3 | 34 | 34 |
| Design with ordering > Common mistakes | H3 | 41 | 41 |
| Iterator design | H2 | 0 | 690 |
| Iterator design > Recognition cues | H3 | 50 | 50 |
| Iterator design > Template | H3 | 408 | 408 |
| Iterator design > Anchor problem: rows with a gap | H3 | 80 | 80 |
| Iterator design > Variants | H3 | 58 | 58 |
| Iterator design > Contrast | H3 | 43 | 43 |
| Iterator design > Common mistakes | H3 | 32 | 32 |
| Worked walkthrough | H2 | 120 | 368 |
| Worked walkthrough > Why this works | H3 | 99 | 99 |
| Worked walkthrough > Boundary cases and cost | H3 | 71 | 71 |
| Worked walkthrough > Check your understanding | H3 | 65 | 65 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Tech Interview Handbook: Hash table cheatsheet](<https://www.techinterviewhandbook.org/algorithms/hash-table/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Tech Interview Handbook: Linked list cheatsheet](<https://www.techinterviewhandbook.org/algorithms/linked-list/>) | Tech Interview Handbook | article / core | 10 | neutral |
| [Linked lists visualized](<https://visualgo.net/en/list>) | VisuAlgo | visualizer / deep | 15 | neutral |

**Other authored/supplemental links**

- Practice — [LRU Cache](<https://leetcode.com/problems/lru-cache/>) (LeetCode, medium)
- Practice — [LFU Cache](<https://leetcode.com/problems/lfu-cache/>) (LeetCode, hard)
- Practice — [Insert Delete GetRandom O(1)](<https://leetcode.com/problems/insert-delete-getrandom-o1/>) (LeetCode, medium)
- Practice — [Time Based Key-Value Store](<https://leetcode.com/problems/time-based-key-value-store/>) (LeetCode, medium)
- Practice — [Snapshot Array](<https://leetcode.com/problems/snapshot-array/>) (LeetCode, medium)
- Practice — [Design Browser History](<https://leetcode.com/problems/design-browser-history/>) (LeetCode, medium)
- Practice — [Flatten Nested List Iterator](<https://leetcode.com/problems/flatten-nested-list-iterator/>) (LeetCode, medium)
- Practice — [Binary Search Tree Iterator](<https://leetcode.com/problems/binary-search-tree-iterator/>) (LeetCode, medium)
- Roadmap — [Hash Tables](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/hash-tables@kSy-8ubESdmIX4Fyl8TSu.md>)
- Roadmap — [Linked Lists](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/linked-lists@bRu9u8pEAQ1TmKygjIjyI.md>)

### 4.3 Competitive Programming — `cp`

A contest-focused path from your first accepted solution to the data structures and techniques behind Div 2 / Div 3 problems on Codeforces, AtCoder and CodeChef. Every topic ends in timed, unseen problems, and Socrat adapts to your speed and accuracy as much as your correctness.

**Course file:** [content/courses/cp/course.yaml](<D:/Socrat/content/courses/cp/course.yaml>). **Version:** 1.0.0. **Languages:** python, cpp, java.

| Module / subject area | Topics | Lesson words | Quiz | Native | Atoms | Reading links | External unique mapped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Contest fundamentals | 3 | 1615 | 17 | 6 | 27 | 8 | 3649 |
| Contest math | 3 | 1848 | 18 | 6 | 30 | 9 | 3465 |
| Core techniques | 4 | 2157 | 12 | 4 | 36 | 12 | 5116 |
| Dynamic programming for contests | 2 | 1215 | 7 | 3 | 0 | 7 | 2412 |
| Graphs and trees | 4 | 2356 | 13 | 5 | 0 | 12 | 1796 |
| Range query structures | 2 | 1366 | 6 | 2 | 0 | 7 | 1426 |
| String algorithms | 2 | 1110 | 6 | 2 | 0 | 6 | 366 |

**Topic-level local coverage**

| Concept ID | Topic | Words | Sections | Quiz | Native | Atom pack / atoms | Estimated minutes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cp:fast-io | Fast I/O, overflow and operation budgets | 603 | 10 | 6 | 2 | released / 9 | 40 |
| cp:simulation | Simulation and implementation | 527 | 9 | 5 | 2 | released / 9 | 40 |
| cp:complete-search | Complete search | 485 | 10 | 6 | 2 | released / 9 | 45 |
| cp:number-theory | Number theory essentials | 606 | 10 | 6 | 2 | released / 9 | 55 |
| cp:modular-arithmetic | Modular arithmetic | 559 | 9 | 6 | 2 | released / 9 | 50 |
| cp:combinatorics | Counting and binomial coefficients | 683 | 7 | 6 | 2 | released / 12 | 50 |
| cp:prefix-difference | Prefix sums and difference arrays | 519 | 9 | 3 | 1 | released / 9 | 45 |
| cp:binary-search-answer | Binary search on the answer | 574 | 10 | 3 | 1 | released / 9 | 50 |
| cp:greedy-cp | Greedy in contests | 577 | 7 | 3 | 1 | released / 9 | 50 |
| cp:bitmasks | Bitmasks and XOR tricks | 487 | 9 | 3 | 1 | released / 9 | 45 |
| cp:dp-classics | Classic contest DPs | 568 | 9 | 4 | 2 | missing / 0 | 65 |
| cp:bitmask-dp | Bitmask DP | 647 | 8 | 3 | 1 | missing / 0 | 60 |
| cp:graph-techniques | Graph techniques for contests | 568 | 10 | 3 | 1 | missing / 0 | 55 |
| cp:mst | Minimum spanning trees | 548 | 9 | 3 | 1 | missing / 0 | 45 |
| cp:tree-techniques | Tree techniques | 606 | 9 | 4 | 2 | missing / 0 | 60 |
| cp:lca | Lowest common ancestor and binary lifting | 634 | 8 | 3 | 1 | missing / 0 | 60 |
| cp:fenwick-tree | Fenwick tree (Binary Indexed Tree) | 555 | 9 | 3 | 1 | missing / 0 | 50 |
| cp:segment-tree | Segment trees | 811 | 8 | 3 | 1 | missing / 0 | 70 |
| cp:string-hashing | String hashing | 573 | 8 | 3 | 1 | missing / 0 | 50 |
| cp:kmp | Prefix function and KMP | 537 | 9 | 3 | 1 | missing / 0 | 60 |

**Topic-level external coverage**

| Concept ID | Reading | Authored practice links | EP | EA | Impl P/C/J | Roadmap | Python exercises | Book refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cp:fast-io | 3 | 2 | 0 | 0 | 0/0/0 | 1 | 0 | 1 |
| cp:simulation | 2 | 3 | 756 | 2448 | 0/0/0 | 1 | 0 | 0 |
| cp:complete-search | 3 | 3 | 456 | 1595 | 0/0/0 | 2 | 2 | 1 |
| cp:number-theory | 3 | 2 | 1051 | 2817 | 10/7/5 | 0 | 0 | 1 |
| cp:modular-arithmetic | 3 | 2 | 2 | 2 | 5/8/2 | 0 | 0 | 1 |
| cp:combinatorics | 3 | 3 | 701 | 1090 | 11/8/6 | 0 | 0 | 1 |
| cp:prefix-difference | 3 | 2 | 3 | 3 | 0/0/0 | 1 | 0 | 2 |
| cp:binary-search-answer | 3 | 2 | 699 | 1243 | 0/0/0 | 1 | 0 | 1 |
| cp:greedy-cp | 3 | 3 | 1697 | 3977 | 0/0/0 | 1 | 0 | 1 |
| cp:bitmasks | 3 | 2 | 349 | 423 | 0/0/0 | 0 | 0 | 1 |
| cp:dp-classics | 4 | 4 | 1095 | 2341 | 15/10/15 | 1 | 0 | 1 |
| cp:bitmask-dp | 3 | 2 | 294 | 349 | 0/0/0 | 1 | 0 | 1 |
| cp:graph-techniques | 3 | 2 | 239 | 936 | 0/0/0 | 2 | 0 | 2 |
| cp:mst | 3 | 2 | 8 | 8 | 16/9/11 | 2 | 0 | 1 |
| cp:tree-techniques | 3 | 3 | 797 | 976 | 0/0/0 | 1 | 0 | 2 |
| cp:lca | 3 | 2 | 15 | 15 | 1/1/0 | 1 | 0 | 2 |
| cp:fenwick-tree | 3 | 2 | 9 | 41 | 2/1/1 | 1 | 0 | 1 |
| cp:segment-tree | 4 | 2 | 505 | 1419 | 5/1/3 | 1 | 0 | 2 |
| cp:string-hashing | 3 | 2 | 263 | 328 | 1/1/2 | 1 | 0 | 1 |
| cp:kmp | 3 | 2 | 46 | 54 | 2/1/0 | 0 | 0 | 1 |

#### Contest fundamentals — `contest-basics`

Fast I/O, overflow, budgeting operations, simulation and complete search.

##### Fast I/O, overflow and operation budgets — `cp:fast-io`

- **Scope:** The contest basics that silently cost points — slow input, 32-bit overflow, and solutions that cannot fit the time limit.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/fast-io.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/fast-io.yaml>)
- **Prerequisites:** `zero:input-and-arithmetic`, `dsa:complexity`
- **Key points:** Read input in bulk and write output once; avoid Scanner (Java) and endl (C++).; Use 64-bit integers for sums and products; cast before multiplying.; Budget ~10^8 simple ops/s in C++, ~10^7 in Python before you code.; With many test cases, reset state per case and rely on the sum-of-n bound.
- **Pitfalls:** TLE from slow I/O on an otherwise correct solution.; Overflow in int × int before assigning to a 64-bit variable.; Re-allocating large arrays for every test case.
- **Local judge problems:** [Many test cases](<D:/Socrat/content/courses/cp/problems/sum-big.yaml>) (`sum-big`, easy); [A million additions](<D:/Socrat/content/courses/cp/problems/pairwise-sums.yaml>) (`pairwise-sums`, easy)
- **Quiz items:** `overflow-product` (mcq, difficulty 2/5); `budget` (mcq, difficulty 1/5); `java-input` (mcq, difficulty 2/5); `endl` (mcq, difficulty 1/5); `sync-off` (mcq, difficulty 4/5); `endl-cost` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 48 | 48 |
| Fast input and output | H2 | 162 | 162 |
| Overflow | H2 | 59 | 59 |
| The operation budget | H2 | 68 | 68 |
| Multiple test cases | H2 | 41 | 41 |
| Read the statement twice | H2 | 25 | 25 |
| Worked walkthrough | H2 | 48 | 173 |
| Worked walkthrough > Why this works | H3 | 25 | 25 |
| Worked walkthrough > Boundary cases and cost | H3 | 46 | 46 |
| Worked walkthrough > Check your understanding | H3 | 41 | 41 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Fast input and output](<https://usaco.guide/general/fast-io>) | USACO Guide | article / core | 15 | neutral |
| [USACO Guide: Time complexity](<https://usaco.guide/bronze/time-comp>) | USACO Guide | article / core | 25 | neutral |
| [Competitive Programmer's Handbook (free PDF)](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 60 | neutral |

**Other authored/supplemental links**

- Practice — [Weird Algorithm](<https://cses.fi/problemset/task/1068>) (CSES, easy)
- Practice — [Theatre Square](<https://codeforces.com/problemset/problem/1/A>) (Codeforces, easy)
- Roadmap — [Language Syntax](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/language-syntax@kE6qddRhO8C5ur3JbeuhF.md>)
- Handbook §1, printed page 3 — [Introduction: input, output and working with numbers](<https://cses.fi/book/book.pdf#page=13>)

##### Simulation and implementation — `cp:simulation`

- **Scope:** Translate a long statement into exact code — the skill behind most Div 3 A–C problems.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/simulation.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/simulation.yaml>)
- **Prerequisites:** `cp:fast-io`, `zero:grids`
- **Key points:** Model the full state, implement one step, then loop.; Direction arrays turn four branches into one formula.; Check the number of steps against the time limit before simulating.; For huge step counts, find a cycle or closed form.
- **Pitfalls:** Updating state in place when all updates should happen "simultaneously".; Misreading the order of operations in the statement.; Simulating 10^18 steps instead of finding the cycle.
- **Local judge problems:** [Robot on a grid](<D:/Socrat/content/courses/cp/problems/robot-walk.yaml>) (`robot-walk`, medium); [Lift log](<D:/Socrat/content/courses/cp/problems/lift-log.yaml>) (`lift-log`, easy)
- **Quiz items:** `turn-right` (mcq, difficulty 2/5); `simultaneous` (mcq, difficulty 2/5); `huge-steps` (mcq, difficulty 3/5); `simulate-size` (mcq, difficulty 4/5); `order-of-updates` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 52 | 52 |
| A reliable workflow | H2 | 63 | 63 |
| Directions and grids | H2 | 134 | 134 |
| When simulation is too slow | H2 | 58 | 58 |
| Cleanliness pays | H2 | 31 | 31 |
| Worked walkthrough | H2 | 37 | 165 |
| Worked walkthrough > Why this works | H3 | 27 | 27 |
| Worked walkthrough > Boundary cases and cost | H3 | 49 | 49 |
| Worked walkthrough > Check your understanding | H3 | 39 | 39 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Simulation](<https://usaco.guide/bronze/simulation>) | USACO Guide | article / core | 30 | neutral |
| [Competitive Programmer's Handbook (free PDF)](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 30 | neutral |

**Other authored/supplemental links**

- Practice — [Beautiful Matrix](<https://codeforces.com/problemset/problem/263/A>) (Codeforces, easy)
- Practice — [Bit++](<https://codeforces.com/problemset/problem/282/A>) (Codeforces, easy)
- Practice — [Number Spiral](<https://cses.fi/problemset/task/1071>) (CSES, medium)
- Roadmap — [Control Structures](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/control-structures@G74Xp8_EMZO2oEzNTRAli.md>)

##### Complete search — `cp:complete-search`

- **Scope:** When the input is small, try everything — systematically, and with an operation count that fits.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/complete-search.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/complete-search.yaml>)
- **Prerequisites:** `cp:simulation`, `dsa:backtracking`
- **Key points:** Small constraints signal complete search - n ≤ 8 permutations, n ≤ 20 subsets.; Count the work (n! · n, 2^n · n) against the time limit before writing.; Use next_permutation / itertools / bitmasks to enumerate cleanly.; Meet in the middle halves the exponent for n ≈ 40.; Brute force on random small tests is the best way to find bugs in clever solutions.
- **Pitfalls:** Forgetting to start next_permutation from the sorted order.; Underestimating the constant factor of 2^n · n in Python.; Missing symmetric duplicates that double the work.
- **Local judge problems:** [Fair split](<D:/Socrat/content/courses/cp/problems/apple-split.yaml>) (`apple-split`, easy); [Packing the van](<D:/Socrat/content/courses/cp/problems/closest-subset-sum.yaml>) (`closest-subset-sum`, medium)
- **Quiz items:** `perm-feasible` (mcq, difficulty 2/5); `subset-count` (mcq, difficulty 1/5); `mitm` (mcq, difficulty 3/5); `stress` (mcq, difficulty 2/5); `search-bound` (mcq, difficulty 4/5); `meet-in-middle` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 54 | 54 |
| Iterating permutations | H2 | 75 | 75 |
| Iterating subsets with bitmasks | H2 | 51 | 51 |
| Searching the answer space | H2 | 43 | 43 |
| Meet in the middle | H2 | 33 | 33 |
| Brute force as a checker | H2 | 38 | 38 |
| Worked walkthrough | H2 | 45 | 160 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 39 | 39 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Competitive Programmer's Handbook — Chapter 5, Complete search](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / core | 30 | neutral |
| [Apple Division](<https://cses.fi/problemset/task/1623>) | CSES | interactive / core | 20 | neutral |
| [Creating Strings](<https://cses.fi/problemset/task/1622>) | CSES | interactive / core | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Apple Division](<https://cses.fi/problemset/task/1623>) (CSES, easy)
- Practice — [Creating Strings](<https://cses.fi/problemset/task/1622>) (CSES, easy)
- Practice — [Chessboard and Queens](<https://cses.fi/problemset/task/1624>) (CSES, medium)
- Roadmap — [Brute Force](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/brute-force@5T2y6Iqi-I_zOtLkeSPzY.md>)
- Roadmap — [Backtracking](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/backtracking@mKoC5o__gLSTjAlq8iXkV.md>)
- Python exercise 99 — [Enumerate permutations](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-99>)
- Python exercise 100 — [Search integer candidates](<https://github.com/zhiwehu/Python-programming-exercises/blob/master/100%2B%20Python%20challenging%20programming%20exercises%20for%20Python%203.md#question-100>)
- Handbook §5, printed page 47 — [Complete search](<https://cses.fi/book/book.pdf#page=57>)

#### Contest math — `math`

Number theory, modular arithmetic and counting.

##### Number theory essentials — `cp:number-theory`

- **Scope:** GCD, primes, the sieve of Eratosthenes and factorization — the math that appears in nearly every contest.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/number-theory.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/number-theory.yaml>)
- **Prerequisites:** `cp:fast-io`, `zero:functions`
- **Key points:** gcd by Euclid in O(log); lcm = a / gcd · b.; Trial division up to √n tests primality and factorizes.; Divisor count = product of (exponent + 1).; The sieve finds all primes up to N in O(N log log N); spf sieve answers factorization queries fast.
- **Pitfalls:** Starting the sieve's crossing-out at 2p instead of p² (correct but slower) or overflowing p*p.; Forgetting the leftover prime > √n after trial division.; Computing lcm as a·b/gcd and overflowing.
- **Local judge problems:** [Primes in a range](<D:/Socrat/content/courses/cp/problems/prime-count-queries.yaml>) (`prime-count-queries`, medium); [How many divisors?](<D:/Socrat/content/courses/cp/problems/divisor-counts.yaml>) (`divisor-counts`, medium)
- **Quiz items:** `divisor-count` (mcq, difficulty 2/5); `sieve-start` (mcq, difficulty 3/5); `leftover` (mcq, difficulty 2/5); `gcd-value` (mcq, difficulty 1/5); `sieve-complexity` (mcq, difficulty 4/5); `gcd-lcm` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 30 | 30 |
| GCD and LCM | H2 | 43 | 43 |
| Primality and factorization by trial division | H2 | 88 | 88 |
| The sieve of Eratosthenes | H2 | 179 | 179 |
| Smallest prime factor sieve | H2 | 27 | 27 |
| Useful facts | H2 | 50 | 50 |
| Worked walkthrough | H2 | 31 | 158 |
| Worked walkthrough > Why this works | H3 | 30 | 30 |
| Worked walkthrough > Boundary cases and cost | H3 | 42 | 42 |
| Worked walkthrough > Check your understanding | H3 | 42 | 42 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Euclidean algorithm for computing the GCD](<https://cp-algorithms.com/algebra/euclid-algorithm.html>) | CP-Algorithms | article / core | 15 | neutral |
| [Sieve of Eratosthenes](<https://cp-algorithms.com/algebra/sieve-of-eratosthenes.html>) | CP-Algorithms | article / core | 20 | neutral |
| [Counting Divisors](<https://cses.fi/problemset/task/1713>) | CSES | interactive / core | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Counting Divisors](<https://cses.fi/problemset/task/1713>) (CSES, medium)
- Practice — [Common Divisors](<https://cses.fi/problemset/task/1081>) (CSES, medium)
- Handbook §21, printed page 197 — [Number theory](<https://cses.fi/book/book.pdf#page=207>)

##### Modular arithmetic — `cp:modular-arithmetic`

- **Scope:** Keep huge answers small with mod 1e9+7, fast exponentiation, and modular inverses.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/modular-arithmetic.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/modular-arithmetic.yaml>)
- **Prerequisites:** `cp:number-theory`
- **Key points:** Reduce after every addition, subtraction and multiplication.; Subtraction - add m before taking mod to stay non-negative.; Fast exponentiation computes a^b mod m in O(log b).; Division mod a prime = multiplication by x^(p−2) (Fermat).; Use 64-bit integers for products of reduced values.
- **Pitfalls:** Negative results from % in C++/Java.; Dividing modular values directly.; Overflow from multiplying before reducing.
- **Local judge problems:** [Modular fractions](<D:/Socrat/content/courses/cp/problems/mod-expressions.yaml>) (`mod-expressions`, medium); [Huge staircase totals](<D:/Socrat/content/courses/cp/problems/triangular-mod.yaml>) (`triangular-mod`, medium)
- **Quiz items:** `subtract` (mcq, difficulty 2/5); `fermat` (mcq, difficulty 2/5); `pow-steps` (mcq, difficulty 2/5); `when-inverse` (mcq, difficulty 3/5); `mod-subtraction` (mcq, difficulty 4/5); `fermat-inverse` (mcq, difficulty 5/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 113 | 113 |
| Fast exponentiation | H2 | 159 | 159 |
| Modular inverse | H2 | 49 | 49 |
| Negative numbers | H2 | 30 | 30 |
| Common mistakes | H2 | 38 | 38 |
| Worked walkthrough | H2 | 37 | 151 |
| Worked walkthrough > Why this works | H3 | 26 | 26 |
| Worked walkthrough > Boundary cases and cost | H3 | 42 | 42 |
| Worked walkthrough > Check your understanding | H3 | 33 | 33 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Binary exponentiation](<https://cp-algorithms.com/algebra/binary-exp.html>) | CP-Algorithms | article / core | 20 | neutral |
| [Modular inverse](<https://cp-algorithms.com/algebra/module-inverse.html>) | CP-Algorithms | article / core | 20 | neutral |
| [Exponentiation II](<https://cses.fi/problemset/task/1712>) | CSES | interactive / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Exponentiation](<https://cses.fi/problemset/task/1095>) (CSES, easy)
- Practice — [Exponentiation II](<https://cses.fi/problemset/task/1712>) (CSES, medium)
- Handbook §21.2, printed page 201 — [Modular arithmetic](<https://cses.fi/book/book.pdf#page=211>)

##### Counting and binomial coefficients — `cp:combinatorics`

- **Scope:** Count arrangements with factorials, nCr modulo a prime, and the classic counting principles.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/combinatorics.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/combinatorics.yaml>)
- **Prerequisites:** `cp:modular-arithmetic`
- **Key points:** Product rule for independent choices; sum rule for disjoint cases.; C(n, k) = n! / (k!(n − k)!); precompute factorials and inverse factorials for O(1) queries.; Grid paths are C(a + b, a); stars and bars gives C(n + k − 1, k − 1).; Complement counting and inclusion–exclusion simplify "at least one" questions.
- **Pitfalls:** Returning garbage for k > n or k < 0 instead of 0.; Computing an inverse for every query instead of precomputing.; Using Fermat inverses with a non-prime modulus.
- **Local judge problems:** [Choosing teams](<D:/Socrat/content/courses/cp/problems/binomial-queries.yaml>) (`binomial-queries`, medium); [Routes across the city grid](<D:/Socrat/content/courses/cp/problems/grid-routes-mod.yaml>) (`grid-routes-mod`, medium)
- **Quiz items:** `c-5-2` (mcq, difficulty 1/5); `grid` (mcq, difficulty 2/5); `stars-bars` (mcq, difficulty 3/5); `precompute` (mcq, difficulty 1/5); `inclusion-exclusion` (mcq, difficulty 5/5); `share-sweets` (mcq, difficulty 4/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral); `trace` (trace, 1 checks, adapters python,cpp,java); `predict` (predict, 1 checks, adapters python,cpp,java); `debug` (debug, 1 checks, adapters python,cpp,java)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 61 | 61 |
| nCr modulo a prime, fast | H2 | 361 | 361 |
| Classic counting patterns | H2 | 88 | 88 |
| Worked walkthrough | H2 | 32 | 156 |
| Worked walkthrough > Why this works | H3 | 25 | 25 |
| Worked walkthrough > Boundary cases and cost | H3 | 42 | 42 |
| Worked walkthrough > Check your understanding | H3 | 44 | 44 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Binomial coefficients](<https://cp-algorithms.com/combinatorics/binomial-coefficients.html>) | CP-Algorithms | article / core | 25 | neutral |
| [Binomial Coefficients (CSES)](<https://cses.fi/problemset/task/1079>) | CSES | interactive / core | 20 | neutral |
| [Competitive Programmer's Handbook — Chapter 22, Combinatorics](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 30 | neutral |

**Other authored/supplemental links**

- Practice — [Binomial Coefficients](<https://cses.fi/problemset/task/1079>) (CSES, easy)
- Practice — [Two Knights](<https://cses.fi/problemset/task/1072>) (CSES, medium)
- Practice — [Bit Strings](<https://cses.fi/problemset/task/1617>) (CSES, easy)
- Handbook §22, printed page 207 — [Combinatorics](<https://cses.fi/book/book.pdf#page=217>)

#### Core techniques — `techniques`

Difference arrays, binary search on the answer, greedy proofs and bitmasks.

##### Prefix sums and difference arrays — `cp:prefix-difference`

- **Scope:** O(1) range queries with prefix sums, O(1) range updates with difference arrays, and their 2D versions.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/prefix-difference.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/prefix-difference.yaml>)
- **Prerequisites:** `dsa:prefix-sums`, `cp:fast-io`
- **Key points:** Prefix sums - O(1) range-sum queries on a static array.; Difference arrays - O(1) range additions, one final prefix pass.; 2D versions use inclusion–exclusion.; Interleaved updates and queries need Fenwick/segment trees.
- **Pitfalls:** Allocating diff of size n + 1 and writing diff[r + 1] out of bounds.; Forgetting 64-bit accumulators.; Sign errors in 2D inclusion–exclusion.
- **Local judge problems:** [Range additions](<D:/Socrat/content/courses/cp/problems/range-add.yaml>) (`range-add`, easy)
- **Quiz items:** `diff-update` (mcq, difficulty 2/5); `twod` (mcq, difficulty 3/5); `choose` (mcq, difficulty 2/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 35 | 35 |
| Difference arrays | H2 | 203 | 203 |
| Sweep with coordinate compression | H2 | 30 | 30 |
| 2D prefix sums | H2 | 37 | 37 |
| Spotting them | H2 | 42 | 42 |
| Worked walkthrough | H2 | 34 | 150 |
| Worked walkthrough > Why this works | H3 | 18 | 18 |
| Worked walkthrough > Boundary cases and cost | H3 | 48 | 48 |
| Worked walkthrough > Check your understanding | H3 | 37 | 37 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Introduction to prefix sums](<https://usaco.guide/silver/prefix-sums>) | USACO Guide | article / core | 30 | neutral |
| [Static Range Sum Queries](<https://cses.fi/problemset/task/1646>) | CSES | interactive / core | 15 | neutral |
| [Competitive Programmer's Handbook (free PDF)](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Static Range Sum Queries](<https://cses.fi/problemset/task/1646>) (CSES, easy)
- Practice — [Subarray Divisibility](<https://cses.fi/problemset/task/1662>) (CSES, medium)
- Roadmap — [Array](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/array@lxY3ErxJ_D3zkSAXIBUpv.md>)
- Handbook §9.1, printed page 84 — [Prefix sum arrays](<https://cses.fi/book/book.pdf#page=94>)
- Handbook §9.4, printed page 93 — [Range updates with difference arrays](<https://cses.fi/book/book.pdf#page=103>)

##### Binary search on the answer — `cp:binary-search-answer`

- **Scope:** Turn "find the optimum" into "is this value feasible?" and binary search the boundary.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/binary-search-answer.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/binary-search-answer.yaml>)
- **Prerequisites:** `dsa:binary-search`, `cp:fast-io`
- **Key points:** Optimisation → feasibility check + binary search, when feasibility is monotonic.; Each check is usually a greedy O(n) scan; total O(n log range).; First-true uses mid = (lo + hi) / 2; last-true uses (lo + hi + 1) / 2.; Cap accumulations inside ok() to avoid overflow with huge candidates.
- **Pitfalls:** Infinite loops from the wrong mid rounding.; Overflow when summing T / t[i] for T up to 10^18.; Applying it when feasibility is not monotonic.
- **Local judge problems:** [Factory machines](<D:/Socrat/content/courses/cp/problems/factory-time.yaml>) (`factory-time`, medium)
- **Quiz items:** `monotonic` (mcq, difficulty 2/5); `last-true` (mcq, difficulty 3/5); `iterations` (mcq, difficulty 1/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 6 checks, adapters neutral); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 60 | 60 |
| The recipe | H2 | 165 | 165 |
| Example: factory machines | H2 | 45 | 45 |
| Example: split into k parts minimising the largest sum | H2 | 31 | 31 |
| Maximising instead | H2 | 44 | 44 |
| Real-valued answers | H2 | 16 | 16 |
| Worked walkthrough | H2 | 48 | 183 |
| Worked walkthrough > Why this works | H3 | 29 | 29 |
| Worked walkthrough > Boundary cases and cost | H3 | 48 | 48 |
| Worked walkthrough > Check your understanding | H3 | 45 | 45 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Binary search (on the answer)](<https://usaco.guide/silver/binary-search>) | USACO Guide | article / core | 40 | neutral |
| [Factory Machines](<https://cses.fi/problemset/task/1620>) | CSES | interactive / core | 20 | neutral |
| [Array Division](<https://cses.fi/problemset/task/1085>) | CSES | interactive / core | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Factory Machines](<https://cses.fi/problemset/task/1620>) (CSES, medium)
- Practice — [Array Division](<https://cses.fi/problemset/task/1085>) (CSES, medium)
- Roadmap — [Binary Search](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/binary-search@Wt74MRKaZcs8lYvfqjffT.md>)
- Handbook §3.3, printed page 33 — [Binary search: finding the smallest solution](<https://cses.fi/book/book.pdf#page=43>)

##### Greedy in contests — `cp:greedy-cp`

- **Scope:** Find the sort key, make the safe choice, prove it with an exchange — and use a multiset when choices interact.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/greedy-cp.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/greedy-cp.yaml>)
- **Prerequisites:** `dsa:greedy`, `cp:fast-io`
- **Key points:** Greedy = right sort order + safe local choice + exchange-argument proof.; Pair extremes with two pointers; best-available matches with a sorted multiset.; The adjacent-swap comparison often gives the sort key directly.; Stress-test greedy ideas against brute force.
- **Pitfalls:** Trusting a greedy that passes samples but has no proof.; Removing the wrong copy from a multiset (erase(value) removes all copies in C++).; Java primitive-array sort worst cases in hacked tests.
- **Local judge problems:** [Ticket desk](<D:/Socrat/content/courses/cp/problems/ticket-matching.yaml>) (`ticket-matching`, hard)
- **Quiz items:** `boats` (mcq, difficulty 2/5); `multiset-erase` (mcq, difficulty 3/5); `proof` (mcq, difficulty 1/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 49 | 49 |
| A toolbox of greedy patterns | H2 | 297 | 297 |
| Contest habits | H2 | 52 | 52 |
| Worked walkthrough | H2 | 39 | 163 |
| Worked walkthrough > Why this works | H3 | 30 | 30 |
| Worked walkthrough > Boundary cases and cost | H3 | 42 | 42 |
| Worked walkthrough > Check your understanding | H3 | 39 | 39 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Greedy algorithms with sorting](<https://usaco.guide/silver/greedy-sorting>) | USACO Guide | article / core | 35 | neutral |
| [Ferris Wheel](<https://cses.fi/problemset/task/1090>) | CSES | interactive / core | 15 | neutral |
| [Concert Tickets](<https://cses.fi/problemset/task/1091>) | CSES | interactive / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Ferris Wheel](<https://cses.fi/problemset/task/1090>) (CSES, easy)
- Practice — [Concert Tickets](<https://cses.fi/problemset/task/1091>) (CSES, medium)
- Practice — [Movie Festival](<https://cses.fi/problemset/task/1629>) (CSES, easy)
- Roadmap — [Greedy Algorithms](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/greedy-algorithms@qUlqyTjk3XKF9DEm6Lsgb.md>)
- Handbook §6, printed page 57 — [Greedy algorithms](<https://cses.fi/book/book.pdf#page=67>)

##### Bitmasks and XOR tricks — `cp:bitmasks`

- **Scope:** Use integers as sets, iterate submasks, and exploit XOR's algebra in contest problems.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/bitmasks.yaml>); [released atom pack](<D:/Socrat/content/atoms/cp/bitmasks.yaml>)
- **Prerequisites:** `dsa:bit-manipulation`, `cp:complete-search`
- **Key points:** Masks are sets - \|, &, & ~ and shifts are O(1) set operations.; sub = (sub − 1) & mask enumerates all submasks; all-masks-all-submasks is O(3^n).; Prefix XOR gives O(1) range XOR; count XOR-k subarrays with a hash map.; Decompose XOR/AND/OR sums bit by bit.
- **Pitfalls:** Forgetting the empty submask in enumeration loops.; Using 1 << i with i ≥ 31 on 32-bit ints.; Operator precedence - & and ^ bind weaker than == in C++/Java.
- **Local judge problems:** [Subarrays with XOR k](<D:/Socrat/content/courses/cp/problems/xor-subarrays.yaml>) (`xor-subarrays`, medium)
- **Quiz items:** `subset-test` (mcq, difficulty 2/5); `range-xor` (mcq, difficulty 2/5); `three-n` (mcq, difficulty 3/5)
- **Atoms:** `hook` (hook, 0 checks, adapters neutral); `concept` (concept, 0 checks, adapters neutral); `worked` (worked, 0 checks, adapters python,cpp,java); `faded` (faded, 1 checks, adapters neutral); `visualizer` (visualizer, 1 checks, adapters python,cpp,java); `micro` (micro, 0 checks, adapters neutral); `syntax-repair` (micro, 0 checks, adapters neutral); `pattern` (pattern, 0 checks, adapters neutral); `explanation` (explanation, 1 checks, adapters neutral)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 36 | 36 |
| Set operations on masks | H2 | 68 | 68 |
| Iterating the submasks of a mask | H2 | 90 | 90 |
| XOR algebra | H2 | 78 | 78 |
| Gray code and parity | H2 | 32 | 32 |
| Worked walkthrough | H2 | 38 | 156 |
| Worked walkthrough > Why this works | H3 | 23 | 23 |
| Worked walkthrough > Boundary cases and cost | H3 | 40 | 40 |
| Worked walkthrough > Check your understanding | H3 | 42 | 42 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Bitmask visualized](<https://visualgo.net/en/bitmask>) | VisuAlgo | visualizer / core | 10 | neutral |
| [Gray Code](<https://cses.fi/problemset/task/2205>) | CSES | interactive / core | 15 | neutral |
| [Competitive Programmer's Handbook — Chapter 10, Bit manipulation](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 30 | neutral |

**Other authored/supplemental links**

- Practice — [Gray Code](<https://cses.fi/problemset/task/2205>) (CSES, medium)
- Practice — [Apple Division](<https://cses.fi/problemset/task/1623>) (CSES, easy)
- Handbook §10.3, printed page 98 — [Representing sets as bits](<https://cses.fi/book/book.pdf#page=108>)

#### Dynamic programming for contests — `dp-module`

Knapsack, LIS and bitmask DP.

##### Classic contest DPs — `cp:dp-classics`

- **Scope:** Knapsack, coin combinations and LIS in O(n log n) — the DP patterns every contestant must know cold.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/dp-classics.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:dp-2d`
- **Key points:** 0/1 knapsack - capacity loop downwards; unbounded - upwards.; Counting coin sums - sum-outer loop counts orderings, coin-outer counts combinations.; LIS in O(n log n) with tails + binary search (lower_bound for strict).; Check n × W (or n × sum) against the operation budget before choosing a DP.
- **Pitfalls:** Wrong loop order changing what is counted.; Using lower_bound vs upper_bound incorrectly for strict vs non-strict LIS.; Forgetting modulo in counting DPs.
- **Local judge problems:** [Book shop](<D:/Socrat/content/courses/cp/problems/book-shop.yaml>) (`book-shop`, medium); [Longest increasing subsequence](<D:/Socrat/content/courses/cp/problems/lis-length.yaml>) (`lis-length`, medium)
- **Quiz items:** `knap-order` (mcq, difficulty 2/5); `combos` (mcq, difficulty 3/5); `lis-len` (mcq, difficulty 2/5); `lis-strict` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 27 | 27 |
| 0/1 knapsack (each item at most once) | H2 | 116 | 116 |
| Coin combinations: order matters or not? | H2 | 35 | 35 |
| Longest increasing subsequence in O(n log n) | H2 | 165 | 165 |
| Other must-knows | H2 | 31 | 31 |
| Worked walkthrough | H2 | 43 | 161 |
| Worked walkthrough > Why this works | H3 | 31 | 31 |
| Worked walkthrough > Boundary cases and cost | H3 | 41 | 41 |
| Worked walkthrough > Check your understanding | H3 | 33 | 33 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Longest Increasing Subsequence](<https://www.youtube.com/watch?v=cjWnW0hdF1Y>) | NeetCode | video / core | 18 | neutral |
| [USACO Guide: Introduction to DP](<https://usaco.guide/gold/intro-dp>) | USACO Guide | article / core | 40 | neutral |
| [Book Shop (0/1 knapsack)](<https://cses.fi/problemset/task/1158>) | CSES | interactive / core | 20 | neutral |
| [Dynamic Programming – full course](<https://www.youtube.com/watch?v=oBt53YbR9Kk>) | freeCodeCamp | video / deep | 300 | neutral |

**Other authored/supplemental links**

- Practice — [Book Shop](<https://cses.fi/problemset/task/1158>) (CSES, medium)
- Practice — [Coin Combinations I](<https://cses.fi/problemset/task/1635>) (CSES, medium)
- Practice — [Coin Combinations II](<https://cses.fi/problemset/task/1636>) (CSES, medium)
- Practice — [Increasing Subsequence](<https://cses.fi/problemset/task/1145>) (CSES, medium)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)
- Handbook §7, printed page 65 — [Dynamic programming: coins, LIS, knapsack](<https://cses.fi/book/book.pdf#page=75>)

##### Bitmask DP — `cp:bitmask-dp`

- **Scope:** DP over subsets — assignments, orderings and travelling-salesman style problems for n ≤ 20.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/bitmask-dp.yaml>); no teaching-atom pack
- **Prerequisites:** `cp:dp-classics`, `cp:bitmasks`
- **Key points:** dp[mask] (optionally × last element) over subsets replaces n! orderings with 2^n states.; Increasing mask order is a valid DP order.; TSP-style - O(2^n · n²); assignment - O(2^n · n) using popcount as the implicit index.; Fits n ≤ ~20; check memory - 2^20 × 20 longs is 160 MB.
- **Pitfalls:** Memory blow-up with dp[1 << 20][20] of 64-bit values.; Forgetting to skip unreachable states (wasted time and overflow).; Off-by-one between bit positions and 1-indexed items.
- **Local judge problems:** [Shortest study tour](<D:/Socrat/content/courses/cp/problems/shortest-tour.yaml>) (`shortest-tour`, hard)
- **Quiz items:** `states` (mcq, difficulty 2/5); `order` (mcq, difficulty 2/5); `assignment` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 56 | 56 |
| Travelling salesman / Hamiltonian paths | H2 | 334 | 334 |
| Assignment problems | H2 | 44 | 44 |
| Recognising it | H2 | 24 | 24 |
| Worked walkthrough | H2 | 47 | 170 |
| Worked walkthrough > Why this works | H3 | 30 | 30 |
| Worked walkthrough > Boundary cases and cost | H3 | 41 | 41 |
| Worked walkthrough > Check your understanding | H3 | 39 | 39 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [USACO Guide: Bitmask DP](<https://usaco.guide/gold/dp-bitmasks>) | USACO Guide | article / core | 40 | neutral |
| [Hamiltonian Flights](<https://cses.fi/problemset/task/1690>) | CSES | interactive / core | 30 | neutral |
| [Elevator Rides](<https://cses.fi/problemset/task/1653>) | CSES | interactive / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [Hamiltonian Flights](<https://cses.fi/problemset/task/1690>) (CSES, hard)
- Practice — [Elevator Rides](<https://cses.fi/problemset/task/1653>) (CSES, hard)
- Roadmap — [Dynamic Programming](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/dynamic-programming@jKAZNybU9cxufNBdFsqsP.md>)
- Handbook §10.5, printed page 102 — [Dynamic programming over subsets](<https://cses.fi/book/book.pdf#page=112>)

#### Graphs and trees — `graph-module`

Multi-source and 0-1 BFS, minimum spanning trees, tree techniques and LCA.

##### Graph techniques for contests — `cp:graph-techniques`

- **Scope:** Multi-source BFS, 0-1 BFS, state-space graphs and Bellman-Ford — the BFS/Dijkstra variants contests love.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/graph-techniques.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:shortest-paths`, `cp:fast-io`
- **Key points:** Multi-source BFS - enqueue every source at distance 0 first.; 0-1 BFS with a deque replaces Dijkstra for weights in {0, 1}.; Encode extra conditions into the state and search the state graph.; Bellman–Ford handles negative weights and detects negative cycles.; Keep parent pointers to reconstruct paths.
- **Pitfalls:** Running one BFS per source (O(k · (V + E))).; Forgetting that a state may need re-processing in 0-1 BFS when its distance improves.; State spaces too large for memory.
- **Local judge problems:** [Distance to the nearest exit](<D:/Socrat/content/courses/cp/problems/nearest-exit.yaml>) (`nearest-exit`, medium)
- **Quiz items:** `multisource` (mcq, difficulty 2/5); `deque` (mcq, difficulty 2/5); `negcycle` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 39 | 39 |
| Multi-source BFS | H2 | 34 | 34 |
| 0-1 BFS | H2 | 213 | 213 |
| State-space graphs | H2 | 45 | 45 |
| Negative weights and cycles | H2 | 42 | 42 |
| Path reconstruction | H2 | 14 | 14 |
| Worked walkthrough | H2 | 37 | 157 |
| Worked walkthrough > Why this works | H3 | 25 | 25 |
| Worked walkthrough > Boundary cases and cost | H3 | 40 | 40 |
| Worked walkthrough > Check your understanding | H3 | 42 | 42 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Breadth First Search (including 0-1 BFS links)](<https://cp-algorithms.com/graph/breadth-first-search.html>) | CP-Algorithms | article / core | 25 | neutral |
| [Labyrinth](<https://cses.fi/problemset/task/1193>) | CSES | interactive / core | 25 | neutral |
| [Algorithms Course – Graph Theory Tutorial](<https://www.youtube.com/watch?v=09_LlHjoEiY>) | freeCodeCamp | video / deep | 360 | neutral |

**Other authored/supplemental links**

- Practice — [Labyrinth](<https://cses.fi/problemset/task/1193>) (CSES, medium)
- Practice — [Shortest Routes II](<https://cses.fi/problemset/task/1672>) (CSES, medium)
- Roadmap — [Breadth First Search](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/breadth-first-search@c7LdXJPv-5M-NPKSCXYuB.md>)
- Roadmap — [Shortest Path Algorithms](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/shortest-path-algorithms@N-qvYirxpORcaTslvlOL0.md>)
- Handbook §16, printed page 149 — [Directed graphs](<https://cses.fi/book/book.pdf#page=159>)
- Handbook §17, printed page 157 — [Strong connectivity](<https://cses.fi/book/book.pdf#page=167>)

##### Minimum spanning trees — `cp:mst`

- **Scope:** Connect every node at minimum total cost with Kruskal (sort + DSU) or Prim (heap).
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/mst.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:union-find`, `dsa:sorting`
- **Key points:** An MST connects all nodes with minimum total weight and has n − 1 edges.; Kruskal - sort edges, add an edge when DSU says it joins different components.; Cut property justifies the greedy choice.; Fewer than n − 1 accepted edges means the graph is disconnected.
- **Pitfalls:** Forgetting to report disconnected graphs.; Sum overflow with 32-bit totals.; Sorting edges by the wrong field.
- **Local judge problems:** [Road repair](<D:/Socrat/content/courses/cp/problems/road-repair.yaml>) (`road-repair`, medium)
- **Quiz items:** `edges` (mcq, difficulty 1/5); `kruskal-skip` (mcq, difficulty 1/5); `maximum` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 37 | 37 |
| Kruskal's algorithm | H2 | 241 | 241 |
| Why greedy works: the cut property | H2 | 41 | 41 |
| Prim's algorithm | H2 | 29 | 29 |
| Variants | H2 | 31 | 31 |
| Worked walkthrough | H2 | 33 | 147 |
| Worked walkthrough > Why this works | H3 | 28 | 28 |
| Worked walkthrough > Boundary cases and cost | H3 | 35 | 35 |
| Worked walkthrough > Check your understanding | H3 | 38 | 38 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Road Reparation](<https://cses.fi/problemset/task/1675>) | CSES | interactive / core | 20 | neutral |
| [Union-Find visualized](<https://visualgo.net/en/ufds>) | VisuAlgo | visualizer / core | 10 | neutral |
| [Algorithms Course – Graph Theory Tutorial (MST section)](<https://www.youtube.com/watch?v=09_LlHjoEiY>) | freeCodeCamp | video / deep | 60 | neutral |

**Other authored/supplemental links**

- Practice — [Road Reparation](<https://cses.fi/problemset/task/1675>) (CSES, medium)
- Practice — [Road Construction](<https://cses.fi/problemset/task/1676>) (CSES, medium)
- Roadmap — [Minimum Spanning Tree](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/minimum-spanning-tree@Ktqau1VkVrnnVYByqcacM.md>)
- Roadmap — [Kruskals Algorithm](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/kruskals-algorithm@F3bPbwIdCNMzL7QXEYJK3.md>)
- Handbook §15, printed page 141 — [Spanning trees](<https://cses.fi/book/book.pdf#page=151>)

##### Tree techniques — `cp:tree-techniques`

- **Scope:** Root a general tree, compute subtree DP bottom-up, flatten it with an Euler tour, and find its diameter.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/tree-techniques.yaml>); no teaching-atom pack
- **Prerequisites:** `dsa:binary-trees`, `dsa:graph-traversal`
- **Key points:** Root the tree, then compute subtree values bottom-up in reverse BFS order.; Iterative traversal avoids recursion limits on deep trees.; Diameter via two BFS passes.; Euler tour turns subtrees into contiguous ranges.; Rerooting computes all-roots answers in O(n).
- **Pitfalls:** Recursive DFS overflowing on chain-shaped trees.; Treating the undirected edge back to the parent as a child.; Forgetting 64-bit for sums of distances (can reach ~10^10 or more).
- **Local judge problems:** [Team sizes](<D:/Socrat/content/courses/cp/problems/subtree-sizes.yaml>) (`subtree-sizes`, easy); [Sum of distances](<D:/Socrat/content/courses/cp/problems/sum-of-distances.yaml>) (`sum-of-distances`, hard)
- **Quiz items:** `edges-tree` (mcq, difficulty 1/5); `reverse-order` (mcq, difficulty 2/5); `euler` (mcq, difficulty 2/5); `reroot` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 38 | 38 |
| Rooting without recursion | H2 | 245 | 245 |
| Classic tree DPs | H2 | 55 | 55 |
| Euler tour (flattening) | H2 | 50 | 50 |
| Rerooting | H2 | 42 | 42 |
| Worked walkthrough | H2 | 33 | 155 |
| Worked walkthrough > Why this works | H3 | 30 | 30 |
| Worked walkthrough > Boundary cases and cost | H3 | 43 | 43 |
| Worked walkthrough > Check your understanding | H3 | 36 | 36 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Subordinates (subtree sizes)](<https://cses.fi/problemset/task/1674>) | CSES | interactive / core | 15 | neutral |
| [Tree Distances I](<https://cses.fi/problemset/task/1132>) | CSES | interactive / core | 25 | neutral |
| [Depth First Search](<https://cp-algorithms.com/graph/depth-first-search.html>) | CP-Algorithms | article / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Subordinates](<https://cses.fi/problemset/task/1674>) (CSES, easy)
- Practice — [Tree Diameter](<https://cses.fi/problemset/task/1131>) (CSES, medium)
- Practice — [Tree Distances II](<https://cses.fi/problemset/task/1133>) (CSES, hard)
- Roadmap — [Tree Traversal](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/tree-traversal@2Od5lNc6fCM6Gyj_axj4n.md>)
- Handbook §14, printed page 135 — [Tree algorithms: diameter and all longest paths](<https://cses.fi/book/book.pdf#page=145>)
- Handbook §18, printed page 163 — [Tree queries](<https://cses.fi/book/book.pdf#page=173>)

##### Lowest common ancestor and binary lifting — `cp:lca`

- **Scope:** Jump up a tree by powers of two to answer ancestor, LCA and distance queries in O(log n).
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/lca.yaml>); no teaching-atom pack
- **Prerequisites:** `cp:tree-techniques`, `dsa:bit-manipulation`
- **Key points:** up[k][v] is the 2^k-th ancestor; up[k][v] = up[k−1][up[k−1][v]].; Equalise depths with binary jumps, then lift both while ancestors differ.; Distance(u, v) = depth[u] + depth[v] − 2·depth[lca].; O(n log n) preprocessing, O(log n) per query; also solves k-th ancestor queries.
- **Pitfalls:** Not making the root its own ancestor (jumps go out of range).; Too few levels (LOG must satisfy 2^LOG > n).; Recursive DFS for depths on deep trees.
- **Local judge problems:** [Distance queries](<D:/Socrat/content/courses/cp/problems/tree-distance-queries.yaml>) (`tree-distance-queries`, hard)
- **Quiz items:** `jumps` (mcq, difficulty 2/5); `distance` (mcq, difficulty 1/5); `log-size` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 72 | 72 |
| Building the table | H2 | 29 | 29 |
| Answering LCA(u, v) | H2 | 327 | 327 |
| Other uses of binary lifting | H2 | 27 | 27 |
| Worked walkthrough | H2 | 44 | 158 |
| Worked walkthrough > Why this works | H3 | 25 | 25 |
| Worked walkthrough > Boundary cases and cost | H3 | 40 | 40 |
| Worked walkthrough > Check your understanding | H3 | 36 | 36 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Lowest Common Ancestor — Binary Lifting](<https://cp-algorithms.com/graph/lca_binary_lifting.html>) | CP-Algorithms | article / core | 25 | neutral |
| [USACO Guide: Binary jumping](<https://usaco.guide/plat/binary-jump>) | USACO Guide | article / core | 40 | neutral |
| [Company Queries II](<https://cses.fi/problemset/task/1688>) | CSES | interactive / deep | 25 | neutral |

**Other authored/supplemental links**

- Practice — [Company Queries I](<https://cses.fi/problemset/task/1687>) (CSES, medium)
- Practice — [Company Queries II](<https://cses.fi/problemset/task/1688>) (CSES, medium)
- Roadmap — [Tree Data Structures](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/tree-data-structures@r2Jagzbx0qOG-VtxBY-mz.md>)
- Handbook §18.1, printed page 163 — [Finding ancestors](<https://cses.fi/book/book.pdf#page=173>)
- Handbook §18.3, printed page 167 — [Lowest common ancestor](<https://cses.fi/book/book.pdf#page=177>)

#### Range query structures — `range-structures`

Fenwick trees and segment trees for fast updates and queries.

##### Fenwick tree (Binary Indexed Tree) — `cp:fenwick-tree`

- **Scope:** Point updates and prefix sums both in O(log n), with a dozen lines of code.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/fenwick-tree.yaml>); no teaching-atom pack
- **Prerequisites:** `cp:prefix-difference`, `dsa:bit-manipulation`
- **Key points:** Index i covers a block of length i & −i ending at i (1-indexed).; add climbs with i += i & −i; prefix descends with i −= i & −i; both O(log n).; Range sum = prefix(r) − prefix(l − 1).; Store differences for range-add/point-query; index by value for counting.; Works for invertible operations; use segment trees for min/max.
- **Pitfalls:** Using 0-based indexes (i & −i is 0 at index 0 → infinite loop).; Forgetting to keep a copy of values when "setting" instead of "adding".; Not compressing values before indexing by value.
- **Local judge problems:** [Dynamic range sums](<D:/Socrat/content/courses/cp/problems/dynamic-range-sum.yaml>) (`dynamic-range-sum`, medium)
- **Quiz items:** `lowbit` (mcq, difficulty 2/5); `zero-index` (mcq, difficulty 2/5); `minmax` (mcq, difficulty 2/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 278 | 278 |
| Setting a value (not adding) | H2 | 18 | 18 |
| Range update, point query | H2 | 29 | 29 |
| Counting with Fenwick trees | H2 | 38 | 38 |
| Limits | H2 | 16 | 16 |
| Worked walkthrough | H2 | 37 | 151 |
| Worked walkthrough > Why this works | H3 | 24 | 24 |
| Worked walkthrough > Boundary cases and cost | H3 | 46 | 46 |
| Worked walkthrough > Check your understanding | H3 | 31 | 31 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Fenwick Tree](<https://cp-algorithms.com/data_structures/fenwick.html>) | CP-Algorithms | article / core | 30 | neutral |
| [Fenwick tree visualized](<https://visualgo.net/en/fenwicktree>) | VisuAlgo | visualizer / core | 15 | neutral |
| [USACO Guide: Point update range sum](<https://usaco.guide/gold/PURS>) | USACO Guide | article / deep | 40 | neutral |

**Other authored/supplemental links**

- Practice — [Dynamic Range Sum Queries](<https://cses.fi/problemset/task/1648>) (CSES, medium)
- Practice — [Range Update Queries](<https://cses.fi/problemset/task/1651>) (CSES, medium)
- Roadmap — [Fenwick Trees](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/fenwick-trees@V9SWO58kaMsU1NT7q26WG.md>)
- Handbook §9.2, printed page 86 — [Binary indexed tree](<https://cses.fi/book/book.pdf#page=96>)

##### Segment trees — `cp:segment-tree`

- **Scope:** A tree over array ranges that answers range queries for any associative operation with point updates in O(log n).
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/segment-tree.yaml>); no teaching-atom pack
- **Prerequisites:** `cp:fenwick-tree`, `zero:recursion`
- **Key points:** Each node stores the answer for its range; queries touch O(log n) nodes.; Works for any associative operation with an identity element.; Iterative bottom-up version - leaves at size + i, parent i/2, children 2i and 2i+1.; Lazy propagation adds range updates; custom merges answer complex range questions.
- **Pitfalls:** Mixing inclusive and half-open query ranges.; Wrong identity element (e.g. 0 for min).; Recursive implementations that are too slow in Python for 10^5 queries.
- **Local judge problems:** [Dynamic range minimum](<D:/Socrat/content/courses/cp/problems/range-min-updates.yaml>) (`range-min-updates`, medium)
- **Quiz items:** `identity` (mcq, difficulty 2/5); `nodes` (mcq, difficulty 2/5); `associative` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 61 | 61 |
| Iterative bottom-up implementation | H2 | 487 | 487 |
| Beyond the basics | H2 | 59 | 59 |
| When to choose what | H2 | 23 | 23 |
| Worked walkthrough | H2 | 36 | 161 |
| Worked walkthrough > Why this works | H3 | 25 | 25 |
| Worked walkthrough > Boundary cases and cost | H3 | 42 | 42 |
| Worked walkthrough > Check your understanding | H3 | 45 | 45 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Segment Tree](<https://cp-algorithms.com/data_structures/segment_tree.html>) | CP-Algorithms | article / core | 45 | neutral |
| [Segment tree visualized](<https://visualgo.net/en/segmenttree>) | VisuAlgo | visualizer / core | 15 | neutral |
| [Segment Tree Range Minimum Query](<https://www.youtube.com/watch?v=ZBHKZF5w4YU>) | Tushar Roy | video / core | 28 | neutral |
| [Dynamic Range Minimum Queries](<https://cses.fi/problemset/task/1649>) | CSES | interactive / deep | 20 | neutral |

**Other authored/supplemental links**

- Practice — [Dynamic Range Minimum Queries](<https://cses.fi/problemset/task/1649>) (CSES, medium)
- Practice — [Static Range Minimum Queries](<https://cses.fi/problemset/task/1647>) (CSES, easy)
- Roadmap — [Segment Trees](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/segment-trees@iFNS3x9wVRIjpixct6H7x.md>)
- Handbook §9.3, printed page 89 — [Segment tree](<https://cses.fi/book/book.pdf#page=99>)
- Handbook §28, printed page 257 — [Segment trees revisited](<https://cses.fi/book/book.pdf#page=267>)

#### String algorithms — `strings-module`

Polynomial hashing and the prefix function.

##### String hashing — `cp:string-hashing`

- **Scope:** Compare any two substrings in O(1) with polynomial rolling hashes — and keep collisions away.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/string-hashing.yaml>); no teaching-atom pack
- **Prerequisites:** `cp:modular-arithmetic`, `zero:strings`
- **Key points:** Prefix hashes make any substring hash O(1) - h[r] − h[l]·B^(r−l).; Equal strings ⇒ equal hashes; unequal strings collide only with tiny probability.; Use a large modulus (2^61 − 1) or double hashing, with a random base.; Combine with binary search for longest-substring style problems.
- **Pitfalls:** Negative values after subtraction (add M before %).; A single 32-bit-sized modulus with many comparisons — collisions.; Character code 0 (use ord(ch) or ch − 'a' + 1, never 0).
- **Local judge problems:** [Longest repeated substring](<D:/Socrat/content/courses/cp/problems/repeated-substring.yaml>) (`repeated-substring`, hard)
- **Quiz items:** `formula` (mcq, difficulty 2/5); `collisions` (mcq, difficulty 2/5); `zero-code` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 53 | 53 |
| Prefix hashes | H2 | 264 | 264 |
| Collisions | H2 | 41 | 41 |
| Typical uses | H2 | 51 | 51 |
| Worked walkthrough | H2 | 37 | 149 |
| Worked walkthrough > Why this works | H3 | 24 | 24 |
| Worked walkthrough > Boundary cases and cost | H3 | 43 | 43 |
| Worked walkthrough > Check your understanding | H3 | 32 | 32 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [String Hashing](<https://cp-algorithms.com/string/string-hashing.html>) | CP-Algorithms | article / core | 30 | neutral |
| [String Matching](<https://cses.fi/problemset/task/1753>) | CSES | interactive / core | 20 | neutral |
| [Competitive Programmer's Handbook — Chapter 26, String algorithms](<https://cses.fi/book/book.pdf>) | Antti Laaksonen | book / deep | 30 | neutral |

**Other authored/supplemental links**

- Practice — [String Matching](<https://cses.fi/problemset/task/1753>) (CSES, easy)
- Practice — [Finding Borders](<https://cses.fi/problemset/task/1732>) (CSES, medium)
- Roadmap — [Hash Tables](<https://github.com/nilbuild/developer-roadmap/blob/8e62a35a8c113d9b52267046941b49f52e3f621e/roadmaps/datastructures-and-algorithms/content/hash-tables@kSy-8ubESdmIX4Fyl8TSu.md>)
- Handbook §26.3, printed page 245 — [String hashing](<https://cses.fi/book/book.pdf#page=255>)

##### Prefix function and KMP — `cp:kmp`

- **Scope:** Deterministic linear-time pattern matching and border analysis with the prefix function.
- **Files:** [lesson/quiz/resources YAML](<D:/Socrat/content/courses/cp/concepts/kmp.yaml>); no teaching-atom pack
- **Prerequisites:** `cp:string-hashing`
- **Key points:** π[i] = length of the longest proper border of s[0..i].; Computed in O(n) by falling back through borders.; KMP - π of pattern + '#' + text; π[i] == \|pattern\| marks a match.; Smallest period = n − π[n−1].; Exact (no collisions), unlike hashing.
- **Pitfalls:** Forgetting the separator, so matches straddle pattern and text.; Using π[i − 1] instead of π[k − 1] when falling back.; Confusing "proper" border (excludes the whole string).
- **Local judge problems:** [Pattern occurrences](<D:/Socrat/content/courses/cp/problems/pattern-count.yaml>) (`pattern-count`, medium)
- **Quiz items:** `pi-value` (mcq, difficulty 2/5); `period` (mcq, difficulty 2/5); `separator` (mcq, difficulty 3/5)

| Subtopic / section | Heading level | Own words | Including children |
| --- | --- | --- | --- |
| The big idea | H2 | 68 | 68 |
| Computing π in O(n) | H2 | 171 | 171 |
| KMP pattern matching | H2 | 30 | 30 |
| Borders and periods | H2 | 35 | 35 |
| Prefix function vs hashing | H2 | 40 | 40 |
| Worked walkthrough | H2 | 45 | 168 |
| Worked walkthrough > Why this works | H3 | 25 | 25 |
| Worked walkthrough > Boundary cases and cost | H3 | 46 | 46 |
| Worked walkthrough > Check your understanding | H3 | 39 | 39 |

| Curated resource | Source | Kind / level | Minutes | Languages |
| --- | --- | --- | --- | --- |
| [Prefix function — Knuth–Morris–Pratt](<https://cp-algorithms.com/string/prefix-function.html>) | CP-Algorithms | article / core | 40 | neutral |
| [String Matching](<https://cses.fi/problemset/task/1753>) | CSES | interactive / core | 20 | neutral |
| [Finding Periods](<https://cses.fi/problemset/task/1733>) | CSES | interactive / deep | 25 | neutral |

**Other authored/supplemental links**

- Practice — [String Matching](<https://cses.fi/problemset/task/1753>) (CSES, easy)
- Practice — [Finding Periods](<https://cses.fi/problemset/task/1733>) (CSES, medium)
- Handbook §26.4, printed page 247 — [Z-algorithm (pattern matching)](<https://cses.fi/book/book.pdf#page=257>)

## 5. Local native problem bank: every problem

Every row below is a stored native problem. Test counts are from the current local cache; answers/hidden inputs are not reproduced. References column names are authored solution implementations, not the learner language choices. All course manifests list Python/C++/Java even where only the Python authoring reference is present; active judge/runtime availability was not checked.

| Course | Problem / source | Concept | Difficulty | Examples / hints | Tests public / hidden | Authored references | Brute / small generator | Review block |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zero | [Above the average](<D:/Socrat/content/courses/zero/problems/above-average.yaml>) (`above-average`) | lists | easy | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| zero | [Bank ledger](<D:/Socrat/content/courses/zero/problems/bank-ledger.yaml>) (`bank-ledger`) | classes-and-objects | medium | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| zero | [Caesar cipher](<D:/Socrat/content/courses/zero/problems/caesar-shift.yaml>) (`caesar-shift`) | strings | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| zero | [Class election](<D:/Socrat/content/courses/zero/problems/class-election.yaml>) (`class-election`) | maps | easy | 1 / 3 | 1 / 8 | python | yes / yes | not recorded |
| zero | [The clock after a wait](<D:/Socrat/content/courses/zero/problems/clock-after.yaml>) (`clock-after`) | operators-and-expressions | easy | 2 / 3 | 2 / 14 | python,cpp,java | yes / yes | not recorded |
| zero | [Who may join the coding club?](<D:/Socrat/content/courses/zero/problems/club-entry.yaml>) (`club-entry`) | boolean-logic | easy | 1 / 3 | 1 / 6 | python | yes / yes | not recorded |
| zero | [Collatz steps](<D:/Socrat/content/courses/zero/problems/collatz-steps.yaml>) (`collatz-steps`) | while-loops | medium | 2 / 3 | 2 / 13 | python | no / no | not recorded |
| zero | [Sum of digits](<D:/Socrat/content/courses/zero/problems/digit-sum.yaml>) (`digit-sum`) | while-loops | easy | 2 / 3 | 2 / 13 | python | no / no | not recorded |
| zero | [Echo a reading](<D:/Socrat/content/courses/zero/problems/echo-reading.yaml>) (`echo-reading`) | programs-and-output | easy | 1 / 2 | 1 / 4 | python,cpp,java | yes / yes | Owner, 2026-10-13 |
| zero | [Exam ranking](<D:/Socrat/content/courses/zero/problems/exam-ranking.yaml>) (`exam-ranking`) | searching-and-sorting | easy | 2 / 3 | 2 / 10 | python,cpp,java | yes / yes | not recorded |
| zero | [First repeated number](<D:/Socrat/content/courses/zero/problems/first-repeat.yaml>) (`first-repeat`) | maps | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [Fix the average](<D:/Socrat/content/courses/zero/problems/fix-the-average.yaml>) (`fix-the-average`) | debugging | easy | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [FizzBuzz](<D:/Socrat/content/courses/zero/problems/fizzbuzz.yaml>) (`fizzbuzz`) | for-loops | easy | 2 / 3 | 2 / 9 | python | no / no | not recorded |
| zero | [Greatest common divisor](<D:/Socrat/content/courses/zero/problems/gcd-function.yaml>) (`gcd-function`) | functions | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| zero | [Letter grade](<D:/Socrat/content/courses/zero/problems/grade-letter.yaml>) (`grade-letter`) | conditionals | easy | 2 / 3 | 2 / 13 | python | no / no | not recorded |
| zero | [Personal greeting](<D:/Socrat/content/courses/zero/problems/greeting.yaml>) (`greeting`) | input-and-arithmetic | easy | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| zero | [Longest rising streak](<D:/Socrat/content/courses/zero/problems/increasing-steps.yaml>) (`increasing-steps`) | lists | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [Leap year](<D:/Socrat/content/courses/zero/problems/leap-year.yaml>) (`leap-year`) | boolean-logic | easy | 3 / 3 | 3 / 14 | python | no / no | not recorded |
| zero | [Largest of three](<D:/Socrat/content/courses/zero/problems/max-of-three.yaml>) (`max-of-three`) | conditionals | easy | 2 / 3 | 2 / 13 | python | no / no | not recorded |
| zero | [Minesweeper numbers](<D:/Socrat/content/courses/zero/problems/minesweeper-counts.yaml>) (`minesweeper-counts`) | grids | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| zero | [Mirror phrase](<D:/Socrat/content/courses/zero/problems/mirror-phrase.yaml>) (`mirror-phrase`) | strings | easy | 2 / 3 | 2 / 10 | python | yes / yes | not recorded |
| zero | [Museum ticket price](<D:/Socrat/content/courses/zero/problems/museum-ticket.yaml>) (`museum-ticket`) | conditionals | easy | 3 / 3 | 3 / 10 | python | yes / yes | not recorded |
| zero | [One more visitor](<D:/Socrat/content/courses/zero/problems/next-counter.yaml>) (`next-counter`) | variables-and-types | easy | 1 / 2 | 1 / 4 | python,cpp,java | yes / yes | Owner, 2026-10-13 |
| zero | [Number mood](<D:/Socrat/content/courses/zero/problems/number-mood.yaml>) (`number-mood`) | math-on-numbers | easy | 3 / 3 | 3 / 13 | python,cpp,java | yes / yes | not recorded |
| zero | [Number triangle](<D:/Socrat/content/courses/zero/problems/number-triangle.yaml>) (`number-triangle`) | nested-loops | easy | 1 / 3 | 1 / 9 | python | yes / yes | not recorded |
| zero | [Pairs that sum to a target](<D:/Socrat/content/courses/zero/problems/pair-count.yaml>) (`pair-count`) | nested-loops | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| zero | [Party packs](<D:/Socrat/content/courses/zero/problems/party-packs.yaml>) (`party-packs`) | operators-and-expressions | easy | 2 / 3 | 2 / 14 | python,cpp,java | yes / yes | not recorded |
| zero | [Fast power](<D:/Socrat/content/courses/zero/problems/power-recursive.yaml>) (`power-recursive`) | recursion | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [Prime or not](<D:/Socrat/content/courses/zero/problems/prime-check.yaml>) (`prime-check`) | functions | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| zero | [Reverse the digits](<D:/Socrat/content/courses/zero/problems/reverse-the-digits.yaml>) (`reverse-the-digits`) | while-loops | easy | 2 / 3 | 2 / 12 | python | yes / yes | not recorded |
| zero | [Row and column totals](<D:/Socrat/content/courses/zero/problems/row-and-column-sums.yaml>) (`row-and-column-sums`) | grids | easy | 1 / 3 | 1 / 8 | python | yes / yes | not recorded |
| zero | [Runner-up score](<D:/Socrat/content/courses/zero/problems/runner-up-score.yaml>) (`runner-up-score`) | lists | easy | 2 / 3 | 2 / 10 | python | yes / yes | not recorded |
| zero | [Split the bill](<D:/Socrat/content/courses/zero/problems/split-the-bill.yaml>) (`split-the-bill`) | input-and-arithmetic | easy | 2 / 3 | 2 / 12 | python | yes / yes | not recorded |
| zero | [Tiling the floor](<D:/Socrat/content/courses/zero/problems/square-tiles.yaml>) (`square-tiles`) | math-on-numbers | easy | 2 / 3 | 2 / 14 | python,cpp,java | yes / yes | not recorded |
| zero | [Right-aligned staircase](<D:/Socrat/content/courses/zero/problems/staircase.yaml>) (`staircase`) | nested-loops | easy | 2 / 3 | 2 / 7 | python | no / no | not recorded |
| zero | [Ways to climb](<D:/Socrat/content/courses/zero/problems/stairs-ways.yaml>) (`stairs-ways`) | recursion | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [Sum of multiples](<D:/Socrat/content/courses/zero/problems/sum-of-multiples.yaml>) (`sum-of-multiples`) | for-loops | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [Counting the swaps](<D:/Socrat/content/courses/zero/problems/swap-count.yaml>) (`swap-count`) | searching-and-sorting | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| zero | [Celsius to Fahrenheit](<D:/Socrat/content/courses/zero/problems/temperature-converter.yaml>) (`temperature-converter`) | variables-and-types | easy | 2 / 3 | 2 / 12 | python | yes / yes | not recorded |
| zero | [Print a ticket stub](<D:/Socrat/content/courses/zero/problems/ticket-stub.yaml>) (`ticket-stub`) | programs-and-output | easy | 2 / 3 | 2 / 10 | python | yes / yes | not recorded |
| zero | [Minutes to hours](<D:/Socrat/content/courses/zero/problems/time-convert.yaml>) (`time-convert`) | input-and-arithmetic | easy | 2 / 3 | 2 / 14 | python | no / no | not recorded |
| zero | [A times table](<D:/Socrat/content/courses/zero/problems/times-table.yaml>) (`times-table`) | for-loops | easy | 1 / 3 | 1 / 11 | python | yes / yes | not recorded |
| zero | [Does a pair exist?](<D:/Socrat/content/courses/zero/problems/two-sum-exists.yaml>) (`two-sum-exists`) | problem-solving | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| zero | [Count the vowels](<D:/Socrat/content/courses/zero/problems/vowel-count.yaml>) (`vowel-count`) | strings | easy | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| zero | [Word frequency](<D:/Socrat/content/courses/zero/problems/word-frequency.yaml>) (`word-frequency`) | maps | easy | 2 / 3 | 2 / 9 | python | no / no | not recorded |
| dsa | [Balance point](<D:/Socrat/content/courses/dsa/problems/balance-point.yaml>) (`balance-point`) | prefix-sums | easy | 2 / 3 | 2 / 10 | python | yes / yes | not recorded |
| dsa | [Balanced brackets](<D:/Socrat/content/courses/dsa/problems/balanced-brackets.yaml>) (`balanced-brackets`) | stacks | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| dsa | [Balanced shifts](<D:/Socrat/content/courses/dsa/problems/balanced-segments.yaml>) (`balanced-segments`) | hashing | medium | 2 / 3 | 2 / 10 | python,cpp,java | yes / yes | not recorded |
| dsa | [Balanced splits](<D:/Socrat/content/courses/dsa/problems/balanced-splits.yaml>) (`balanced-splits`) | tree-patterns | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Validate a BST](<D:/Socrat/content/courses/dsa/problems/bst-validate.yaml>) (`bst-validate`) | bst | medium | 1 / 3 | 1 / 4 | python | no / no | not recorded |
| dsa | [Bundles of stickers](<D:/Socrat/content/courses/dsa/problems/bundle-count.yaml>) (`bundle-count`) | knapsack-unbounded | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Jump to the end](<D:/Socrat/content/courses/dsa/problems/can-reach-end.yaml>) (`can-reach-end`) | greedy | medium | 2 / 3 | 2 / 12 | python | no / no | not recorded |
| dsa | [Cheapest routes](<D:/Socrat/content/courses/dsa/problems/cheapest-routes.yaml>) (`cheapest-routes`) | shortest-paths | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Longest unbroken run of values](<D:/Socrat/content/courses/dsa/problems/consecutive-run.yaml>) (`consecutive-run`) | arrays-hashing | medium | 1 / 3 | 1 / 9 | python | yes / yes | not recorded |
| dsa | [Container with most water](<D:/Socrat/content/courses/dsa/problems/container-water.yaml>) (`container-water`) | two-pointers | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Count inversions](<D:/Socrat/content/courses/dsa/problems/count-inversions.yaml>) (`count-inversions`) | sorting | hard | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Count the islands](<D:/Socrat/content/courses/dsa/problems/count-islands.yaml>) (`count-islands`) | graph-traversal | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Courier vans](<D:/Socrat/content/courses/dsa/problems/courier-vans.yaml>) (`courier-vans`) | binary-search-on-answer | medium | 2 / 3 | 2 / 13 | python,cpp,java | yes / yes | not recorded |
| dsa | [Course order](<D:/Socrat/content/courses/dsa/problems/course-order.yaml>) (`course-order`) | topological-sort | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Merging crate stacks](<D:/Socrat/content/courses/dsa/problems/crate-merging.yaml>) (`crate-merging`) | dp-partition | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Pairs with a fixed gap](<D:/Socrat/content/courses/dsa/problems/difference-pairs.yaml>) (`difference-pairs`) | two-pointers | medium | 2 / 3 | 2 / 9 | python | yes / yes | not recorded |
| dsa | [Profits that split evenly](<D:/Socrat/content/courses/dsa/problems/divisible-subarrays.yaml>) (`divisible-subarrays`) | prefix-sums | medium | 1 / 3 | 1 / 9 | python | yes / yes | not recorded |
| dsa | [Exact change at the festival](<D:/Socrat/content/courses/dsa/problems/exact-change-festival.yaml>) (`exact-change-festival`) | knapsack-01 | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Fair teams](<D:/Socrat/content/courses/dsa/problems/fair-teams.yaml>) (`fair-teams`) | knapsack-01 | medium | 3 / 3 | 3 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Colouring the posts](<D:/Socrat/content/courses/dsa/problems/fence-painting.yaml>) (`fence-painting`) | dp-introduction | medium | 3 / 3 | 3 / 13 | python,cpp,java | yes / yes | not recorded |
| dsa | [Fewest hops](<D:/Socrat/content/courses/dsa/problems/fewest-hops.yaml>) (`fewest-hops`) | graph-traversal | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Grid paths with obstacles](<D:/Socrat/content/courses/dsa/problems/grid-paths.yaml>) (`grid-paths`) | dp-2d | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Heaviest rising chain](<D:/Socrat/content/courses/dsa/problems/heaviest-rise.yaml>) (`heaviest-rise`) | dp-lis | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Non-adjacent picks](<D:/Socrat/content/courses/dsa/problems/house-robber.yaml>) (`house-robber`) | dp-1d | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Minimum reading speed](<D:/Socrat/content/courses/dsa/problems/koko-speed.yaml>) (`koko-speed`) | binary-search | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [The k-th cheapest meal](<D:/Socrat/content/courses/dsa/problems/kth-cheapest-meal.yaml>) (`kth-cheapest-meal`) | binary-search-on-answer | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Live k-th best score](<D:/Socrat/content/courses/dsa/problems/kth-largest-stream.yaml>) (`kth-largest-stream`) | heaps | medium | 1 / 3 | 1 / 10 | python | no / no | not recorded |
| dsa | [Lab partners](<D:/Socrat/content/courses/dsa/problems/lab-partners.yaml>) (`lab-partners`) | dp-advanced-patterns | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Longest common subsequence](<D:/Socrat/content/courses/dsa/problems/lcs-length.yaml>) (`lcs-length`) | dp-2d | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [The popular shelf](<D:/Socrat/content/courses/dsa/problems/library-shelf.yaml>) (`library-shelf`) | design-data-structures | hard | 2 / 3 | 2 / 13 | python,cpp,java | yes / yes | not recorded |
| dsa | [Longest evenly shared run](<D:/Socrat/content/courses/dsa/problems/longest-divisible-run.yaml>) (`longest-divisible-run`) | hashing | medium | 2 / 3 | 2 / 13 | python,cpp,java | yes / yes | not recorded |
| dsa | [Longest substring without repeats](<D:/Socrat/content/courses/dsa/problems/longest-unique-substring.yaml>) (`longest-unique-substring`) | sliding-window | medium | 3 / 3 | 3 / 11 | python | no / no | not recorded |
| dsa | [Count in range](<D:/Socrat/content/courses/dsa/problems/lower-bound-queries.yaml>) (`lower-bound-queries`) | binary-search | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| dsa | [Matching sock pairs](<D:/Socrat/content/courses/dsa/problems/matching-pairs.yaml>) (`matching-pairs`) | complexity | easy | 1 / 3 | 1 / 9 | python | yes / yes | not recorded |
| dsa | [Most mentoring sessions](<D:/Socrat/content/courses/dsa/problems/max-meetings.yaml>) (`max-meetings`) | greedy | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Best k-day streak](<D:/Socrat/content/courses/dsa/problems/max-window-sum.yaml>) (`max-window-sum`) | sliding-window | easy | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Fence around the meadow](<D:/Socrat/content/courses/dsa/problems/meadow-fence.yaml>) (`meadow-fence`) | dp-squares | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Merge study sessions](<D:/Socrat/content/courses/dsa/problems/merge-intervals.yaml>) (`merge-intervals`) | intervals | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Fewest coins](<D:/Socrat/content/courses/dsa/problems/min-coins.yaml>) (`min-coins`) | dp-1d | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [N-Queens](<D:/Socrat/content/courses/dsa/problems/n-queens-count.yaml>) (`n-queens-count`) | backtracking | hard | 2 / 3 | 2 / 9 | python | no / no | not recorded |
| dsa | [Shortest walk to a leaf](<D:/Socrat/content/courses/dsa/problems/nearest-leaf.yaml>) (`nearest-leaf`) | tree-patterns | medium | 2 / 3 | 2 / 9 | python,cpp,java | yes / yes | not recorded |
| dsa | [Nearest taller neighbour](<D:/Socrat/content/courses/dsa/problems/nearest-taller-either-side.yaml>) (`nearest-taller-either-side`) | monotonic-stack | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Days until warmer](<D:/Socrat/content/courses/dsa/problems/next-greater.yaml>) (`next-greater`) | stacks | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Next taller building](<D:/Socrat/content/courses/dsa/problems/next-taller-building.yaml>) (`next-taller-building`) | stacks | medium | 1 / 3 | 1 / 9 | python | yes / yes | not recorded |
| dsa | [Growing friend groups](<D:/Socrat/content/courses/dsa/problems/online-components.yaml>) (`online-components`) | union-find | medium | 1 / 3 | 1 / 10 | python | no / no | not recorded |
| dsa | [Pair sum in a sorted array](<D:/Socrat/content/courses/dsa/problems/pair-sum-sorted.yaml>) (`pair-sum-sorted`) | two-pointers | easy | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Palindrome trimming](<D:/Socrat/content/courses/dsa/problems/palindrome-trim.yaml>) (`palindrome-trim`) | dp-lcs | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Peak totals](<D:/Socrat/content/courses/dsa/problems/peak-totals.yaml>) (`peak-totals`) | monotonic-stack | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Playlist editor](<D:/Socrat/content/courses/dsa/problems/playlist-editor.yaml>) (`playlist-editor`) | linked-lists | medium | 1 / 3 | 1 / 10 | python | no / no | not recorded |
| dsa | [Autocomplete counts](<D:/Socrat/content/courses/dsa/problems/prefix-counts.yaml>) (`prefix-counts`) | tries | medium | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| dsa | [Range sum queries](<D:/Socrat/content/courses/dsa/problems/range-sum-queries.yaml>) (`range-sum-queries`) | prefix-sums | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| dsa | [Leaderboard](<D:/Socrat/content/courses/dsa/problems/rank-students.yaml>) (`rank-students`) | sorting | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| dsa | [Trading with rest days](<D:/Socrat/content/courses/dsa/problems/rest-days.yaml>) (`rest-days`) | dp-stocks | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Ride tokens](<D:/Socrat/content/courses/dsa/problems/ride-tokens.yaml>) (`ride-tokens`) | knapsack-unbounded | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Seating plans](<D:/Socrat/content/courses/dsa/problems/seating-plans.yaml>) (`seating-plans`) | recursion-patterns | medium | 2 / 3 | 2 / 13 | python,cpp,java | yes / yes | not recorded |
| dsa | [Shortest stretch to reach a goal](<D:/Socrat/content/courses/dsa/problems/shortest-fundraiser.yaml>) (`shortest-fundraiser`) | sliding-window | medium | 2 / 3 | 2 / 9 | python | yes / yes | not recorded |
| dsa | [Signal splits](<D:/Socrat/content/courses/dsa/problems/signal-splits.yaml>) (`signal-splits`) | dp-partition | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [The unpaired badge](<D:/Socrat/content/courses/dsa/problems/single-number.yaml>) (`single-number`) | bit-manipulation | easy | 2 / 3 | 2 / 9 | python | no / no | not recorded |
| dsa | [Solar panel plots](<D:/Socrat/content/courses/dsa/problems/solar-squares.yaml>) (`solar-squares`) | dp-squares | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Squares in order](<D:/Socrat/content/courses/dsa/problems/sorted-squares.yaml>) (`sorted-squares`) | two-pointers | easy | 1 / 3 | 1 / 8 | python | yes / yes | not recorded |
| dsa | [Squad selection](<D:/Socrat/content/courses/dsa/problems/squad-selection.yaml>) (`squad-selection`) | recursion-patterns | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Stepping stones](<D:/Socrat/content/courses/dsa/problems/stepping-stones-path.yaml>) (`stepping-stones-path`) | dp-introduction | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Street lamps on a tree](<D:/Socrat/content/courses/dsa/problems/street-lamps.yaml>) (`street-lamps`) | dp-on-trees | hard | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Subarrays summing to K](<D:/Socrat/content/courses/dsa/problems/subarray-sum-k.yaml>) (`subarray-sum-k`) | prefix-sums | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Subsets with target sum](<D:/Socrat/content/courses/dsa/problems/subset-sum-count.yaml>) (`subset-sum-count`) | backtracking | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| dsa | [Triangle number queries](<D:/Socrat/content/courses/dsa/problems/sum-queries.yaml>) (`sum-queries`) | complexity | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| dsa | [Thumbnail cache](<D:/Socrat/content/courses/dsa/problems/thumbnail-cache.yaml>) (`thumbnail-cache`) | design-data-structures | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Tidy shelf](<D:/Socrat/content/courses/dsa/problems/tidy-shelf.yaml>) (`tidy-shelf`) | dp-lis | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Top K frequent](<D:/Socrat/content/courses/dsa/problems/top-k-frequent.yaml>) (`top-k-frequent`) | arrays-hashing | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| dsa | [Binary tree diameter](<D:/Socrat/content/courses/dsa/problems/tree-diameter.yaml>) (`tree-diameter`) | binary-trees | medium | 2 / 3 | 2 / 8 | python | no / no | not recorded |
| dsa | [Level sums](<D:/Socrat/content/courses/dsa/problems/tree-levels.yaml>) (`tree-levels`) | binary-trees | easy | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| dsa | [Take one or two](<D:/Socrat/content/courses/dsa/problems/two-coin-take.yaml>) (`two-coin-take`) | dp-advanced-patterns | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Priced typo fixes](<D:/Socrat/content/courses/dsa/problems/typo-costs.yaml>) (`typo-costs`) | dp-edit-distance | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Anagram check](<D:/Socrat/content/courses/dsa/problems/valid-anagram.yaml>) (`valid-anagram`) | arrays-hashing | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| dsa | [Warehouse trading](<D:/Socrat/content/courses/dsa/problems/warehouse-trading.yaml>) (`warehouse-trading`) | dp-stocks | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| dsa | [Watchtowers on the trails](<D:/Socrat/content/courses/dsa/problems/watchtowers.yaml>) (`watchtowers`) | dp-on-trees | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Shared playlist](<D:/Socrat/content/courses/dsa/problems/weighted-common-playlist.yaml>) (`weighted-common-playlist`) | dp-lcs | medium | 2 / 3 | 2 / 11 | python,cpp,java | yes / yes | not recorded |
| dsa | [Whole-number square root](<D:/Socrat/content/courses/dsa/problems/whole-square-root.yaml>) (`whole-square-root`) | binary-search | medium | 1 / 3 | 1 / 3 | python | yes / yes | not recorded |
| dsa | [Wildcard sightings](<D:/Socrat/content/courses/dsa/problems/wildcard-sightings.yaml>) (`wildcard-sightings`) | dp-edit-distance | medium | 2 / 3 | 2 / 12 | python,cpp,java | yes / yes | not recorded |
| cp | [Fair split](<D:/Socrat/content/courses/cp/problems/apple-split.yaml>) (`apple-split`) | complete-search | easy | 2 / 3 | 2 / 10 | python | no / no | not recorded |
| cp | [Choosing teams](<D:/Socrat/content/courses/cp/problems/binomial-queries.yaml>) (`binomial-queries`) | combinatorics | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Book shop](<D:/Socrat/content/courses/cp/problems/book-shop.yaml>) (`book-shop`) | dp-classics | medium | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [Packing the van](<D:/Socrat/content/courses/cp/problems/closest-subset-sum.yaml>) (`closest-subset-sum`) | complete-search | medium | 2 / 3 | 2 / 9 | python | yes / yes | not recorded |
| cp | [How many divisors?](<D:/Socrat/content/courses/cp/problems/divisor-counts.yaml>) (`divisor-counts`) | number-theory | medium | 1 / 3 | 1 / 6 | python | yes / yes | not recorded |
| cp | [Dynamic range sums](<D:/Socrat/content/courses/cp/problems/dynamic-range-sum.yaml>) (`dynamic-range-sum`) | fenwick-tree | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Factory machines](<D:/Socrat/content/courses/cp/problems/factory-time.yaml>) (`factory-time`) | binary-search-answer | medium | 1 / 3 | 1 / 10 | python | no / no | not recorded |
| cp | [Routes across the city grid](<D:/Socrat/content/courses/cp/problems/grid-routes-mod.yaml>) (`grid-routes-mod`) | combinatorics | medium | 1 / 3 | 1 / 3 | python | yes / yes | not recorded |
| cp | [Lift log](<D:/Socrat/content/courses/cp/problems/lift-log.yaml>) (`lift-log`) | simulation | easy | 1 / 3 | 1 / 7 | python | yes / yes | not recorded |
| cp | [Longest increasing subsequence](<D:/Socrat/content/courses/cp/problems/lis-length.yaml>) (`lis-length`) | dp-classics | medium | 1 / 3 | 1 / 10 | python | no / no | not recorded |
| cp | [Modular fractions](<D:/Socrat/content/courses/cp/problems/mod-expressions.yaml>) (`mod-expressions`) | modular-arithmetic | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Distance to the nearest exit](<D:/Socrat/content/courses/cp/problems/nearest-exit.yaml>) (`nearest-exit`) | graph-techniques | medium | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [A million additions](<D:/Socrat/content/courses/cp/problems/pairwise-sums.yaml>) (`pairwise-sums`) | fast-io | easy | 1 / 3 | 1 / 3 | python | yes / yes | not recorded |
| cp | [Pattern occurrences](<D:/Socrat/content/courses/cp/problems/pattern-count.yaml>) (`pattern-count`) | kmp | medium | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| cp | [Primes in a range](<D:/Socrat/content/courses/cp/problems/prime-count-queries.yaml>) (`prime-count-queries`) | number-theory | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Range additions](<D:/Socrat/content/courses/cp/problems/range-add.yaml>) (`range-add`) | prefix-difference | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Dynamic range minimum](<D:/Socrat/content/courses/cp/problems/range-min-updates.yaml>) (`range-min-updates`) | segment-tree | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Longest repeated substring](<D:/Socrat/content/courses/cp/problems/repeated-substring.yaml>) (`repeated-substring`) | string-hashing | hard | 2 / 3 | 2 / 11 | python | no / no | not recorded |
| cp | [Road repair](<D:/Socrat/content/courses/cp/problems/road-repair.yaml>) (`road-repair`) | mst | medium | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Robot on a grid](<D:/Socrat/content/courses/cp/problems/robot-walk.yaml>) (`robot-walk`) | simulation | medium | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [Shortest study tour](<D:/Socrat/content/courses/cp/problems/shortest-tour.yaml>) (`shortest-tour`) | bitmask-dp | hard | 1 / 3 | 1 / 10 | python | no / no | not recorded |
| cp | [Team sizes](<D:/Socrat/content/courses/cp/problems/subtree-sizes.yaml>) (`subtree-sizes`) | tree-techniques | easy | 1 / 3 | 1 / 8 | python | no / no | not recorded |
| cp | [Many test cases](<D:/Socrat/content/courses/cp/problems/sum-big.yaml>) (`sum-big`) | fast-io | easy | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [Sum of distances](<D:/Socrat/content/courses/cp/problems/sum-of-distances.yaml>) (`sum-of-distances`) | tree-techniques | hard | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [Ticket desk](<D:/Socrat/content/courses/cp/problems/ticket-matching.yaml>) (`ticket-matching`) | greedy-cp | hard | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [Distance queries](<D:/Socrat/content/courses/cp/problems/tree-distance-queries.yaml>) (`tree-distance-queries`) | lca | hard | 1 / 3 | 1 / 9 | python | no / no | not recorded |
| cp | [Huge staircase totals](<D:/Socrat/content/courses/cp/problems/triangular-mod.yaml>) (`triangular-mod`) | modular-arithmetic | medium | 1 / 3 | 1 / 4 | python | yes / yes | not recorded |
| cp | [Subarrays with XOR k](<D:/Socrat/content/courses/cp/problems/xor-subarrays.yaml>) (`xor-subarrays`) | bitmasks | medium | 2 / 3 | 2 / 10 | python | no / no | not recorded |

**Native bank totals:** 152 problems; 259 sample examples; 454 hints; 259 public and 1519 hidden cached tests. Every problem has a Python reference and input generator. Only 69 have a brute/small-generator pair and C++/Java authored references. Only 4 have explicit per-language starters; the runtime otherwise supplies generic starters. Two problems record Owner review on 2026-10-13: `echo-reading` and `next-counter`. Other review status is unestablished by these YAMLs.

## 6. External practice bank: sources, subjects and raw tags

| Platform | Unique problems | Easy | Medium | Hard | Locally stored statements/solutions |
| --- | --- | --- | --- | --- | --- |
| Codeforces | 10485 | 2700 | 2306 | 5479 | 0 |
| LeetCode | 3110 | 693 | 1684 | 733 | 0 |
| CSES | 294 | 51 | 111 | 132 | 0 |

There are 31,464 problem→concept mappings across 13,889 problems. 74 are Striver-A2Z-flagged. 3,096 problems have company counts. These flags/frequencies do not form separate lesson collections or guarantee current employer interview usage.

**Complete individual external entries:** filter `asset_type=external_problem` in [content-inventory.csv](<D:/Socrat/content-inventory.csv>). It includes each ID/title/URL, all mapped concepts and modules, primary concept, platform, difficulty and provider tags. For exact company associations/frequencies, use [content/practice/companies.json](<D:/Socrat/content/practice/companies.json>); the CSV includes all 637 company summaries and their problem IDs.

### Raw external tags / provider subtopics

These are the exact imported tag strings, not additional authored Socrat topics. A problem can have multiple tags, so the counts overlap. Heuristic concept mapping can be broad; large tag counts do not establish equally deep local teaching coverage.

| Raw tag | Problem records | Providers |
| --- | --- | --- |
| 0-1 BFS | 2 | LeetCode |
| 0-1 Knapsack | 8 | LeetCode |
| 2-sat | 40 | Codeforces |
| A* Search | 5 | LeetCode |
| Advanced Graph Problems | 28 | CSES |
| Advanced Techniques | 1 | CSES |
| Aho–Corasick Algorithm | 4 | LeetCode |
| Algorithm X | 3 | LeetCode |
| Array | 1910 | LeetCode |
| Articulation Point | 1 | LeetCode |
| Backtracking | 107 | LeetCode |
| Bellman–Ford Algorithm | 2 | LeetCode |
| Biconnected Component | 1 | LeetCode |
| Bidirectional Search | 7 | LeetCode |
| Binary Indexed Tree | 39 | LeetCode |
| Binary Lifting | 12 | LeetCode |
| Binary Search | 298 | LeetCode |
| Binary Search Tree | 40 | LeetCode |
| Binary Tree | 169 | LeetCode |
| Bipartite Graph | 10 | LeetCode |
| Bit Manipulation | 244 | LeetCode |
| Bitmask | 48 | LeetCode |
| Bitwise Operations | 11 | CSES |
| Borůvka's Algorithm | 3 | LeetCode |
| Boyer–Moore Majority Vote Algorithm | 3 | LeetCode |
| Boyer–Moore String-Search Algorithm | 6 | LeetCode |
| Bracket Sequences | 15 | LeetCode |
| Brainteaser | 18 | LeetCode |
| Breadth-First Search | 244 | LeetCode |
| Bridge (Graph) | 1 | LeetCode |
| Brute-Force Search | 2 | LeetCode |
| Bubble Sort | 4 | LeetCode |
| Bucket Sort | 6 | LeetCode |
| Bézout's Lemma | 2 | LeetCode |
| Cartesian Tree | 5 | LeetCode |
| Combinatorics | 50 | LeetCode |
| Complete Knapsack | 5 | LeetCode |
| Construction Problems | 8 | CSES |
| Convex Hull | 1 | LeetCode |
| Counting | 181 | LeetCode |
| Counting Problems | 18 | CSES |
| Counting Sort | 10 | LeetCode |
| DP on Trees | 30 | LeetCode |
| Dancing Links | 1 | LeetCode |
| Data Stream | 24 | LeetCode |
| Depth-First Search | 317 | LeetCode |
| Design | 130 | LeetCode |
| Dijkstra's Algorithm | 16 | LeetCode |
| Dinic's Algorithm | 3 | LeetCode |
| Directed Acyclic Graph | 17 | LeetCode |
| Divide and Conquer | 55 | LeetCode |
| Doubly-Linked List | 13 | LeetCode |
| Dynamic Programming | 598 | CSES, LeetCode |
| Edmonds–Karp Algorithm | 3 | LeetCode |
| Enumeration | 119 | LeetCode |
| Euclidean Algorithm | 20 | LeetCode |
| Euler's Theorem | 1 | LeetCode |
| Euler's Totient Function | 1 | LeetCode |
| Eulerian Circuit | 3 | LeetCode |
| Eulerian Graph | 1 | LeetCode |
| Eulerian Path | 3 | LeetCode |
| Extended Euclidean Algorithm | 2 | LeetCode |
| Fermat's Little Theorem | 10 | LeetCode |
| Flow Network | 7 | LeetCode |
| Floyd's Cycle Finding Algorithm | 6 | LeetCode |
| Floyd–Warshall Algorithm | 2 | LeetCode |
| Game Theory | 26 | LeetCode |
| Geometry | 42 | LeetCode |
| Graph Algorithms | 36 | CSES |
| Graph Coloring | 5 | LeetCode |
| Graph Theory | 165 | LeetCode |
| Greatest Common Divisor | 22 | LeetCode |
| Greedy | 423 | LeetCode |
| Hamiltonian Path | 2 | LeetCode |
| Hash Function | 37 | LeetCode |
| Hash Table | 736 | LeetCode |
| Heap (Priority Queue) | 201 | LeetCode |
| Heuristic Search | 5 | LeetCode |
| Hungarian Algorithm | 4 | LeetCode |
| Impartial Game | 4 | LeetCode |
| Inclusion-Exclusion Principle | 3 | LeetCode |
| Introductory Problems | 24 | CSES |
| Iterator | 9 | LeetCode |
| K Shortest Path | 1 | LeetCode |
| K-D Tree | 1 | LeetCode |
| Knapsack Problem | 15 | LeetCode |
| Knuth–Morris–Pratt Algorithm | 10 | LeetCode |
| Kosaraju's Algorithm | 5 | LeetCode |
| Kruskal's Algorithm | 3 | LeetCode |
| Least Common Multiple | 6 | LeetCode |
| Lexicographically Minimal String Rotation | 1 | LeetCode |
| Linear Algebra | 3 | LeetCode |
| Linked List | 75 | LeetCode |
| Longest Common Subsequence | 6 | LeetCode |
| Longest Increasing Subsequence | 10 | LeetCode |
| Lowest Common Ancestor | 11 | LeetCode |
| Lyndon Factorization | 1 | LeetCode |
| MPM Algorithm | 3 | LeetCode |
| Manacher | 2 | LeetCode |
| Matching (Graph) | 6 | LeetCode |
| Math | 585 | LeetCode |
| Mathematics | 37 | CSES |
| Matrix | 251 | LeetCode |
| Maximum Flow | 2 | LeetCode |
| Maximum Matching | 2 | LeetCode |
| Meet in the Middle | 4 | LeetCode |
| Memoization | 40 | LeetCode |
| Merge Sort | 13 | LeetCode |
| Minimax | 14 | LeetCode |
| Minimum Cut | 1 | LeetCode |
| Minimum Enclosing Circle | 1 | LeetCode |
| Minimum Spanning Tree | 6 | LeetCode |
| Minimum-Cost Flow | 3 | LeetCode |
| Mixed Knapsack | 1 | LeetCode |
| Monotonic Queue | 18 | LeetCode |
| Monotonic Stack | 69 | LeetCode |
| Multiple Knapsack | 1 | LeetCode |
| Newton's Method | 1 | LeetCode |
| Nim Game | 3 | LeetCode |
| Number Theory | 79 | LeetCode |
| Ordered Set | 69 | LeetCode |
| Perfect Matching | 2 | LeetCode |
| Persistent Data Structure | 1 | LeetCode |
| Pigeonhole Principle | 5 | LeetCode |
| Planar Graph | 1 | LeetCode |
| Polygons | 7 | LeetCode |
| Prefix Sum | 224 | LeetCode |
| Prim's Algorithm | 3 | LeetCode |
| Primality Test | 8 | LeetCode |
| Prime Factorization | 12 | LeetCode |
| Prime Number Sieve | 6 | LeetCode |
| Probability and Statistics | 6 | LeetCode |
| Push-Relabel Algorithm | 3 | LeetCode |
| Queue | 50 | LeetCode |
| Quickselect | 7 | LeetCode |
| Quicksort | 6 | LeetCode |
| Radix Sort | 3 | LeetCode |
| Randomized | 12 | LeetCode |
| Range Minimum/Maximum Query | 2 | LeetCode |
| Range Queries | 25 | CSES |
| Recursion | 47 | LeetCode |
| Rejection Sampling | 2 | LeetCode |
| Reservoir Sampling | 4 | LeetCode |
| Rolling Hash | 27 | LeetCode |
| Segment Tree | 70 | LeetCode |
| Semi-Eulerian Graph | 2 | LeetCode |
| Shortest Path | 34 | LeetCode |
| Sieve Theory | 9 | LeetCode |
| Simulation | 180 | LeetCode |
| Sliding Window | 146 | LeetCode |
| Sliding Window Problems | 11 | CSES |
| Sort | 2 | LeetCode |
| Sorting | 478 | LeetCode |
| Sorting and Searching | 35 | CSES |
| Sparse Table | 1 | LeetCode |
| Splay Tree | 1 | LeetCode |
| Sprague–Grundy Theorem | 3 | LeetCode |
| Sqrt Decomposition | 6 | LeetCode |
| Stack | 170 | LeetCode |
| String | 779 | LeetCode |
| String Algorithms | 21 | CSES |
| String Matching | 33 | LeetCode |
| Strongly Connected Component | 2 | LeetCode |
| Successive Shortest Path Algorithm | 5 | LeetCode |
| Suffix Array | 7 | LeetCode |
| Suffix Automaton | 4 | LeetCode |
| Suffix Tree | 4 | LeetCode |
| Sweep Line | 8 | LeetCode |
| Tarjan's SCC Algorithm | 5 | LeetCode |
| Ternary Search | 1 | LeetCode |
| Timsort | 1 | LeetCode |
| Topological Sort | 38 | LeetCode |
| Tournament Sort | 1 | LeetCode |
| Treap | 6 | LeetCode |
| Tree | 238 | LeetCode |
| Tree Algorithms | 16 | CSES |
| Triangulation | 1 | LeetCode |
| Trie | 56 | LeetCode |
| Two Pointers | 223 | LeetCode |
| Union-Find | 91 | LeetCode |
| Z Algorithm | 11 | LeetCode |
| Zero-Sum Game | 11 | LeetCode |
| binary search | 1269 | Codeforces |
| bitmasks | 707 | Codeforces |
| brute force | 1962 | Codeforces |
| chinese remainder theorem | 26 | Codeforces |
| combinatorics | 830 | Codeforces |
| communication | 5 | Codeforces |
| constructive algorithms | 2083 | Codeforces |
| data structures | 2005 | Codeforces |
| dfs and similar | 1055 | Codeforces |
| divide and conquer | 357 | Codeforces |
| dp | 2483 | Codeforces |
| dsu | 412 | Codeforces |
| expression parsing | 29 | Codeforces |
| fft | 113 | Codeforces |
| flows | 143 | Codeforces |
| games | 268 | Codeforces |
| geometry | 356 | Codeforces |
| graph matchings | 94 | Codeforces |
| graphs | 1190 | Codeforces |
| greedy | 3512 | Codeforces |
| hashing | 236 | Codeforces |
| implementation | 2937 | Codeforces |
| interactive | 265 | Codeforces |
| math | 3443 | Codeforces |
| matrices | 135 | Codeforces |
| meet-in-the-middle | 49 | Codeforces |
| number theory | 888 | Codeforces |
| probabilities | 265 | Codeforces |
| schedules | 15 | Codeforces |
| shortest paths | 290 | Codeforces |
| sortings | 1231 | Codeforces |
| string suffix structures | 100 | Codeforces |
| strings | 794 | Codeforces |
| ternary search | 67 | Codeforces |
| trees | 960 | Codeforces |
| two pointers | 652 | Codeforces |

### Reference implementations and handbook

| Implementation language | Linked files | Stored code bodies in this index |
| --- | --- | --- |
| python | 212 | 0 |
| java | 187 | 0 |
| cpp | 139 | 0 |

The handbook is [Competitive Programmer's Handbook](<https://cses.fi/book/book.pdf>) by Antti Laaksonen. It has 47 mapped chapter/page references across 39 concepts. Its manifest says `CC BY-NC-SA 4.0 (linked, not reproduced)`. PDF bytes and chapter prose are not stored in the active content tree. The inventory preserves printed page and PDF page offset (10); it does not claim the PDF version/page numbers were reverified online.

## 7. Teaching atoms, language coverage and content depth

Controlled misconception IDs: `syntax-delimiters`; `programs-and-output-repair`; `variables-and-types-repair`; `input-and-arithmetic-repair`; `conditionals-repair`; `boolean-logic-repair`; `while-loops-repair`; `for-loops-repair`; `nested-loops-repair`; `lists-repair`; `strings-repair`; `complexity-repair`; `arrays-hashing-repair`; `prefix-sums-repair`; `two-pointers-repair`; `sliding-window-repair`; `stacks-repair`; `binary-search-repair`; `sorting-repair`; `intervals-repair`; `greedy-repair`; `fast-io-repair`; `simulation-repair`; `complete-search-repair`; `number-theory-repair`; `modular-arithmetic-repair`; `combinatorics-repair`; `prefix-difference-repair`; `binary-search-answer-repair`; `greedy-cp-repair`; `bitmasks-repair`; `window-off-by-one`; `stop-after-first`; `confuse-index-value`; `lower-vs-upper-bound`; `half-open-bound`; `exclude-candidate-mid`; `lo-hi-confusion`; `off-by-one-output`; `overwrite-not-accumulate`; `count-not-sum`; `bound-instead-of-variable`; `product-not-sum`; `accumulator-init-one`; `accumulator-starts-at-first`; `accumulator-starts-at-bound`; `loop-bound-off-by-one`; `trace-step-slip`; `shrink-with-if`; `window-length-off-by-one`; `stale-window-summary`; `window-sum-not-length`; `window-rule-boundary`; `drop-wrong-end`; `reset-instead-of-shrink`; `overwrite-best`; `skip-first-element`; `window-with-negatives`; `pattern-fixed-vs-variable-window`; `pattern-window-vs-prefix-sums`; `pattern-window-vs-two-pointers`; `pattern-window-for-single-item`; `pattern-brute-force-default`; `pattern-sort-breaks-order`; `pattern-search-vs-scan`; `stale-zero-count`; `k-distinct-boundary`; `exactly-vs-at-most`; `distinct-count-not-length`; `shrink-too-far`; `predicate-boundary`; `predicate-inverted`; `predicate-wrong-variable`; `predicate-not-monotone`; `predicate-average-shortcut`; `answer-max-not-min`; `ceil-vs-floor`; `rate-inverted`; `search-range-confusion`; `pattern-search-needs-sorted-input`; `greedy-coin-change`; `count-vs-min`; `dp-missing-plus-one`; `dp-wrong-subproblem`; `count-vs-sum`; `coin-equals-amount`; `dp-overwrite-min`; `min-vs-max`; `missing-unreachable-check`; `dp-vague-state`; `dp-loop-order`; `unbounded-vs-01`; `top-k-direction`; `top-k-returns-max`; `heap-size-off-by-one`; `heap-negation-confusion`; `heap-size-vs-input-size`; `top-k-distinct-confusion`; `filter-boundary`; `filter-ignored`; `filter-inverted`; `filter-wrong-test`; `reset-inside-loop`; `filter-empty-crash`; `filter-running-average`; `distinct-vs-frequency`; `count-all-not-each`; `first-char-only`; `frequency-single-bucket`; `double-count`; `case-insensitive-assumption`; `tie-break-ignored`; `order-matters-assumption`; `frequency-max-only`; `missing-prefix-sum`; `diff-end-off-by-one`; `diff-sign-error`; `diff-missing-end`; `diff-wrong-endpoint`; `diff-online-queries`; `power-as-multiply`; `fast-power-step`; `mod-wrong-modulus`; `fast-power-parity`; `fast-power-wrong-variable`; `fast-power-base-not-square`; `sum-not-product`; `square-vs-double`; `product-init-zero`; `mod-only-at-end`; `power-as-repeat`; `mod-division`; `exact-vs-at-least`; `subset-count-off-by-one`; `subsets-vs-elements`; `skip-empty-subset`; `bit-test-wrong`; `bit-test-missing-and`; `missing-reset`; `subsets-linear`; `greedy-partition`; `dp-recompute-subproblems`; `dp-memo-not-stored`; `dp-wrong-base-case`; `dp-no-overlap`; `dp-greedy-local-choice`; `dp-compressed-loses-path`; `dp-reconstruct-forward`; `dp-count-vs-exists`; `dp-rolling-update-order`; `sum-instead-of-term`; `pattern-ordered-vs-unordered-ways`; `pattern-dp-vs-greedy`; `pattern-value-vs-choice`; `knapsack-forward-capacity-loop`; `knapsack-greedy-ratio`; `knapsack-capacity-boundary`; `knapsack-weight-for-value`; `knapsack-always-take`; `knapsack-ignore-capacity`; `knapsack-single-item`; `knapsack-zero-skipped`; `subset-sum-empty-base`; `partition-odd-total`; `partition-half-not-difference`; `count-target-transform`; `two-capacity-one-loop`; `pattern-01-vs-unbounded-knapsack`; `pattern-subset-vs-subarray`; `pattern-partition-greedy-vs-dp`; `pattern-count-vs-exists`; `pattern-two-budgets-vs-two-bags`; `unbounded-advance-after-take`; `exact-capacity-zero-init`; `coin-min-zero-init`; `pattern-exact-vs-at-most-capacity`; `lcs-greedy-match`; `lcs-mismatch-diagonal`; `lcs-index-offset`; `scs-forget-lcs`; `lps-fill-order`; `pattern-subsequence-vs-substring`; `pattern-two-pointers-vs-lcs`; `pattern-palindrome-subsequence-vs-substring`; `edit-base-zero`; `edit-missing-replace`; `edit-match-costs-one`; `edit-position-compare`; `distinct-subseq-forward-loop`; `wildcard-star-one-char`; `interleave-length-check`; `palindrome-odd-centres-only`; `pattern-edit-vs-lcs-deletions`; `pattern-wildcard-vs-regex-star`; `stock-greedy-runs`; `stock-sell-before-buy`; `stock-unlimited-when-limited`; `stock-buy-wrong-count`; `stock-sell-sign`; `stock-hold-init-zero`; `stock-cooldown-yesterday`; `stock-fee-twice`; `pattern-stock-unlimited-vs-limited`; `lis-greedy-extend`; `lis-answer-last-cell`; `lis-non-strict-compare`; `lis-compare-direction`; `lis-tails-is-sequence`; `lis-upper-vs-lower`; `lis-envelope-tie-order`; `pattern-strict-vs-nondecreasing-lis`; `pattern-sort-then-lis`; `mcm-length-order`; `mcm-cost-index`; `mcm-greedy-order`; `cut-unsorted-positions`; `burst-first-not-last`; `boolean-true-only`; `front-greedy-longest`; `pattern-interval-vs-front-partition`; `bitmask-greedy-assign`; `bitmask-check-bit`; `bitmask-worker-index`; `game-greedy-end`; `game-own-score-only`; `state-forgets-rule`; `digit-ignore-tight`; `pattern-bitmask-vs-knapsack`; `pattern-game-greedy-vs-minimax`; `pattern-state-remembers-rules`; `pattern-digit-dp-vs-brute-force`; `mono-max-to-the-right`; `mono-strictness`; `mono-wrong-direction`; `mono-neighbour-only`; `mono-top-vs-bottom`; `mono-answer-wrong-element`; `mono-stores-value-not-index`; `histogram-tallest-only`; `histogram-width-off-by-one`; `histogram-no-sentinel`; `contribution-tie-rule`; `deque-no-expiry`; `pattern-next-greater-vs-max-right`; `pattern-stack-vs-deque`; `tree-return-both-branches`; `tree-negative-branch`; `tree-best-only-downward`; `tree-sum-all`; `tree-only-downward-search`; `tree-view-right-children-only`; `tree-one-child-is-leaf`; `tree-pass-down-vs-return-up`; `lca-not-self`; `lca-lift-before-equal`; `bfs-no-visited`; `tree-width-counts-nodes`; `tree-width-overflow`; `pattern-return-vs-record`; `sq-missing-diagonal`; `sq-side-not-area`; `sq-one-row-left-stale`; `sq-zero-cell-kept`; `histogram-no-reset`; `pattern-square-vs-rectangle`; `rob-alternate-levels`; `rob-take-adds-take`; `rob-skip-forces-take`; `rob-answer-take-only`; `path-skip-blocked-subtree`; `cover-two-states-only`; `cover-leaves-greedy`; `cover-root-uncovered`; `pattern-one-answer-vs-states`; `prefix-store-last-index`; `prefix-missing-empty`; `prefix-seed-index-zero`; `prefix-count-vs-longest`; `pattern-first-vs-last-index`; `hash-insert-before-lookup`; `hash-key-collision`; `set-walk-every-element`; `split-average-greedy`; `split-lower-bound-answer`; `maxmin-round-down`; `kth-half-each`; `pattern-first-vs-last-true`; `pnp-stop-at-target`; `pnp-base-ignores-target`; `pnp-take-without-element`; `pnp-forget-skip`; `gen-close-limit-n`; `stack-push-back-on-top`; `josephus-no-shift`; `power-half-twice`; `pattern-filter-vs-valid-prefix`; `lru-fifo-not-lru`; `lru-get-no-refresh`; `lru-evict-most-recent`; `lru-capacity-off-by-one`; `lru-evict-on-update`; `pattern-queue-vs-linked-list`; `design-shift-delete`; `design-stale-index`; `design-latest-only`; `iterator-no-skip`; `mod-chain-missing`; `mod-swap-div`; `mod-wrong-divisor`; `python-slash-decimal`; `precedence-left-to-right`; `compound-eq-plus`; `short-circuit-order`; `ceil-plus-one`; `float-sqrt-trust`; `pattern-divide-vs-remainder`; `div-square-twice`; `div-sqrt-bound-strict`; `div-no-partner`; `div-forget-self`; `pattern-root-vs-all`; `mod-operands-swapped`; `digit-count-vs-value`; `digit-loop-stops-early`; `infinite-loop-condition`; `digit-reverse-order`; `digit-fixed-power`; `prime-one-is-prime`; `gcd-vs-lcm`; `seq-update-one-at-a-time`; `sort-pass-equals-sorted`; `sort-wrong-direction`; `sort-inner-bound-short`; `sort-overwrite-not-swap`; `sort-confuse-algorithms`; `search-decide-too-early`; `sort-tie-left-to-chance`; `pattern-bubble-selection-insertion`.

| Atom kind | Instances |
| --- | --- |
| micro | 60 |
| hook | 30 |
| concept | 30 |
| worked | 30 |
| faded | 30 |
| visualizer | 30 |
| pattern | 30 |
| explanation | 30 |
| trace | 3 |
| predict | 3 |
| debug | 3 |

The 279 atom instances have 127 distinct normalized body strings. Shared/template bodies and the same explanation reused as concept/worked content account for part of the difference. This is a literal text-identity measurement, not an automatic judgment of pedagogical redundancy. There are 107 authored interactive checks and 201 language adapter records.

| Course | Released packs | Topics without packs | Atoms | Atom adapters P/C/J | Concept quizzes mcq/output/bug | Native easy/medium/hard |
| --- | --- | --- | --- | --- | --- | --- |
| Programming from Zero | 10 | 11 | 93 | 23/23/23 | 91/34/1 | 32/13/0 |
| DSA for Interviews | 10 | 30 | 93 | 22/22/22 | 240/8/2 | 12/63/4 |
| Competitive Programming | 10 | 10 | 93 | 22/22/22 | 79/0/0 | 6/17/5 |

**No teaching-atom pack yet (standard lessons/quizzes still exist):**

- **Programming from Zero:** Classes and objects (`zero:classes-and-objects`); Debugging calmly (`zero:debugging`); Functions (`zero:functions`); Grids and 2D lists (`zero:grids`); Dictionaries and maps (`zero:maps`); Math on numbers (`zero:math-on-numbers`); Operators and expressions (`zero:operators-and-expressions`); Solving unfamiliar problems (`zero:problem-solving`); Recursion (`zero:recursion`); Scope, references and mutation (`zero:scope-and-mutation`); Searching and sorting basics (`zero:searching-and-sorting`)
- **DSA for Interviews:** Backtracking (`dsa:backtracking`); Binary search on the answer (`dsa:binary-search-on-answer`); Binary trees (`dsa:binary-trees`); Bit manipulation (`dsa:bit-manipulation`); Binary search trees (`dsa:bst`); Designing data structures (`dsa:design-data-structures`); Dynamic programming (1D) (`dsa:dp-1d`); Dynamic programming (2D) (`dsa:dp-2d`); More interview DP patterns (`dsa:dp-advanced-patterns`); Strings DP: edits and matching (`dsa:dp-edit-distance`); Dynamic programming: the idea (`dsa:dp-introduction`); Strings DP: the LCS family (`dsa:dp-lcs`); Longest increasing subsequence family (`dsa:dp-lis`); DP on trees (`dsa:dp-on-trees`); Partition DP (matrix chain) (`dsa:dp-partition`); DP on squares and rectangles (`dsa:dp-squares`); Stock trading DP (`dsa:dp-stocks`); Graphs, BFS and DFS (`dsa:graph-traversal`); Hashing patterns (`dsa:hashing`); Heaps and priority queues (`dsa:heaps`); 0/1 knapsack family (`dsa:knapsack-01`); Unbounded knapsack family (`dsa:knapsack-unbounded`); Linked lists (`dsa:linked-lists`); Monotonic stack and deque (`dsa:monotonic-stack`); Recursion patterns (`dsa:recursion-patterns`); Weighted shortest paths (`dsa:shortest-paths`); Topological sort (`dsa:topological-sort`); Binary tree patterns (`dsa:tree-patterns`); Tries (prefix trees) (`dsa:tries`); Union-Find (Disjoint Set Union) (`dsa:union-find`)
- **Competitive Programming:** Bitmask DP (`cp:bitmask-dp`); Classic contest DPs (`cp:dp-classics`); Fenwick tree (Binary Indexed Tree) (`cp:fenwick-tree`); Graph techniques for contests (`cp:graph-techniques`); Prefix function and KMP (`cp:kmp`); Lowest common ancestor and binary lifting (`cp:lca`); Minimum spanning trees (`cp:mst`); Segment trees (`cp:segment-tree`); String hashing (`cp:string-hashing`); Tree techniques (`cp:tree-techniques`)

### Language-specific access

| Course | Resources available Python/C++/Java | Lessons containing Python/C++/Java code fences | Quiz code records Python/C++/Java |
| --- | --- | --- | --- |
| Programming from Zero | 49/47/44 | 20/19/19 | 34/18/18 |
| DSA for Interviews | 135/134/134 | 40/40/40 | 11/9/9 |
| Competitive Programming | 61/61/61 | 20/20/20 | 0/0/0 |

Language-neutral resource and atom records can serve multiple language choices. Code-fence counts indicate literal examples present, not proof of compiled/correct translations. No stored course-owned PDF, notebook, audio or instructional video file was found in `content/`; videos, books and visualizers in resources are links. Tracked archived demo `.webm` files are product walkthroughs, not course lessons. Learner-requested AI explainers and lesson variants are runtime features; their private/generated database outputs were not queried or counted as an authored corpus.

## 8. Gaps and limits relevant to the next content instruction

| Concept | Native problems | External primary | External all matches | Atoms |
| --- | --- | --- | --- | --- |
| zero:classes-and-objects | 1 | 0 | 0 | 0 |
| zero:debugging | 1 | 0 | 0 | 0 |
| zero:functions | 2 | 0 | 0 | 0 |
| zero:grids | 2 | 24 | 206 | 0 |
| zero:maps | 3 | 0 | 0 | 0 |
| zero:math-on-numbers | 2 | 0 | 0 | 0 |
| zero:operators-and-expressions | 2 | 0 | 0 | 0 |
| zero:problem-solving | 1 | 0 | 0 | 0 |
| zero:recursion | 2 | 8 | 44 | 0 |
| zero:scope-and-mutation | 0 | 0 | 0 | 0 |
| zero:searching-and-sorting | 2 | 0 | 0 | 0 |
| dsa:backtracking | 2 | 81 | 107 | 0 |
| dsa:binary-search-on-answer | 2 | 0 | 0 | 0 |
| dsa:binary-trees | 2 | 166 | 236 | 0 |
| dsa:bit-manipulation | 1 | 90 | 206 | 0 |
| dsa:bst | 1 | 39 | 40 | 0 |
| dsa:design-data-structures | 2 | 0 | 0 | 0 |
| dsa:dp-1d | 2 | 358 | 547 | 0 |
| dsa:dp-2d | 2 | 90 | 136 | 0 |
| dsa:dp-advanced-patterns | 2 | 0 | 0 | 0 |
| dsa:dp-edit-distance | 2 | 0 | 0 | 0 |
| dsa:dp-introduction | 2 | 0 | 0 | 0 |
| dsa:dp-lcs | 2 | 0 | 0 | 0 |
| dsa:dp-lis | 2 | 0 | 0 | 0 |
| dsa:dp-on-trees | 2 | 0 | 0 | 0 |
| dsa:dp-partition | 2 | 0 | 0 | 0 |
| dsa:dp-squares | 2 | 0 | 0 | 0 |
| dsa:dp-stocks | 2 | 0 | 0 | 0 |
| dsa:graph-traversal | 2 | 367 | 1384 | 0 |
| dsa:hashing | 2 | 0 | 0 | 0 |
| dsa:heaps | 1 | 155 | 201 | 0 |
| dsa:intervals | 1 | 19 | 19 | 9 |
| dsa:knapsack-01 | 2 | 0 | 0 | 0 |
| dsa:knapsack-unbounded | 2 | 0 | 0 | 0 |
| dsa:linked-lists | 1 | 49 | 75 | 0 |
| dsa:monotonic-stack | 2 | 0 | 0 | 0 |
| dsa:recursion-patterns | 2 | 0 | 0 | 0 |
| dsa:shortest-paths | 1 | 327 | 331 | 0 |
| dsa:topological-sort | 1 | 42 | 42 | 0 |
| dsa:tree-patterns | 2 | 0 | 0 | 0 |
| dsa:tries | 1 | 56 | 56 | 0 |
| dsa:union-find | 1 | 402 | 492 | 0 |
| cp:binary-search-answer | 1 | 699 | 1243 | 9 |
| cp:bitmask-dp | 1 | 294 | 349 | 0 |
| cp:bitmasks | 1 | 349 | 423 | 9 |
| cp:dp-classics | 2 | 1095 | 2341 | 0 |
| cp:fenwick-tree | 1 | 9 | 41 | 0 |
| cp:graph-techniques | 1 | 239 | 936 | 0 |
| cp:greedy-cp | 1 | 1697 | 3977 | 9 |
| cp:kmp | 1 | 46 | 54 | 0 |
| cp:lca | 1 | 15 | 15 | 0 |
| cp:mst | 1 | 8 | 8 | 0 |
| cp:prefix-difference | 1 | 3 | 3 | 9 |
| cp:segment-tree | 1 | 505 | 1419 | 0 |
| cp:string-hashing | 1 | 263 | 328 | 0 |
| cp:tree-techniques | 2 | 797 | 976 | 0 |

Other observed limits:

- Only three course manifests exist. There is no active SQL, Git, web-development, data-science or general mathematics course. Contest math is a module of Competitive Programming. Foundry's synthetic SQL/Git test fixtures are not real published courses.
- Native practice coverage ranges from zero to two concept-linked problems. One topic has zero: zero:scope-and-mutation. 25 concepts have fewer than two. Large external pools do not fill a local unseen/controlled judge-bank requirement automatically.
- 51/81 concepts lack atom packs, including most later DSA/CP material. A stored lesson is not equivalent to a complete released sequence of worked/faded/visual/repair teaching atoms.
- 455 concept quizzes are reused by multiple activity types; there is no distinct authored bug-kind concept quiz (debug atoms are a separate category). No independent psychometric/difficulty calibration or learning-outcome evidence was audited.
- 150/152 native problems lack an explicit review block and lack authored brute/small-generator and C++/Java reference pairs. Current generated-cache validity does not prove all correctness/maximum-input/multi-language quality gates were run.
- 81 lesson files and their quiz items have no per-item source/license/reviewer fields. Resource publisher URLs identify recommended material, not the provenance of local explanation text.
- External sources are primarily recorded as links/metadata. No general indexed licensed article/book corpus is established by these catalog files. Provider robots/ToS/license validity, link health, video availability and mutable-source freshness remain unverified in this audit.
- External topic and implementation mappings are heuristic, not per-record instructional review. Company recency/frequency values are snapshot metadata. The full original Striver curriculum, complete Developer Roadmap prose, and book chapter bodies are not imported local courses.
- The historical launch backlog mentions a different-branch 5,779-record/429-company resource pool under contracts/resource-pool. That path is absent in this checkout; those historical counts are excluded rather than merged with the current bank.
- Counts in legacy product/release documents can differ from executable files. The inventory below is tied to this snapshot's content hashes and commit; it should be regenerated after any content changes.

## 9. Foundry status versus existing content

M0–M2 are implemented; M3 is a local incomplete checkpoint with live indexing disabled and no S4/S5 worker wiring. See [foundry backlog.md](<D:/Socrat/foundry backlog.md>). Automatic first-demand skill discovery/resolution is M4; graph induction/export is M5; review/gates/status/takedown is M6; calibration/report is M7. None of those planned features creates additional current course counts.

The default `.cache/foundry-snapshots` directory was absent at audit time. No live/deployed database, bucket, private `.env` or learner data was opened. Therefore production Foundry source/chunk/embedding/pack counts are **not established by this audit**; they must not be reported as either a verified usable corpus or a verified global zero. Test artifacts and temporary synthetic Foundry data are excluded.

## 10. Validation, reproducibility and inventory file map

Read-only checks passed: authoring schemas, global prerequisite DAG/references, atom-pack schemas/version linkage, runtime catalog loading from existing test caches, source-cache hashes for all 152 problems, external concept references and company problem IDs. The runtime load read 1778 cached tests. Reference programs, generators, importers, LLMs and source fetchers were not executed. No frontend files or learning content were edited; no push was performed.

Active `content/` scan: **512 files** (8,741,997 bytes). Composite SHA-256 of sorted path→file-hash mapping: `cb260b8e0488483a8c225d10fc7823bbedbbe7b54897307a19dff0afd626b3f3`. This fingerprint excludes generated caches, fixtures, code and this report. Word counts split on whitespace and include inline code/Markdown. Atom uniqueness collapses whitespace in `body` only. URL uniqueness uses exact stored/resolved URL strings, not semantic page equivalence.

| Inventory record type | CSV rows |
| --- | --- |
| course | 3 |
| module | 20 |
| lesson | 81 |
| lesson_section | 1240 |
| quiz | 455 |
| course_resource | 274 |
| practice_link | 310 |
| native_problem | 152 |
| teaching_atom | 279 |
| roadmap_link | 132 |
| python_exercise_link | 35 |
| book_chapter_link | 47 |
| implementation_link | 538 |
| external_problem | 13889 |
| company_index_metadata | 637 |

CSV fields include stable record ID, asset type, course/module/concept IDs, primary concept, title, source URL/name/file/revision, storage type, difficulty/languages, word count, recorded rights/review and additional metadata. Section rows reference the parent lesson; company rows are metadata. Source file SHA-256 ties each record to the audited source snapshot. Quiz entries name prompts and source files; no answer keys or hidden-test bodies were exported. Leading spreadsheet formula characters are apostrophe-escaped in CSV string cells; source files remain unchanged.

| Source file / directory | Purpose |
| --- | --- |
| [content/courses](<D:/Socrat/content/courses>) | Active course manifests, lessons, quizzes and native problems |
| [content/atoms](<D:/Socrat/content/atoms>) | Versioned teaching atoms and misconception taxonomy |
| [content/learning-resources.json](<D:/Socrat/content/learning-resources.json>) | Roadmap and Python exercise supplements |
| [content/practice/problems.jsonl](<D:/Socrat/content/practice/problems.jsonl>) | All 13,889 external problem records |
| [content/practice/companies.json](<D:/Socrat/content/practice/companies.json>) | All 637 company groups and associations |
| [content/practice/implementations.jsonl](<D:/Socrat/content/practice/implementations.jsonl>) | All 538 reference code links |
| [content/practice/book.json](<D:/Socrat/content/practice/book.json>) | Handbook metadata and chapter/page mappings |
| [content/practice/sources.json](<D:/Socrat/content/practice/sources.json>) | Import source revisions and policy declarations |
| [services/api/src/socrat/catalog/practice.py](<D:/Socrat/services/api/src/socrat/catalog/practice.py>) | Library loading and ranking/filtering |
| [services/api/src/socrat/learn/resources.py](<D:/Socrat/services/api/src/socrat/learn/resources.py>) | Language filtering and personalized resource ranking |
| [services/api/src/socrat/planner/sessions.py](<D:/Socrat/services/api/src/socrat/planner/sessions.py>) | Atom-based session composition |
| [services/api/src/socrat/assessments/service.py](<D:/Socrat/services/api/src/socrat/assessments/service.py>) | Assessment composition from existing quiz/problem pools |

### Snapshot history (Git commit metadata, not source-fetch timestamps)

- `content/courses`: c295242 \| 2026-10-24T16:33:05+05:30 \| content(zero): searching-and-sorting: linear and binary search, simple sorts, key sort
- `content/atoms`: c295242 \| 2026-10-24T16:33:05+05:30 \| content(zero): searching-and-sorting: linear and binary search, simple sorts, key sort
- `content/practice`: 82a2bd4 \| 2026-10-10T03:13:52+05:30 \| feat(v2): personalised practice library, Codeforces sync and tutor tools
- `content/learning-resources.json`: c295242 \| 2026-10-24T16:33:05+05:30 \| content(zero): searching-and-sorting: linear and binary search, simple sorts, key sort

## 11. Suggested structure for your next content instruction

Specify the course/module/concept IDs to change, desired learning outcomes and subtopics, target learner/language, how many local lessons/quiz items/native problems/atoms are wanted, which external links may be added, source/rights evidence, reviewer/quality requirements, and whether the change is a draft or a release. Keep local authored material, link-only metadata and Foundry-ingested licensed text as explicit separate quantities. This report sets the current baseline; it does not choose new quotas or authorize publishing.

Skipped: external link/license verification, deployed/private corpus inventory, code/compiler execution and pedagogical calibration. Recorded reviews/rights are declarations in the files; missing metadata and incomplete atom/native-bank coverage are documented above.
