# Wondering research record, 2026-11-05

Everything gathered while studying how Wondering (wondering.app, YC S26) generates courses and
practice. The analysis and conclusions are in
`docs/implementation/universal-engine-audit-3.md`, sections 7, 8 and 9. This folder is the
evidence behind them.

## How it was gathered

1. **Signed out, static** (sections 7 and 8 of the audit): headless Chromium opened the public
   landing page; REA (`rea-agents` 6.8.0) captured it passively and exported the 37 scripts it
   loaded. The scripts were read as data and never run. Evidence ids: `static/rea-evidence.txt`.
2. **Signed in** (section 9): the owner's own account, signed in with a one-time email code in an
   isolated browser profile that was deleted afterwards. One test course was created: "Teach me
   fractions. I am 10 years old and I like games." (answers: knows halves and quarters; wants to
   compare, add and subtract). Lesson 1 was opened. A recorder (`tools/w_recorder.cjs`) logged
   every backend call: time, path, status, duration and the structure of request and response.
   It never recorded headers, so no tokens. Full responses were kept for the generation and
   content calls.

## What is here

| Path | Contents |
|---|---|
| `network/requests.jsonl` | All 166 recorded backend calls, one JSON object per line: `t`, `ms`, `method`, `path`, `query`, `status`, `ct`, `bytes`, `req`/`res` (value-free structure), `events` (stream event types), `raw` (file in `responses/`) |
| `responses/` | 101 full responses: the creation chat (`001`-`003`), outline and lesson briefs (`004`, `013`, `029`), course rows and lesson shells, lesson-1 pages (`096`), practice items (`055`), mind map, cover, status polls |
| `screenshots/` | 15 screens of the signed-out page, sign-in, the creation chat, the outline, the course and lesson 1 |
| `screenshots/socrat-checks/` | Socrat's own screens from the same work (practice sets, order and match questions, notes box) |
| `static/findings.json` | From the scripts: database tables, RPCs, server functions, practice types, visual kinds, feature flags, review constants, figure library, lesson components |
| `static/script-manifest.json` | Address, size and SHA-256 of every script captured (the scripts themselves are not stored here, see below) |
| `static/rea-evidence.txt` | REA evidence identifiers for the page capture and the script export |
| `tools/` | The scripts used: browser steps, recorder and this export |
| `archive/` | Unredacted originals and the whole session workspace (see below) |

## Timeline of the signed-in run

Status polls of lesson rows (every 2 s, 54 in all) are left out of the table; they are in the log.

