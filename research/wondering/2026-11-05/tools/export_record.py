"""Builds the research record: redacted network log and responses, redacted screenshots,
static findings and a script manifest (addresses and checksums, not the scripts)."""
import glob, hashlib, json, os, re, shutil, sys
from collections import Counter
from PIL import Image, ImageDraw

S, R = sys.argv[1], sys.argv[2]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
NAMES = [n for n in os.environ.get("REDACT_NAMES", "").split("|") if n]  # e.g. "Full Name|First"
ids: dict[str, str] = {}

def redact(text: str) -> str:
    text = EMAIL.sub("<email>", text)
    for n in NAMES:
        text = text.replace(n, "<name>")
    return UUID.sub(lambda m: ids.setdefault(m.group(0).lower(), f"<id-{len(ids) + 1}>"), text)

# 1. network log
with open(f"{R}/network/requests.jsonl", "w") as out:
    for line in open(f"{S}/wnet/net.jsonl"):
        out.write(redact(line))
# 2. full responses captured from the generation and content calls
for f in sorted(glob.glob(f"{S}/wnet/raw/*")):
    body = open(f, encoding="utf8", errors="replace").read()
    name = os.path.basename(f)
    if name.endswith(".json") and body.strip():
        try:
            body = json.dumps(json.loads(body), indent=1, ensure_ascii=False)
        except ValueError:
            pass
    open(f"{R}/responses/{name}", "w", encoding="utf8").write(redact(body))
# 3. screenshots, with the account chip and the email line covered
cover = {
    "04-code-sent.png": [(636, 276, 822, 299)],
    **{n: [(8, 695, 250, 748)] for n in ("05-after-login.png", "06-create.png", "13-course.png", "14-lesson1.png")},
}
for f in sorted(glob.glob(f"{S}/wshots/*.png")):
    img = Image.open(f).convert("RGB")
    draw = ImageDraw.Draw(img)
    for box in cover.get(os.path.basename(f), []):
        draw.rectangle(box, fill=(40, 40, 40))
    img.save(f"{R}/screenshots/{os.path.basename(f)}", optimize=True)
os.makedirs(f"{R}/screenshots/socrat-checks", exist_ok=True)
for f in sorted(glob.glob(f"{S}/shots/*.png")):
    shutil.copy(f, f"{R}/screenshots/socrat-checks/{os.path.basename(f)}")
# 4. script manifest: where each script came from and its checksum, not the code itself
manifest = json.load(open(f"{S}/wondering/scripts/manifest.json"))
rows = []
for s in manifest.get("scripts", manifest if isinstance(manifest, list) else []):
    c = s.get("content", {})
    rows.append(dict(url=s.get("url"), bytes=c.get("bytes"), sha256=c.get("sha256")))
json.dump(dict(captured="2026-11-05", page="https://wondering.app/", scripts=rows), open(f"{R}/static/script-manifest.json", "w"), indent=1)
# 5. static findings read from the main bundle (names only)
src = "".join(open(f, encoding="utf8").read() for f in glob.glob(f"{S}/wondering/scripts/files/origins/*/assets/*.js"))
def counted(pattern):
    return dict(Counter(re.findall(pattern, src)).most_common())
findings = dict(
    supabase_tables=counted(r'\.from\("([a-z_]{3,50})"\)'),
    rpcs=counted(r'\.rpc\("([a-zA-Z_]{3,60})"'),
    edge_functions=counted(r'invokeEdgeFunction(?:Anon)?\(\s*"([a-zA-Z0-9_\-]{2,70})"'),
    practice_types=re.search(r"PRACTICE_TYPES=\{([^}]*)\}", src).group(1),
    async_graded=re.search(r"ASYNC_GRADED_TYPES=\[([^\]]*)\]", src).group(1),
    visual_kinds=sorted(set(re.findall(r'kind==="([a-z_]{3,30})"', src))),
    feature_flags=dict(re.findall(r"(ENABLED_[A-Z_]+)=!([01])", src)),
    review_constants=dict(re.findall(r"(PRACTICES_PER_SESSION_REVIEW|PRACTICES_PER_QUICK_REVIEW|MAX_REVIEW_RESERVATION_CANDIDATES|GLOBAL_REVIEW_MAX_PRACTICES|PRACTICE_WAIT_POLL_MS)=([0-9e]+)", src)),
    figure_library=re.findall(r'\{id:"([a-z0-9\-]+)",concept:', src),
    lesson_components_seen=sorted(set(re.findall(r"\{\{interactive:([a-z0-9\-]+)", "".join(open(f, encoding="utf8", errors="replace").read() for f in glob.glob(f"{S}/wnet/raw/*"))))),
    third_party_hosts=sorted(set(re.findall(r"https://([a-z0-9.\-]+\.(?:supabase\.co|posthog\.com|sentry\.io|openai\.com))", src))),
)
findings["feature_flags"] = {k: v == "0" for k, v in findings["feature_flags"].items()}  # !0 is true
json.dump(findings, open(f"{R}/static/findings.json", "w"), indent=1)
# 6. REA evidence identifiers
open(f"{R}/static/rea-evidence.txt", "w").write(
    "page capture (inspect_web_page): ev_ec4b721c8068a926606785ffc1d0ff24463c6ed747dc9c296ada0a389643534a\n"
    "script export (export_web_scripts): ev_e1c60c83d007a58d16c02d020dad8ea789feed8dccf70eb9cd781b20630f1725\n"
)
print("ids redacted:", len(ids))
