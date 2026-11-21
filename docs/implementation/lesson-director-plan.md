# Lesson director plan: maths, interactive lessons, generated images, Gemini speech

Written 2026-11-21 after the owner's review: generated lessons show raw LaTeX, and read like a
textbook (text only, no interaction, no pictures). Facts below cite files as of that date.

## 1. Maths shows as raw LaTeX

Causes (all confirmed in code):

1. `apps/web/src/components/markdown.tsx` is a hand-written renderer with no maths support and
   no KaTeX/MathJax dependency: `$$...$$` and `$...$` print as text.
2. Its `INLINE` regex reads `_..._` and `*...*` as emphasis inside maths:
   `\sigma_{\text{origin}} ... \text{available\_seats}` became italics with its underscores eaten.
3. The `LESSON` prompt (`coursegen/package.py`) gives no maths convention, so the model mixes
   delimiters. `learn/sections.py` already assumes `$$...$$` for the Formulas section.
4. Latent: lessons arrive as JSON, where `\f \b \n \r \t` are escapes. `\frac`, `\beta`, `\nabla`,
   `\rho`, `\theta` written with one backslash are silently corrupted by `json.loads`.

Fix (step 1, done in the same change as this file):
- Web: `katex`; display maths as a block, inline maths tokenised before emphasis; same in
  `codeSpans` (quiz prompts). Bad TeX falls back to its source, never throws.
- Prompt: one maths rule shared by the lesson, quiz and atom authors.
- `roles.parse_json`: a single backslash before a known LaTeX command is doubled before parsing.
- `check_lesson`: unbalanced `$$` is a lesson issue.

## 2. Why lessons read like a textbook

Generation is already one job per lesson (`coursegen/jobs.run_package`), not per module. Inside a
job, one author call writes the whole lesson as one Markdown essay (up to 16k tokens), then quiz
and atoms, then fact checker and reviewer, then the Experience Designer.

What exists but is off or thin:
- Experience Designer (`engine/design.py`): `gen_visuals=False` by default, at most 2 visuals,
  sees `lesson[:6000]`, and its visuals are placed after the text, not inside it.
- Renderer registry (`engine/renderers.py`): typed manifests with Pydantic params, validated by
  code. Only 8 renderers.
- Lesson images (`learn/images.py`): off by default, search only (Commons, Openverse).
- `assistant/vertex.py`: `generate_image()` and `speak()` work (one live call each on 2026-11-20,
  `vertex-ai-handoff.md`) but nothing calls them.
- Listen: browser `speechSynthesis` (`apps/web/src/lib/speech.ts`).

## 3. The plan

### Step 2: inline embeds and more interactive components
- `:::embed N:::` markers in `Concept.lesson`; `markdown.tsx` parses an `embed` block and the
  lesson page resolves it to `visuals[N]`. Reuses `visuals`, `sequence`, `LessonPages`.
- Raise `Concept.visuals` max length (4) and `design.MAX_VISUALS` (2).
- New renderers, each one Pydantic params class plus one React component in `VisualizationHost`:
  predict-then-reveal, step-through worked example, drag-to-order, sort-into-buckets,
  fill-in-the-blank, matching, hotspot-on-image, flashcard. Every one keeps `fallback_text`.

### Step 3: lesson director and specialists (flag `gen_lesson_director`, default off)
- Director: one call returns a blueprint of 6-12 beats
  `{id, kind: text|interactive|image|check, objective, misconception, learner_hook, brief}`.
  Code checks it: every objective and misconception covered, an interaction at least every two
  text beats, kinds allowed by the course shape and adapter, every beat names the onboarding
  detail it uses (`Brief.learner`, `learner_plan.data_block`, `learner_hook.lesson_block`).
- Text writer: all text beats in one call (one voice, one set of example values). Runs first.
- Interactive builder (parallel, per beat): its brief, the neighbouring text beats, the registry
  with param schemas, the learner summary. Specs go through `renderers.validate_spec`; a bad
  spec is dropped and its fallback text used.
- Image specialist (parallel, per beat): prompt from the beat and the learner's context, calls
  `vertex.generate_image`. No image whose correctness depends on text drawn in it; a Gemini
  vision check that the image matches its caption or it is dropped; real-world things prefer a
  Commons picture. Storage: GCS bucket or an additive table with a tested downgrade.
- Stitch: code assembles the embeds; one editor call smooths transitions (text beats only);
  the existing fact checker and reviewer see the whole package.
- Benchmark against the current flow on the same concepts (cost, latency, reviewer scores,
  dropped specs) before turning it on. Set `vertex_image_price_usd` to the real price first:
  courses are private, so generated images are not shared, and the default 0 never blocks.

### Step 4: generated images (as above), first a live probe with lesson-style prompts.

### Step 5: Gemini speech
- `GET /api/v1/learn/{concept}/audio?page=N`: page text without Markdown, display maths skipped
  or spoken, `vertex.speak`, cached by concept version + page + voice. Style prompt from the
  learner's pace.
- `listen.tsx` plays it, falls back to the browser voice when off or failed.
- WAV is about 48 KB/s: encode to Opus/MP3 (needs ffmpeg on the VM).

## 4. Not verified
Nothing in steps 2-5 is built. Step 1 is covered by unit tests only; no live generation run.
