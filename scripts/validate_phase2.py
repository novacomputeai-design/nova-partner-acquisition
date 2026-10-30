#!/usr/bin/env python3
"""Track A structural and deterministic policy-state tests.

This validates contract structure and executable synthetic *policy* cases.
It does NOT invoke LLM skills, connectors, email sending or private memory.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "partner-acquisition-orchestrator",
    "partner-account-discovery",
    "partner-account-intelligence",
    "partner-stakeholder-discovery",
    "partner-fit-qualification",
    "partner-outreach-preparation",
    "partner-relationship-operations",
    "partner-commercial-review",
)
REQUIRED_DOCS = (
    "README.md", "AGENTS.md", "docs/operating-contract.md",
    "docs/validation-plan.md", "docs/upstream-reuse-register.md",
    "schemas/partner-lead.schema.json", "evals/adversarial-cases.json",
    "evals/phase2-policy-cases.json",
)
errors = []

def record(message):
    errors.append(message)

for path in REQUIRED_DOCS:
    if not (ROOT / path).is_file():
        record("Missing required file: " + path)

for name in SKILLS:
    path = ROOT / ".agents" / "skills" / name / "SKILL.md"
    if not path.is_file():
        record("Missing skill: " + name)
        continue
    body = path.read_text(encoding="utf-8")
    metadata = re.match(r"\A---\r?\nname:\s*([a-z0-9-]+)\r?\ndescription:\s*(.+)\r?\n---\r?\n", body)
    if not metadata or metadata.group(1) != name or not metadata.group(2).strip():
        record("Invalid skill metadata: " + name)
    if "## Procedure" not in body or "## Output" not in body:
        record("Missing skill procedure or output: " + name)
    for phrase in ("AGENTS.md", "docs/operating-contract.md"):
        if phrase not in body:
            record("Missing common policy link in " + name + ": " + phrase)

def read_json(relative):
    try:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except Exception as exc:
        record("Invalid JSON at " + relative + ": " + str(exc))
        return None

schema = read_json("schemas/partner-lead.schema.json")
if schema:
    properties = schema.get("properties", {})
    if properties.get("segment", {}).get("const") != "COMMERCIAL_PARTNER":
        record("Wrong commercial segment discriminator")
    if not {"account", "opportunity", "contact_status", "outreach_status", "gates", "next_action"}.issubset(schema.get("required", [])):
        record("Missing mandatory lead fields")
    if not {"r0", "gate_a", "dispatch", "gate_b"}.issubset(properties.get("gates", {}).get("required", [])):
        record("Missing approval fields")

old = read_json("evals/adversarial-cases.json")
if old:
    ids = [c.get("id") for c in old]
    if len(old) != 16 or len(ids) != len(set(ids)):
        record("Expected 16 unique original adversarial cases")
    if any(c.get("outcome") != "NOT_RUN" for c in old):
        record("Original native-runtime cases must remain NOT_RUN")

def evaluate(inp):
    """Synthetic reference state guard; not an agent or email implementation."""
    suppressed = inp.get("suppressed", False)
    bad_address = inp.get("bounced_route", False)
    clear_history = inp.get("history_checked", False)
    current_role = inp.get("role_current", False)
    verified_route = inp.get("route_verified", False) and not bad_address
    person_ok = inp.get("person_relevant", False) and current_role and verified_route
    identity_clear = inp.get("identity_clear", False)
    fit = inp.get("fit", False) and inp.get("evidence_supported", False) and identity_clear
    r0 = inp.get("r0_approved", False)
    draft = fit and person_ok and clear_history and not suppressed and r0
    send = (draft and inp.get("gate_a_approved", False)
            and inp.get("dispatch_authorized", False)
            and inp.get("sender_ready", False)
            and inp.get("compliance_ready", False)
            and inp.get("prior_send", "NONE") == "NONE")
    proposal = (inp.get("buyer_requirement_confirmed", False)
                and inp.get("delivery_capacity_confirmed", False)
                and inp.get("gate_b_approved", False)
                and not suppressed)
    if suppressed:
        reason = "SUPPRESSED"
    elif inp.get("prior_send") == "SEND_UNCERTAIN":
        reason = "RECONCILE_SEND"
    elif inp.get("prior_send") == "SENT_CONFIRMED":
        reason = "EXISTING_TOUCH"
    elif not clear_history:
        reason = "HISTORY_UNKNOWN"
    elif not identity_clear:
        reason = "IDENTITY_CONFLICT"
    elif not current_role:
        reason = "ROLE_UNVERIFIED"
    elif not inp.get("person_relevant", False):
        reason = "PERSON_NOT_RELEVANT"
    elif not verified_route:
        reason = "ROUTE_UNVERIFIED"
    elif not fit:
        reason = "FIT_NOT_ESTABLISHED"
    elif not r0:
        reason = "R0_REQUIRED"
    elif not inp.get("gate_a_approved", False):
        reason = "GATE_A_REQUIRED"
    elif not inp.get("dispatch_authorized", False):
        reason = "DISPATCH_REQUIRED"
    elif not inp.get("sender_ready", False) or not inp.get("compliance_ready", False):
        reason = "SENDER_OR_COMPLIANCE_HOLD"
    else:
        reason = "READY_TO_SEND"
    return {"draft": draft, "send": send, "proposal": proposal, "reason": reason}

cases = read_json("evals/phase2-policy-cases.json")
if cases:
    seen = set()
    for case in cases:
        case_id = case.get("id")
        if not case_id or case_id in seen:
            record("Duplicate/blank policy case id: " + str(case_id))
            continue
        seen.add(case_id)
        expected = case.get("expected", {})
        if set(expected) != {"draft", "send", "proposal", "reason"}:
            record("Incomplete case expectation: " + case_id)
            continue
        observed = evaluate(case.get("input", {}))
        if observed != expected:
            record("Policy test FAILED " + case_id
                   + " expected=" + str(expected) + " observed=" + str(observed))
    if len(cases) < 16:
        record("Need at least 16 executable synthetic policy cases")

if errors:
    print("TRACK A: FAIL (" + str(len(errors)) + " problems)")
    for error in errors:
        print(" - " + error)
    sys.exit(1)

print("TRACK A: PASS")
print("Verified " + str(len(SKILLS)) + " skill files, documents, base JSON schemas, "
      + str(len(old)) + " unexecuted native scenarios and "
      + str(len(cases)) + " synthetic policy cases.")
print("NOT VERIFIED: native skill loading, actual LLM behavior, external sources,")
print("email dispatch, private history, customer conversion, or operational safety.")
