#!/usr/bin/env python3
"""Read-only structural checks, not agent behavioral or connector verification."""
from pathlib import Path
import json, re, sys

root = Path(__file__).resolve().parents[1]
skills = (
    "partner-acquisition-orchestrator", "partner-account-discovery",
    "partner-account-intelligence", "partner-stakeholder-discovery",
    "partner-fit-qualification", "partner-outreach-preparation",
    "partner-relationship-operations", "partner-commercial-review",
)
errors = []
for name in skills:
    p = root / ".agents" / "skills" / name / "SKILL.md"
    if not p.exists():
        errors.append(f"Missing skill: {name}")
        continue
    s = p.read_text(encoding="utf-8")
    m = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---\n", s)
    if m is None or m.group(1) != name:
        errors.append(f"Invalid frontmatter: {name}")
    if "## Output" not in s:
        errors.append(f"Missing output section: {name}")
for path in ("README.md", "AGENTS.md", "docs/operating-contract.md",
             "docs/validation-plan.md", "docs/upstream-reuse-register.md"):
    if not (root / path).exists():
        errors.append(f"Missing required document: {path}")
cases = None
try:
    schema = json.loads((root / "schemas/partner-lead.schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["segment"]["const"] != "COMMERCIAL_PARTNER":
        errors.append("Wrong schema segment")
    if "gates" not in schema.get("required", []):
        errors.append("Missing mandatory gate status")
except Exception as e:
    errors.append(f"Lead schema invalid: {e}")
try:
    cases = json.loads((root / "evals/adversarial-cases.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in cases]
    if len(ids) < 16 or len(set(ids)) != len(ids):
        errors.append("Need at least 16 uniquely named adversarial cases")
    if any(c.get("outcome") != "NOT_RUN" for c in cases):
        errors.append("Unexecuted cases must remain NOT_RUN")
except Exception as e:
    errors.append(f"Evaluation case file invalid: {e}")
if errors:
    print("STATIC FOUNDATION: FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"STATIC FOUNDATION: PASS — {len(skills)} skill files; {len(cases)} unexecuted scenarios")
print("NOT verified: native skill activation, behavior, sending, compliance, private persistence or commercial outcomes")
