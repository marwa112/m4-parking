#!/usr/bin/env python3
"""Build the M4 Parking Check specification from spec/requirements.yaml.

Usage (from the repository root):
    python3 spec/build.py            # writes docs/spec/M4-Parking-Spec-v<version>.html

Checks before it writes:
  * every ID is unique and sits under the correct epic, feature or category
  * every requirement has priority, verification, status, source and text
  * every requirement text passes the ASD-STE100 checker (spec/tools/ste-lint),
    with on-screen texts in quotes left out of the check
The script never overwrites an existing version. Raise "version" in the YAML file instead.
"""
import collections, html, json, re, subprocess, sys, tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "spec" / "requirements.yaml"
OUT_DIR = ROOT / "docs" / "spec"
LINT = ROOT / "spec" / "tools" / "ste-lint" / "ste-lint.py"

PRIO = ["Must", "Should", "Could", "Won't"]
VERIFY = {"T": "Test", "D": "Demonstration", "I": "Inspection", "A": "Analysis"}
STATUS_MARK = {"Implemented": "✓", "Implemented, not verified on device": "◐", "Partly": "◑", "Open": "○", "Withdrawn": "–"}
PLANNED = [  # later chapters of the plan, shown so the reviewer sees the full structure
    ("Technical specification", "Algorithms in detail: geometry matching, label placement, Android shell."),
    ("Data pipeline", "Each script step, fields used, sanity checks, manual refresh."),
    ("Known limits and risks", "Impact and mitigation for each limit."),
    ("Installation guides", "IG-01 web app, IG-02 Android app, IG-03 developer setup."),
    ("User guide", "Task-based steps, with screens."),
    ("Traceability", "Requirements against test cases. Excel test matrix."),
    ("Appendix A: Sales deck", "Slides and link."),
    ("Change log", "Changes per version."),
]

def die(msg):
    sys.exit("build.py: " + msg)

def load():
    d = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    for c in d["nfr"]:
        c["category"] = str(c["category"])
    return d

def all_reqs(d):
    for e in d["epics"]:
        for f in e["features"]:
            for r in f["requirements"]:
                yield r, e, f
    for c in d["nfr"]:
        for r in c["requirements"]:
            yield r, None, c

def validate(d):
    ids, problems = [], []
    for e in d["epics"]:
        ids.append(e["id"])
        for f in e["features"]:
            ids.append(f["id"])
            if not f["id"].startswith("FE-" + e["id"][3:] + "."):
                problems.append(f"{f['id']} is not under {e['id']}")
    for r, e, f in all_reqs(d):
        ids.append(r["id"])
        if e is not None and not re.fullmatch(r"FR-%s\.\d{3}" % re.escape(f["id"][3:]), r["id"]):
            problems.append(f"{r['id']} is not a valid FR ID under {f['id']}")
        if e is None and not re.fullmatch(r"NFR-%s-\d{3}" % f["category"], r["id"]):
            problems.append(f"{r['id']} is not a valid NFR ID in {f['category']}")
        for k in ("p", "v", "st", "src", "text"):
            if k not in r:
                problems.append(f"{r['id']} has no '{k}'")
        if r.get("p") not in PRIO:
            problems.append(f"{r['id']} has priority {r.get('p')!r}")
        if r.get("v") not in VERIFY:
            problems.append(f"{r['id']} has verification {r.get('v')!r}")
        if r.get("st") not in STATUS_MARK:
            problems.append(f"{r['id']} has status {r.get('st')!r}")
        if r.get("src") not in d["sources"]:
            problems.append(f"{r['id']} has unknown source {r.get('src')!r}")
    dup = [k for k, n in collections.Counter(ids).items() if n > 1]
    if dup:
        problems.append("duplicate IDs: " + ", ".join(dup))
    if problems:
        die("validation failed:\n  " + "\n  ".join(problems))

def ste_check(d):
    """Run the STE checker. Quoted on-screen texts are replaced by a neutral word first."""
    texts = [(r["id"], re.sub(r"'[^']*'", "TEXT", r["text"])) for r, _, _ in all_reqs(d)]
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write("\n\n".join(t for _, t in texts) + "\n")
        tmp = fh.name
    res = subprocess.run([sys.executable, str(LINT), "--json", tmp], capture_output=True, text=True)
    out = json.loads(res.stdout or "{}")
    lines = {}
    n = 1
    for rid, t in texts:
        lines[n] = rid
        n += 2
    found = [(lines.get(v["line"], "?"), v["rule"], v["message"]) for v in out.get("violations", [])]
    return out.get("hard_count", 0), found, out.get("words", 0)

# ---------- HTML ----------
E = html.escape
# ---------- assets: screens, diagrams, design system, chapters ----------
import markdown as _md

ASSETS = {}

def load_assets(d):
    a = d.get("assets", {})
    base = OUT_DIR
    def j(sub, ver, name):
        f = base / sub / f"v{ver}" / name
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    ASSETS["screens_ver"] = a.get("screens")
    ASSETS["screens"] = (j("screens", a["screens"], "manifest.json") or {}).get("screens", []) if a.get("screens") else []
    ASSETS["diag_dir"] = base / "diagrams" / f"v{a.get('diagrams')}"
    ASSETS["design_ver"] = a.get("design")
    ASSETS["ds"] = j("design", a["design"], "ds.json") if a.get("design") else None
    ASSETS["design"] = yaml.safe_load((ROOT / "spec" / "design.yaml").read_text(encoding="utf-8"))
    ASSETS["chapters"] = {p.stem: p.read_text(encoding="utf-8") for p in sorted((ROOT / "spec" / "chapters").glob("*.md"))}
    missing = [n for n in ("screens", "ds") if not ASSETS[n]]
    if missing or not ASSETS["diag_dir"].exists():
        die("missing assets: " + ", ".join(missing + ([] if ASSETS["diag_dir"].exists() else ["diagrams"])))

