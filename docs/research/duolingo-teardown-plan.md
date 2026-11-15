# Duolingo teardown: plan

Status: plan, not findings. Written 2026-11-15.
Target: Duolingo Android 6.105.1 (versionCode 2496, `com.duolingo`, posted 2026-11-05),
APKMirror bundle `base.apk` + `split_config.arm64_v8a.apk`. Static inspection only; nothing
was installed or run.

## The lens

Socrat is not becoming Duolingo. Duolingo optimises daily return (DAU, streaks, paid
conversion). Socrat's contract is **demonstrated capability, not content consumption**
(`docs/product/v1-product-requirements.md`), and `docs/product/metric-contract.md` already says
a reminder open or a passive view is not a meaningful session.

So every Duolingo technique goes through one filter:

> Does it make the learner come back **and** produce evidence they can do something without
> help? Keep it, tied to evidence. Does it only make them come back? Change it or drop it.

A second rule from the owner (2026-11-15): **Socrat must never be annoyingly strict.** How
strict quizzes, assessments and the tutor are is the learner's choice. Someone who wants a
demanding tutor and strict quizzes gets them; someone who wants a relaxed, playful or gentle
style gets that. Evidence is still recorded honestly (independent or assisted), but by default
it labels progress instead of blocking it. Duolingo is a good teacher here: it is forgiving by
default and lets people opt into harder modes.

Each area below ends with a verdict: **Adopt** (as is), **Adapt** (bend it to evidence),
**Avoid** (conflicts with the mission), or **Later** (right idea, wrong time).

## What the APK already shows (first pass)

These are observations from package names, native libraries and bundled assets. They show
that a feature exists in the build, not how it behaves or whether a given user sees it.

| Signal | Where | What it suggests |
|---|---|---|
| `ai/churn/TomorrowReturnProbability…` | dex | A model predicts whether you return tomorrow, and the app acts on it |
| `libonnxruntime.so` | arm64 split | Machine-learning models run on the phone itself |
| `ai/ema` (Explain My Answer), `ai/roleplay`, `ai/videocall` | dex | The AI features of the paid Max tier |
| `streak/`: freeze, repair, earnback, gift, perfectStreak, friendsStreak, streakSociety, widget, alarm, calendar | dex | Streaks are a whole subsystem, not one counter |
| `feature/`: streakjackpot, streakgoal, nostreakfreezechallenge, earlybird, xpboost, tieredchest, gemreward, shardcollections, dailyquests, friendsquest, leagues, yearinreview, liveevents, timedevents | dex | Layered reward and event systems |
| `sessionend/`: learning summary, progress milestone, streak, goals, rating primer, word of mouth, follow suggestions, interstitial ad | dex | The end of a lesson is a carefully sequenced set of screens |
| `energy/` + `RewardedVideoForEnergyActivity` | dex | Free users run out of energy; watching ads or paying refills it |
| `onboarding/`: MotivationFragment, CoachGoalFragment, AcquisitionSurvey, HowMuchYouRemember, BasicsPlacementSplash, NotificationOptIn, WidgetPromo | dex | Onboarding asks for motivation and a goal, places you, then asks for notification and widget permission |
| `delaysignup/` + `assets/hardcoded_sessions/` (math, chess) | dex, assets | The first lessons run before sign-up, bundled in the app |
| `experiments.duostrings.json`, `core/experiments` (372 refs) | assets, dex | Heavy A/B testing. One day-1 test compares framing the streak as an accomplishment, as progress, as visibility, or as easier learning |
| `librive*.so`, `modular_rive_lily.json`, `librlottie.so` | native, assets | Character animation in Rive (the cast, for example Lily) plus Lottie |
| `libunity.so`, `libil2cpp.so`, `feature/chess`, `feature/math` | native, dex | Unity runs the game-like subjects |
| `libuberchord*.so`, `feature/music` | native | Real-time pitch detection for the music course |
| `libduoopuscodec.so`, `speechrecognition/` | native, dex | Speaking exercises: voice is recorded, compressed and graded |
| Moloco, Vungle, ironSource, Facebook Audience Network, Pangle (ByteDance), Confiant | dex | Ad mediation stack for free users |
| Adjust, Firebase, Sentry, Google Play review prompt and in-app update | dex | Attribution, analytics, crash reports, store ratings |
| `feature/widget`, `feature/appicon`, `feature/haptics` | dex | Phone-native touches: home-screen widget, changing app icon, haptics |

## Breakdown: the twelve areas

For each area: what to find out, how, and the first guess at Socrat's verdict. Guesses get
replaced by findings.

### 1. Acquisition and first run
- Find out: acquisition survey, attribution, first lesson before sign-up, when sign-up is asked,
  placement test.
- How: `onboarding/`, `delaysignup/`, `hardcoded_sessions`; walk the web onboarding.
- Socrat: **Adapt.** A first verified win before any form is strong, and Socrat just moved
  sign-in before placement (`e1aa69fb`). Test both against activation, measured as the first
  piece of independent evidence.

### 2. Goal, motivation and placement
- Find out: motivation question, daily goal picker, coach goal, "how much do you remember".
- Socrat: **Adopt.** This matches Ask → Blueprint in the universal engine spec. Borrow the
  one-question-per-screen pacing and the visible commitment ("10 minutes a day").

### 3. The core lesson loop
- Find out: session structure, exercise types, difficulty ramp, mistakes review, hearts and
  energy, speaking and listening.
- How: `session/`, `rampup/`, `energy/`, `speechrecognition/`.
- Socrat: **Adapt** pacing, feedback timing and the sound and animation of "correct".
  **Avoid** energy and hearts that block learning after mistakes: productive struggle is the
  point.

