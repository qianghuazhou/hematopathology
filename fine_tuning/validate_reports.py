#!/usr/bin/env python3
"""Basic checks for curated supervised pathology report examples.

Requires explicit expected_checks for clinical assertions; this is not
an autonomous medical validation system.
"""
import argparse
import json
import re
from pathlib import Path

def validate(record):
    errors = []
    for key in ("id", "category", "source_file", "review_status", "source_findings", "expected_checks", "messages"):
        if key not in record:
            errors.append("missing field: " + key)
    messages = record.get("messages", [])
    if not isinstance(messages, list) or [m.get("role") for m in messages] != ["system", "user", "assistant"]:
        errors.append("messages must have system/user/assistant roles in order")
        return errors
    user = messages[1].get("content", "")
    report = messages[2].get("content", "")
    if not user.strip() or not report.strip():
        errors.append("empty input or report")
    if record.get("review_status") != "approved":
        errors.append("not approved for training")
    if record.get("source_findings", "").strip() != user.strip():
        errors.append("source_findings differs from user message")
    checks = record.get("expected_checks", {})
    for field in ("required_strings", "forbidden_strings"):
        if not isinstance(checks.get(field, []), list):
            errors.append(field + " must be a list")
    for required in checks.get("required_strings", []):
        if required not in report:
            errors.append("missing exact string: " + repr(required))
    for forbidden in checks.get("forbidden_strings", []):
        if forbidden in report:
            errors.append("forbidden exact string: " + repr(forbidden))
    for item in checks.get("marker_results", []):
        marker = item.get("marker")
        result = item.get("result")
        if not marker or not result:
            errors.append("marker_results entry requires marker and result")
            continue
        # Requires human-authored exact evidence; do not guess status from proximity.
        evidence = item.get("evidence")
        if not evidence or evidence not in report:
            errors.append(f"missing evidence for {marker}={result}: {evidence!r}")
    if checks.get("malignant_diagnosis"):
        lines = [s.strip() for s in report.splitlines() if s.strip().startswith("- ")]
        if not lines or not any(line[2:] == line[2:].upper() for line in lines):
            errors.append("no uppercase malignant diagnosis line")
    if re.search(r"\b(?:patient name|medical record number|health card number)\s*:", user, re.I):
        errors.append("possible identifiable patient field")
    return errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    args = ap.parse_args()
    ids = set()
    n = failed = 0
    for line_no, line in enumerate(args.data.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        n += 1
        try:
            record = json.loads(line)
            errors = validate(record)
            ident = record.get("id")
            if ident in ids:
                errors.append("duplicate id")
            ids.add(ident)
        except Exception as exc:
            errors = [f"invalid record: {exc}"]
        if errors:
            failed += 1
            print(f"FAIL line {line_no}: " + "; ".join(errors))
    print(f"Checked {n}; failed {failed}; passed {n-failed}")
    raise SystemExit(1 if failed else 0)

if __name__ == "__main__":
    main()
