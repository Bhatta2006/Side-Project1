# Full-course learner journeys — 23 Oct 2026

Follow-up to `learner-simulation-2026-10-23.md`. That audit walked onboarding and the first lesson. This one runs each persona **from sign-up until their plan is empty**. Audit only: no product code changed.

## How this was run

- A script drove the **real engine code** (`placement/engine.py`, `planner/engine.py`, `planner/gates.py`, `mastery/model.py`, `learn/quizzes.next_gate_item`) against the real `content/` catalog. Each simulated study day it rebuilt the plan, did that day's items in order, recorded evidence the way `learn/quizzes.finish` and `learn/routes.on_submission` do, and stopped once the queue and the locked modules were both empty.
- 14 personas: every self-report level in every course. Each was run with 5 random seeds; the tables give the median, with the range in brackets.
- **Learner model (an assumption, not data).** After a lesson, the chance of getting a question right is the persona's ability minus 7 points per difficulty step, plus up to 20 points from practice. A skill the persona already knows is about 90% right. A question written in another language is answered at 55% of the normal rate (85% for skills they already know). A judged problem is solved in 1 to 4 submits.
- **Best case for effort.** The learner studies every scheduled day and finishes every item. Real adherence will be lower.
- **Not simulated:** accepting test-out or stretch proposals (these only appear after 3 strong results in a row, one topic at a time), the tutor, weekly assessments, the Practice page (external problems), missed days. Java can't run code locally (D-7), so the Java persona's judged problems are simulated as if they could be submitted.

---

## What every learner goes through (the loop)

