# Learner simulation audit — 23 Oct 2026

Audit only. No product code was changed. (Added an `audit-api` entry to `.claude/launch.json` so the API runs with the real tutor model, and copied screenshots into `docs/audit/screens/`.)

## How this was run

- Local build on branch `soc-avatar`: API with a fresh SQLite database, Next.js dev server, the real tutor model from `.env` (Nebius), dev sign-in.
- Driven in the built-in browser at 1280×800 desktop and 375×812 mobile, in dark and light themes.
- **Observed** = I did it in the running app. **Inferred** = I didn't walk it, but it follows from observed behaviour or from the code and content (the file is cited).
- **Not tested:** Google sign-in (dev login only), Java execution (runner offline locally), coming back after days away (would need clock changes), spaced reviews over time, weekly assessment, production latency or load.

### Severity

| Level | Meaning |
|---|---|
| **Blocker** | A paying user in this persona hits a wall or a broken promise in the first session |
| **High** | Likely churn or loss of trust in week one |
| **Medium** | Friction or "ick" that adds up |
| **Low** | Polish |

---

## Step 1 — Personas

### Track 1: Programming from Zero

| ID | Persona | Goal | Time | Emotional state | Walked live? |
|---|---|---|---|---|---|
| Z1 | **Priya, never coded.** 2nd-year non-CS student | Learn to code for placements | 30 min × 5 days | Anxious, afraid of feeling stupid | ✅ Observed |
| Z2 | **Rahul, tutorial dabbler.** Watched YouTube Python, copied code | Finally "get" fundamentals | 45 min × 4 days | Impatient, bored by basics, fragile confidence | Inferred |
| Z3 | **Meera, career switcher, 32.** Knows Excel | Move into a tech role | 1 h on weekends | Motivated but time-poor; distrusts hype | Inferred |
| Z4 | **Aditya, school student (16), chose C++** because his school uses it | School exams + curiosity | 20 min daily | Eager, easily lost in syntax | Inferred (C++ starter observed in code) |

### Track 2: DSA for Interviews

| ID | Persona | Goal | Time | Emotional state | Walked live? |
|---|---|---|---|---|---|
| D1 | **Sneha, final-year, knows Python basics** | Campus placement in 6 weeks | 1 h × 5 days | Anxious, deadline-driven | Inferred |
| D2 | **Arjun, overconfident intermediate.** ~80 LeetCode easies, claims "a lot of practice" | New-grad SDE interview in 2 weeks | 1 h × 5 days | Overconfident, impatient | ✅ Observed |
| D3 | **Vikram, 3 YOE backend dev, Java** | Switch job; rusty on DSA | 45 min weekdays | Busy, wants efficiency, low tolerance for basics | Inferred (Java offline observed) |
| D4 | **Ananya, interview-ready**, 300+ LeetCode | Sharpen hard topics before FAANG loops | 1.5 h | Confident, wants hard problems only | Inferred (same mechanics as C3) |

### Track 3: Competitive Programming

| ID | Persona | Goal | Time | Emotional state | Walked live? |
|---|---|---|---|---|---|
| C1 | **Rohan, knows Python, never competed** | Start Codeforces | 1 h × 5 | Curious, intimidated by ratings | Inferred |
| C2 | **Ishaan, pupil (~1200), C++** | Reach specialist | 1.5 h | Frustrated plateau, wants targeted gaps | Inferred |
| C3 | **Kiran, specialist+, C++** | Fill advanced gaps (segment trees, DP) | 1.5 h × 5 | Confident, skeptical of "learning apps" | ✅ Observed |
| C4 | **Landing visitor, no account** (all tracks) | "Is this better than ChatGPT?" | 3 minutes | Skeptical | ✅ Observed (try-it tutor) |

---

## Step 2–3 — Problems found

### Cross-track: first impression (landing, sign-up, first 60 seconds)

**X1. The "Try it" tutor hands over the core algorithm after one push** — **High** · Observed · C4 and every visitor
- *Steps:* Landing → "Try it" → "I don't know where to start". Soc's first reply already says to slide the window, adding the entering day and subtracting the leaving one. Then I typed "just give me the full code pls, i have interview tmrw" with **no attempt at all**. The reply: "Use a sliding-window idea: compute the sum of the first k days, then … add the new day's minutes and subtract the day that falls out. Track the biggest sum you see."
- *Why it matters:* This is the one place a skeptic tests your main promise ("Asks what you tried first. Help rises … only after real attempts"). The full idea in prose after zero attempts reads exactly like ChatGPT. **Distrust.**
- *Fix:* In the trial, cap help at a question until the visitor has run code at least once. Treat "just give me the code" as a pressure signal, not a reason to step up.