def frlink(i):
    return f'<a class="mono" href="#{i}">{i}</a>'

def screens_html(fid):
    seq = [s for s in ASSETS["screens"] if s["fe"] == fid]
    if not seq:
        return '<p class="screens">No user screens. See the chapters Architecture and Data pipeline.</p>'
    cards = []
    for s in seq:
        dots = "".join(f'<span class="mk" style="left:{m["x"]}%;top:{m["y"]}%" aria-hidden="true">{m["n"]}</span>' for m in s["marks"])
        legend = "".join(f'<li><span class="mk inl">{m["n"]}</span> {E(m["text"])}</li>' for m in s["marks"])
        mock = '<span class="mock">Mock-up</span>' if s.get("mock") else ""
        cards.append(
            f'<figure class="sc" id="{s["id"]}"><div class="shot"><img loading="lazy" src="screens/v{ASSETS["screens_ver"]}/{s["file"]}" '
            f'alt="{E(s["title"])}" width="{s["w"]}" height="{s["h"]}">{dots}</div>'
            f'<figcaption><div class="scid"><a href="#{s["id"]}">{s["id"]}</a> {mock}</div><b>{E(s["title"])}</b>'
            f'<p>{E(s["caption"])}</p>{"<ol class=mkl>" + legend + "</ol>" if legend else ""}'
            f'<p class="frs">Shows: {", ".join(frlink(i) for i in s["frs"])}</p></figcaption></figure>')
    return '<div class="seq">' + "".join(cards) + "</div>"

def figure_html(name, caption):
    f = ASSETS["diag_dir"] / f"{name}.svg"
    if not f.exists():
        die(f"diagram {name} not found in {ASSETS['diag_dir']}")
    svg = f.read_text(encoding="utf-8")
    return (f'<figure class="diag" id="fig-{name}"><div class="dw">{svg}</div>'
            f'<figcaption>{E(caption)} <a href="diagrams/v{ASSETS["diag_dir"].name[1:]}/{name}.svg">Open SVG</a> · source <code>spec/diagrams/{name}.mmd</code></figcaption></figure>')

def chapter_html(key, h, numprefix):
    """Markdown chapter -> HTML. '## ID Title {#ID}' become numbered level-2 headings."""
    text = ASSETS["chapters"][key]
    figs = {}
    def keep(m):
        k = f"FIGURE{len(figs)}X"
        figs[k] = figure_html(m.group(1), m.group(2))
        return "\n\n" + k + "\n\n"
    text = re.sub(r'\[\[figure ([\w-]+) "([^"]+)"\]\]', keep, text)
    out = _md.markdown(text, extensions=["tables", "attr_list"])
    for k, v in figs.items():
        out = out.replace(f"<p>{k}</p>", v)
    n = [0]
    def head(m):
        n[0] += 1
        anchor, title = m.group(1), re.sub("<[^>]+>", "", m.group(2))
        return h(2, f"{numprefix}.{n[0]}", title, anchor)
    out = re.sub(r'<h2 id="([^"]+)">(.*?)</h2>', head, out)
    out = out.replace("<table>", '<div class="tw"><table class="plain">').replace("</table>", "</table></div>")
    return out

_RGB = re.compile(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)")
def hexify(v):
    def f(m):
        a = m.group(4)
        hx = "#%02x%02x%02x" % tuple(int(m.group(i)) for i in (1, 2, 3))
        if a is not None and float(a) < 1:
            return hx + f" {round(float(a) * 100)}%"
        return hx
    return _RGB.sub(f, v or "")

def sw(c):
    c = (c or "").strip()
    return f'<span class="swatch" style="background:{E(c)}"></span><code>{E(c)}</code>' if c else "–"

