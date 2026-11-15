# Duolingo teardown, and what Socrat takes from it

Written 2026-11-15. Plan: `docs/research/duolingo-teardown-plan.md`.

**Sources.** Each finding is tagged:
- **[APK]**: static read of Duolingo Android 6.105.1 (versionCode 2496, `com.duolingo`, built
  2026-11-05). This covers package and class names, bundled assets, native libraries, the
  resource string table and the bundled experiment file. Nothing was installed or run. Code shows
  that a feature exists; it does not show who sees it.
- **[Web]**: a signed-out walk through duolingo.com on 2026-11-15, from Math onboarding through
  the first lesson to the home path. Styles were measured with computed CSS.
- **[Public]**: Duolingo's papers, blog and shareholder letters, plus press. Figures from
  secondary sources are marked *unverified*.

**The two rules this is read against.**
1. Socrat sells **demonstrated capability**, not time in the app. A Duolingo technique is kept
   when it brings people back *and* produces honest evidence of what they can do.
2. **The learner chooses how strict Socrat is** (owner, 2026-11-15). The default is friendly and
   never annoying. Strict quizzes and a demanding tutor are an opt-in. Evidence is always recorded
   honestly (independent or assisted), but by default it labels progress instead of blocking it.

Socrat is not becoming Duolingo. It borrows the psychology and the craft and keeps its own
mission, brand and voice. No code, art, characters or copy are reused.

---

## 1. The scale of what they built

- **Size [Public].** 64.9M daily active users in Q3 2026 (up 29% a year), 13.1M paid subscribers
  (up 14%), and $309M revenue in the quarter. Daily users are growing about twice as fast as paid
  subscribers.
- **Subjects [APK].** One app runs languages, Math, Music and Chess:
  - Unity (`libunity.so`, `libil2cpp.so`) runs the game-like subjects.
  - A real-time pitch engine (`libuberchord*.so`) grades music.
  - An on-device ONNX model (`model.onnx`, `chess_bot_model_version`) is the chess opponent.
  - Speech is recorded and compressed (`libduoopuscodec.so`, `speechrecognition/`).
- **Experimentation [APK].** There are 372 references to the experiments framework. One
  experiment bundled for day 1 tests four headline framings for the streak: as an
  accomplishment, as progress, as visibility, and as easier learning
  (`reng_android_d1_widget_se_hook_headline_copy`) [Public, *unverified*]. Reportedly 600+
  experiments have been run on streaks alone.
- **AI-made content [Public].** 148 new courses were launched in under a year using generative AI
  and "shared content": one high-quality base course, customised per language. The first 100
  courses took about 12 years.

**Lesson for Socrat:** the moat is a learning engine that many subjects share, plus relentless
measurement. That is already Socrat's universal-engine bet. What Socrat lacks is the
measurement habit.

---

## 2. Area by area

