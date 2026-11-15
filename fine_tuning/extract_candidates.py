#!/usr/bin/env python3
"""Extract candidate wording from local reporting HTML/TXT files.

Offline, stdlib-only. Candidate phrases are NOT supervised training pairs.
No model calls, network calls, or clinical data generation.
"""
import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

SOURCES = [
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
    "diagnosis_templates_v3.html",
]

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("p", "li", "h1", "h2", "h3", "option", "label", "textarea"):
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in ("p", "li", "option", "textarea"):
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def candidates(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".html":
        parser = TextExtractor()
        parser.feed(raw)
        visible = "\n".join(parser.parts)
        # Capture quoted JS strings as *candidates*, not executable output.
        strings = re.findall(r'(?<!\\)(["\x27\x60])((?:(?!\1).){25,500})\1', raw, flags=re.S)
        lines = visible.splitlines() + [value for _, value in strings]
    else:
        lines = raw.splitlines()
    seen = set()
    for line in lines:
        phrase = clean(line)
        if len(phrase) < 25 or len(phrase) > 1000:
            continue
        if re.search(r"[{}<>]|\b(function|document\.|window\.|const |return |addEventListener)\b", phrase):
            continue
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        yield phrase

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("private_candidates.jsonl"))
    args = ap.parse_args()
    count = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as output:
        for name in SOURCES:
            path = args.repo / name
            if not path.exists():
                print(f"SKIP missing: {name}")
                continue
            n = 0
            for phrase in candidates(path):
                record = {"source_file": name, "candidate_text": phrase, "status": "unreviewed"}
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                n += 1
            print(f"{name}: {n} candidates")
    print(f"Total: {count} UNREVIEWED candidates in {args.out}")
    print("Do not train directly on candidate extraction output.")

if __name__ == "__main__":
    main()