1. **Onboarding:** course → level → language → schedule → goal.
2. **Placement.** A beginner gets 0 questions. Every other level gets 4–8 multiple-choice questions that binary-search the prerequisite chain. Since the C-1 fix, a topic **inside the enrolled course** is skipped only if it was asked about and answered correctly. Topics from other courses (Zero and DSA prerequisites) can be inferred as known.
3. **Per topic**, in this order:
   - lesson (about 30% of the topic's estimated time)
   - a 5-question concept check (the **5 easiest** items for your language)
   - 1–4 judged coding problems
   
   The check is marked done whatever the score. A problem is done only when accepted.
4. **Module checkpoint**, after a module's last topic. It's an adaptive staircase of up to 10 questions. To pass you need a difficulty-weighted score of 80% or more, **2 correct at the module's hardest level**, and fewer than 3 misses. A failed attempt locks the checkpoint for 24 hours and adds 2 reviews. Passing it unlocks the next module.
5. **Spaced reviews:** 3 questions, 5 minutes, at most 2 per day, at 1/3/7/14/30/60-day spacing.
6. **The end:** the plan empties. **There is no finish moment.** Today says "Everything planned for today is complete" (`apps/web/src/app/today/page.tsx:256`). No certificate or "course complete" screen exists; the Skill Passport is the only artifact.

---

## Results by persona

"Plan says" is what the learner sees on day 1. "Simulated" is what it actually took. Topics are the lessons they ended up doing; Problems are judged problems accepted.

### Programming from Zero (18 topics, 39 judged problems)

| Persona | Placement | Day-1 plan says | Simulated | Topics / Problems | Checkpoint fails | Skills "strong" at the end |
|---|---|---|---|---|---|---|
| **Z1 Priya**, never coded, Python, 30 min × 5 | none, starts at Programs & output | 16 h, done 9 Dec | **15 wk (13–17), 34 h** | 18 / 39 | 20 (12–30) | 0 / 18 |
| **Z3 Meera**, never coded, weekends 1 h × 2 | none | 16 h, done 25 Dec | 14 wk (13–22), 22 h | 18 / 39 | 5 | 1 / 18 |
| **Z4 Aditya**, never coded, **C++**, 20 min daily | none | 16 h, done 12 Dec | **does not finish in 2.5 years** in 3 of 5 runs; 78+ wk otherwise | 18 / 39 | 74 (40–247) | 5 / 18 |
| **Z2 Rahul**, tried a tutorial, Python | 5 Qs → **starts at Programs & output** | 16 h | 9 wk (8–11), 24 h | 18 / 39 | 9 | 2 / 18 |
| **Z5**, writes small programs, Python | 6 Qs → **starts at Programs & output** | 16 h | 6 wk, 21 h | 18 / 38 | 4 | 0 / 18 |
| **Z6**, comfortable with basics, Python | 5 Qs → **starts at Programs & output** | 16 h | 6 wk, 21 h | 17 / 36 | 3 | 1 / 18 |

**What they see:**
- **Priya (Z1):** Day 1 is Programs & output: lesson, a 5-question check and "Echo a reading". Every topic follows the same lesson → check → 2–3 problems loop. She reaches the *First steps* checkpoint around week 2. In the simulation she failed module checkpoints about 4 times each (most at *Making decisions and repeating*). Each fail means a day's lock and two reviews. She finishes in about 15 weeks against the 7 weeks promised, and her skill map shows almost nothing "strong" when the plan empties.
- **Aditya (Z4, C++):** He gets the same loop, but checkpoints draw from **every** item in the module, not only C++ ones. At *First steps* the hardest-level items are **100% Python code** (`print-order`, `rebinding`, `negative-mod`), and he must get 2 of them right. *Collections* failed 91 times in one run. This is a wall, not friction.
- **Z2, Z5 and Z6** all start at lesson 1. Self-reporting "comfortable" changes where placement probes, but not where they start. They redo 17–18 of 18 lessons. They finish fastest, mostly bored.

### DSA for Interviews (23 own topics + up to 16 Zero bridge topics, 45 judged problems)

| Persona | Placement | Day-1 plan says | Simulated | Topics (own + bridge) / Problems | Checkpoint fails | Skills "strong" at the end |
|---|---|---|---|---|---|---|
| **D0**, new to programming, Python, 1 h × 5 | none, all 16 Zero bridges | 40 h, done 22 Dec | 16 wk (13–18), 68 h | 23 + 16 / 82 | 55 (24–88) | 0 / 23 |
| **D1 Sneha**, knows basics, Python, 6-week deadline | 6 Qs, 12 assumed, starts at **Recursion** | 27 h, done 4 Dec | **12 wk (11–14), 52 h** | 23 + 15 / 78 | 10 | 0 / 23 |
| **D3 Vikram**, some DSA, **Java**, 45 min × 5 | 5 Qs, 19 assumed, starts at **Complexity** | 25 h | 14 wk, 52 h (*assumes Java runs*) | 23 + 15 / 75 | 9 | 1 / 23 |
| **D2 Arjun**, lots of practice, Python, 2 weeks to interview | 4 Qs, 16 assumed, starts at **Complexity** | 25 h, done 1 Dec | **10 wk, 47 h** | 22 + 14 / 74 | 3 | 1 / 23 |

**What they see:**
- **Sneha (D1)** starts with Recursion and then works through the whole DSA path in order. She gets the feasibility nudge ("6 weeks is not enough"), which is honest, but the realistic time is about 12 weeks at 1 h a day. About 15 of her "known" Zero topics come back as full lessons (see N3).
- **Arjun (D2)** placed well on bridge topics, but his own course topics weren't asked, so he does Big-O, Arrays & hashing, Prefix sums, Two pointers and so on, all from scratch. Test-out offers only appear after 3 straight strong results, and then for one topic at a time. That's 10 weeks against a 2-week deadline. The product doesn't serve this persona.
- **Vikram (D3, Java):** In production his judged problems can't be submitted (D-7), so problems never complete and the plan **never empties**. His checkpoints also include C++/Python-specific items (25 asked across the run).

### Competitive Programming (20 own topics + up to 34 Zero/DSA bridges, 28 judged problems)

| Persona | Placement | Day-1 plan says | Simulated | Topics (own + bridge) / Problems | Checkpoint fails | Skills "strong" at the end |
|---|---|---|---|---|---|---|
| **C0**, new to programming, **C++** | none, 34 bridges | 57 h, done 14 Jan | **does not finish** in 4 of 5 runs (45+ wk otherwise) | 20 + 34 / 100 | 923 | 2 / 20 |
| **C1 Rohan**, DSA basics, Python, 1 h × 5 | 8 Qs, 16 assumed, starts at **Number theory** | 34 h, done 14 Dec | 16 wk (15–16), 75 h | 20 + 34 / 98 | 25 | 1 / 20 |
| **C2 Ishaan**, pupil, C++, 1.5 h × 5 | 7 Qs, 29 assumed, starts at **Fast I/O** | 24 h, done 18 Nov | 9 wk, 67 h | 20 + 34 / 98 | 21 | 0 / 20 |
| **C3 Kiran**, specialist, C++, 1.5 h × 5 | 6 Qs, 35 assumed, starts at **Fast I/O** | 22 h, done 16 Nov | 9 wk, 60 h | 19 + 33 / 95 | 12 | 2 / 20 |

**What Kiran (C3) actually did,** from the trace, one line per study day:

| Day | Items |
|---|---|
| 1 | Fast I/O lesson, check, 2 problems, then Simulation lesson |
| 2 | 2 reviews, Complete search, **CP checkpoint 1** |
| 3 | Shortest paths (a DSA bridge he didn't know, which is fine) |
| 4 | Number theory, Modular arithmetic |
| 5 | **Arrays & hashing lesson**, check and 3 problems |
| 7 | **Bit manipulation lesson**, **DSA "Dynamic programming" checkpoint** |
| 10 | **Intervals lesson** |
| 11 | **Backtracking lesson** |
| 12 | **1-D DP lesson**, **Sorting lesson** |

A Codeforces specialist is taken back through 33 bridge lessons from Zero and DSA. He also failed the Zero *First steps* checkpoint 10 times, because its hardest questions are Python.

---

## New findings (not in the first audit)

**N1. Checkpoints ignore the learner's language** — **Blocker** for every C++/Java learner who passes through Zero (Z4, C0, and bridge checkpoints for C2/C3)
- `gate_pool` (`services/api/src/socrat/learn/quizzes.py:51`) uses `catalog.concept(c).quiz` unfiltered, while checks, reviews and test-outs use `fitting()`.
- Zero *First steps*: the hardest-level items are 3/3 Python-only. *Making decisions…*: 3/5. *Working with data*: 2/4.
- Monte Carlo of the real staircase for a learner at 85% per-item accuracy: First steps passes **72% in Python vs 10% in C++**, and Making decisions… **63% vs 9%**.
- *Fix:* filter `gate_pool` with `q.fits(enrollment.language)` and take `levels` and `hard_available` from the filtered pool. It's one line plus the callers at lines 94, 158 and 275.

**N2. Placement now skips almost nothing inside the chosen course** — **High** (an over-correction of C-1)
- `placement.engine.result` only skips own-course topics that were directly asked about and answered correctly. With 4–8 questions, that's 1–3 topics.
- "Comfortable" Zero learners start at lesson 1. Arjun ("lots of practice") does 22 of 23 DSA topics including Big-O. Kiran (specialist) starts CP at Fast I/O.
- *Fix:* keep "own topics need evidence", but turn the gap into a visible, one-tap **module test-out** right after placement ("You placed past *Linear patterns*. Prove it in 10 questions and skip the module"), rather than waiting for 3 strong results.

**N3. Skills placed as "known" get re-taught from scratch** — **High** · every non-beginner persona
- Placement gives a known skill α=4.2/β=1. That isn't "mastered" (confidence 0.47 < 0.55); it only survives as `assumed` until its first review. Verified with `mastery.model`:
  - One **2/3** review drops `assumed` (mean 0.78), and the planner schedules the full lesson, check and problems again.
  - A **perfect** review that then goes 7 days overdue falls below 0.8 by day 12 and gets re-scheduled.
- Reviews are capped at 2 a day (`MAX_REVIEWS_PER_DAY`), while advanced learners carry 16–35 assumed skills that all come due on day 2. The backlog guarantees they go overdue.
- Result: 14–34 re-taught bridge lessons per non-beginner. This is the main reason Arjun takes 10 weeks and Kiran 9.
- The planner also queues **bridge-module checkpoints** (for example Zero *First steps* for a CP specialist) once any assumed member loses that flag (`planner/engine.py`, `last_of_module` block).
- *Fix:* a failed review of an assumed skill should schedule a short refresher or another review, not the whole topic. Give assumed skills a higher review cap, or batch them into one "confirm what you know" quiz. Don't queue checkpoints for modules outside the enrolled course.

**N4. Checkpoints are steep, and small pools repeat** — **High** for anxious beginners
- In practice, passing needs about 80% accuracy on the module's hardest questions. At a flat 75% accuracy, the pass rate is 30–48% per try.
- Simulated Priya failed about 20 times across 5 checkpoints, each followed by a 24-hour lock. That's the exact "I feel stupid" trigger for Z1.
- The pools are small: CP *Range structures* 6 items, *Strings* 6, *DP* 7, DSA *Linked structures* 8 (with 1 item at the hardest level). Every retry shows the same questions, and the concept check already showed 5 of them. Passing turns into remembering answers.
- *Fix:* for Zero, lower the bar (for example 70% weighted and 1 hard item), and say "unlocks tomorrow" kindly. Add items to modules under 15, or use `content/quiz/generators` for parametric variants.

**N5. The day-1 forecast is about half the real time** — **Medium** · everyone
- The plan's estimate counts lesson, check, problem and one checkpoint, but not reviews, checkpoint retries or failed submits. For example, Priya is told 16 h and done 9 Dec; the simulation took 34 h and finished in early February. Sneha is told 27 h; it took 52 h.
- *Fix:* add an allowance for reviews and retries (about ×1.8 for beginners), or show a range.

**N6. No finish line, and the skill map disagrees** — **Medium**
- When the plan empties, the course-skill map showed **0–2 skills "strong"** in every persona: "strong" needs spaced-review evidence, and reviews are still backlogged.
- The learner "finishes" the course while their map mostly says "developing", and nothing marks the end.
- *Fix:* a completion screen (what you can now do, problems solved, Passport link, a "next course" offer). Either a "completed — keep it fresh" state, or a final review sprint before you call it done.

---

## How much content each path actually delivers

| Course | Topics | Lesson text | Check questions | Judged problems | Topics with ≤1 judged problem | Mapped external problems |
|---|---|---|---|---|---|---|
| Zero | 18 | ~11.9k words (~12.5 h estimated) | 98 (4–7 per topic) | 39 | 4: scope (**0**), debugging, problem-solving, classes | Only 4 of 18 topics have any (1.5k on Codeforces/LeetCode) |
| DSA | 23 | ~14.1k words (~21 h) | 107 (4–7 per topic) | 45 | **9**: intervals, linked lists, BST, heaps, tries, topological sort, union-find, shortest paths, bits | ~9.9k (6k LeetCode); thin on intervals (19), BST (40), topological sort (42) |
| CP | 20 | ~11.7k words (~17 h) | 79 (**3** for 11 topics) | 28 | **12** of 20 | ~20k (mostly Codeforces); modular arithmetic **2**, prefix/difference 3, MST 8, LCA 15 |

For comparison: a typical intro-programming course has hundreds of small exercises. NeetCode 150 is 150 interview problems. CSES alone has 300.

### What each persona ends up learning, and is it enough for a beta?

| Persona | What they come away with | Enough for beta? |
|---|---|---|
| Z1 Priya, Z3 Meera (Python beginners) | Variables to classes, 39 solved programs, about 550 check questions. A solid first course, comparable to the first half of an intro unit. | **Yes, after N4** (a kinder checkpoint bar for Zero). The craft module is thin (0–1 problems per topic), so add 2 problems each there. |
| Z4 Aditya (C++/Java beginner) | Same content, but blocked by Python checkpoint questions | **No**, until N1 is fixed. The ~100 MB compiler download (first audit) is also still open. |
| Z2, Z5, Z6 (some experience) | Re-learn what they knew; the new material is the last third | **Weak.** Usable only if N2 (module test-out after placement) lands. Otherwise invite only true beginners. |
| D0 (new to programming → DSA) | All of Zero plus all of DSA, about 80 problems, ~68 h | **Yes as content**, but it's 16 weeks. Steer them to Zero first. |
| D1 Sneha (knows basics, 6 weeks) | The full pattern set with 1–4 problems per pattern | **Partly.** Fine as a "learn the patterns" beta. Not enough as interview prep alone: 45 judged problems, 9 patterns with one problem each. Lean on mapped LeetCode practice and say so. The timeline doesn't fit 6 weeks. |
| D2 Arjun (experienced, 2 weeks) | Mostly re-learning | **No**, until N2 and N3 are fixed. He needs a gap-finder plus hard problems, which the path doesn't do. |
| D3 Vikram (Java) | Can read and quiz, can't submit | **No**, until Java execution is live (D-7). |
| C0 (new → CP, C++) | Doesn't finish | **No.** Fix N1 and route these learners to Zero. |
| C1 Rohan (DSA basics → CP) | Contest math, techniques, intro DP/graphs/range structures, ~100 problems including bridges | **Yes for beta**, once N3 stops the re-teaching. |
| C2 Ishaan (pupil) | Mostly re-learning bridges; 28 CP judged problems | **Weak.** What he needs is 1300–1600 targeted problems. The Codeforces pool exists but isn't in the plan. |
| C3 Kiran (specialist) | Starts at Fast I/O and redoes 33 bridge lessons | **No.** Don't target rated competitors in this beta. |

## Bottom line for the beta

- **Ready to invite (after N1 and N4):** absolute beginners in **Python** (Zero), and DSA learners who know the basics and want to learn patterns rather than cram.
- **Fix before inviting anyone with experience:** N2 + N3. Together they turn every "I already know some of this" learner into a re-learner. They cost 25–50 extra hours per person in the simulation.
- **Don't target yet:** C++/Java beginners (N1), Java anyone (D-7), experienced interview candidates on a deadline, rated competitive programmers.
- **Content to add next:** a second and third judged problem for the 25 topics that have one or none; 10+ checkpoint items for the 6 modules under 15; and Practice-page problems for the 14 Zero topics that have none.

The simulation script is in the session scratchpad and isn't committed. The learner model is synthetic: treat hours and fail counts as directional and the mechanisms (N1–N6) as verified in code.