### 2.1 Acquisition and first run
**Observed [Web].** The landing page has one line ("The most fun way to learn languages, chess,
and more!") and two buttons. Then:
1. "I want to learn…" shows a grid of subjects, each with a learner count as social proof
   ("41.9M learners").
2. The character greets you in three short screens: "Hi there! I'm Duo!", "Let's get this party
   started!", then "It can be hard to stay motivated…" / "…so Duolingo is designed to be fun like
   a game!"
3. Four questions, one per screen, with a progress bar along the top:
   - who you are (student / adult);
   - why you're learning (multi-select);
   - how you heard about Duolingo (attribution);
   - daily goal: 5, 10, 15 or 20 min, labelled *Casual, Regular, Serious, Intense*.
4. Starting point: Beginner (marked RECOMMENDED) or Intermediate, with "you can change this
   later".
5. **The first lesson starts immediately, before any account.**

**Observed [APK].** The APK has matching pieces:
- First lessons ship inside the app (`assets/hardcoded_sessions/{math,chess,music}`), so the
  first lesson needs no network.
- Delayed sign-up (`delaysignup/`), an acquisition survey and a placement splash.
- A notification opt-in and a widget promo sit inside onboarding.

**Why it works.** Nothing stands between curiosity and the first success. Every question is one
tap and also personalises the course. Picking a time goal *labelled* "Regular" or "Serious" is
a small public commitment.

**Socrat today.** Sign-in now comes before placement (`e1aa69fb`, branch
`feat/signin-before-placement`). The universal engine spec already wants a single box for
"what do you want to learn and how".

**Verdict: Adapt.** Let a guest do a first lesson or placement and *earn* something before
sign-up. Ask for sign-up to save that progress. A/B test this against sign-in first, measuring
the first independent evidence in each arm. Keep "Ask" to one box plus at most two one-tap
questions (who, daily time), with labelled time goals.

### 2.2 The lesson loop
**Observed [Web]**, in the Math first lesson:
- **Mixed formats that hand over control step by step.** Pick the answer, then drag it onto a
  number line, then build the equation from tiles, then type the answer from memory. Support
  fades within one lesson.
- **Mistakes cost nothing in the moment.** A red bottom bar shows "Incorrect" with the correct
  answer and a Continue button. You move on.
- **Missed items come back at the end**, tagged "PREVIOUS MISTAKE". The lesson ends only when
  each one is answered correctly.
- **Momentum feedback.** A "4 IN A ROW" label sits above the progress bar, the bar turns gold at
  6 in a row, and the praise rotates ("Amazing!", "Nice!", "Good job!").
- **Keyboard and tap both work**: number keys pick, Enter checks and continues.
- A **Toolkit** (calculator) is always one tap away.

**Observed [APK]:**
- `rampup/` (difficulty ramp) and `LessonCoach` (an in-lesson coach).
- `max_consecutive_mistakes` (the lesson adapts after repeated errors).
- **Energy** replaced hearts in 2025 [Public]. Free users get 25 energy, and every exercise uses
  some, right or wrong. It refills over time, by watching ads or with Super. There was public
  backlash and petitions.

**Socrat today.** Socratic hints, code exercises, checkpoints. Failed checkpoints have retry
**cooldowns** (`learn/service.py` `gate_cooldowns`).

**Verdict: Adopt** the lesson psychology:
- feedback right after each item, in a bottom sheet;
- support that fades within a lesson;
- missed items re-asked at the end;
- combo feedback;
- full keyboard flow.

**Avoid** energy, hearts and cooldowns that stop someone mid-learning. A retry wait becomes
something the learner opts into (strict mode), not the default.

### 2.3 End of lesson
**Observed [Web], in order:**
1. "Lesson Complete!" with an animated celebration, Total XP (20) and accuracy (94%, "GREAT!").
2. A day-1 streak screen: a big flame, the week laid out ahead, the rule in plain words
   ("skipping a day resets it"), and a button the learner presses to commit: **"I CAN DO IT!"**
3. "Let's commit to learning with a Streak Goal!": 7, 14, 30 or 50 days, labelled *Good, Great,
   Incredible, Unstoppable*.
4. "All Daily Quests complete!" with a chest.
5. "You earned 5 gems! Nice job reaching your daily goal!"
6. Only then: "Time to create a profile!", pitched as "save your progress". **"Later"** is
   allowed.

**Observed [APK].** The server decides which end-of-lesson screens appear and in what order
(`session_end_backend_arrange`, `session_end_screen_providers`). The pool also includes a
learning summary, a progress milestone, a rating prompt, word of mouth, follow suggestions, a
paywall trial offer and an interstitial ad.

**Why it works.** The peak-end rule: the last moment shapes how the whole session is remembered.
Commitments are made at peak happiness. Sign-up comes after the learner has something to lose.

**Verdict: Adapt.** Socrat's end screen leads with **evidence**, then habit, then the next step:
- *"3 solved without hints. Sliding window is now demonstrated."*
- The streak.
- *"Tomorrow: 8 minutes, review two-pointer."*

The server picks and orders the screens so they can be tested.

### 2.4 Streaks
**Observed [APK].** The `streak/` package and related features include:
- freeze, freeze gift, repair and repair gift, earn-back challenges;
- perfect streak, Streak Society (an elite club at long streaks);
- friend streaks, calendar, alarm (with "gentle" and "silent" variants), widget;
- streak goal, jackpot, the Early Bird / Night Owl timing bonuses.

The copy [APK] says it directly: *"Learners that reach a 21 day streak are 6x more likely to
complete their course!"*

**Churn model [APK].** The app loads a server-computed "tomorrow return probability"
(`tomorrow_return_probability_load/refresh`). It uses that score to **give at-risk learners a
free streak freeze** (`ChurnStreakFreezeReward`, `lastChurnStreakFreezeEquippedTimestamp`) and an
extra notification (`isChurnExtraNotif`).

**Public, *unverified* figures:**
- "commit to my goal" beat "continue" in retention;
- a reminder that names the learner's own goal raised daily users by 5%;
- the first 7 days decide long-term retention.

**Socrat today.** A streak already counts *scheduled* study days, and earned freezes cover
missed days (`learn/service.py:269`, `learn/streaks.py`). Badges exist for 7 and 30 days
(`learn/achievements.py`). This is already kinder than Duolingo's daily rule.

**Verdict: Adapt.** Add:
- the day-1 commitment screen and a streak goal;
- a calendar view;
- repair and earn-back ("do a 10-minute review today to restore yesterday");
- **automatic freezes for learners at risk** (a simple rule first, a model later).

Count a day when it has a meaningful session as `metric-contract.md` defines it. Never use
shame copy.

### 2.5 Rewards: XP, gems, chests, quests, boosts
**Observed [APK]:**
- XP with boosts (`xp_boost_*`, stackable) and timed events (Early Bird, XP Happy Hour,
  `timedevents/`);
- gems and tiered chests on the path (`path_chest_*`);
- daily quests, friends quests, family quests, weekend quests.

**Observed [Web]:**
- a guest starts with 505 gems (an endowment);
- the first daily quest is completed by the first lesson (an early win);
- a chest sits along the path.

**Observed signed in [Web].** The quests page shows:
- a daily countdown ("40 MINUTES" left);
- one quest slot open and the rest locked ("More quests unlock soon");
- "Monthly challenges unlock soon! … earn exclusive badges".

Even the loading screen is a short character animation.

**Verdict:**
- **Adapt** quests into *capability quests*, for example "Solve one unseen sliding-window
  problem without hints" or "Review 3 due concepts".
- **Avoid** a separate gem economy and XP multipliers. They reward grinding, not ability. One
  small, honest number is enough (for example "minutes practised" or "problems solved").

### 2.6 Social and competition
**Observed [APK, Web]:**
- **Leagues** in ten tiers (Bronze to Diamond, with Obsidian, Pearl, Amethyst, Sapphire and others
  in the copy), weekly promotion and demotion, and a "League Repair" to buy.
- The leaderboard is **locked** until "2 more lessons" [Web]: features unlock gradually.
- Friend streaks, friends quests, follow suggestions, contact sync.
- Year in Review, and shareable cards ("I got 1st place in the Diamond League!").

**Verdict: Later**, and ranked by evidence, never by XP. Small study groups ("pods"), a friend
streak and shareable passport cards come first. The V1 product requirements exclude social
features, but shareable *verified* skills fit the long-term "competency verification" goal.

### 2.7 Notifications and win-back
**Observed [APK]:**
- Firebase Cloud Messaging (push notifications).
- Notifications scheduled on the phone (`android_can_schedule_local_notifications`) and
  triggered follow-ups (`FollowUpNotificationBroadcastReceiver`).
- Early Bird and Night Owl settings, an opt-in to be told when energy is full.
- A resurrection flow for returning users (`resurrection/`, "Welcome back, {name}! Refill the
  Streak Freezes you used.").
- The famous plain line: "Duo misses you!"

**Socrat today.** In-app nudges only (`adaptive/views.py` `nudges`). There is a service worker
and a manifest, but no web push and no email reminders.

**Verdict: Adopt.** This is the biggest gap. Build:
- web push and email at a time the learner picks;
- copy that names *their* goal ("10 minutes keeps your interview plan on track");
- a gentle comeback flow ("Your plan was adjusted while you were away. Here's a 5-minute
  restart.");
- automatic freezes for learners at risk.

### 2.8 Money
**Observed [APK, Web, Public]:**
- **Super** (no ads, unlimited energy) and a **Family plan** ("6 Super accounts for the price of
  1!").
- **Max** (AI features). Press reports in late 2026 say Max is being wound down to focus on Super
  [Public, *unverified*].
- Free trials ("Start my free week"), referral weeks ("one week of free Super for every friend").
- Promo codes, a New Year promo, partner bundles ("1 free year of New York Times Games with
  Super!").
- Paywalls at moments of need: energy runs out mid-lesson (`MidSessionNoEnergyBottomSheet`), and
  rewarded ads as the free alternative.
- An ad stack for free users: Moloco, Vungle, ironSource, Facebook Audience Network, Pangle,
  plus Confiant ad-quality screening.

**Observed signed in [Web].**
- **Upsell right after sign-up.** A "Try Super for free / START MY FREE MONTH" card moves to the
  top of the side panel the moment an account exists. A one-month trial banner also sits on top
  of the shop.
- **Shop.** The shop has two sections. *Hearts* has "Refill Hearts" and "Unlimited Hearts" (the
  latter via a free trial). *Power-Ups* shows "Streak Freeze: 2 / 2 EQUIPPED". New accounts start
  with their streak already protected.
- **Web still uses hearts** (5), while the Android app has moved to energy. Duolingo runs the
  two platforms on different economies.
- **The paywall.** It opens with an outcome claim, "Super learners are 4.2x more likely to finish
  the Math course!" That is a correlation presented as a benefit. Then comes a three-row Free vs
  Super table (learning content, unlimited hearts, no ads), "START MY FREE MONTH", and a plain
  "NO THANKS".

**Socrat today.** Paywalls are triggered by context, each with its own reason copy
(`components/paywall.tsx`): first 2 modules free, then Founding Member pricing.

**Verdict:**
- **Adapt.** Keep paywalls tied to moments of proven value. Add a trial, family and student
  plans, and referral weeks.
- **Avoid** ads and pay-to-continue-learning walls. Socrat sells trust.
- **Lesson from Max.** A separate premium AI tier seems not to have held up. Socrat should put
  the AI tutor in the core plan.

### 2.9 The AI behind it
**Memory model [Public].** Half-life regression (Settles and Meeder, 2016) predicts how long
each item stays in memory. Reported results:
- 45%+ lower error than baselines at predicting recall;
- **+12% daily engagement** in a live test.

**Memory model [APK].** Spaced repetition is still in the app. `SpacedRepetitionContext` carries
the number of knowledge components covered, and old and new strength values. A Practice Hub
covers mistakes review, vocabulary review and "Keep your memory fresh" unit reviews.

**Other models and AI features:**
- **Churn model [APK]:** the tomorrow-return probability drives free freezes and extra
  notifications.
- **Explain My Answer [APK]:** `ai/ema`, a button on graded items.
- **Roleplay and Video Call with Lily [APK, Public]:** live speaking with an AI character, with
  captions, difficulty surveys, a session report and a "low-stress speaking practice" pitch.
- **Math tutor [APK]:** `MathTutorNextStepRequest`, "Force LLM fallback for Tutor next-step
  responses". It is a step-by-step tutor where rules decide and an LLM is the fallback, the
  same pattern as Socrat's "engine is the harness".
- **Content [Public]:** AI-generated courses at scale from a shared base.

**Socrat today.** A Socratic tutor with move selection (`assistant/engine.py`) and a weekly
review. There is no per-item memory model and no daily review queue.

**Verdict:**
- **Adopt** a memory model per concept and item. Start simple (recall half-life from success,
  lag and hint use), and expose a daily **Review** queue. This is the strongest
  research-backed retention lever, and it is pure "engine" work.
- **Adopt** "Explain my answer" on every graded item.
- **Later:** voice tutoring (pairs with the existing listen mode).

### 2.10 Content and curriculum
**Observed:**
- The home is a **path** of round nodes with chests and guidebooks, sections and units, and a
  "JUMP HERE?" placement shortcut [Web].
- There are Stories, DuoRadio, Adventures, Guidebook/Skill tips, alphabets and a CEFR-mapped
  **Duolingo Score** [APK]. The Score grows with skill and can be added to LinkedIn ("Add your
  Duolingo Score to LinkedIn!").

**Verdict:**
- **Adopt** a per-course capability score built only from independent evidence. It becomes the
  headline number in Socrat's passport and on shareable cards.
- **Adapt** the path: one clear "Start" node, upcoming nodes visible, "jump ahead" placement
  checks.

### 2.11 UI, brand and feel: the psychology behind it
Measured on duolingo.com [Web]. These describe the *feeling*; Socrat applies them in its own
notebook style.

| Principle | How Duolingo does it | Socrat version (notebook brand) |
|---|---|---|
| Buttons look pressable | 16px corners plus a solid, unblurred 4px ledge in a darker shade under the button; it sinks on press | A "stamped" button: a book-blue fill with a darker ink ledge, which sinks on press. One per screen |
| Calm surfaces | Flat cards: 2px outline, 16px corners, 18px padding, no drop shadows | Paper cards with a ruled-line or margin outline, no shadows (already in the brand rules) |
| One thing per screen | One question, one big primary button pinned bottom right, progress bar on top | Same layout for lessons and onboarding |
| Instant, kind feedback | A full-width bottom sheet (green correct, red incorrect) with the answer and Continue | A bottom sheet in red pen (incorrect) or yellow highlighter (correct), using the existing `--pen` / `--highlight` tokens |
| A character who cares | Duo speaks in speech bubbles, has emotional states, celebrates, explains why ("It can be hard to stay motivated…") | Soc (the stone bust) with a few states (curious, proud, thinking, encouraging) and pen-note speech bubbles |
| Momentum | A combo counter; the bar changes colour on a run; rotating praise | An "n in a row" pen tally; a highlighter sweep on the bar |
| Celebration at the peak | Confetti, XP counting up, accuracy badge | Highlight the *evidence*: the concept stamped "demonstrated", with a short ink animation |
| Friendly type | Rounded bold sans; uppercase tracked button labels | Geist stays. Socrat's brand rules avoid uppercase tracked labels, so warmth comes from weight and rhythm, not capitals |
| Low-stakes language | "Later" always offered; "You can change this later" | The same promise wherever a choice is made |

Underlying psychology: lower the effort of each step (one tap), give the learner a sense of
progress (bar, combo), make them feel competent (instant correct, early wins), make them
commit (choosing a goal, "I can do it"), use loss aversion gently (streak, "save your
progress") and give the app a social presence (the character).

---

## 3. Socrat adaptation map

| Area | Verdict | Web | Mobile | Scale | Socrat touchpoint |
|---|---|---|---|---|---|
| First win before sign-up | Adapt | Guest lesson or placement, then "save your progress" | Same; bundle a first lesson offline | A/B by funnel step | `app/placement`, `learn/placement.py`, sign-in flow |
| Learner-chosen strictness | Adopt (owner rule) | Learning-style setting: Relaxed, Balanced, Strict | Same | Policy per learner, not global | `learn/service.py` `gate_cooldowns`, `assistant/engine.py`, checkpoints |
| Lesson feel | Adopt | Bottom-sheet feedback, combo, end-of-lesson retry of misses, keyboard flow, fading support | Haptics, sound | Exercise-type library shared across courses | lesson and quiz components, `coursegen/exercise.py` |
| End of lesson | Adapt | Evidence first, then streak, goal and next step | Same | Server-ordered, testable screens | new `sessionend` module |
| Streaks | Adapt | Day-1 commitment, streak goal, calendar, repair and earn-back | Widget, alarm | Automatic freeze for at-risk learners (rule, then model) | `learn/streaks.py`, `learn/achievements.py` |
| Review engine | Adopt | Daily Review queue, mistakes practice | Same | Per-item recall model trained on Socrat data | `adaptive/profile.py`, new scheduler |
| Notifications | Adopt | Web push and email at a chosen time, goal-specific copy, comeback flow | Native push | Send-time tuning, churn-aware | `public/sw.js`, new notifications service |
| Capability score | Adopt | Per-course score from independent evidence; share card | Same | Calibrate against the metric contract | `app/passport` |
| Soc as a character | Adapt | Speech-bubble onboarding, a few states | Rive or Lottie states | One asset set for every course | `components/socrat/*`, `app/dev-mascots` |
| Money | Adapt | Value-moment paywalls, trial, family and student plans, referral weeks | Store billing | Pricing experiments | `components/paywall.tsx`, `billing.py` |
| Quests | Adapt | Capability quests | Same | Generated per course | new |
| Social | Later | Pods, friend streak, share cards | Contacts | Evidence-ranked groups | new |
| Voice tutor / roleplay | Later | Talk to Soc (listen mode exists) | Mic | Model cost control | `assistant/` |
| Energy, hearts, gems, ads, XP leagues | Avoid | | | | |

**Mobile path (owner, 2026-11-15): web app only.** Socrat stays one web app. People use it in
the browser or add it to their home screen; there is no separate native app. So "Mobile" in
this map means the installed web app (PWA) on a phone:
- an install prompt and a proper `app/manifest.ts` (icons, standalone display);
- web push through `public/sw.js` (supported by installed web apps on Android, and on iOS 16.4+
  once added to the home screen);
- the vibration API for light haptics where the browser supports it;
- an offline first lesson cached by the service worker;
- a fast, light UI on low-end phones.

Native-only extras from Duolingo's APK (home-screen widgets, a changing app icon, store
billing) are out of scope.

---

## 4. Ranked backlog

Ranked by expected effect on D7/D30 retention and on independent solve rate, against effort.
Small (S) is a few days, medium (M) one to two weeks, large (L) longer.

| # | Change | Why | Effort |
|---|---|---|---|
| 1 | **Learning-style setting** (Relaxed, Balanced, Strict) controlling gates, retry waits, hint limits and tutor tone. Default: Balanced, with no blocking cooldowns | Owner rule; removes the most annoying friction | M |
| 2 | **Lesson feel pass** (built 2026-11-16 behind `lesson_feel_enabled`; see the progress log in `docs/implementation/universal-engine-plan.md`): feedback bottom sheet, end-of-lesson retry of misses, combo, keyboard flow, pressable stamped buttons | Duolingo's core "this is easy and fun" feeling | M |
| 3 | **End-of-lesson sequence** (built 2026-11-16 behind `session_end_enabled`; see the progress log in `docs/implementation/universal-engine-plan.md`) led by evidence, then streak and next step | Peak-end moment; the commitment point | S–M |
| 4 | **Daily Review queue** backed by a simple recall-half-life model | Best-evidenced retention lever (+12% engagement at Duolingo) | M–L |
| 5 | **Streak upgrade**: day-1 commitment, goal, calendar, repair and earn-back, automatic freeze for at-risk learners | The first 7 days decide retention | M |
| 6 | **Web push and email reminders** at a chosen time, goal-specific copy, comeback flow | Socrat's biggest missing channel | M |
| 7 | **Guest first lesson, then "save your progress"**, A/B against sign-in first | First win before any form | M |
| 8 | **Capability score** per course in the passport, with share cards | Turns evidence into pride and organic reach | M |
| 9 | **Soc character states** in onboarding, feedback and celebrations | Social presence; makes the app feel warm and familiar | M |
| 10 | **Experimentation and event plumbing**: feature flags and A/B arms wired to the metric contract | Duolingo's real engine; lets everything above be tested | M |

**Added by the owner (2026-11-15): a lighter UI pass.** Duolingo feels light: flat cards, no
shadows or blur, one thing per screen. Socrat's current UI is heavy and makes some devices lag.
Make it clean, light and fast on low-end phones and laptops:
- fewer layers, effects and animations running at once;
- smaller pages to download;
- check against Core Web Vitals on a throttled device.

Do this before or together with item 2.

Later: capability quests, pods and friend streaks, voice tutor, native app with widget, a
churn model.

## 5. Open questions
- Signed-in surfaces seen: home, quests, shop, Super paywall. Not reachable on a new account:
  leagues (locked until 2 more lessons), Practice Hub, and long-streak screens (Streak Society,
  repair, earn-back). Looking at those needs an account with some history.
- A deep code read of specific flows (for example exactly which end-of-lesson screens show and
  when) needs a decompiler; JADX is not installed.
- Figures marked *unverified* need primary sources before anyone quotes them.

## Sources
- Duolingo Q3 2026 shareholder letter (SEC 8-K):
  https://www.sec.gov/Archives/edgar/data/0001562088/000162828026069474/q3fy26duolingo9-30x26share.htm
- Settles and Meeder 2016, half-life regression: https://preview.aclanthology.org/fix_video/P16-1174.pdf
  and https://blog.duolingo.com/how-we-learn-how-you-learn
- Streak experiments (secondary): https://www.lennysnewsletter.com/p/duolingo-streaks,
  https://lazyweb.com/research/duolingo-retention-experiments
- Energy replacing hearts: https://duolingo.fandom.com/wiki/Energy,
  https://techissuestoday.com/duolingo-energy-system-user-backlash
- Max and Video Call: https://blog.duolingo.com/duolingo-max
- Max wind-down (secondary): https://www.customerexperiencedive.com/news/duolingo-ceo-monetize-without-degrading-free-user-experience/873877/
- 148 AI-built courses: https://investors.duolingo.com/news-releases/news-release-details/duolingo-launches-148-new-language-courses