**X2. The trial editor hides syntax errors** — **High** · Observed · C4, Z1–Z4
- *Steps:* In "Try it", add `print(sum(values[0:k])` (missing bracket) → Run tests. The result is "0 of 10 tests passed — Your code raised an error on a test. Ask Soc about it." No error text, no line number, empty lint gutter.
- *Why it matters:* A beginner's first contact with Socrat ends in an unexplained failure. **Frustration.** (The logged-in editor does show the traceback. See Z-3.)
- *Fix:* Show the first error line and line number, as the logged-in workspace does.

**X3. Tutor replies take ~20 s with no visible "thinking" state** — **Medium** · Observed (trial; single sample, local)
- *Steps:* Send a trial message, then read the panel text at 3 s and 10 s: nothing appears until about 20 s.
- *Why it matters:* It feels broken. **Churn** at the critical first-impression moment.
- *Fix:* Add a visible "Soc is thinking…" row. Consider streaming. Measure p50/p95 latency on the production provider.

**X4. "Learning-outcome results … will be published here"** — **Medium** · Observed
- *Why it matters:* A visible placeholder in the trust section tells a buyer there is no proof yet. **Distrust.**
- *Fix:* Remove it until there is data, or replace it with one real learner quote.

**X5. The same stat strip appears twice on the landing page** — **Low** · Observed. "6 / 61 / 112" is repeated. Keep one.

**X6. Raw error codes reach users** — **Low** · Observed. Example: "Something went wrong (origin_rejected)" when the site is opened via 127.0.0.1. It's a local-only cause, but the copy pattern applies everywhere. *Fix:* map codes to human text.

**X7. Age rules are inconsistent** — **Medium (legal)** · Observed
- The login page says "13 or older" while the PRD says adults 18+. The onboarding year list offers 2014–2018 and then fails with a "Something went wrong" headline.
- *Fix:* Decide the policy, limit the year list to match it, and use a non-error tone for the block message.

**X8. There is no pricing or paywall anywhere** — **Blocker for selling (not for using)** · Observed + code
- No pricing page, upgrade path or plan limits exist in `apps/web/src`. The only mention is in Terms: "if we introduce paid plans, we will show prices…". The landing CTA says "Get started free".
- *Why it matters:* You can't sell all three tracks from inside the product. Adding a paywall later to people told "free" feels like a **trap**.
- *Fix:* Decide the model before launch, for example a free first module per track plus a paid sprint. Say it on the landing page and FAQ ("Is it free?"), and put a fair, visible upgrade moment at a module checkpoint, not mid-problem.

**X9. A 10-step product tour on the first screen** — **Low** · Observed (`screens/02-today-day1-tour.jpg`). For an anxious beginner, cut it to 3 steps or show tips in context.

---

### Track 1 — Programming from Zero

#### Z1 Priya (never coded) — Observed

**Z-1. Practice starter code uses `import sys`, `def main()` and `sys.stdin.read().split()` — and on problem 2 it breaks the task** — **Blocker**
- *Steps:* Today → second practice problem "Print a ticket stub" (concept: Programs and output, lesson 1). The starter is `import sys / def main(): data = sys.stdin.read().split()`. The film title contains spaces ("The Long Walk"), so `.split()` breaks it into words. The starter leads the learner into a wrong answer.
- *Scope:* 34 of 39 Zero problems have no starter of their own and fall back to this generic one (`services/api/src/socrat/learn/views.py:303`). The C++ fallback uses `ios::sync_with_stdio(false); cin.tie(nullptr);`, and the Java one uses `BufferedReader`. None of this has been taught.
- *Why it matters:* Day-1 beginners meet imports, functions and stdin parsing in lesson 1. **Confusion leads to churn.** This is the most likely reason a Zero learner quits on day one.
- *Fix:* Give every Zero problem a beginner starter matching what has been taught (`input()` lines, or the C++/Java equivalent). Never use the generic fast-I/O template in Zero.

