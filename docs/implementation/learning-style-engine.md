# Learning-style engine (admin testing)

Goal: one engine that can teach any subject in any style: gamified, in depth, a top-level
overview, quantum mechanics for kids under 10, five minutes of physics a day, Harvard-level
math. Today it is available to admin accounts only.

## Assessment of the engine before this change

| Area | What it did | Limit for "any style" |
| --- | --- | --- |
| Path style | `thorough / balanced / fast_track / goal_focused` in `planner/goals.py` | Changes order and pacing only. Content, tone and level never change. |
| Course brief | audience, outcome, background, languages | No way to say how it should be taught. |
| Lesson author | Fixed rules: 3000+ characters, 3+ headings, matched to the DSA reference lesson | A 5-minute or kids lesson would be rejected by the gates. |
| Reviewer | Seven dimensions judged against the DSA reference | Rewards one register; cannot score fit to a learner. |
| Tutor prompt | "learn programming, interviews, competitive programming"; hidden steer toward contest practice | Wrong identity for any other subject or audience. |
| Concept size | `estimated_minutes >= 10` | A 5-minute daily course cannot be expressed. |

Strengths kept: lazy per-concept generation, the gate-and-reviewer pipeline, fact checking,
code verified by execution, budgets, versioned DB storage, the Socratic help ladder and the
adaptive profile.

## What was added

- `socrat/style/spec.py`: `StyleSpec` (learner, level, depth, format bite/standard/deep,
  session minutes, tone, tutor mode, rigor, gamified, notes), six presets, keyword rules, the
  Stylist agent prompt (`interpret`), and the blocks given to authors and the tutor.
- Course builder: a brief may carry `style` or a free-text `style_request`. The Stylist
  compiles the request; the architect sizes concepts by it; authors follow it; lesson gates
  use the style's length bounds; the reviewer adds a `style_fit` score (must be 4+). Courses
  without a style behave exactly as before.
- Tutor: `GENERAL_SYSTEM` (the same tutor without the programming and contest steering) and a
  `<learning_style>` context section, used when an admin sets a personal style.
- `Concept.estimated_minutes` now accepts 3 and up.
- Admin API `/api/v1/admin/style/*` and the "Learning styles" tab on `/admin`.

## Rollout

- Admin only: the tutor reads a stored style only for accounts that pass
  `style.access.is_admin`; other accounts ignore it even if data exists.
- Kill switch: `SOCRAT_STYLE_ENGINE_ENABLED=false` hides the admin API and the tutor ignores
  styles.
- No migration: the personal style is stored in `Enrollment.adaptive["learning_style"]`; a
  course's style lives in the brief JSON.

## Next

1. Per-learner restyling of released lessons (extend `lesson_variant` with the style) so one
   shared canonical course can be delivered in many styles.
2. Real game mechanics for gamified (quests, XP) rather than tutor framing only.
3. Style-aware quiz difficulty and spaced-review cadence from `session_minutes`.
4. Evals: score generated lessons per preset against a fixed rubric before widening access.
