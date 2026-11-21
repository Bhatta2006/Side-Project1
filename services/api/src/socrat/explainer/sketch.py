"""Declarative sketches: the model writes data, the host owns every line of code that runs.

Master prompt 5 and 14: never run model-written JavaScript in the learner's browser. A sketch spec
is JSON: a title, a summary, and one to three *variants* (what an input choice selects), each a
list of steps with a short note and a ``Sketch`` scene (rows, links, pointers, focus; see
``kit.js``). ``check`` validates it, including that every id a link, pointer or focus names exists
in the same scene, and ``page`` builds the document from fixed host code plus the data, exactly as
3D films do (``film.py``). The model computes the steps itself, so traces are as reliable as its
arithmetic: the review pass and the browser check still run, and the accuracy label stays.

Spec:
    {"title", "desc", "summary",
     "input": {"label", "options": [str, ...]}  (optional, one per variant),
     "variants": [{"steps": [{"note", "scene": {"rows", "links"?, "pointers"?, "focus"?}}]}]}
"""

from __future__ import annotations

import html
import json
import re
from typing import NoReturn

from socrat.explainer.artifact import ArtifactError

MAX_VARIANTS = 3
MAX_STEPS = 40
MAX_ROWS = 6
MAX_ITEMS = 16
MAX_LINKS = 12
STATES = {"", "active", "hit", "done", "dim"}
TONES = {"pen", "primary", "ink", "muted"}
ROW_ID = re.compile(r"[A-Za-z][\w-]{0,23}")


def _fail(message: str) -> NoReturn:
    raise ArtifactError(message)


def _text(value, field: str, low: int, high: int) -> str:
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        _fail(f"{field} must be text of {low} to {high} characters")
    return value.strip()


def parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text)
    start = text.find("{")
    try:
        # The first complete object: a model sometimes runs on past its closing brace (measured
        # 2026-11-21: Gemini appended stray words after a finished sketch), which is not part
        # of the sketch and must not cost a repair round trip.
        spec, _ = json.JSONDecoder().raw_decode(text, max(start, 0))
    except json.JSONDecodeError as exc:
        _fail(f"The sketch must be one JSON object; it did not parse ({exc.msg} at {exc.pos})")
    if not isinstance(spec, dict):
        _fail("The sketch must be one JSON object")
    return spec


def normalize(spec: dict) -> dict:
    """Fix slips that change nothing a learner reads, so they do not cost a repair round trip:
    an unknown tone or state falls back to the default, and a link label longer than three
    characters is dropped (the link stays). Anything that carries meaning is left for check."""
    for variant in spec.get("variants") or []:
        for step in (variant.get("steps") or []) if isinstance(variant, dict) else []:
            scene = step.get("scene") if isinstance(step, dict) else None
            if not isinstance(scene, dict):
                continue
            for row in scene.get("rows") or []:
                for item in (row.get("items") or []) if isinstance(row, dict) else []:
                    if isinstance(item, dict) and item.get("state", "") not in STATES:
                        item["state"] = ""
                    if isinstance(item, dict) and isinstance(item.get("text"), int | float):
                        item["text"] = f"{item['text']:g}"
            for mark in [*(scene.get("links") or []), *(scene.get("pointers") or [])]:
                if isinstance(mark, dict) and mark.get("tone", "pen") not in TONES:
                    mark.pop("tone")
            for link in scene.get("links") or []:
                if isinstance(link, dict) and len(str(link.get("label", ""))) > 3:
                    link.pop("label")
    return spec