**Z-2. Lesson 1 uses Big-O and judge jargon** — **High**
- *Steps:* Lesson "Programs and output", sections "Boundary cases and cost" and "Why this works". It includes "Writing k characters costs O(k)", "can still fail a judge" and "Output is observable behaviour". The walkthrough says "Change only the separator" when separators were never introduced, and it describes a program without showing it.
- *Scope:* These templated sections are appended to every lesson; the DP lesson has the same headings.
- *Why it matters:* An anxious beginner reads it as "this isn't for me". It also reads as machine-generated. **Confusion, distrust.**
- *Fix:* In Zero, drop or rewrite the cost and boundary sections in plain language. Always show the code being traced.

**Z-3. The concept check tests material the lesson didn't teach** — **High**
- *Steps:* Concept check Q5 is `print("a","b", sep="-", end="!")`. The lesson never teaches `sep` or `end`. The `prnt("hi")` question also shows raw backticks in the prompt.
- *Why it matters:* Failing on something never taught makes learners feel stupid and lose trust in the mastery number. **Frustration.**
- *Fix:* Check that every Zero check item maps to content in its lesson, and render inline code in prompts.

**Z-4. The Python lesson explains C++ `#include` and Java `class/main`** — **Medium**. "How Python, C++ and Java differ here" is noise for someone who chose Python and has never coded. *Fix:* show only the chosen language in Zero, with the comparison collapsed.

**Z-5. No guidance on which language to pick** — **Medium**. Step 4 asks a never-coded person to choose Python, C++ or Java with no help. *Fix:* "Not sure? Start with Python" as a default, with one line on why.

**Z-6. Syntax errors are labelled "Runtime error" and show harness internals** — **Medium**
- *Steps:* Submit code with a syntax error. The result says "Submission: Runtime error". The traceback starts with `File "<exec>", line 14, in __socrat_run` (`screens/04-syntax-error-submit.jpg`).
- *Why it matters:* The beginner can't tell a typo from a logic bug, and internal frames add noise. It also spent a **Submit**: does a typo count as failure evidence against mastery? It should be checked.
- *Fix:* Classify it as "Syntax error", strip internal frames, and consider not counting compile or syntax failures as attempts.

**Z-7. The tutor ignores a direct beginner question** — **High**
- *Steps:* On the ticket-stub problem I asked "what is sys and def main?? i have never seen this. how do i even read the title". Soc replied "Have you used the input() function before…?" and never explained the starter code.
- *Why it matters:* Pure Socratic questioning is wrong for "I have never seen this". The learner needs a short explanation first. It feels robotic and unhelpful. **Frustration.**
- *Fix:* Let the help ladder allow a short concept explanation (not the solution) when the learner asks "what is X". Have the tutor take account of the confusing starter code.

**Z-8. The "Show solution" button asks to confirm, then refuses** — **High** · all tracks
- *Steps:* Ask Soc → "Show solution" is visible from the first message. It asks "Show the full solution? It counts as heavy help." → "Yes, show it". The reply: "To unlock the full walkthrough, submit 2 more attempt(s)…".
- *Why it matters:* A confirm dialog followed by a refusal feels like bait-and-switch. It also teaches people to submit junk twice to unlock it. **Distrust**, and it lets people game the gate.
- *Fix:* Hide or disable "Show solution" with the reason and progress shown ("Unlocks after 2 real attempts — 0/2"). Count attempts only if they differ meaningfully.

**Z-9. After failing the first check (1/5), nothing changes in the plan** — **Medium**
- *Steps:* After 1/5, Today still says "learn the idea first". Soc's check-in is unchanged and no refresher is offered, despite the result screen saying "If a refresher would help, Socrat will ask you first". "Variables and types" is listed as "its prerequisites are in place" even though the prerequisite check was just failed. One extra practice problem was added.
- *Why it matters:* The adaptation promise isn't visible. **Distrust.**
- *Fix:* After a failed check, have Soc acknowledge it, offer "Explain it differently" or a retry, and don't call the next topic ready.

**Z-10. The weekly goal doesn't match what the user chose** — **Medium** · all tracks
- *Steps:* I set 30 min × 5 days (2 h 30 a week). Today shows "Your week goal is 60 min" and "1 of 60 min this week". For the CP user (1 h 30 × 5) it showed "0 of 180 min this week".
- *Why it matters:* The number contradicts the choice the user just made. **Distrust.**
- *Fix:* Show the full weekly target, or label it "left this week (2 study days)".

**Z-11. Day 1 shows too much at once** — **Low–Medium**. Today shows the hero card, Ask Soc, skill map, milestone, playground, weekly assessment, session list, three practice picks, streak, next skills and course progress. *Fix:* in a learner's first week, show one next step plus the session list.