### 4. The end-of-lesson sequence
- Find out: screen order and the conditions for each screen (summary, milestone, streak,
  quests, rating prompt, share, ad).
- Socrat: **Adapt.** Keep the moment, but fill it with evidence ("you solved 3 without hints;
  2-pointer is now *demonstrated*"), not points.

### 5. Habit system: streaks
- Find out: what counts toward a streak, freeze, repair, earnback, perfect streak, friend
  streaks, Streak Society, calendar, alarm, widget.
- Socrat: **Adapt.** Count a day only when it has a meaningful session as `metric-contract.md`
  defines it. Freeze and repair fit the PRD's "adjust without pretending missed work was
  done". This is the highest-leverage area.

### 6. Reward layers: XP, gems, chests, quests, boosts
- Find out: currencies, sources, sinks, timing (Early Bird, XP boost, jackpot).
- Socrat: **Adapt** quests into capability quests ("prove sliding window on an unseen problem").
  **Avoid** a separate currency economy. It rewards activity, not capability.

### 7. Social and competition
- Find out: leagues (tiers, promotion and demotion), friends quest, friend streak, follow
  suggestions, contact sync, Year in Review, sharing.
- Socrat: **Later**, and rank by evidence, not XP. The V1 PRD excludes social features, but a
  shareable "passport" of verified skills fits the long-term "competency verification" vision.

### 8. Notifications and win-back
- Find out: opt-in timing, triggered notifications, follow-ups, resurrection flow, the
  tomorrow-return model and what it changes.
- How: `notifications/`, `resurrection/`, `ai/churn`.
- Socrat: **Adopt** smart timing and a gentle comeback ("your plan was adjusted, here is a
  5-minute review"). Socrat has no push yet (no web push, no FCM). This is a mobile-scale gap.

### 9. Money: subscriptions, paywalls, ads
- Find out: Super and Max tiers, family plan, paywall placements (`purchaseflow/`,
  `itemoffer/`, `promo/`, `newyearspromo/`), trial length, what free users lose, the ad stack.
- Socrat: **Adapt** paywall placement at moments of proven value. **Avoid** ads in a learning
  product that sells trust. Compare with `apps/web/src/components/paywall.tsx` and
  `services/api/src/socrat/billing.py`.

### 10. The AI behind it
- Find out: Explain My Answer, roleplay, video call (Lily), the churn model, on-device ONNX
  models, Birdbrain-style difficulty estimation, spaced repetition, AI-generated content at
  scale.
- How: `ai/`, `explanations/`, the ONNX model files and how they are loaded; Duolingo's
  published research and blog for the public half.
- Socrat: **Adopt** the pattern of a model predicting difficulty and recall per item. It is the
  engine's job and fits "engine is the harness". Socrat has no spaced-repetition scheduler
  today. Roleplay and voice tutoring map to the Socratic tutor plus listen mode.

### 11. Content and curriculum
- Find out: path and sections (`newpath/`, `pathsection/`), Stories, DuoRadio, Adventures,
  guidebooks and tips, alphabets, how new subjects (math, music, chess) reuse one engine.
- Socrat: **Adapt.** Several subjects on one engine is exactly Socrat's universal-engine bet.
  Study how they reuse session, path and reward pieces across subjects.

### 12. UI, brand, motion and feel
- Find out: character system (Rive), sound and haptics, colour, layout of the home path,
  widget, app icon, accessibility, performance work (`performance_mode_devices.json`).
- Socrat: **Adapt** the craft: motion with a reason, sound, haptics, Soc as a character with
  states. Keep the notebook brand (`socrat-design-system-v1`). Copy no art, names or
  characters.

Cross-cutting areas covered inside the twelve: experimentation culture (which features are
A/B tested and how), and analytics events (what Duolingo measures).

## How the research runs

| Phase | Source | Output |
|---|---|---|
| A. Static code | REA `inspect_android_package` (needs REA connected and JADX/Java) on `base.apk`: classes, strings, flows per area | Evidence-backed finding per area |
| B. Bundled data | Experiments file, Rive and Lottie files, hardcoded sessions, string resources (notification and paywall copy) | Copy, experiment list, onboarding content |
| C. Live product | duolingo.com in the built-in browser: onboarding, a lesson, end-of-lesson, paywall, leagues | Screens and sequences as users see them |
| D. Public record | Duolingo research papers (spaced repetition, Birdbrain), engineering blog, shareholder letters (DAU, paid subscribers) | The why and the numbers |

Each finding records observation, inference or unknown, and its source. Code shows that a
feature exists; it does not show which A/B arm a user gets.

## Deliverables

1. **Teardown**: one section per area with findings and evidence.
2. **Socrat adaptation map**: per area, Adopt, Adapt, Avoid or Later, with the Socrat file or
   feature it touches, split into web, mobile and scale.
3. **Ranked backlog**: top 10 changes by expected effect on D7 and D30 retention *and*
   independent solve rate, with effort.

## Rules for this work

- Learn mechanics and strategy; copy no code, art, characters, names or copy text.
- Keep this analysis out of the root README. The repository is public, so decide whether this
  file is committed or kept local before committing it.
- The APK came from a third-party mirror. Treat it as untrusted: inspect it, never install or
  run it on a personal device.

## Starting points already known in Socrat

- Streak exists: `apps/web/src/app/today/page.tsx`, `progress/page.tsx`, `components/shell.tsx`.
- Paywall and billing: `components/paywall.tsx`, `services/api/src/socrat/billing.py`.
- Review and retention signals: `services/api/src/socrat/adaptive/profile.py`.
- Service worker and manifest exist (`apps/web/public/sw.js`, `app/manifest.ts`), but there is no
  push notification code and no native app.
