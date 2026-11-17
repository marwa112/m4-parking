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
PLANNED = [  # later chapters of the plan, shown in the TOC so the reviewer sees the full structure
    ("Architecture", "Context, components, data flow, deployment."),
    ("Technical specification", "Data model, rules engine, geometry matching, map labels, Android shell."),
    ("Data pipeline", "Sources, scripts, matching, schedule, sanity checks, manual refresh."),
    ("Solution design", "Design decisions (ADR) and their reasons."),
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
                'This draft contains the requirements catalogue for review. The later chapters follow in version 1.0.</p>')
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
            body.append('<p class="screens">Screens: <i>sequence SC-' + f["id"][3:] + '-1 … follows in version 1.0.</i></p>')
            body.append(req_table(f["requirements"], d))

    # 3 Non-functional
    sec += 1
    body.append(h(1, f"{sec}", "Non-functional requirements", "nonfunctional"))
    for ci, c in enumerate(d["nfr"], 1):
        body.append(h(2, f"{sec}.{ci}", f'NFR-{c["category"]} {c["name"]}', f'nfr-{c["category"]}'))
        body.append(req_table(c["requirements"], d))

    # 4 Review points
    sec += 1
    body.append(h(1, f"{sec}", "Points for review", "review"))
    openr = [r for r in reqs if r["st"] != "Implemented"]
    body.append('<p>These requirements are not fully verified. Version 1.0 closes them with a test, a measurement or a decision.</p>')
    body.append('<div class="tw"><table class="plain"><thead><tr><th>ID</th><th>Status</th><th>Requirement</th></tr></thead><tbody>' +
                "".join(f'<tr><td class="mono"><a href="#{r["id"]}">{r["id"]}</a></td><td>{status_cell(r["st"])}</td><td>{E(r["text"])}</td></tr>' for r in openr) + "</tbody></table></div>")

    # 5 Planned chapters
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap">
<style>
/* Layout: sticky table of contents on the left (top on phones), one reading column. App blue as accent. Priority and status use shape and text, not colour alone. */
:root{{--bg:#f7f8fa;--paper:#fff;--ink:#121a24;--muted:#4b5767;--line:#d3d9e1;--accent:#0b5cad;--soft:#e8f0fa;--f-body:"IBM Plex Sans",system-ui,sans-serif;--f-mono:"IBM Plex Mono",ui-monospace,monospace}}
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