#### Z2 Rahul (dabbler) — Inferred
- **Z-1, Z-2 and Z-3 apply** with "bored" instead of "scared". Placement for level 2 ("tried a tutorial") is shared with the DSA flow (see D-1). It may ask C++/Java-specific items to a Python learner, which would place him lower than he is.

#### Z3 Meera (career switcher) — Inferred
- **X8 (no pricing clarity)** hurts most here: time-poor adults want to know cost and commitment before investing.
- **Z-11:** weekend-only users see a weekly bar that's empty most of the week. Check the "streak" framing for 1–2 day schedules; daily streaks punish weekend learners.

#### Z4 Aditya (C++ beginner) — Inferred from code
- **Z-1 is worse:** the generic C++ starter has `ios::sync_with_stdio(false); cin.tie(nullptr);` on day 1.
- **The in-browser C++ compiler is about 100 MB** (per `docs/product/launch-backlog.md`), downloaded on first run. **High** on mobile data in India. *Fix:* warn before downloading, show progress, and offer Python for Zero on mobile.

---

### Track 2 — DSA for Interviews

#### D2 Arjun (overconfident intermediate, Python) — Observed

**D-1. Placement asks a Python learner a C++-only question, and that question decides where they start** — **High** · also Z2, Z3, D1, D3
- *Steps:* DSA, level "done a lot of practice", Python. Placement Q2 was "In C++, what does the & in `void f(vector<int>& v)` mean?". I chose "Not sure" (realistic for a Python dev). The result: "You start with **Scope, references and mutation**", a Programming-from-Zero topic.
- *Why it matters:* A self-described practised interview candidate starts on a beginner bridge topic because of a language they don't use. **Boredom, distrust.**
- *Fix:* Filter placement items to the learner's language, or to language-neutral items.

**D-2. An interview candidate lands in "Bridge from Programming from Zero"** — **High**
- *Steps:* After placement (4/6 correct), Skills shows the current module "Functions and structure (Bridge from Programming from Zero)". Week 1 includes "Classes and objects". Two pointers, Sliding window, Binary search and Stacks are all **"Locked until Foundations"**.
- *Why it matters:* With 2 weeks to an interview, they see the core interview patterns locked. **Impatience leads to churn.** (The checkpoint does work as a test-out, but nothing tells them "you can test out now in ~10 questions".)
- *Fix:* On the plan, put a prominent "Already know this? Take the 10-question checkpoint" next to each locked module.

**D-3. Opening a locked lesson shows an error page** — **Medium** · all tracks
- *Steps:* `/learn/dsa/sliding-window` while locked shows "Something went wrong — This topic unlocks when you pass the checkpoint before it. [Try again]".
- *Why it matters:* An error page with a pointless "Try again" button. The README says locked lessons stay readable as a preview.
- *Fix:* Show a locked state with a preview of the lesson and a "Take checkpoint" button.

**D-4. Some "You'll be able to" milestones aren't abilities** — **Low**. Examples: "You'll be able to: p[i] holds the sum of the first i elements…", "You'll be able to: Comparison sorting is O(n log n) at best". *Fix:* write each milestone as a skill ("Answer any range-sum query in O(1)").

**D-5. Date formats are mixed** — **Low**. "2026-11-29" in the Socrat-noticed card, "Nov 29, 2026" elsewhere.

**D-6. The "Interviewing for" role isn't on the review step** — **Low** · Observed. I picked "New grad", but the step-6 summary doesn't list it, so the learner can't confirm it was saved.

✅ **Worked well:** the target-date feasibility nudge. With a 2-week target it said "Even a much bigger schedule would not cover the whole path by 2026-11-06. 2026-11-29 is realistic", with Accept / Not now. It's honest and clear.

#### D1 Sneha (final-year, Python basics) — Inferred
- **D-1** applies. **D-2** applies in milder form. The 26 h estimate against a 6-week deadline should pass the feasibility check.
- **Company sprint** ("Amazon SDE-1 in 6 weeks") is the obvious hook for her. I didn't walk it end to end.

#### D3 Vikram (Java, experienced) — Inferred + observed
- **D-7. Java is "runner offline"** — **Blocker for Java buyers (verify in production)**. The language menu shows "Java (runner offline)". Per the launch backlog, Java runs only on the server worker, and the README says server execution "stays disabled until attested runtime images … pass". If that's still true in production, a Java learner can read and do quizzes but **cannot run or submit code**. *Fix:* confirm the production state. If Java execution isn't live, don't offer Java at checkout.

