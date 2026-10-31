"""3D films: the model writes a declarative film (JSON); the host validates it and owns the page.

A film is one assembly (parts), its callouts (labels), continuous motions and flows, and chapters
that act as keyframes. Clicky3D.film() plays it. Every message raised here is written for the
model's repair turn: it names the field and says what to do.
"""

from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

from socrat.explainer.artifact import ArtifactError

_GEOMETRY = (Path(__file__).parent / "clicky3d-geometry.js").read_text(encoding="utf-8")
_SHAPES = re.search(r"const SHAPES = \{(.*?)\};", _GEOMETRY, re.S)
KINDS = {
    name.strip().split(":")[0].strip()
    for name in (_SHAPES.group(1) if _SHAPES else "").replace("\n", " ").split(",")
    if name.strip()
} | {"group"}
MATERIALS = set(
    "steel alu aluminum aluminium titanium chrome brass copper gold iron black rubber glass water "
    "wood ceramic paper gloss paint plastic soft matte metal glow".split()
)
MOTION_TYPES = {"spin", "slide", "swing"}
TONES = {"primary", "pen", "muted"}
ID = re.compile(r"[A-Za-z][\w-]{0,47}")
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}|[a-z]{3,20}")
MAX_PARTS = 140
MAX_CHAPTERS = 10


def _fail(message: str):
    raise ArtifactError(message)


def _text(value, field: str, low: int, high: int) -> str:
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        _fail(f"{field} must be text of {low}-{high} characters")
    return value.strip()


