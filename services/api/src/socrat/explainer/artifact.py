"""Validate generated documents and compile them for an opaque-origin sandbox."""

import html
import json
import re
import secrets
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from socrat.catalog.registry import REPO_ROOT

# The host's drawing kit (layout, links, pointers, audit); generated scripts call it, never replace it.
KIT = (Path(__file__).parent / "kit.js").read_text(encoding="utf-8")
# The 3D stage: geometry kernel, WebGL2 renderer, then the Clicky3D scene kit that mounts them.
STAGE_3D = [
    (Path(__file__).parent / name).read_text(encoding="utf-8")
    for name in ("clicky3d-geometry.js", "clicky3d-render.js", "clicky3d.js")
]

MAX_BYTES = 300_000


def _font_faces() -> str:
    """Socrat's own typefaces, inlined: the sandbox only accepts data: fonts."""
    import base64

    faces = []
    for family, name, weight in (
        ("Geist", "geist-wght.woff2", "100 900"),
        ("Delicious Handrawn", "delicious-handrawn-latin-400.woff2", "400"),
    ):
        path = REPO_ROOT / "apps/web/src/fonts" / name
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            faces.append(
                f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{data}) format("woff2");'
                f"font-weight:{weight};font-display:block}}"
            )
    return "".join(faces)


FONT_FACES = _font_faces()
TAGS = set(
    "html head body title meta style script main section article header footer nav aside figure figcaption div span p h1 h2 h3 h4 h5 h6 strong em b i u s small mark sub sup abbr cite q dfn time var samp kbd code pre blockquote ul ol li dl dt dd table thead tbody tfoot tr th td caption button input label select option optgroup textarea fieldset legend output details summary progress meter br hr svg g path rect circle ellipse line polyline polygon text tspan defs desc marker lineargradient radialgradient stop clippath mask pattern symbol use canvas math mrow mi mn mo mfrac msup msub msqrt mroot mtext".split()
)
TAGS.update(
    "filter feturbulence fedisplacementmap fegaussianblur feoffset feflood feblend fecolormatrix fecomposite femerge femergenode fedropshadow".split()
)
VOID = {"meta", "input", "br", "hr"}
URL_ATTRS = {
    "src",
    "srcset",
    "href",
    "xlink:href",
    "action",
    "formaction",
    "ping",
    "poster",
    "background",
}


class ArtifactError(ValueError):
    """Safe, actionable validation messages; never include model output or credentials."""


@dataclass
class Document:
    html: str
    title: str
    transcript: str
    scripts: list[str]