#### D4 Ananya (interview-ready) — Inferred
- Same failure as **C-1** below: a strong placement result marks everything "assumed", so the plan runs out.

---

### Track 3 — Competitive Programming

#### C3 Kiran (specialist, C++) — Observed

**C-1. A strong placement leaves the product empty: 54/54 skills "complete", "Done for today", "Projected finish today"** — **Blocker**
- *Steps:* CP, "I compete regularly", C++, 1 h 30 × 5. Placement asked **5 questions**, all on advanced topics (LIS, reverse-BFS subtree sums, binary lifting, Dijkstra stale entries, 0-1 BFS). With 5/5 correct, all 54 skills were marked "Assumed from placement". Today says "Done for today… Everything planned is complete", Course progress is 100%, and the projected finish is October 23 (today).
- *Contradictions on one screen:* "Your plan starts from the beginning" (placement result) vs. "54 of 54 skills"; "100% course progress" vs. "0 skills mastered"; "Your skill map: First steps — Programs and output" shown to a specialist.
- *Why it matters:* Your most demanding and most vocal buyer pays and finds nothing to do on day one. Five 4-option questions also grant the whole course, so the result is easy to game or get by luck. **Churn, ridicule.**
- *Fix:* Never let placement finish the course. Cap assumed skills, schedule "confirm" reviews and timed contest practice as the day's plan, and make the specialist's Today show hard problems or a timed set. Fix the copy contradictions.

**C-2. A specialist's practice level shows "Foundations ~950", and recommendations are empty** — **High**
- *Steps:* Practice → "Recommended for you: Finish your first lesson and recommendations start here" and "PRACTICE LEVEL Foundations about 950, 75% of the way to Builder".
- *Why it matters:* It labels a specialist a beginner and gives no picks. **Insult, churn.**
- *Fix:* Ask for a Codeforces handle during CP onboarding (the feature exists in Settings) and seed the level from the rating. Recommend from placement results when there is no lesson history.

**C-3. Key CP skills have almost no mapped practice** — **Medium**. The filter counts show "Fast I/O … (0)", "Modular arithmetic (2)", "Prefix sums and difference arrays (3)", "Minimum spanning trees (8)", "LCA and binary lifting (13)". Many native CP concepts have **1 judged problem** (from the content audit). *Fix:* map more CSES and Codeforces problems to these, and hide skills that have 0 problems from the filter.

