# Vertex AI (Gemini) integration: handoff

Written 2026-11-20. Read `HANDOFF.md` first for the repo rules; this file covers only the Vertex layer.
State: code written and tested offline, **not committed** (it sits in the working tree on `gbuild/main`),
no feature uses it yet. Nothing changes unless a Vertex key and `SOCRAT_AI_PROVIDER=vertex` are set.

## 1. What exists

`services/api/src/socrat/assistant/vertex.py` is the one place that talks to Vertex, through the
official `google-genai` SDK (added to `pyproject.toml`; lockfiles not yet updated).

| Piece | Use it for |
|---|---|
| `VertexProvider` | Text, streaming and tool calls. Implements the same `Provider` protocol as the Anthropic and OpenAI providers, so every existing call site gets Gemini by config. Chosen by `make_provider` when `ai_provider == "vertex"`. |
| `generate_image(settings, prompt, aspect_ratio=, reference_images=, engine=, user_id=, feature=)` | One image, optionally edited from reference images. Returns `Media(data, mime, model)`. |
| `speak(settings, text, voice=, engine=, user_id=, feature=)` | Spoken audio as WAV (headerless PCM replies are wrapped). Returns `Media`. |

All three share one client (`make_client`), the kill switch (`SOCRAT_AI_ENABLED`), and one error vocabulary:
`ProviderError` with `provider_offline`, `provider_rate_limited`, `provider_http_<code>`,
`provider_unreachable`, `provider_empty_reply` (safety block or text-only reply). Provider messages are
never echoed. Pass `engine` (and `user_id` when a learner caused the call) to `generate_image` and `speak`
to have them budget-checked and recorded in `AIUsage`; text calls are metered by the existing `Metered`
wrapper and `coursegen.roles.ask`.

Small edits elsewhere: `config.py` (settings, validator), `assistant/gateway.py` (`make_provider`),
`assistant/budget.py` (`record(cost_usd=)` flat price, `model_name` for vertex), `coursegen/roles.py`
(role `model` key also sets `vertex_model`; JSON mode for vertex), `.env.example`.

## 2. Turn it on

```env
SOCRAT_AI_PROVIDER=vertex
SOCRAT_VERTEX_MODEL=gemini-3.8-flash         # required for the text provider
SOCRAT_VERTEX_PROJECT=<gcp project id>
SOCRAT_VERTEX_LOCATION=global                # default
# key: VERTEX_AI_MAIN_GEMINI_API (the owner's .env name) or SOCRAT_VERTEX_API_KEY, or
# SOCRAT_VERTEX_API_KEY_FILE. Never put a key in .env.example or a commit.
SOCRAT_AI_PRICE_INPUT_PER_MTOK=...           # still default to 3 / 15: set Gemini's real prices
SOCRAT_AI_PRICE_OUTPUT_PER_MTOK=...
```

Images and speech need only the key (the provider setting is for text). Optional settings:
`SOCRAT_VERTEX_IMAGE_MODEL`, `SOCRAT_VERTEX_TTS_MODEL`, `SOCRAT_VERTEX_TTS_VOICE`,
`SOCRAT_VERTEX_IMAGE_PRICE_USD` and `SOCRAT_VERTEX_TTS_PRICE_USD` (flat per call, default 0, so metering
counts but never blocks), `SOCRAT_VERTEX_THINKING_LEVEL` (`minimal|low|medium|high`, default is the model's),
`SOCRAT_VERTEX_JSON_MODE` (ask for `application/json` on course-generation calls, default off).

Mixing providers per role: `SOCRAT_GEN_ROLES='{"critic": {"provider": "vertex", "model": "gemini-3.8-flash"}}'`
or per tier, `SOCRAT_GEN_TIERS='{"strong": {"provider": "vertex", "model": "gemini-3.1-pro-preview"}}'`.
Any role or tier that still says `"provider": "openai"` keeps using OpenAI, and `SOCRAT_OPENAI_*` is
ignored for roles on vertex. The tutor stays off until `SOCRAT_TUTOR_MODEL_ENABLED` and its rollout change.

## 3. Verified on 2026-11-20 (live key, project `the-signal-452716-u7`, location `global`)

Model ids that answered: `gemini-3.1-pro-preview`, `gemini-3.8-flash` (text); `gemini-3.1-flash-image`
(Nano Banana 2) and `gemini-3.1-flash-lite-image` (images); `gemini-3.8-flash-lite-tts`,
`gemini-3.8-flash-tts`, `gemini-3.1-flash-tts-preview` (speech, voice `Kore`).
Through the layer itself: one text reply, one tool-calling round trip (call, result, final answer),
one image (JPEG) and one speech clip (WAV). Sample outputs are in `tmp-gemini-out/` (not tracked: delete
it or keep it out of commits).
Tests: `services/api/tests/test_vertex.py`, 12 tests, no network (a fake client stands in). They and the
existing gateway and budget tests pass; ruff clean; mypy clean for the new code.

## 4. Not verified, and gotchas

- **Never run:** a full course generation, `scripts/dev/benchmark.py`, the tutor, or any real feature on
  Gemini. The course prompts are tuned for the OpenAI-compatible models; benchmark before relying on them.
  Only short prompts were tried, so quality, latency, rate limits and credit burn are unknown.
- **Not found:** `gemini-4-hydrogen` exists on `global` but returned `429 RESOURCE_EXHAUSTED` on four tries
  (quota or capacity; cause unknown). No id found for "Nano Banana 2.1". Wrong ids return 404; the model
  list call needs OAuth and does not work with a key.
- **Region:** an earlier probe without a project resolved to `asia-southeast1`, where `gemini-2.5-flash` and
  some image ids were 404. Keep `SOCRAT_VERTEX_LOCATION=global` unless a model needs a region.
- **Thinking tokens** count against `max_output_tokens` (about 80 on a trivial prompt). They are counted as
  output for metering, but a small budget can truncate a JSON reply; raise it or set a thinking level.
  Gemini 3 needs the model's own parts, including thought signatures, replayed between tool rounds; the
  provider does this.
- **Key settings** accept only the alias names (`socrat_vertex_api_key`, `vertex_ai_main_gemini_api`) when
  built in code or tests; `vertex_api_key=` as a keyword is silently ignored. If both aliases are present
  the first wins, even when empty.
- **Mypy:** one error remains in `learn/images.py` that is not part of this work. Two tests in
  `test_model_tiers.py` error with "missing tests for village-sentries" (content catalog); not checked
  whether they fail without these changes.
- **Lockfiles** (`uv.lock`, `requirements.lock.txt`) do not yet list `google-genai`; regenerate before CI.
- **Image and speech pricing** are flat guesses you must set; there is no per-token pricing for them.
- On this machine run tests from the repo root with `--basetemp` pointing at a folder you own.

## 5. Next steps, in order

1. Decide the branch and commit (stage specific paths only; `tmp-gemini-out/` and any `.env` stay out).
2. Regenerate lockfiles; run the full API suite.
3. Set Gemini's real prices; run `scripts/dev/benchmark.py` on `vertex`, then try a cheap tier split
   (flash for fast roles, pro for the strong tier).
4. Wire one feature to the capabilities behind a flag, default off (candidates: lesson narration with
   `speak`; lesson visuals in `learn/images.py` with `generate_image`). Add `engine` and `user_id` so it is metered.
5. Retry `gemini-4-hydrogen` later; find the Nano Banana 2.1 id in the Vertex Model Garden.
6. Consider Application Default Credentials for production instead of an API key (the client takes
   `credentials=`); not built.