| Time (UTC) | Method | Path | Status | ms | Response file |
|---|---|---|---|---|---|
| 02:31:12 | POST | `/functions/v1/course-creation-chat` | 200 | 3187 | 001-course-creation-chat.txt |
| 02:31:15 | POST | `/rest/v1/chat_conversations` | 201 | 328 |  |
| 02:31:49 | PATCH | `/rest/v1/chat_conversations` | 204 | 205 |  |
| 02:31:49 | POST | `/functions/v1/course-creation-chat` | 200 | 2298 | 002-course-creation-chat.txt |
| 02:31:51 | PATCH | `/rest/v1/chat_conversations` | 204 | 144 |  |
| 02:33:59 | PATCH | `/rest/v1/chat_conversations` | 204 | 154 |  |
| 02:33:59 | POST | `/functions/v1/course-creation-chat` | 200 | 2935 | 003-course-creation-chat.txt |
| 02:34:02 | PATCH | `/rest/v1/chat_conversations` | 204 | 147 |  |
| 02:35:50 | POST | `/functions/v1/generate-lesson-plan-from-content` | 200 | 6616 | 004-generate-lesson-plan-from-content.json |
| 02:37:13 | POST | `/rest/v1/projects` | 201 | 246 | 005-projects.json |
| 02:37:13 | GET | `/rest/v1/course_learning_preferences` | 200 | 285 |  |
| 02:37:13 | PATCH | `/rest/v1/chat_conversations` | 204 | 135 |  |
| 02:37:13 | POST | `/rest/v1/course_nodes` | 201 | 229 | 006-course_nodes.json |
| 02:37:14 | POST | `/rest/v1/course_nodes` | 201 | 160 | 007-course_nodes.json |
| 02:37:14 | POST | `/rest/v1/lesson_sessions` | 201 | 232 | 008-lesson_sessions.json |
| 02:37:14 | POST | `/rest/v1/course_nodes` | 201 | 147 | 009-course_nodes.json |
| 02:37:14 | POST | `/rest/v1/lesson_sessions` | 201 | 148 | 010-lesson_sessions.json |
| 02:37:13 | POST | `/functions/v1/course-chat` | 200 | 5275 |  |
| 02:37:13 | POST | `/functions/v1/course-chat` | 200 | 5652 |  |
| 02:37:19 | GET | `/rest/v1/projects` | 200 | 185 | 011-projects.json |
| 02:37:19 | PATCH | `/rest/v1/projects` | 200 | 428 | 012-projects.json |
| 02:37:14 | POST | `/functions/v1/generate-lesson-plan-from-content` | 200 | 6842 | 013-generate-lesson-plan-from-content.json |
| 02:37:21 | GET | `/rest/v1/course_nodes` | 200 | 170 | 014-course_nodes.json |
| 02:37:21 | PATCH | `/rest/v1/course_nodes` | 204 | 180 | 015-course_nodes.txt |
| 02:37:22 | PATCH | `/rest/v1/lesson_sessions` | 204 | 196 | 017-lesson_sessions.txt |
| 02:37:22 | PATCH | `/rest/v1/lesson_plans` | 204 | 182 | 018-lesson_plans.txt |
| 02:37:13 | POST | `/functions/v1/generate-course-cover` | 200 | 10789 | 019-generate-course-cover.json |
| 02:37:24 | GET | `/rest/v1/projects` | 200 | 165 | 020-projects.json |
| 02:37:24 | PATCH | `/rest/v1/projects` | 200 | 132 | 021-projects.json |
| 02:37:24 | POST | `/functions/v1/generate-lesson` | 202 | 2812 | 022-generate-lesson.json |
| 02:37:22 | POST | `/functions/v1/generate-lesson-plan-from-content` | 200 | 17010 | 029-generate-lesson-plan-from-content.json |
| 02:37:39 | PATCH | `/rest/v1/lesson_plans` | 204 | 126 | 030-lesson_plans.txt |
| 02:37:39 | POST | `/functions/v1/generate-course-mind-map` | 200 | 5596 | 033-generate-course-mind-map.json |
| 02:38:04 | POST | `/functions/v1/lesson-podcast` | 202 | 2269 |  |
| 02:39:13 | GET | `/rest/v1/xp_events` | 200 | 198 |  |
| 02:39:13 | POST | `/rest/v1/rpc/get_own_streak_earn_back` | 200 | 201 |  |
| 02:39:13 | POST | `/rest/v1/rpc/get_global_review_preview` | 200 | 211 |  |
| 02:39:13 | GET | `/rest/v1/projects` | 200 | 225 | 044-projects.json |
| 02:39:13 | GET | `/rest/v1/projects` | 200 | 342 | 045-projects.json |
| 02:39:13 | GET | `/rest/v1/lesson_sessions` | 200 | 363 | 046-lesson_sessions.json |
| 02:39:13 | POST | `/rest/v1/rpc/set_course_learning_format` | 204 | 376 |  |
| 02:39:14 | GET | `/rest/v1/lesson_sessions` | 200 | 182 | 047-lesson_sessions.json |
| 02:39:14 | GET | `/rest/v1/lesson_sessions` | 200 | 274 | 049-lesson_sessions.json |
| 02:39:14 | GET | `/rest/v1/course_nodes` | 200 | 257 | 050-course_nodes.json |
| 02:39:13 | POST | `/functions/v1/backfill-project-path-order` | 200 | 626 |  |
| 02:39:14 | POST | `/functions/v1/lesson-progress` | 200 | 1058 | 051-lesson-progress.json |
| 02:39:32 | POST | `/rest/v1/rpc/get_course_learning_format` | 200 | 142 |  |
| 02:39:32 | GET | `/rest/v1/lesson_learning_formats` | 200 | 287 |  |
| 02:39:32 | GET | `/rest/v1/lesson_podcast_episodes` | 200 | 317 |  |
| 02:39:32 | GET | `/rest/v1/lesson_assessment_attempts` | 200 | 344 |  |
| 02:39:32 | GET | `/rest/v1/lesson_sessions` | 200 | 337 | 052-lesson_sessions.json |
| 02:39:32 | GET | `/rest/v1/practices` | 200 | 187 | 055-practices.json |
| 02:39:32 | POST | `/functions/v1/lesson-progress` | 200 | 944 | 056-lesson-progress.json |
| 02:39:32 | POST | `/functions/v1/lesson-video` | 200 | 2204 |  |
| 02:39:55 | POST | `/rest/v1/rpc/set_course_learning_format` | 204 | 138 |  |
| 02:39:56 | GET | `/rest/v1/lesson_sessions` | 200 | 175 | 058-lesson_sessions.json |
| 02:39:56 | POST | `/functions/v1/lesson-progress` | 200 | 1056 | 060-lesson-progress.json |
| 02:39:57 | GET | `/rest/v1/knowledge_cards` | 200 | 211 |  |
| 02:39:57 | GET | `/rest/v1/lesson_sessions` | 200 | 175 | 064-lesson_sessions.json |
| 02:39:57 | POST | `/functions/v1/generate-lesson` | 202 | 1022 | 065-generate-lesson.json |
| 02:39:57 | POST | `/functions/v1/generate-lesson` | 202 | 2047 | 066-generate-lesson.json |
| 02:40:58 | GET | `/rest/v1/lesson_sessions` | 200 | 136 | 094-lesson_sessions.json |
| 02:41:00 | GET | `/rest/v1/lesson_sessions` | 200 | 150 | 095-lesson_sessions.json |
| 02:41:02 | GET | `/rest/v1/lesson_sessions` | 200 | 136 | 096-lesson_sessions.json |
| 02:41:04 | GET | `/rest/v1/lesson_sessions` | 200 | 125 | 097-lesson_sessions.json |
| 02:41:06 | GET | `/rest/v1/lesson_sessions` | 200 | 130 | 098-lesson_sessions.json |
| 02:41:08 | GET | `/rest/v1/lesson_sessions` | 200 | 128 | 099-lesson_sessions.json |
| 02:41:10 | GET | `/rest/v1/lesson_sessions` | 200 | 145 | 100-lesson_sessions.json |
| 02:41:13 | GET | `/rest/v1/lesson_sessions` | 200 | 146 | 101-lesson_sessions.json |

## Redactions and what is not here

- The account email, the account name and every database id were replaced: ids by stable
  placeholders (`<id-1>`, `<id-2>`...) so links between files still line up, the email by
  `<email>`, the name by `<name>`. The account chip and the email line are covered in the
  screenshots.
- `archive/` holds the **unredacted** originals, committed at the owner's request on 2026-11-05:
  - `wondering-full-record-2026-11-05.zip`: raw network captures and responses, the full REA page
    capture, Wondering's JavaScript as served to the browser, original screenshots, tools.
  - `session-workspace-2026-11-05.zip`: everything else produced in the session (probe scripts,
    patches, browser and server logs, the REA setup plan, all background test-run outputs).
  Both contain the account email and ids and a competitor's code: keep this repository private.
  Left out on purpose: the browser profile (cookies and cache) and the downloaded REA package
  (reinstall with `npx -y rea-agents@6.8.0`).
- `static/script-manifest.json` lists each script's address and checksum.
- Not observed: Wondering's server code, prompts, models, validators and retry logic. Their
  terms of service may restrict automated access; this was one light, read-only session on the
  owner's own account.