def _scene_ids(scene: dict, where: str) -> set[str]:
    rows = scene.get("rows")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        _fail(f"{where}.scene.rows needs 1 to {MAX_ROWS} rows")
    ids: set[str] = set()
    seen_rows: set[str] = set()
    for r, row in enumerate(rows):
        if not isinstance(row, dict):
            _fail(f"{where}.scene.rows[{r}] must be an object")
        rid = row.get("id")
        if not isinstance(rid, str) or not ROW_ID.fullmatch(rid) or rid in seen_rows:
            _fail(f'{where}.scene.rows[{r}].id must be a unique short word without "." or "#"')
        seen_rows.add(rid)
        if "label" in row:
            _text(row["label"], f"{where}.scene.rows[{r}].label", 1, 24)
        if row.get("kind", "") not in ("", "bars"):
            _fail(f"{where}.scene.rows[{r}].kind is 'bars' or absent")
        items = row.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
            _fail(f"{where}.scene.rows[{r}].items needs 1 to {MAX_ITEMS} items")
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                _fail(f"{where}.scene.rows[{r}].items[{i}] must be an object")
            _text(str(item.get("text", "")), f"{where}.scene.rows[{r}].items[{i}].text", 1, 18)
            if item.get("state", "") not in STATES:
                _fail(f"{where}...items[{i}].state is one of {sorted(STATES)}")
            if row.get("kind") == "bars" and not isinstance(item.get("value"), int | float):
                _fail(f"{where}.scene.rows[{r}] is 'bars': every item needs a numeric value")
            key = f"{rid}.{item['id']}" if isinstance(item.get("id"), str) else f"{rid}.{i}"
            ids.add(key)
            chips = item.get("chips", [])
            if not isinstance(chips, list) or len(chips) > 8:
                _fail(f"{where}...items[{i}].chips is a list of at most 8")
            for c in range(len(chips)):
                ids.add(f"{key}#{c}")
    return ids


def _scene(scene, where: str) -> None:
    if not isinstance(scene, dict):
        _fail(f"{where}.scene must be an object")
    ids = _scene_ids(scene, where)
    links = scene.get("links", [])
    if not isinstance(links, list) or len(links) > MAX_LINKS:
        _fail(f"{where}.scene.links is a list of at most {MAX_LINKS}")
    for n, link in enumerate(links):
        if not isinstance(link, dict) or link.get("from") not in ids or link.get("to") not in ids:
            _fail(f"{where}.scene.links[{n}] must join two ids from this scene, like 'row.0'")
        if len(str(link.get("label", ""))) > 3 or link.get("tone", "pen") not in TONES:
            _fail(
                f"{where}.scene.links[{n}]: label at most 3 characters, tone one of {sorted(TONES)}"
            )
    pointers = scene.get("pointers", [])
    if not isinstance(pointers, list) or len(pointers) > 6:
        _fail(f"{where}.scene.pointers is a list of at most 6")
    for n, p in enumerate(pointers):
        if not isinstance(p, dict) or p.get("at") not in ids:
            _fail(f"{where}.scene.pointers[{n}].at must name an item in this scene")
        _text(str(p.get("text", "")), f"{where}.scene.pointers[{n}].text", 1, 8)
    focus = scene.get("focus", [])
    if not isinstance(focus, list) or len(focus) > 2 or any(f not in ids for f in focus):
        _fail(f"{where}.scene.focus is at most 2 ids that exist in this scene")


NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    """The numbers written in a text, normalised ("1,000" and "1000.0" are both "1000")."""
    out = set()
    for raw in NUMBER.findall(text):
        number = float(raw.replace(",", ""))
        out.add(str(int(number)) if number == int(number) else f"{number:g}")
    return out


def _visible(scene: dict | None) -> str:
    """Every piece of text a scene shows: labels, item texts and values, chips, pointers, links."""
    if not scene:
        return ""
    parts: list[str] = []
    for row in scene.get("rows", []):
        parts.append(str(row.get("label", "")))
        for item in row.get("items", []):
            parts += [str(item.get("text", "")), str(item.get("value", ""))]
            for chip in item.get("chips", []):
                parts.append(str(chip.get("text", "")) if isinstance(chip, dict) else str(chip))
    parts += [str(p.get("text", "")) for p in scene.get("pointers", [])]
    parts += [str(link.get("label", "")) for link in scene.get("links", [])]
    return " ".join(parts)