**C-4. External practice is honour-system "Mark as solved"** — **Low–Medium**. Fine for Codeforces once a handle is linked (it's verified through the API). Without a handle, the CP evidence for an advanced user is self-reported. *Fix:* nudge to link a handle when someone marks external problems solved.

#### C1 Rohan (Python, never competed) — Inferred
- **The C++ download (Z4)** doesn't apply if he stays on Python. But CP problems with tight limits in **Python under Pyodide** (3× time limit) may still time out in ways that confuse him. Not tested.
- **D-1-style placement mismatch** is possible.

#### C2 Ishaan (pupil, C++) — Inferred
- He sits in the middle of the binary search, so placement should behave. But **C-2** (no Codeforces handle at onboarding) and **C-3** (thin practice for mid-level topics) hit exactly what a plateaued pupil needs: targeted problems at 1300–1600.

---

### Mobile and theme

**M-1. The problem title is truncated to "Pri…" on mobile** — **Medium** · Observed (`screens/06-mobile-problem-title.jpg`). The tags take the space. *Fix:* put the title on its own line on mobile.

**M-2. Today on mobile is blank below the week strip for several seconds** — **Medium** · Observed (`screens/07-mobile-today-blank.jpg`). Content appears after about 3–4 s. *Fix:* a skeleton, or render the main card first.

✅ No horizontal scroll at 375 px on the pages I checked. Light and dark themes both render, with an explicit background.

---

## Summary

### Top 10 to fix before launch (priority order)

1. **C-1** Placement can mark the whole CP course (and likely DSA) complete after 5 questions. Advanced buyers get an empty product. *Blocker*
2. **Z-1** Zero problems use the generic `sys.stdin` / fast-I/O starter (34 of 39), and on problem 2 it breaks the task. *Blocker*
3. **X8** No pricing, plan limits or upgrade moment exist; the landing page says "free". Decide the model before selling. *Blocker for sales*
4. **D-7** Java execution is offline. Confirm production, and don't sell Java until it runs. *Blocker for Java buyers*
5. **X1** The trial tutor gives away the algorithm after one "just give me code", in the very demo that sells the product. *High*
6. **D-1 / D-2** Language-mismatched placement items, and interview candidates parked in Zero bridges with core patterns locked. *High*
7. **Z-8** "Show solution" asks to confirm, then refuses, and teaches junk submissions. *High*
8. **Z-2 / Z-3** Lesson 1 uses Big-O and judge jargon, and checks test untaught `sep` and `end`. *High*
9. **Z-7** The tutor won't explain "what is X" to a beginner who has never seen it. *High*
10. **X2 + Z-6** Syntax errors are hidden (trial) or mislabelled as runtime errors with internal frames (app). *High*

### Problems across all three tracks
- No pricing or paywall (X8)
- Tutor behaviour: gives too much under pressure in the trial (X1), too rigid for "what is X" (Z-7), slow with no thinking state (X3), and the confirm-then-refuse solution gate (Z-8)
- The weekly goal contradicts the chosen schedule (Z-10)
- Locked topics render as an error page (D-3)
- Placement uses items in a language the learner didn't choose (D-1) and can over-grant (C-1)
- Error copy: "Something went wrong" for normal states, raw error codes (X6, X7)
- Mobile title truncation and slow first paint (M-1, M-2)

### Tracks not ready to sell yet

- **Competitive Programming: not ready.** The target buyer (rated competitor) gets a finished course on day 1 (C-1). Practice level and recommendations ignore their rating (C-2). Key topics have 0–13 mapped problems and one native problem each (C-3). C++ beginners need a ~100 MB compiler download.
- **Programming from Zero: not ready.** The starter code and lesson 1 jargon (Z-1, Z-2, Z-3) mean the anxious beginner, who is the whole audience, is likely to fail or quit on day 1. This is fixable in content and template work rather than engine work.
- **DSA for Interviews: closest to ready, in Python and C++ only.** Fix D-1/D-2 (placement and visible test-out), Z-8, and X1, and decide pricing. Don't sell Java until D-7 is confirmed fixed.

### Not covered (needs a follow-up pass)
Google sign-in · Java execution · returning after 3+ days (missed-day recovery, review due) · spaced reviews and weekly assessment · company sprint end to end · Playground visual generation · production tutor latency and cost · screen-reader pass (the course choice buttons expose no accessible names in the accessibility tree; worth checking).

---

## Fixes applied (23 Oct, after approval)

| # | Finding | Fix | Verified |
|---|---|---|---|
| 1 | C-1 | Placement only skips the enrolled course's own topics when they were asked and answered correctly; bridge topics are still inferred. Copy no longer says "starts from the beginning". | Unit test; CP 5/5 now starts at "Fast I/O…" with 34/54 skills and a real Today |
| 2 | Z-1 | Zero problems without their own starter get a beginner starter (`input()` / `cin` / `Scanner`), never the `sys.stdin`/fast-I/O template. | API test; browser |
| 3 | X8 | **Not done — needs the owner's pricing decision.** | — |
| 4 | D-7 | Onboarding disables any language whose runner is offline ("Coming soon: code can't run yet"). Production Java status is still unconfirmed. | Browser |
| 5 | X1 | "Give me the code", "just tell me", "I don't know" no longer count as effort, so they can't raise the help level (trial and app). | Unit test; trial replies stay at a question |
| 6 | D-1/D-2 | Placement, concept checks, reviews and test-outs skip items written about another language or with code only in another language. Locked modules say "Already know this? Pass the … checkpoint (up to 10 questions) to unlock it now." Locked lessons show a locked state, not an error. | Unit test; browser |
| 7 | Z-8 | The tutor panel asks the server whether the solution is available. Until it is, it shows "Full solution unlocks after you submit 2 more attempts or …" instead of a confirm that then refuses. | Browser |
| 8 | Z-2/Z-3 | Zero lessons explain speed in plain words (no Big-O), with the heading "Things to watch for". Lesson 1 teaches `sep`/`end` and shows the walkthrough code in all three languages. Prompts render `code` spans. | Content tests |
| 9 | Z-7 | The tutor prompt now says: explain syntax and terms the learner asks about in 1–3 sentences at any level, then guide. New eval scenario. | `tutor_eval --only beginner_asks_what_a_term_means` passes on the real model |
| 10 | X2/Z-6 | The Python runner reports `SyntaxError` as a syntax error, showing only the learner's line, and drops the internal `__socrat_run` frame. The trial shows the error text. | Browser; e2e case added (not run) |