def _number(value, field: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _fail(f"{field} must be a number")
    if not low <= value <= high:
        _fail(f"{field} must be between {low:g} and {high:g}")
    return float(value)


def _vector(value, field: str, limit: float = 50) -> None:
    if not (isinstance(value, list) and len(value) == 3):
        _fail(f"{field} must be [x, y, z]")
    for k, item in enumerate(value):
        _number(item, f"{field}[{k}]", -limit, limit)


def _numbers_finite(value, path: str = "film") -> None:
    """Every number anywhere in the film is finite and sane (recipes are free-form)."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(value) or abs(value) > 1e5:
            _fail(f"{path} has an invalid number")
        return
    if isinstance(value, list):
        for k, item in enumerate(value[:4000]):
            _numbers_finite(item, f"{path}[{k}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _numbers_finite(item, f"{path}.{key}")


def parse(raw: str) -> dict:
    """The model's reply as a film object (tolerating a Markdown fence or stray prose)."""
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        _fail("Return the film as one JSON object, starting with { and ending with }")
    try:
        film = json.loads(
            text[start : end + 1],
            parse_constant=lambda name: _fail(f"JSON must not contain {name}"),
        )
    except json.JSONDecodeError as exc:
        _fail(f"The film is not valid JSON ({exc.msg} at line {exc.lineno}, column {exc.colno})")
    if not isinstance(film, dict):
        _fail("The film must be a JSON object")
    return film


def _slug(value: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", value).strip("-_")[:48] or "part"
    return slug if slug[0].isalpha() else "p-" + slug[:46]


def rename_ids(film: dict) -> dict[str, str]:
    """Turn part ids like "brake pad" or "wheel.front" into valid slugs, everywhere they are used.

    A dot is reserved for copies ("rotor.3"), so a dotted id the author declared is renamed too.
    """
    parts = [p for p in film.get("parts", []) if isinstance(p, dict)]
    taken = {p["id"] for p in parts if isinstance(p.get("id"), str) and ID.fullmatch(p["id"])}
    renamed: dict[str, str] = {}
    for p in parts:
        pid = p.get("id")
        if not isinstance(pid, str) or not pid.strip() or ID.fullmatch(pid):
            continue
        new, n = _slug(pid), 2
        while new in taken:
            new, n = f"{_slug(pid)[:44]}-{n}", n + 1
        taken.add(new)
        renamed[pid] = p["id"] = new
    if not renamed:
        return renamed

    def ref(value):
        if not isinstance(value, str):
            return value
        if value in renamed:
            return renamed[value]
        base, dot, copy = value.rpartition(".")
        return f"{renamed[base]}.{copy}" if dot and base in renamed and copy.isdigit() else value

    for p in parts:
        if "parent" in p:
            p["parent"] = ref(p["parent"])
        if isinstance(p.get("on"), dict) and "part" in p["on"]:
            p["on"]["part"] = ref(p["on"]["part"])
    for item in film.get("labels", []) + film.get("motions", []):
        if isinstance(item, dict) and "part" in item:
            item["part"] = ref(item["part"])
    for flow in film.get("flows", []):
        if isinstance(flow, dict) and "parent" in flow:
            flow["parent"] = ref(flow["parent"])
    for chapter in film.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for key in ("focus", "hide"):
            if isinstance(chapter.get(key), list):
                chapter[key] = [ref(v) for v in chapter[key]]
        if isinstance(chapter.get("camera"), dict) and "target" in chapter["camera"]:
            chapter["camera"]["target"] = ref(chapter["camera"]["target"])
        if isinstance(chapter.get("pose"), dict):
            chapter["pose"] = {ref(k): v for k, v in chapter["pose"].items()}
    return renamed


def check(film: dict) -> dict:
    """Validate a film against the player's contract; returns it unchanged."""
    _numbers_finite(film)
    _text(film.get("title"), "title", 4, 90)
    _text(film.get("summary"), "summary", 100, 900)
    _text(film.get("desc", "A 3D model"), "desc", 3, 200)

    parts = film.get("parts")
    if not isinstance(parts, list) or not 3 <= len(parts) <= MAX_PARTS:
        _fail(f"parts must list 3-{MAX_PARTS} parts")
    rename_ids(film)
    ids: set[str] = set()
    for k, part in enumerate(parts):
        where = f"parts[{k}]"
        if not isinstance(part, dict):
            _fail(f"{where} must be an object")
        pid = part.get("id")
        if not isinstance(pid, str) or not ID.fullmatch(pid):
            _fail(f"{where}.id must be a short id of letters, digits and dashes")
        if pid in ids:
            _fail(f"Duplicate part id {pid}; every part needs its own id")
        ids.add(pid)
        if part.get("kind") not in KINDS:
            _fail(
                f"{where}.kind {str(part.get('kind'))[:20]!r} is unknown; use one of {', '.join(sorted(KINDS))}"
            )
        if part.get("kind") != "group" and not isinstance(part.get("recipe", {}), dict):
            _fail(f"{where}.recipe must be an object")
        material = part.get("mat", part.get("material"))
        if isinstance(material, str) and material not in MATERIALS and COLOUR.fullmatch(material):
            # A colour written as a material ("green", "#3a7"): painted in that colour.
            part.pop("material", None)
            part.setdefault("color", material)
            part["mat"] = material = "paint"
        if material is not None and material not in MATERIALS:
            _fail(
                f"{where}.mat {str(material)[:20]!r} is unknown; use one of {', '.join(sorted(MATERIALS))}"
            )
        for key in ("at", "rot", "explode"):
            if key in part:
                _vector(part[key], f"{where}.{key}", 360 if key == "rot" else 50)
        if "apart" in part and not isinstance(part["apart"], bool):
            _fail(f"{where}.apart must be true or false")
        copies = part.get("copies")
        if copies is not None:
            _number(copies, f"{where}.copies", 1, 120)
        around = part.get("around")
        if around is not None:
            if not isinstance(around, dict):
                _fail(f"{where}.around must be an object")
            _number(around.get("count", 6), f"{where}.around.count", 1, 120)
    groups = {p["id"] for p in parts if p.get("kind") == "group"}
    for k, part in enumerate(parts):
        parent = part.get("parent")
        if parent is not None and parent not in ids:
            _fail(f"parts[{k}].parent {str(parent)[:48]!r} is not a part id")
        if parent == part["id"]:
            _fail(f"parts[{k}] cannot be its own parent")
    by_id = {p["id"]: p for p in parts}
    for k, part in enumerate(parts):
        on = part.get("on")
        if on is None:
            continue
        where = f"parts[{k}].on"
        if not isinstance(on, dict) or on.get("part") not in by_id or on.get("part") == part["id"]:
            _fail(f"{where}.part must name another part")
        target = by_id[on["part"]]
        if target.get("kind") == "group":
            _fail(f"{where}.part {on['part']!r} is a group; attach to a real shape")
        if target.get("parent") != part.get("parent"):
            _fail(f"{where}.part {on['part']!r} must have the same parent as {part['id']!r}")
        if on.get("face", "+y") not in {"+x", "-x", "+y", "-y", "+z", "-z", "inside"}:
            _fail(f"{where}.face must be +x, -x, +y, -y, +z, -z or inside")
        for key in ("align", "offset"):
            if key in on:
                _vector(on[key], f"{where}.{key}", 50)
        if "inset" in on:
            _number(on["inset"], f"{where}.inset", -1, 1)
    if len(groups) == len(parts):
        _fail("parts must include real shapes, not only groups")

    def part_ref(value, field: str) -> None:
        if not isinstance(value, str):
            _fail(f"{field} must be a part id")
        base = value.split(".")[0] if value not in ids else value
        if base not in ids:
            _fail(f"{field} {value[:48]!r} is not a part id (copies are id.0, id.1, ...)")

    labels = film.get("labels", [])
    if not isinstance(labels, list) or len(labels) > 12:
        _fail("labels must list at most 12 callouts")
    label_ids: set[str] = set()
    for k, label in enumerate(labels):
        where = f"labels[{k}]"
        if not isinstance(label, dict):
            _fail(f"{where} must be an object")
        _text(label.get("text"), f"{where}.text", 1, 28)
        if "note" in label:
            _text(label["note"], f"{where}.note", 1, 44)
        # The part card a learner opens by selecting the callout: required, so every labelled
        # part can be explored in the exploded view.
        _text(label.get("detail"), f"{where}.detail", 60, 420)
        part_ref(label.get("part"), f"{where}.part")
        if "anchor" in label:
            _vector(label["anchor"], f"{where}.anchor")
        if label.get("tone", "primary") not in TONES:
            _fail(f"{where}.tone must be primary, pen or muted")
        lid = str(label.get("id") or label.get("part"))
        if lid in label_ids:
            _fail(f"Two labels share the id {lid[:48]}; give each label its own id")
        label_ids.add(lid)

    runners: set[str] = set()
    motions = film.get("motions", [])
    if not isinstance(motions, list) or len(motions) > 24:
        _fail("motions must list at most 24 motions")
    for k, motion in enumerate(motions):
        where = f"motions[{k}]"
        if not isinstance(motion, dict):
            _fail(f"{where} must be an object")
        mid = motion.get("id")
        if not isinstance(mid, str) or not ID.fullmatch(mid) or mid in runners:
            _fail(f"{where}.id must be a unique short id")
        runners.add(mid)
        part_ref(motion.get("part"), f"{where}.part")
        if motion.get("type", "spin") not in MOTION_TYPES:
            _fail(f"{where}.type must be spin, slide or swing")
        if motion.get("type", "spin") == "spin":
            _number(motion.get("speed", 0.5), f"{where}.speed", -8, 8)
        else:
            _number(motion.get("period", 1), f"{where}.period", 0.1, 30)
    flows = film.get("flows", [])
    if not isinstance(flows, list) or len(flows) > 8:
        _fail("flows must list at most 8 flows")
    for k, flow in enumerate(flows):
        where = f"flows[{k}]"
        if not isinstance(flow, dict):
            _fail(f"{where} must be an object")
        fid = flow.get("id")
        if not isinstance(fid, str) or not ID.fullmatch(fid) or fid in runners:
            _fail(f"{where}.id must be a unique short id (not shared with a motion)")
        runners.add(fid)
        path = flow.get("path")
        if not isinstance(path, list) or not 2 <= len(path) <= 40:
            _fail(f"{where}.path must list 2-40 points")
        for j, point in enumerate(path):
            _vector(point, f"{where}.path[{j}]")
        if "parent" in flow:
            part_ref(flow["parent"], f"{where}.parent")
        _number(flow.get("count", 14), f"{where}.count", 1, 80)

    chapters = film.get("chapters")
    if not isinstance(chapters, list) or not 2 <= len(chapters) <= MAX_CHAPTERS:
        _fail(f"chapters must list 2-{MAX_CHAPTERS} chapters")
    if "show" not in chapters[0]:
        _fail('chapters[0] must set "show": the callouts visible at the start ([] for none)')
    says: set[str] = set()
    total = 0.0
    for k, chapter in enumerate(chapters):
        where = f"chapters[{k}]"
        if not isinstance(chapter, dict):
            _fail(f"{where} must be an object")
        _text(chapter.get("title"), f"{where}.title", 2, 40)
        say = _text(chapter.get("say"), f"{where}.say", 20, 240)
        if say in says:
            _fail(f"{where}.say repeats an earlier chapter; every chapter must say something new")
        says.add(say)
        total += _number(chapter.get("seconds", 6), f"{where}.seconds", 2, 20)
        for key in ("focus", "hide"):
            refs = chapter.get(key, [])
            if isinstance(refs, list):
                # A family name ("pistons", "pad") means every part named after it
                # (piston_left, piston_right); a name that matches nothing is dropped.
                resolved: list = []
                for value in refs:
                    if not isinstance(value, str) or value in ids or value.split(".")[0] in ids:
                        resolved.append(value)
                        continue
                    stem = value.lower().removesuffix("s")
                    resolved += [
                        pid for pid in ids if len(stem) >= 3 and pid.lower().startswith(stem)
                    ]
                chapter[key] = list(dict.fromkeys(resolved))
            for j, value in enumerate(chapter.get(key, []) or []):
                part_ref(value, f"{where}.{key}[{j}]")
        show = chapter.get("show", [])
        if isinstance(show, list):
            # Models often name the part instead of its callout: show that part's label. An id
            # that matches nothing just shows no callout, which is not worth a failed film.
            by_part = {
                str(label.get("part")).split(".")[0]: str(label.get("id") or label.get("part"))
                for label in labels
            }
            mapped = [
                value if value in label_ids else by_part.get(str(value).split(".")[0])
                for value in show
            ]
            chapter["show"] = list(dict.fromkeys(value for value in mapped if value))
        for j, value in enumerate(chapter.get("show", []) or []):
            if value not in label_ids:
                _fail(f"{where}.show[{j}] {str(value)[:48]!r} is not a label id")
        run = chapter.get("run", {})
        if not isinstance(run, dict):
            _fail(f"{where}.run must map motion or flow ids to speeds")
        for key, value in run.items():
            if key not in runners:
                _fail(f"{where}.run names {key[:48]!r}, which is not a motion or flow id")
            _number(value, f"{where}.run.{key}", -4, 4)
        pose = chapter.get("pose", {})
        if not isinstance(pose, dict):
            _fail(f"{where}.pose must map part ids to {{at, rot, scale}}")
        for key, value in pose.items():
            part_ref(key, f"{where}.pose key")
            if not isinstance(value, dict):
                _fail(f"{where}.pose.{key} must be {{at, rot, scale}}")
            for field in ("at", "rot"):
                if field in value:
                    _vector(
                        value[field], f"{where}.pose.{key}.{field}", 360 if field == "rot" else 50
                    )
        camera = chapter.get("camera", {})
        if not isinstance(camera, dict):
            _fail(f"{where}.camera must be an object")
        target = camera.get("target")
        if isinstance(target, str):
            part_ref(target, f"{where}.camera.target")
        elif target is not None:
            _vector(target, f"{where}.camera.target")
        if "explode" in chapter:
            _number(chapter["explode"], f"{where}.explode", 0, 2)
        if "cut" in chapter and not isinstance(chapter["cut"], bool):
            _number(chapter["cut"], f"{where}.cut", 0, 1)
    if total > 120:
        _fail("The film runs over 120 seconds; shorten chapters")
    orient(film)
    return film


# Round kinds are built about +Y. A model that forgets recipe.axis gets wheels lying flat and
# pens standing on end, although the film itself says which way the part really turns.
ROUND = {"cyl", "cylinder", "cone", "tube", "lathe", "torus", "capsule", "spring", "gear", "rotor"}
ROUND |= {"tire", "rim"}
ELONGATED = {"cyl", "cylinder", "cone", "tube", "lathe", "capsule", "spring"}
AXES = {"x", "-x", "y", "-y", "z", "-z", "+x", "+y", "+z"}


def orient(film: dict) -> list[str]:
    """Give round parts with no stated orientation the axis the film implies.

    Evidence, strongest first: a spin motion on the part (or on the group that carries it)
    turns about the part's own axis; a long part attached to a side face runs out of that
    face. A part with recipe.axis or rot set is the author's choice and is left alone; a spin
    on such a part follows the part's axis. Returns what changed, for logging.
    """
    parts = film["parts"]
    by_id = {p["id"]: p for p in parts}
    kids: dict[str, list] = {}
    for p in parts:
        kids.setdefault(p.get("parent") or "", []).append(p)

    def free(p) -> bool:
        recipe = p.get("recipe") or {}
        return p.get("kind") in ROUND and "axis" not in recipe and not any(p.get("rot") or [])

    changes: list[str] = []

    def turn(p, axis: str, why: str) -> None:
        p.setdefault("recipe", {})["axis"] = axis.lstrip("+")
        changes.append(f"{p['id']} axis {axis.lstrip('+')} ({why})")

    for motion in film.get("motions", []):
        if motion.get("type", "spin") != "spin":
            continue
        axis = motion.get("axis", "y")
        if not isinstance(axis, str) or axis not in AXES:
            continue
        target = by_id.get(str(motion.get("part", "")).split(".")[0])
        if target is None:
            continue
        if target.get("kind") == "group":
            # A spinning wheel or crank group: its round parts share the spin axis.
            stack = [(child, 0) for child in kids.get(target["id"], [])]
            while stack:
                child, depth = stack.pop()
                if free(child):
                    turn(child, axis, f"spins with {target['id']}")
                if child.get("kind") == "group" and depth < 2:
                    stack += [(c, depth + 1) for c in kids.get(child["id"], [])]
        elif free(target):
            turn(target, axis, "spin axis")
        elif target.get("kind") in ROUND and not any(target.get("rot") or []):
            own = str((target.get("recipe") or {}).get("axis", "y")).lstrip("+-")
            if own != axis.lstrip("+-"):
                motion["axis"] = own
                changes.append(
                    f"{motion.get('id', target['id'])} spins about {own}, its part's axis"
                )
    for p in parts:
        on = p.get("on")
        if isinstance(on, dict) and p.get("kind") in ELONGATED and free(p):
            face = on.get("face", "+y")
            if face in ("+x", "-x", "+z", "-z"):
                turn(p, face, f"runs out of {on.get('part')}'s {face} face")
    return changes


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
main{{max-width:920px;margin:0 auto}}
h1{{font-size:26px;font-weight:600;letter-spacing:-.02em;line-height:1.2;margin:0 0 6px}}
.lede{{font-size:16px;color:var(--muted-foreground);margin:0 0 16px;max-width:68ch}}
.restart{{margin-top:14px;min-height:40px;padding:0 16px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--foreground);font-size:14px;font-weight:500}}
#transcript{{margin-top:28px;font-size:15px;color:var(--muted-foreground)}}
#transcript h2{{font-size:17px;font-weight:600;color:var(--foreground);margin:0 0 6px}}
#transcript ol{{padding-left:20px}}#transcript li{{margin:4px 0}}#transcript strong{{color:var(--foreground);font-weight:600}}
</style></head>
<body><main>
<h1>{title}</h1>
<p class="lede">{lede}</p>
<section id="visual" aria-label="{desc}"><div id="board"></div></section>
<button type="button" class="restart" id="restart">Watch from the start</button>
<section id="transcript"><h2>In short</h2><p>{summary}</p><h2>Chapters</h2><ol>{chapters}</ol></section>
</main>
<script>
const FILM = {film};
const player = Clicky3D.film('#board', FILM, {{ desc: FILM.desc || FILM.title }});
document.getElementById('restart').addEventListener('click', () => {{ player.reset(); player.play(); }});
window.__explainer = player;
</script>
</body></html>"""


def page(film: dict) -> str:
    """The host-owned HTML document that plays a checked film."""
    escape = html.escape
    summary = film["summary"].strip()
    lede = re.split(r"(?<=[.!?])\s", summary, maxsplit=1)[0]
    chapters = "".join(
        f"<li><strong>{escape(c['title'].strip())}.</strong> {escape(c['say'].strip())}</li>"
        for c in film["chapters"]
    )
    data = json.dumps(film, ensure_ascii=False, separators=(",", ":"))
    # Inside <script>, a "<" in a string could close the element; \\u003c is the same character.
    data = data.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return PAGE.format(
        title=escape(film["title"].strip()),
        lede=escape(lede),
        desc=escape(str(film.get("desc") or film["title"]).strip()),
        summary=escape(summary),
        chapters=chapters,
        film=data,
    )