def _accuracy(spec: dict, request: str) -> None:
    """Deterministic checks that a trace agrees with itself. The model computes the trace, so
    these catch its slips before a learner does: every step changes the drawing, a bar's
    printed number is its height, and every number a note states is on the sheet (now or one
    step back) or in the request. Small whole numbers pass: they can be positions or counts."""
    known = _numbers(" ".join([request, spec["title"], str(spec.get("desc", ""))]))
    variants = spec["variants"]
    for v, variant in enumerate(variants):
        steps = variant["steps"]
        width = max(len(row["items"]) for step in steps for row in step["scene"]["rows"])
        option = spec["input"]["options"][v] if len(variants) > 1 else ""
        previous: dict | None = None
        for s, step in enumerate(steps):
            where = f"variants[{v}].steps[{s}]"
            scene = step["scene"]
            if previous is not None and scene == previous:
                _fail(f"{where}.scene draws the same as the step before; every step must change it")
            for r, row in enumerate(scene["rows"]):
                if row.get("kind") != "bars":
                    continue
                for i, item in enumerate(row["items"]):
                    printed = _numbers(str(item.get("text", "")))
                    value = float(item["value"])
                    # A rounded height is fine ("$1,464.10" on a bar of 1464); a different one is not.
                    if len(printed) == 1 and abs(float(next(iter(printed))) - value) > max(
                        0.5, abs(value) * 0.005
                    ):
                        _fail(
                            f"{where}.scene.rows[{r}].items[{i}] prints {item['text']!r} but its "
                            f"bar value is {item['value']}; make them agree"
                        )
            shown = _numbers(_visible(scene) + " " + _visible(previous) + " " + option)
            for number in sorted(_numbers(step["note"]) - shown - known):
                if number.isdigit() and int(number) <= max(width, 10):
                    continue
                _fail(
                    f"{where}.note says {number}, which is not in its scene or the step before. "
                    "Recheck the arithmetic: every value in a note must match the drawing"
                )
            previous = scene


def check(spec: dict, request: str = "") -> dict:
    """Validate a sketch spec; messages name the field so the model can repair it.

    ``request`` is the learner's question: a number it gives may appear in any note."""
    _text(spec.get("title"), "title", 2, 140)
    _text(spec.get("desc", spec.get("title")), "desc", 2, 200)
    _text(spec.get("summary"), "summary", 100, 700)
    variants = spec.get("variants")
    if not isinstance(variants, list) or not 1 <= len(variants) <= MAX_VARIANTS:
        _fail(f"variants needs 1 to {MAX_VARIANTS} entries")
    choice = spec.get("input")
    if len(variants) > 1:
        if not isinstance(choice, dict):
            _fail("several variants need an input: {label, options} with one option per variant")
        _text(choice.get("label"), "input.label", 2, 40)
        options = choice.get("options")
        if not isinstance(options, list) or len(options) != len(variants):
            _fail("input.options needs exactly one option per variant")
        for n, o in enumerate(options):
            _text(o, f"input.options[{n}]", 1, 40)
    for v, variant in enumerate(variants):
        steps = variant.get("steps") if isinstance(variant, dict) else None
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            _fail(f"variants[{v}].steps needs 1 to {MAX_STEPS} steps")
        notes = []
        for s, step in enumerate(steps):
            where = f"variants[{v}].steps[{s}]"
            if not isinstance(step, dict):
                _fail(f"{where} must be an object")
            notes.append(_text(step.get("note"), f"{where}.note", 3, 160))
            _scene(step.get("scene"), where)
        if len(steps) > 1 and len(set(notes)) < len(notes):
            _fail(f"variants[{v}]: every step needs its own note saying what changed")
    if len(variants) == 1 and len(variants[0]["steps"]) < 2:
        _fail("Give the one variant at least 2 steps (or add a second variant to choose)")
    if len(variants) > 1 and len({o.strip().lower() for o in choice["options"]}) < len(variants):
        _fail("input.options must all differ: each one picks its own variant")
    _accuracy(spec, request)
    return spec