def ds_html(h, sec):
    D, ds = ASSETS["design"], ASSETS["ds"]
    ver = ASSETS["design_ver"]
    tok_l, tok_d = ds["tokens"]["light"], ds["tokens"]["dark"]
    out = [f'<p>{E(D["intro"])}</p>']
    # colours
    out.append(h(2, f"{sec}.1", "Colours (DS-COL)", "ds-colours"))
    rows = "".join(f'<tr id="{v[0]}"><td class="mono">{v[0]}</td><td><b>{E(v[1])}</b><br><code>{E(k)}</code></td><td>{sw(tok_l.get(k))}</td><td>{sw(tok_d.get(k))}</td><td>{E(v[2])}{("<br><i>" + E(v[3]) + "</i>") if v[3] else ""}</td></tr>' for k, v in D["colours"].items())
    out.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Token</th><th>Light</th><th>Dark</th><th>Use and rule</th></tr></thead><tbody>' + rows + "</tbody></table></div>")
    # type
    out.append(h(2, f"{sec}.2", "Typography (DS-TYP)", "ds-type"))
    def spec_style(spec):
        fam = "var(--f-app-mono)" if "Mono" in spec else "var(--f-app)"
        wt = re.search(r"\b([1-9]00)\b", spec); sz = re.search(r"([\d.]+) px", spec)
        return f"font-family:{fam};font-weight:{wt.group(1) if wt else 400};font-size:{min(float(sz.group(1)) if sz else 16, 36)}px;" + ("text-transform:uppercase;letter-spacing:.08em;" if "upper" in spec else "")
    rows = "".join(f'<tr id="{t[0]}"><td class="mono">{t[0]}</td><td><span style="{spec_style(t[2])}">{E(t[1])}</span></td><td>{E(t[2])}</td><td>{E(t[3])}</td></tr>' for t in D["type"])
    out.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Sample</th><th>Font</th><th>Use</th></tr></thead><tbody>' + rows + "</tbody></table></div>")
    # spacing, icons
    out.append(h(2, f"{sec}.3", "Spacing, shape and size (DS-SPC)", "ds-spacing"))
    out.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Name</th><th>Value</th><th>Where</th></tr></thead><tbody>' + "".join(f'<tr id="{t[0]}"><td class="mono">{t[0]}</td><td>{E(t[1])}</td><td>{E(t[2])}</td><td>{E(t[3])}</td></tr>' for t in D["spacing"]) + "</tbody></table></div>")
    out.append(h(2, f"{sec}.4", "Icons and marks (DS-ICN)", "ds-icons"))
    out.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Mark</th><th>Meaning</th><th>Note</th></tr></thead><tbody>' + "".join(f'<tr id="{t[0]}"><td class="mono">{t[0]}</td><td class="icn">{E(t[1])}</td><td>{E(t[2])}</td><td>{E(t[3])}</td></tr>' for t in D["icons"]) + "</tbody></table></div>")
    # components
    out.append(h(2, f"{sec}.5", "Components (DS-CMP)", "ds-components"))
    out.append('<p>Each card shows the element from the app in light and dark mode, with numbered parts. The inspect panel gives the measured values. Colours are given as light / dark.</p>')
    meta = D["components"]
    for el in ds["elements"]:
        L, Dk = el["light"], el["dark"]
        if not L:
            continue
        pad = L.get("pad", 6); rw = float(L["root"]["width"][:-2]); rh = float(L["root"]["height"][:-2])
        dots = ""
        for i, p in enumerate(L["parts"], 1):
            if p.get("missing"):
                continue
            x = (pad + p["box"][0] / 100 * rw) / (rw + 2 * pad) * 100
            y = (pad + (p["box"][1] + p["box"][3] / 2) / 100 * rh) / (rh + 2 * pad) * 100
            dots += f'<span class="mk" style="left:{x:.1f}%;top:{y:.1f}%">{i}</span>'
        r = L["root"]
        root_rows = [("Size", f'{r["width"]} × {r["height"]}'), ("Padding", r["padding"]), ("Corner radius", r["borderRadius"]),
                     ("Border", hexify(r["border"])), ("Fill", hexify(r["backgroundColor"]) + " / " + hexify(Dk["root"]["backgroundColor"] if Dk else "")),
                     ("Shadow", r["boxShadow"] if r["boxShadow"] != "none" else "")]
        if r.get("backgroundImage", "none") != "none":
            root_rows.append(("Pattern", "diagonal stripes"))
        rr = "".join(f"<tr><th>{k}</th><td>{E(v)}</td></tr>" for k, v in root_rows if v and v.strip() not in ("0px", "none", "/"))
        prow = ""
        for i, p in enumerate(L["parts"], 1):
            if p.get("missing"):
                continue
            dp = (Dk["parts"][i - 1] if Dk and i - 1 < len(Dk["parts"]) else {}) or {}
            fam = p["fontFamily"].split(",")[0].strip('"')
            font = f'{fam} {p["fontWeight"]}, {p["fontSize"]}/{p["lineHeight"]}' + (f', {p["letterSpacing"]}' if p["letterSpacing"] not in ("normal", "0px") else "") + (", upper case" if p["textTransform"] == "uppercase" else "")
            prow += (f'<tr><td><span class="mk inl">{i}</span></td><td><b>{E(p["label"])}</b><br><span class="muted">{p["width"]} × {p["height"]} · at {p["offset"][0]}, {p["offset"][1]}</span></td>'
                     f'<td>{E(font)}</td><td>{sw(hexify(p["color"]))} / {sw(hexify(dp.get("color", "")))}</td>'
                     f'<td>{sw(hexify(p["backgroundColor"])) if "0%" not in hexify(p["backgroundColor"]) else "–"}</td></tr>')
        m = meta.get(el["id"], {})
        dark_img = f'<img loading="lazy" src="design/v{ver}/{el["id"]}-dark.png" alt="{E(el["name"])}, dark mode">' if Dk else ""
        out.append(
            f'<section class="cmp" id="{el["id"]}"><h4><span class="num">{el["id"]}</span> {E(el["name"])}</h4><div class="cmpg">'
            f'<div class="cmpi"><div class="shot ds"><img loading="lazy" src="design/v{ver}/{el["id"]}.png" alt="{E(el["name"])}">{dots}</div>'
            f'<div class="darkimg">{dark_img}<span class="muted">Dark mode</span></div></div>'
            f'<div class="insp"><table class="kvs">{rr}</table>'
            f'<div class="tw"><table class="plain parts"><thead><tr><th></th><th>Part</th><th>Font</th><th>Text light / dark</th><th>Fill</th></tr></thead><tbody>{prow}</tbody></table></div>'
            f'<p><b>Use.</b> {E(m.get("use", ""))}</p><p><b>Behaviour.</b> {E(m.get("behaviour", ""))}</p></div></div></section>')
    # extra components that exist only as states
    for st in ds.get("states", []):
        if not any(e["id"] == st["id"] for e in ds["elements"]):
            m = meta.get(st["id"], {})
            out.append(f'<section class="cmp" id="{st["id"]}"><h4><span class="num">{st["id"]}</span> {E(m.get("name") or st.get("name") or "")}</h4>'
                       f'<p><b>Use.</b> {E(m.get("use", ""))}</p><p><b>Behaviour.</b> {E(m.get("behaviour", ""))}</p><p class="muted">States: see {sec}.6.</p></section>')
    # states
    out.append(h(2, f"{sec}.6", "Interaction states (DS-STA)", "ds-states"))
    out.append('<p>These rules apply to every interactive element. The column "In app" says if the app has the state today. The strips below are captures from the app. A state that the app does not style looks the same as Default.</p>')
    out.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>State</th><th>Rule</th><th>In app</th></tr></thead><tbody>' + "".join(f'<tr id="{t[0]}"><td class="mono">{t[0]}</td><td><b>{E(t[1])}</b></td><td>{E(t[2])}</td><td>{E(t[3])}</td></tr>' for t in D["state_rules"]) + "</tbody></table></div>")
    names = {e["id"]: e["name"] for e in ds["elements"]}
    for st in ds.get("states", []):
        nm = names.get(st["id"]) or meta.get(st["id"], {}).get("name") or st.get("name") or ""
        cells = ""
        base = st["states"][0]["css"] if st["states"] else {}
        for s in st["states"]:
            diff = [f"{k}: {hexify(v)}" for k, v in s["css"].items() if v != base.get(k) and k in ("backgroundColor", "borderColor", "outline", "opacity", "cursor", "transform", "boxShadow")]
            same = s["state"] != "default" and not diff
            cells += (f'<figure class="stc{" same" if same else ""}"><img loading="lazy" src="design/v{ver}/{s["file"]}" alt="{E(nm)}, {s["state"]}">'
                      f'<figcaption><b>{s["state"].capitalize()}</b><br>{E("; ".join(diff)) if diff else ("No own style" if same else "Base style")}{(" · " + E(s["note"])) if s.get("note") else ""}</figcaption></figure>')
        out.append(f'<div class="strip"><h5><a class="mono" href="#{st["id"]}">{st["id"]}</a> {E(nm)}</h5><div class="stg">{cells}</div></div>')
    # debt
    out.append(h(2, f"{sec}.7", "Design debt (DS-DEBT)", "ds-debt"))
    out.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Gap</th><th>Fix</th></tr></thead><tbody>' + "".join(f'<tr id="{t[0]}"><td class="mono">{t[0]}</td><td>{E(t[1])}</td><td>{E(t[2])}</td></tr>' for t in D["debt"]) + "</tbody></table></div>")
    return "\n".join(out)

