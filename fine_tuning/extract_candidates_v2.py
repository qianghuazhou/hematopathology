#!/usr/bin/env python3
"""Extract *unreviewed* clinical wording candidates from local HTML/TXT templates.

Stdlib only; no external services. This does NOT produce training pairs.
"""
import argparse, csv, hashlib, html, json, re
from html.parser import HTMLParser
from pathlib import Path

FILES = [
"bone_marrow_reporting_template_v18.html",
"bone_marrow_synoptic_who5_with_dx_v14.html",
"bm_report_tool_uhn_style_v2.html",
"cbc_smear_comment_generator_v91.html",
"flow_cytometry_reporting_tool.html",
"lymph_node_morphology_generator.html",
"lymph_node_reporting_workspace_v1.html",
"dr_delabie_style_lymphoma_generator_v16.html",
"lymphoma_synoptic_generator_who5_v34.html",
"hodgkin_synoptic_generator_v16.html",
"heme_bodyfluid_comment_generator.html",
"integrated_hematopathology_cytology.html",
"Comments.txt",
]
MEDICAL = re.compile(r"\b(?:lymphoma|lymphoid|leukemia|marrow|megakaryocyt\w*|erythroid|myeloid|plasma|blast\w*|immunohistochem\w*|cytomet\w*|CD\d+|PAX5|BCL2|BCL6|Ki-67|cyclin|neutrophil\w*|monocyt\w*|thrombocyt\w*|anemia|granulocyt\w*|kappa|lambda|clonal|cytogenetic|dysplas\w*|follicul\w*|hematopoie\w*|morpholog\w*|biopsy|aspirate|infiltrat\w*|reactive|EBER|MUM1|FISH|MYC)\b", re.I)
REPORT = re.compile(r"\b(?:sections show|the biopsy|the aspirate|the marrow|positive for|negative for|highlights|no evidence of|findings support|correlation with|recommend|consistent with|favou?rs?|proliferation index|approximately|not identified|limited by)\b", re.I)
NOISE = re.compile(r"document\.|window\.|getElementById|querySelector|addEventListener|function\s*\(|\bconst\s+|\blet\s+|\breturn\s+|\.innerHTML|\.textContent|grid-template|font-size|border-radius|localStorage|JSON\.stringify|=>|https?://|<[^>]+>", re.I)

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.buf = []; self.blocks = []
    def flush(self):
        if self.buf: self.blocks.append(" ".join(self.buf)); self.buf = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg"): self.flush(); self.skip += 1
        elif tag in ("p","div","li","option","label","h1","h2","h3","textarea","br","td"): self.flush()
    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg"): self.skip = max(0, self.skip - 1)
        elif tag in ("p","div","li","option","label","h1","h2","h3","textarea","td"): self.flush()
    def handle_data(self, data):
        if not self.skip: self.buf.append(data)

# Extracts simple JS quoted strings; never evaluates JS or interpolated templates.
JS_STRINGS = re.compile(r"""(?P<q>['"`])(?P<s>(?:\\.|(?!(?P=q)).)*?)(?P=q)""", re.S)

def candidates(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".txt":
        for line_no, line in enumerate(raw.splitlines(), 1):
            yield line, "text_line", line_no
    else:
        parser = Visible(); parser.feed(raw); parser.flush()
        for s in parser.blocks: yield s, "visible_html", None
        for match in JS_STRINGS.finditer(raw):
            yield match.group("s"), "js_literal", raw.count("\n", 0, match.start()) + 1

def classify(s):
    s = re.sub(r"\s+", " ", html.unescape(s.replace("\\n", " "))).strip()
    if len(s) < 35 or len(s) > 850 or NOISE.search(s) or "${" in s or "{" in s or "}" in s:
        return None
    if not MEDICAL.search(s): return None
    kind = "report_phrase" if REPORT.search(s) else "clinical_fragment" if len(s.split()) >= 8 else "clinical_option"
    priority = {"report_phrase":"high","clinical_fragment":"medium","clinical_option":"low"}[kind]
    return s, kind, priority

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, default=Path("fine_tuning/candidates_v2.jsonl"))
    p.add_argument("--review", type=Path, default=Path("fine_tuning/review_queue_50.csv"))
    p.add_argument("--limit", type=int, default=50)
    a = p.parse_args()
    rows = []; seen = set()
    for name in FILES:
        path = a.repo / name
        if not path.exists(): print("SKIP:", name); continue
        n = 0
        for raw, origin, line in candidates(path):
            result = classify(raw)
            if result is None: continue
            phrase, kind, priority = result
            key = phrase.casefold()
            if key in seen: continue
            seen.add(key); n += 1
            rows.append({"id":hashlib.sha256((name+phrase).encode()).hexdigest()[:16],
                         "source_file":name,"source_kind":origin,"source_line":line,
                         "candidate_type":kind,"priority":priority,
                         "candidate_text":phrase,"review_status":"unreviewed"})
        print(f"{name}: {n} filtered candidates")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False)+"\n")
    buckets = {name:[] for name in FILES}
    for row in rows: buckets[row["source_file"]].append(row)
    for bucket in buckets.values(): bucket.sort(key=lambda x: {"high":0,"medium":1,"low":2}[x["priority"]])
    selected = []
    while len(selected) < a.limit and any(buckets.values()):
        for name in FILES:
            if buckets[name] and len(selected) < a.limit: selected.append(buckets[name].pop(0))
    cols = ["id","source_file","source_kind","source_line","candidate_type","priority",
            "candidate_text","review_status","reviewer_notes","paired_input","approved_target_report"]
    with a.review.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for row in selected: w.writerow(row)
    print(f"Total: {len(rows)} UNREVIEWED candidates -> {a.out}")
    print(f"Review queue: {len(selected)} candidates -> {a.review}")
    print("These are NOT clinically validated examples or supervised training pairs.")

if __name__ == "__main__": main()