PLAYER = """
const board=Sketch.mount('#board',{desc:SPEC.desc||SPEC.title});
const note=document.getElementById('note'),pick=document.getElementById('variant'),scrub=document.getElementById('scrub');
let variant=0,step=0;
const steps=()=>SPEC.variants[variant].steps;
function render(){const s=steps()[step];board.draw(s.scene);note.textContent=s.note;scrub.max=String(steps().length-1);scrub.value=String(step);scrub.setAttribute('aria-valuetext','Step '+(step+1)+' of '+steps().length);}
window.__explainer={describe(){return note.textContent},get stepCount(){return steps().length},get currentStep(){return step},step(i){step=Math.max(0,Math.min(steps().length-1,i));render()},reset(){variant=0;if(pick)pick.value='0';step=0;render()}};
if(pick)pick.addEventListener('change',()=>{variant=Number(pick.value)||0;step=0;render()});
scrub.addEventListener('input',()=>{step=Math.max(0,Math.min(steps().length-1,Number(scrub.value)||0));render()});
render();
"""

STYLE = (
    # The app's own look, kept quiet: its sans font, card and border tokens, no handwriting,
    # ruled lines or hard shadows (owner, 2026-11-21).
    ":root,:root body{background:var(--card)}"  # it sits in the app's card: no second backdrop
    "main{max-width:760px;margin:0 auto}"
    "h1{font-size:22px;font-weight:600;line-height:1.3;margin:0 0 4px}"
    ".note{font-size:16px;color:var(--foreground);min-height:3.1em;margin:4px 0 12px}"
    ".sheet{background:var(--card);border:1px solid var(--border);"
    "border-radius:var(--radius,12px);padding:12px}"
    ".controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end;margin-top:12px}"
    ".controls label{display:grid;gap:4px;font-size:14px;color:var(--muted-foreground)}"
    ".controls input{accent-color:var(--primary);min-width:180px}"
    ".controls select{border:1px solid var(--border);border-radius:8px;"
    "background:var(--card);color:var(--foreground);padding:0 12px}"
    "#transcript{font-size:15px;color:var(--muted-foreground)}"
    "#transcript h2{font-size:16px;font-weight:600;color:var(--foreground);margin:0 0 4px}"
)


def page(spec: dict) -> str:
    """The host-owned document that plays a checked sketch: fixed code, the spec as data."""
    escape = html.escape
    data = json.dumps(spec, ensure_ascii=False, separators=(",", ":"))
    # Inside <script> a "</" could end the element; \\u003c is the same character in JSON.
    data = data.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    # The step slider is always there (host code), so every sketch has an input that moves it.
    picker = ""
    if len(spec["variants"]) > 1:
        options = "".join(
            f'<option value="{n}">{escape(o.strip())}</option>'
            for n, o in enumerate(spec["input"]["options"])
        )
        picker = (
            f'<label for="variant">{escape(spec["input"]["label"].strip())}'
            f'<select id="variant">{options}</select></label>'
        )
    last = len(spec["variants"][0]["steps"]) - 1
    controls = (
        f'<div class="controls">{picker}<label for="scrub">Step'
        f'<input id="scrub" type="range" min="0" max="{last}" step="1" value="0"></label></div>'
    )
    title = escape(spec["title"].strip())
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title><style>{STYLE}</style></head><body><main>"
        f"<h1>{title}</h1>"
        '<p id="note" class="note" role="status"></p>'
        f'<section id="visual" aria-label="{escape(str(spec.get("desc") or spec["title"]).strip())}" '
        'class="sheet"><div id="board"></div></section>'
        f"{controls}"
        f'<section id="transcript"><h2>In short</h2><p>{escape(spec["summary"].strip())}</p></section>'
        f"</main><script>const SPEC={data};{PLAYER}</script></body></html>"
    )