class Validator(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.scripts: list[str] = []
        self.title: list[str] = []
        self.transcript: list[str] = []
        self.stack: list[str] = []
        self.transcript_depth = 0
        self.script = False
        self.style = False
        self.visual = False
        self.controls = 0
        self.closed = False
        self.ids: set[str] = set()

    def handle_decl(self, decl):
        if decl.lower() != "doctype html":
            raise ArtifactError("Only the HTML doctype is allowed")

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            raise ArtifactError(
                f"Unsupported HTML element: {tag[:40]}; use standard HTML/SVG/canvas without embeds"
            )
        if self.closed:
            raise ArtifactError("HTML elements must be inside the document")
        attributes = {}
        for key, value in attrs:
            value = value or ""
            if (
                key in attributes
                or key.startswith("on")
                or key in {"srcdoc", "nonce", "is", "autofocus", "contenteditable"}
            ):
                raise ArtifactError(
                    "Use addEventListener; inline handlers and privileged attributes are forbidden"
                )
            if key in URL_ATTRS and not (
                tag == "use" and key in {"href", "xlink:href"} and re.fullmatch(r"#[\w-]+", value)
            ):
                raise ArtifactError("External resources and navigation are forbidden")
            if key == "style":
                self.check_css(value)
            attributes[key] = value
        if tag == "meta" and not (
            "charset" in attributes
            or attributes.get("name", "").lower() in {"viewport", "description"}
        ):
            raise ArtifactError("Only charset, viewport and description metadata are allowed")
        if tag == "script" and any(
            k != "type" or v not in {"text/javascript", "application/javascript"}
            for k, v in attributes.items()
        ):
            raise ArtifactError("Scripts must be inline vanilla JavaScript")
        identity = attributes.get("id")
        if identity:
            if identity in self.ids:
                raise ArtifactError(
                    f"Duplicate element id: {identity[:80]}; use a unique id for each element and update its references"
                )
            self.ids.add(identity)
        if identity == "transcript":
            self.transcript_depth = len(self.stack) + 1
        if identity == "visual":
            self.visual = True
        if tag in {"button", "input", "select"}:
            self.controls += 1
        self.parts.append(
            "<"
            + tag
            + "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in attributes.items())
            + ">"
        )
        if tag not in VOID:
            self.stack.append(tag)
        if tag == "script":
            self.script = True
            self.scripts.append("")
        self.style = tag == "style" or self.style

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            expected = self.stack[-1] if self.stack else "no open element"
            raise ArtifactError(
                f"Close {expected[:40]} before closing {tag[:40]}; all HTML elements must be balanced"
            )
        if self.transcript_depth == len(self.stack):
            self.transcript_depth = 0
        self.stack.pop()
        self.parts.append(f"</{tag}>")
        if tag == "script":
            self.script = False
        if tag == "style":
            self.style = False
        if tag == "html":
            self.closed = True

    def handle_data(self, data):
        if not self.stack and data.strip():
            raise ArtifactError("Text must be inside the HTML document")
        self.parts.append(data)
        if self.script:
            self.scripts[-1] += data
        elif self.style:
            self.check_css(data)
        else:
            if self.stack and self.stack[-1] == "title":
                self.title.append(data)
            if self.transcript_depth:
                self.transcript.append(data)

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")

    @staticmethod
    def check_css(css):
        local_urls = re.findall(r"url\s*\((.*?)\)", css, re.I | re.S)
        if re.search(r"@import|expression\s*\(|-moz-binding|behavior\s*:", css, re.I) or any(
            not re.fullmatch(r"(['\"]?)#[\w-]+\1", value.strip()) for value in local_urls
        ):
            raise ArtifactError("CSS must not load resources or execute code")


def validate(raw: str) -> Document:
    raw = raw.strip()
    if raw.startswith("```html\n") and raw.endswith("```"):
        raw = raw[8:-3].strip()
    if len(raw.encode("utf-8")) > MAX_BYTES:
        raise ArtifactError("Document exceeds the 300 KB limit")
    parser = Validator()
    parser.feed(raw)
    parser.close()
    title = html.unescape(" ".join(parser.title)).strip()
    transcript = html.unescape("\n".join(t.strip() for t in parser.transcript if t.strip()))
    if parser.stack or not parser.closed or not all(t in raw.lower() for t in ["<head", "<body"]):
        raise ArtifactError("Return a complete, balanced HTML document")
    if not 2 <= len(title) <= 140 or "transcript" not in parser.ids or len(transcript) > 30_000:
        raise ArtifactError(
            "Include a meaningful title and section id=transcript for the complete explanation"
        )
    if not parser.visual or not parser.controls or not parser.scripts:
        raise ArtifactError("Include id=visual, interactive input controls, and working JavaScript")
    if not any("__explainer" in script for script in parser.scripts):
        raise ArtifactError("Expose the required window.__explainer interface")
    return Document("<!DOCTYPE html>" + "".join(parser.parts), title, transcript, parser.scripts)


BASE_STYLE = """
:root{color-scheme:light dark;--background:Canvas;--foreground:CanvasText;--card:Canvas;--muted:ButtonFace;--muted-foreground:GrayText;--border:ButtonBorder;--primary:AccentColor;--primary-foreground:AccentColorText;--radius:.7rem}
:root{--ink:var(--foreground);--pen:#CC2A24;--highlight:#F6E05E;--sans:"Geist",ui-sans-serif,system-ui,"Segoe UI",sans-serif;--hand:"Delicious Handrawn","Segoe Print","Bradley Hand",cursive;--paper-lines:repeating-linear-gradient(to bottom,transparent 0,transparent 27px,color-mix(in srgb,var(--foreground) 8%,transparent) 27px,color-mix(in srgb,var(--foreground) 8%,transparent) 28px)}
:root[style*="color-scheme: dark"]{--pen:#FF7D72;--highlight:#E9D53A}
*{box-sizing:border-box}html,body{margin:0;background:var(--background);color:var(--foreground);font-family:var(--sans)}body{padding:20px;line-height:1.55}button,input,select,textarea{font:inherit}button,input,select{min-height:44px}button{cursor:pointer}button:disabled{cursor:default;opacity:.5}button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--primary);outline-offset:3px}svg,canvas{max-width:100%}pre{overflow:auto}#visual{min-height:220px}#transcript{margin-top:24px}a{pointer-events:none}
@media(max-width:600px){body{padding:12px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
html[data-reduced-motion=true] *,html[data-reduced-motion=true] *::before,html[data-reduced-motion=true] *::after{animation:none!important;transition:none!important}
"""


def compile_document(
    document: str, channel: str, app_origin: str, theme: str = "light", mode: str = "sketch"
) -> tuple[str, str]:
    """Revalidate stored content; only this compiler grants script nonces and messaging."""
    clean = validate(document).html
    nonce = secrets.token_urlsafe(24)
    clean = re.sub(r"<script(?=[ >])", f'<script nonce="{nonce}"', clean)
    config = json.dumps(dict(channel=channel, origin=app_origin)).replace("<", "\\u003c")
    # Read the dashboard's actual tokens before generated code first computes canvas/SVG colors.
    css = (REPO_ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")
    selector = r"\.dark" if theme == "dark" else r":root"
    palette = re.search(r"(?ms)^" + selector + r"\s*\{(.*?)^\}", css)
    theme_style = ":root{" + (palette.group(1) if palette else "") + f"color-scheme:{theme};" + "}"
    runtime = """
(() => {
const config = CONFIG, root = document.documentElement;
let current = 0, failed = false;
const send = (type, data={}) => parent.postMessage({type,channel:config.channel,...data}, config.origin);
// Side-by-side panels with fixed widths would need a sideways scroll: let those rows wrap or stack.
// shortcut: only flex and grid rows are repaired; inline-block rows, tables and absolute layouts still scroll.
const wrap = () => {
  for (const el of document.body.querySelectorAll('*')) {
    if (!(el.scrollWidth > el.clientWidth + 1)) continue;
    const style = getComputedStyle(el);
    if (style.overflowX !== 'visible') continue;
    if (style.display.includes('flex')) el.style.flexWrap = 'wrap';
    else if (style.display.includes('grid')) el.style.gridTemplateColumns = 'repeat(auto-fit,minmax(min(100%,260px),1fr))';
    else continue;
    for (const child of el.children) { child.style.minWidth = '0'; child.style.maxWidth = '100%'; }
  }
};
const state = () => {
  wrap();
  const api = window.__explainer;
  if (!api || typeof api.describe !== 'function' || typeof api.step !== 'function' || typeof api.reset !== 'function') throw Error('Missing visual controls');
  const count = Number(api.stepCount), description = String(api.describe());
  if (!Number.isInteger(count) || count < 1 || count > 2000 || !description.trim() || description.length > 30000) throw Error('Invalid visual state');
  const reported = api.currentStep;
  if (reported !== undefined && (!Number.isInteger(reported) || reported < 0 || reported >= count)) throw Error('Invalid selected visual step');
  current = reported === undefined ? Math.min(current,count-1) : reported;
  // A film keeps its own clock: the host's play button drives it instead of stepping.
  const timed = typeof api.play === 'function' && typeof api.pause === 'function';
  return {count,current,description:description.slice(0,6000),height:Math.min(1600,Math.max(420,document.body.scrollHeight+24)),timed,playing:timed&&!!api.playing};
};
const update = () => { if (failed) return; try { send('state',state()); } catch { failed=true;send('error'); } };
addEventListener('message',event => {
  if (event.source!==parent || event.origin!==config.origin || event.data?.channel!==config.channel) return;
  const data=event.data;
  if (data.type==='theme') {
    const names=['background','foreground','card','muted','muted-foreground','border','primary','primary-foreground','success','warning','destructive','chart-1','chart-2','chart-3','chart-4','chart-5','radius'];
    for (const name of names) { const value=data.tokens?.[name]; if(typeof value==='string' && value.length<160 && !/[{};]|url/i.test(value)) root.style.setProperty('--'+name,value); }
    root.style.colorScheme=data.dark?'dark':'light';root.dataset.reducedMotion=String(!!data.reducedMotion);update();
  } else if (data.type==='step' && Number.isInteger(data.index)) {
    try { current=Math.max(0,Math.min(Number(window.__explainer.stepCount)-1,data.index));window.__explainer.step(current);update(); } catch { failed=true;send('error'); }
  } else if ((data.type==='play'||data.type==='pause') && typeof window.__explainer.play==='function') {
    try { data.type==='play' ? window.__explainer.play() : window.__explainer.pause(); update(); } catch { failed=true;send('error'); }
  } else if (data.type==='rate' && Number.isFinite(data.value) && data.value>=0.25 && data.value<=4 && 'rate' in window.__explainer) {
    window.__explainer.rate = data.value; update();
  } else if (data.type==='reset') { try {current=0;window.__explainer.reset();update();} catch {failed=true;send('error');} }
});
addEventListener('resize',()=>update());
addEventListener('error',()=>{failed=true;send('error')});
addEventListener('unhandledrejection',()=>{failed=true;send('error')});
document.addEventListener('click',()=>setTimeout(update,0));document.addEventListener('input',()=>setTimeout(update,0));document.addEventListener('change',()=>setTimeout(update,0));
document.addEventListener('DOMContentLoaded',()=>{send('ready');update()});
setInterval(()=>{if(!failed){send('heartbeat');update()}},1000);
})();
""".replace("CONFIG", config)
    clean = clean.replace(
        "</head>",
        f'<style>{FONT_FACES}{BASE_STYLE}{theme_style}</style><script nonce="{nonce}">{KIT}</script></head>',
    )
    if mode == "3d":
        stage = "".join(f'<script nonce="{nonce}">{source}</script>' for source in STAGE_3D)
        clean = clean.replace("</head>", stage + "</head>")
    clean = clean.replace("</body>", f'<script nonce="{nonce}">{runtime}</script></body>')
    # Both policies must pass: copying an inline nonce must never authorize external scripts.
    csp = (
        f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
        f"img-src data:; font-src data:; connect-src 'none'; frame-src 'none'; worker-src 'none'; "
        f"object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors {app_origin}; sandbox allow-scripts"
        ", script-src 'unsafe-inline'"
    )
    return clean, csp