def ids_from_assets():
    g = collections.OrderedDict()
    g["Screens (SC)"] = [(s["id"], s["title"]) for s in ASSETS["screens"]]
    for key, label in (("04-information-architecture", "Information architecture (IA)"), ("06-architecture", "Architecture (AR)"), ("07-solution-design", "Solution design (AR, ADR)")):
        g[label] = [(m.group(1), m.group(2)) for m in re.finditer(r"^## (\S+) (.+?) \{#\1\}", ASSETS["chapters"][key], re.M)]
    D = ASSETS["design"]
    g["Design system (DS)"] = [(v[0], v[1]) for v in D["colours"].values()] + [(t[0], t[1]) for t in D["type"] + D["spacing"] + D["icons"]] + \
        [(e["id"], e["name"]) for e in ASSETS["ds"]["elements"]] + [(k, v.get("name", "")) for k, v in D["components"].items() if not any(e["id"] == k for e in ASSETS["ds"]["elements"])] + \
        [(t[0], t[1]) for t in D["state_rules"]] + [(t[0], t[1][:40]) for t in D["debt"]]
    return g


def prio_badge(p):
    return f'<span class="prio p-{p.lower().replace(chr(39), "")}" title="Priority: {p}">{p}</span>'

def status_cell(st):
    return f'<span class="st" title="{E(st)}"><b aria-hidden="true">{STATUS_MARK[st]}</b> {E(st)}</span>'

def req_table(reqs, d):
    rows = "".join(
        f'<tr id="{r["id"]}"><td class="id"><a href="#{r["id"]}">{r["id"]}</a></td>'
        f'<td class="txt">{E(r["text"])}</td><td>{prio_badge(r["p"])}</td>'
        f'<td title="{VERIFY[r["v"]]}">{VERIFY[r["v"]]}</td><td>{status_cell(r["st"])}</td>'
        f'<td><a href="#src-{r["src"]}" title="{E(d["sources"][r["src"]])}">{r["src"]}</a></td></tr>'
        for r in reqs)
    return ('<div class="tw"><table class="req"><thead><tr><th>ID</th><th>Requirement</th><th>Priority</th>'
            '<th>Verification</th><th>Status</th><th>Source</th></tr></thead><tbody>' + rows + "</tbody></table></div>")

def build(d, lint_summary):
    ver = str(d["version"])
    reqs = [r for r, _, _ in all_reqs(d)]
    fr = [r for r in reqs if r["id"].startswith("FR")]
    nfr = [r for r in reqs if r["id"].startswith("NFR")]
    toc, body = [], []
    sec = 0

    def h(level, num, title, anchor):
        toc.append((level, num, title, anchor))
        return f'<h{level + 1} id="{anchor}"><span class="num">{num}</span> {E(title)}</h{level + 1}>'

    # 1 Introduction
    sec += 1
    pc = collections.Counter(r["p"] for r in reqs)
    sc = collections.Counter(r["st"] for r in reqs)
    body.append(h(1, f"{sec}", "Introduction", "intro"))
    body.append(h(2, f"{sec}.1", "Purpose and scope", "purpose"))
    body.append('<p>This document specifies M4 Parking Check. The app tells a holder of an M4 residential parking permit in Göteborg where and when the permit allows parking. '
                'This draft contains the requirements, the screens, the information architecture, the design system, the architecture and the solution design, for review.</p>')
    body.append(h(2, f"{sec}.2", "How to read the IDs", "ids"))
    body.append('<div class="tw"><table class="plain"><thead><tr><th>Item</th><th>Format</th><th>Example</th></tr></thead><tbody>'
                '<tr><td>Epic</td><td class="mono">EP-nn</td><td class="mono">EP-08</td></tr>'
                '<tr><td>Feature</td><td class="mono">FE-nn.mm</td><td class="mono">FE-08.04</td></tr>'
                '<tr><td>Functional requirement</td><td class="mono">FR-nn.mm.kkk</td><td class="mono">FR-08.04.001</td></tr>'
                '<tr><td>Non-functional requirement</td><td class="mono">NFR-CAT-nnn</td><td class="mono">NFR-ACC-001</td></tr>'
                '<tr><td>Screen (v1.0)</td><td class="mono">SC-nn.mm-k</td><td class="mono">SC-08.04-2</td></tr>'
                '<tr><td>Test case (v1.0)</td><td class="mono">TC-nnnn</td><td class="mono">TC-0001</td></tr>'
                '</tbody></table></div><p>An ID never changes and is never used again. A removed requirement keeps its ID with the status Withdrawn.</p>')
    body.append(h(2, f"{sec}.3", "Priority, verification and status", "keys"))
    body.append('<ul class="keys"><li>' + prio_badge("Must") + ' The app is not acceptable without it.</li><li>' + prio_badge("Should") +
                ' Important. The app is acceptable without it for a short time.</li><li>' + prio_badge("Could") + ' Useful if time permits.</li><li>' +
                prio_badge("Won't") + ' Not in this version.</li></ul>'
                '<p><b>Verification:</b> Test (a test case checks a result), Demonstration (a person does the steps and sees the result), Inspection (a person examines the screen, the code or the data), Analysis (a calculation or a measurement).</p>'
                '<p><b>Status:</b> ' + " · ".join(f'<b aria-hidden="true">{m}</b> {E(s)}' for s, m in STATUS_MARK.items() if s != "Withdrawn") + '.</p>')
    body.append(h(2, f"{sec}.4", "Summary", "summary"))
    rows = ""
    for e in d["epics"]:
        rs = [r for f in e["features"] for r in f["requirements"]]
        c = collections.Counter(r["p"] for r in rs)
        rows += f'<tr><td class="mono"><a href="#{e["id"]}">{e["id"]}</a></td><td>{E(e["title"])}</td><td class="n">{len(e["features"])}</td>' + "".join(f'<td class="n">{c.get(p, 0) or ""}</td>' for p in PRIO[:3]) + f'<td class="n"><b>{len(rs)}</b></td></tr>'
    for cat in d["nfr"]:
        c = collections.Counter(r["p"] for r in cat["requirements"])
        rows += f'<tr><td class="mono"><a href="#nfr-{cat["category"]}">NFR-{cat["category"]}</a></td><td>{E(cat["name"])}</td><td class="n">–</td>' + "".join(f'<td class="n">{c.get(p, 0) or ""}</td>' for p in PRIO[:3]) + f'<td class="n"><b>{len(cat["requirements"])}</b></td></tr>'
    body.append('<div class="tw"><table class="plain sum"><thead><tr><th>ID</th><th>Name</th><th>Features</th><th>Must</th><th>Should</th><th>Could</th><th>Total</th></tr></thead><tbody>' + rows +
                f'<tr class="tot"><td></td><td>Total</td><td class="n">{sum(len(e["features"]) for e in d["epics"])}</td>' + "".join(f'<td class="n">{pc.get(p, 0)}</td>' for p in PRIO[:3]) + f'<td class="n"><b>{len(reqs)}</b></td></tr></tbody></table></div>')
    body.append(f'<p>{len(d["epics"])} epics, {sum(len(e["features"]) for e in d["epics"])} features, {len(fr)} functional and {len(nfr)} non-functional requirements. '
                + ", ".join(f"{n} {s.lower()}" for s, n in sc.most_common()) + ".</p>")

    # 2 Functional requirements
    sec += 1
    body.append(h(1, f"{sec}", "Epics, features and functional requirements", "functional"))
    for ei, e in enumerate(d["epics"], 1):
        body.append(h(2, f"{sec}.{ei}", f'{e["id"]} {e["title"]}', e["id"]))
        body.append(f'<p class="goal"><b>Goal.</b> {E(e["goal"])}</p>')
        for fi, f in enumerate(e["features"], 1):
            body.append(h(3, f"{sec}.{ei}.{fi}", f'{f["id"]} {f["title"]}', f["id"]))
            body.append(f'<p>{E(f["description"])}</p>')
            if f.get("use"):
                body.append(f'<div class="use"><b>Intended use</b><p>{E(f["use"])}</p></div>')
            body.append(req_table(f["requirements"], d))
            body.append('<h5 class="seqh">Screens</h5>' + screens_html(f["id"]))

    # 3 Non-functional
    sec += 1
    body.append(h(1, f"{sec}", "Non-functional requirements", "nonfunctional"))
    for ci, c in enumerate(d["nfr"], 1):
        body.append(h(2, f"{sec}.{ci}", f'NFR-{c["category"]} {c["name"]}', f'nfr-{c["category"]}'))
        body.append(req_table(c["requirements"], d))

    # Information architecture, design system, architecture, solution design
    for key, title, anchor in (("04-information-architecture", "Information architecture", "ia"), (None, "Design system", "ds"),
                               ("06-architecture", "Architecture", "architecture"), ("07-solution-design", "Solution design", "solution")):
        sec += 1
        body.append(h(1, f"{sec}", title, anchor))
        body.append(ds_html(h, sec) if key is None else chapter_html(key, h, sec))

    # Review points
    sec += 1
    body.append(h(1, f"{sec}", "Points for review", "review"))
    openr = [r for r in reqs if r["st"] != "Implemented"]
    body.append('<p>These requirements are not fully verified. Version 1.0 closes them with a test, a measurement or a decision.</p>')
    body.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Status</th><th>Requirement</th></tr></thead><tbody>' +
                "".join(f'<tr><td class="mono"><a href="#{r["id"]}">{r["id"]}</a></td><td>{status_cell(r["st"])}</td><td>{E(r["text"])}</td></tr>' for r in openr) + "</tbody></table></div>")

    # Planned chapters
    sec += 1
    body.append(h(1, f"{sec}", "Chapters in version 1.0", "planned"))
    body.append('<ol class="planned">' + "".join(f"<li><b>{E(t)}.</b> {E(x)}</li>" for t, x in PLANNED) + "</ol>")

    # 6 Glossary
    sec += 1
    body.append(h(1, f"{sec}", "Glossary", "glossary"))
    body.append('<dl class="gloss">' + "".join(f'<dt id="term-{re.sub(r"[^a-z0-9]+", "-", g["term"].lower())}">{E(g["term"])}</dt><dd>{E(g["text"])}</dd>' for g in sorted(d["glossary"], key=lambda g: g["term"].lower())) + "</dl>")

    # 7 Sources
    sec += 1
    body.append(h(1, f"{sec}", "Sources", "sources"))
    body.append('<dl class="gloss">' + "".join(f'<dt id="src-{k}" class="mono">{k}</dt><dd>{E(v)}</dd>' for k, v in d["sources"].items()) + "</dl>")

    # 8 Index
    sec += 1
    body.append(h(1, f"{sec}", "Index", "index"))
    body.append(h(2, f"{sec}.1", "Term index", "term-index"))
    items = []
    for g in sorted(d["glossary"], key=lambda g: g["term"].lower()):
        pat = re.compile(r"\b" + re.escape(g["term"].lower()), re.I)
        hits = [r["id"] for r in reqs if pat.search(r["text"])]
        anchor = "term-" + re.sub(r"[^a-z0-9]+", "-", g["term"].lower())
        items.append(f'<li><a href="#{anchor}"><b>{E(g["term"])}</b></a> ' + (", ".join(f'<a class="mono" href="#{i}">{i}</a>' for i in hits) if hits else '<span class="muted">glossary only</span>') + "</li>")
    body.append('<ul class="tindex">' + "".join(items) + "</ul>")
    body.append(h(2, f"{sec}.2", "ID index", "id-index"))
    groups = collections.OrderedDict()
    for e in d["epics"]:
        groups.setdefault(f'{e["id"]} {e["title"]}', []).extend([(e["id"], e["title"])] + [(f["id"], f["title"]) for f in e["features"]] + [(r["id"], "") for f in e["features"] for r in f["requirements"]])
    for c in d["nfr"]:
        groups.setdefault(f'NFR-{c["category"]} {c["name"]}', []).extend([(r["id"], "") for r in c["requirements"]])
    groups.update(ids_from_assets())
    body.append('<div class="idx">' + "".join(f'<div><h4>{E(g)}</h4><p>' + " ".join(f'<a class="mono" href="#{i}" title="{E(t)}">{i}</a>' for i, t in lst) + "</p></div>" for g, lst in groups.items()) + "</div>")

    toc_html = "".join(f'<li class="l{lv}"><a href="#{a}"><span class="num">{n}</span> {E(t)}</a></li>' for lv, n, t, a in toc if lv <= 2)
    hard, found, words = lint_summary
    return TEMPLATE.format(ver=E(ver), date=E(str(d["date"])), toc=toc_html, body="\n".join(body),
                           nreq=len(reqs), lint=f"{hard} hard findings in {words} words")

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>M4 Parking Check Specification v{ver}</title>
<meta name="description" content="Requirements specification for M4 Parking Check, version {ver}.">
<link rel="icon" href="../icons/icon-192.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&family=Overpass:wght@400;600;800;900&family=Overpass+Mono:wght@500;700&display=swap">
<style>
/* Layout: sticky table of contents on the left (top on phones), one reading column. App blue as accent. Priority and status use shape and text, not colour alone. */
:root{{--f-app:"Overpass",system-ui,sans-serif;--f-app-mono:"Overpass Mono",ui-monospace,monospace;--bg:#f7f8fa;--paper:#fff;--ink:#121a24;--muted:#4b5767;--line:#d3d9e1;--accent:#0b5cad;--soft:#e8f0fa;--f-body:"IBM Plex Sans",system-ui,sans-serif;--f-mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#0d1218;--paper:#151c25;--ink:#eef2f7;--muted:#a9b5c4;--line:#2d3947;--accent:#79b4ff;--soft:#13263d;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0d1218;--paper:#151c25;--ink:#eef2f7;--muted:#a9b5c4;--line:#2d3947;--accent:#79b4ff;--soft:#13263d;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.55 var(--f-body)}}
.wrap{{display:grid;grid-template-columns:300px minmax(0,1fr);max-width:1400px;margin:0 auto}}
nav.toc{{position:sticky;top:0;height:100vh;overflow:auto;padding:28px 20px 40px max(20px,env(safe-area-inset-left,0px));border-right:1px solid var(--line)}}
nav.toc h2{{font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}}
nav.toc ol{{list-style:none;margin:0;padding:0}}
nav.toc li a{{display:flex;gap:8px;color:var(--ink);text-decoration:none;padding:3px 6px;border-radius:5px;font-size:.92rem}}
nav.toc li a:hover{{background:var(--soft)}}
nav.toc li.l1{{margin-top:10px}} nav.toc li.l1 a{{font-weight:600}}
nav.toc li.l2 a{{padding-left:22px;color:var(--muted);font-size:.86rem}}
nav.toc .num{{font-family:var(--f-mono);color:var(--accent);min-width:2.6em}}
main{{padding:36px max(20px,env(safe-area-inset-right,0px)) 80px 48px;min-width:0}}
header.doc{{border-bottom:3px solid var(--accent);padding-bottom:18px;margin-bottom:10px}}
header.doc .kick{{font:600 .8rem var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}}
header.doc h1{{font-size:2.3rem;line-height:1.1;margin:.2em 0 .3em;letter-spacing:-.01em;text-wrap:balance}}
.meta{{display:flex;flex-wrap:wrap;gap:8px 22px;color:var(--muted);font-size:.9rem}}
.draft{{display:inline-block;border:2px dashed var(--ink);font:600 .8rem var(--f-mono);padding:2px 8px;border-radius:4px;color:var(--ink)}}
h2,h3,h4{{line-height:1.25;text-wrap:balance;scroll-margin-top:16px}}
h2{{font-size:1.65rem;margin:2.2em 0 .5em;padding-top:.4em;border-top:1px solid var(--line)}}
h3{{font-size:1.25rem;margin:1.8em 0 .4em}}
h4{{font-size:1.05rem;margin:1.4em 0 .3em}}
.num{{font-family:var(--f-mono);color:var(--accent);font-weight:600;margin-right:.3em}}
p{{max-width:72ch}}
.goal{{background:var(--soft);border-radius:8px;padding:10px 14px;max-width:none}}
.screens{{color:var(--muted);font-size:.9rem}}
.mono,.id{{font-family:var(--f-mono);font-size:.86em}}
a{{color:var(--accent)}}
.tw{{overflow-x:auto;margin:10px 0 18px;border:1px solid var(--line);border-radius:8px;background:var(--paper)}}
table{{border-collapse:collapse;width:100%;font-size:.92rem}}
th{{text-align:left;font-weight:600;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
tr:target td{{background:var(--soft)}}
table.req td.id{{white-space:nowrap}} table.req td.id a{{text-decoration:none;color:var(--ink);font-weight:600}}
table.req td.txt{{min-width:280px}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}}
tr.tot td{{border-top:2px solid var(--ink);font-weight:600}}
.prio{{display:inline-block;font:600 .74rem var(--f-mono);padding:2px 7px;border-radius:4px;border:1.5px solid var(--ink);white-space:nowrap}}
.p-must{{background:var(--ink);color:var(--paper)}}
.p-should{{background:transparent}}
.p-could{{border-style:dashed}}
.p-wont{{border-style:dotted;color:var(--muted)}}
.st{{white-space:nowrap;font-size:.86rem}} .st b{{font-size:1.05rem;margin-right:3px}}
ul.keys{{list-style:none;padding:0}} ul.keys li{{margin:6px 0}}
dl.gloss{{display:grid;grid-template-columns:max-content 1fr;gap:6px 20px;max-width:90ch}}
dl.gloss dt{{font-weight:600}} dl.gloss dd{{margin:0;color:var(--muted)}}
ul.tindex{{columns:2 320px;padding-left:18px}} ul.tindex li{{break-inside:avoid;margin:4px 0}}
.idx{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:4px 26px}}
.idx p{{margin:.2em 0 .8em;line-height:1.9}} .idx a{{margin-right:6px}}
.muted{{color:var(--muted)}}
ol.planned li{{margin:4px 0}}
footer{{margin-top:60px;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);padding-top:14px}}
:focus-visible{{outline:3px solid var(--accent);outline-offset:2px}}
@media (max-width:900px){{.wrap{{grid-template-columns:1fr}} nav.toc{{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:20px max(16px,env(safe-area-inset-right,0px)) 16px max(16px,env(safe-area-inset-left,0px))}} main{{padding:24px max(16px,env(safe-area-inset-right,0px)) 60px max(16px,env(safe-area-inset-left,0px))}} header.doc h1{{font-size:1.8rem}} nav.toc li.l2{{display:none}}}}
/* screens, figures, design system */
.use{{border-left:0;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:10px 0}} .use p{{margin:.3em 0 0}}
h5{{font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:16px 0 8px}}
.seq{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px;margin:6px 0 28px}}
figure{{margin:0}}
.sc{{background:var(--paper);border:1px solid var(--line);border-radius:10px;overflow:hidden;scroll-margin-top:16px}}
.sc:target{{outline:3px solid var(--accent)}}
.shot{{position:relative;line-height:0;background:#e9ecf0}} .shot img{{width:100%;height:auto;display:block}}
.sc .shot{{max-height:520px;overflow:hidden}}
.mk{{position:absolute;transform:translate(-50%,-50%);width:24px;height:24px;border-radius:50%;background:#ef7e0d;color:#1d1d1d;border:2px solid #121a24;font:700 13px/20px var(--f-mono);text-align:center;box-shadow:0 0 0 2px #fff}}
.mk.inl{{position:static;display:inline-block;transform:none;width:20px;height:20px;font-size:11px;line-height:16px;vertical-align:-3px;box-shadow:none}}
.sc figcaption{{padding:10px 12px 12px;font-size:.88rem}} .sc figcaption p{{margin:.3em 0}}
.scid{{font:600 .8rem var(--f-mono);margin-bottom:2px}} .scid a{{text-decoration:none}}
.mock{{display:inline-block;border:2px dashed var(--ink);border-radius:4px;padding:0 6px;font:700 .7rem var(--f-mono);text-transform:uppercase;margin-left:4px}}
ol.mkl{{list-style:none;padding:0;margin:.4em 0}} ol.mkl li{{margin:2px 0}}
.frs{{color:var(--muted)}}
.diag{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px;margin:12px 0 22px}}
.diag .dw{{overflow-x:auto}} .diag svg{{max-width:100%;height:auto;display:block;margin:0 auto}}
.diag figcaption{{color:#3f4b5a;font-size:.86rem;margin-top:8px}} .diag figcaption a{{color:#0b5cad}}
.swatch{{display:inline-block;width:18px;height:18px;border-radius:4px;border:1px solid var(--line);vertical-align:-4px;margin-right:6px}}
td.icn{{font:800 1.3rem var(--f-app)}}
.cmp{{border:1px solid var(--line);border-radius:10px;background:var(--paper);padding:14px;margin:14px 0;scroll-margin-top:16px}}
.cmp h4{{margin:0 0 10px}}
.cmpg{{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:18px;align-items:start}}
.shot.ds{{background:repeating-conic-gradient(#eef1f4 0 25%,#fff 0 50%) 0 0/16px 16px;border:1px solid var(--line);border-radius:6px}}
.darkimg{{margin-top:8px;font-size:.8rem}} .darkimg img{{max-width:100%;display:block;border:1px solid var(--line);border-radius:6px;margin-bottom:2px}}
table.kvs{{border-collapse:collapse;font-size:.86rem;margin-bottom:8px}} table.kvs th{{text-transform:none;letter-spacing:0;font-size:.82rem;padding:3px 12px 3px 0;border:0;color:var(--muted)}} table.kvs td{{padding:3px 0;border:0;font-family:var(--f-mono);font-size:.82rem}}
table.parts td{{font-size:.84rem}}
.strip{{margin:16px 0}} .stg{{display:flex;flex-wrap:wrap;gap:12px}}
.stc{{width:200px;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:8px}} .stc img{{max-width:100%;display:block;margin-bottom:6px}}
.stc figcaption{{font-size:.76rem;line-height:1.35;word-break:break-word}} .stc.same{{border-style:dashed}}
@media (max-width:760px){{.cmpg{{grid-template-columns:minmax(0,1fr)}}}}
.cmpg>*{{min-width:0}} table.kvs td{{word-break:break-word}} td.mono{{white-space:nowrap}}
@media (max-width:640px){{table.req thead{{display:none}} table.req,table.req tbody,table.req tr,table.req td{{display:block;width:100%}} table.req tr{{border-bottom:1px solid var(--line);padding:10px 12px}} table.req tr:last-child{{border-bottom:0}} table.req td{{border:0;padding:2px 0}} table.req td.txt{{min-width:0;margin:4px 0 8px}} table.req td:nth-child(n+3){{display:inline-block;width:auto;margin-right:12px;font-size:.84rem;color:var(--muted)}}}}
@media print{{nav.toc{{display:none}} .wrap{{display:block}} main{{padding:0}} .tw{{overflow:visible;border:0}} h2{{break-before:page}}}}
</style>
</head>
<body>
<div class="wrap">
<nav class="toc" aria-label="Table of contents"><h2>Contents</h2><ol>{toc}</ol></nav>
<main>
<header class="doc">
  <div class="kick">Requirements specification</div>
  <h1>M4 Parking Check</h1>
  <div class="meta"><span class="draft">Version {ver}</span><span>Date {date}</span><span>{nreq} requirements</span><span>Writing standard: ASD-STE100 (structural rules), {lint}</span></div>
</header>
{body}
<footer>Generated by spec/build.py from spec/requirements.yaml. Do not edit this file. Change the YAML file, raise the version and build again.</footer>
</main>
</div>
</body>
</html>
"""

def main():
    d = load()
    validate(d)
    load_assets(d)
    uses = [re.sub(r"'[^']*'", "TEXT", f["use"]) for e in d["epics"] for f in e["features"] if f.get("use")]
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write("\n\n".join(uses)); tmpu = fh.name
    ru = json.loads(subprocess.run([sys.executable, str(LINT), "--json", "--disable", "synonym-rotation", tmpu], capture_output=True, text=True).stdout or "{}")
    if ru.get("hard_count"):
        die("ASD-STE100 check failed on intended use: " + "; ".join(v["message"] for v in ru["violations"] if v.get("level") != "advisory"))
    hard, found, words = ste_check(d)
    if hard:
        die("ASD-STE100 check failed:\n  " + "\n  ".join(f"{i}: {rule}: {m}" for i, rule, m in found))
    for i, rule, m in found:
        print(f"advisory {i}: {rule}: {m}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"M4-Parking-Spec-v{d['version']}.html"
    if out.exists():
        die(f"{out.name} exists. A version is never overwritten. Raise 'version' in requirements.yaml.")
    out.write_text(build(d, (hard, found, words)), encoding="utf-8")
    print("wrote", out.relative_to(ROOT))
    write_index()

def write_index():
    """List every version. This page is a list, not a version, so the script renews it."""
    files = sorted(OUT_DIR.glob("M4-Parking-Spec-v*.html"), reverse=True)
    rows = "".join(f'<li><a href="{f.name}">{E(f.stem.replace("M4-Parking-Spec-", ""))}</a></li>' for f in files)
    (OUT_DIR / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>M4 Parking Check Specification</title><style>body{font:16px/1.6 system-ui,sans-serif;margin:0;padding:32px 16px;background:#f7f8fa;color:#121a24}'
        'main{max-width:640px;margin:0 auto}a{color:#0b5cad}@media (prefers-color-scheme:dark){body{background:#0d1218;color:#eef2f7}a{color:#79b4ff}}</style></head>'
        f'<body><main><h1>M4 Parking Check Specification</h1><p>All versions. The newest is first. Older versions stay unchanged.</p><ul>{rows}</ul></main></body></html>',
        encoding="utf-8")

if __name__ == "__main__":
    main()
