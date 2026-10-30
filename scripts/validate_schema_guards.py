#!/usr/bin/env python3
"""JSON Schema 2020-12 positive/negative tests for synthetic records only.

A schema and synthetic evidence strings cannot authenticate approvals,
provider email IDs or private records. Those require controlled Track C tests.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import json
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "schemas/partner-lead.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
def fingerprint(packet):
    fields = {key: packet[key] for key in ("sender", "recipient", "subject", "body", "attachments")}
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

F = fingerprint({"sender": "founder@example.test", "recipient": "partner@example.test",
                 "subject": "Exploratory introduction", "body": "Synthetic only", "attachments": []})
G = "b" * 64

sent = {
    "record_version": "1.0", "segment": "COMMERCIAL_PARTNER",
    "account": {"account_key": "SYN-A", "company": "Synthetic Consulting Inc",
                "source_url": "https://example.test/account",
                "checked_at": "2026-10-30T10:00:00-07:00"},
    "opportunity": {"category": "EXPLORATORY_PARTNER",
                    "evidence": "PARTNERSHIP_HYPOTHESIS",
                    "verdict": "PRIORITIZE", "hypothesis": "One bounded integration"},
    "contact_status": "PROFESSIONAL_REFERRAL_CONTACT",
    "contact": {"person_key": "SYN-P", "role": "Delivery Lead",
                "employer": "Synthetic Consulting Inc",
                "source_url": "https://example.test/people",
                "verified_at": "2026-10-30T10:00:00-07:00",
                "business_route_status": "VERIFIED", "history_status": "CLEAR"},
    "outreach_status": "SENT_CONFIRMED",
    "gates": {"r0": "APPROVED", "gate_a": "APPROVED",
              "dispatch": "APPROVED", "gate_b": "NOT_ASSESSED"},
    "cross_segment_history_checked": True, "suppression_checked": True,
    "suppression_clear": True, "sender_ready": True, "compliance_ready": True,
    "approval_refs": {"r0": "SYN-R0", "gate_a": "SYN-A1",
                      "dispatch": "SYN-D1", "gate_b": None},
    "approval_binding": {"sender": "founder@example.test",
                         "recipient": "partner@example.test",
                         "message_fingerprint": F,
                         "gate_a_message_fingerprint": F,
                         "dispatch_message_fingerprint": F},
    "message_packet": {"sender": "founder@example.test",
                       "recipient": "partner@example.test",
                       "subject": "Exploratory introduction", "body": "Synthetic only",
                       "fingerprint": F, "attachments": []},
    "attempt_evidence": {"operation_id": "SYN-OP1",
                         "attempted_at": "2026-10-30T10:01:00-07:00",
                         "message_fingerprint": F},
    "send_evidence": {"provider_message_id": "SYN-M1",
                      "sent_at": "2026-10-30T10:02:00-07:00",
                      "message_fingerprint": F},
    "next_action": "Reconcile synthetic provider event"
}

def mutate(obj, path, value):
    keys = path.split(".")
    node = obj
    for key in keys[:-1]:
        node = node[key]
    if value is DELETE:
        node.pop(keys[-1], None)
    else:
        node[keys[-1]] = value

class _Delete:
    pass
DELETE = _Delete()

def invariant_errors(record):
    """Cross-field consistency not expressible as standard JSON Schema equality."""
    errors = []
    status = record.get("outreach_status")
    approved = status in {"GATE_A_APPROVED", "DISPATCH_AUTHORIZED",
                          "SEND_ATTEMPTED", "SEND_UNCERTAIN", "SEND_FAILED",
                          "SENT_CONFIRMED"}
    if approved:
        packet = record.get("message_packet") or {}
        if all(k in packet for k in ("sender", "recipient", "subject", "body", "attachments")):
            if packet.get("fingerprint") != fingerprint(packet):
                errors.append("Message fingerprint does not represent exact content")
        binding = record.get("approval_binding") or {}
        for key in ("sender", "recipient"):
            if packet.get(key) != binding.get(key):
                errors.append("Approval binding mismatch: " + key)
        if not packet.get("fingerprint") or packet.get("fingerprint") != binding.get("message_fingerprint"):
            errors.append("Message fingerprint differs from binding")
        if packet.get("fingerprint") != binding.get("gate_a_message_fingerprint"):
            errors.append("Gate A fingerprint differs from message")
    if status in {"DISPATCH_AUTHORIZED", "SEND_ATTEMPTED", "SEND_UNCERTAIN",
                  "SEND_FAILED", "SENT_CONFIRMED"}:
        packet = record.get("message_packet") or {}
        binding = record.get("approval_binding") or {}
        if packet.get("fingerprint") != binding.get("dispatch_message_fingerprint"):
            errors.append("Dispatch fingerprint differs from message")
    if status in {"SEND_ATTEMPTED", "SEND_UNCERTAIN", "SEND_FAILED", "SENT_CONFIRMED"}:
        if (record.get("attempt_evidence") or {}).get("message_fingerprint") != (record.get("message_packet") or {}).get("fingerprint"):
            errors.append("Attempt fingerprint differs from message")
    if status == "SENT_CONFIRMED":
        if (record.get("send_evidence") or {}).get("message_fingerprint") != (record.get("message_packet") or {}).get("fingerprint"):
            errors.append("Sent fingerprint differs from message")
    return errors

def valid(record):
    return not list(validator.iter_errors(record)) and not invariant_errors(record)

positive = {
    "signed-off-synthetic-send": sent,
}
draft = deepcopy(sent)
draft["outreach_status"] = "DRAFTED"
draft["gates"] = dict.fromkeys(("r0", "gate_a", "dispatch", "gate_b"), "NOT_ASSESSED")
draft["approval_refs"] = dict.fromkeys(("r0", "gate_a", "dispatch", "gate_b"), None)
draft["approval_binding"] = None
draft["message_packet"] = None
draft["attempt_evidence"] = None
draft["send_evidence"] = None
draft["contact"] = None
draft["contact_status"] = "RESEARCH_ONLY"
draft["cross_segment_history_checked"] = None
draft["suppression_checked"] = None
draft["suppression_clear"] = None
draft["sender_ready"] = None
draft["compliance_ready"] = None
positive["incomplete-research-not-sent"] = draft
gate_a = deepcopy(sent)
gate_a["outreach_status"] = "GATE_A_APPROVED"
gate_a["gates"]["dispatch"] = "NOT_ASSESSED"
gate_a["approval_refs"]["dispatch"] = None
gate_a["approval_binding"]["dispatch_message_fingerprint"] = None
gate_a["attempt_evidence"] = None
gate_a["send_evidence"] = None
positive["approved-but-not-authorized"] = gate_a
uncertain = deepcopy(sent)
uncertain["outreach_status"] = "SEND_UNCERTAIN"
uncertain["send_evidence"] = None
positive["uncertain-with-attempt"] = uncertain
followup = deepcopy(sent)
followup["contact"]["history_status"] = "EXISTING"
positive["existing-contact-with-separate-authorization"] = followup

negative = [
    ("sent-without-contact", "contact", DELETE),
    ("sent-with-contact-null", "contact", None),
    ("sent-empty-company", "account.company", ""),
    ("sent-no-source", "account.source_url", ""),
    ("sent-no-contact-source", "contact.source_url", ""),
    ("sent-unknown-route", "contact.business_route_status", "UNVERIFIED"),
    ("sent-research-only-person", "contact_status", "RESEARCH_ONLY"),
    ("sent-suppressed-person", "contact.history_status", "SUPPRESSED"),
    ("sent-history-unchecked", "cross_segment_history_checked", False),
    ("sent-suppression-unchecked", "suppression_checked", False),
    ("sent-not-clear-suppression", "suppression_clear", False),
    ("sent-r0-unapproved", "gates.r0", "NOT_ASSESSED"),
    ("sent-gate-a-unapproved", "gates.gate_a", "NOT_ASSESSED"),
    ("sent-dispatch-unapproved", "gates.dispatch", "NOT_ASSESSED"),
    ("sent-missing-gate-a-evidence", "approval_refs.gate_a", None),
    ("sent-missing-dispatch-evidence", "approval_refs.dispatch", None),
    ("sent-no-message", "message_packet", None),
    ("sent-no-approval-binding", "approval_binding", None),
    ("sent-no-sender", "sender_ready", False),
    ("sent-compliance-unverified", "compliance_ready", False),
    ("sent-no-attempt", "attempt_evidence", None),
    ("sent-no-provider-proof", "send_evidence", None),
    ("sent-empty-provider-id", "send_evidence.provider_message_id", ""),
    ("sent-packet-changed", "message_packet.fingerprint", G),
    ("sent-body-tampered", "message_packet.body", "Changed body"),
    ("sent-subject-tampered", "message_packet.subject", "Changed subject"),
    ("sent-attachments-tampered", "message_packet.attachments", [{"name": "Synthetic.pdf", "sha256": G}]),
    ("sent-recipient-changed", "message_packet.recipient", "other@example.test"),
    ("sent-gate-a-mismatch", "approval_binding.gate_a_message_fingerprint", G),
    ("sent-dispatch-mismatch", "approval_binding.dispatch_message_fingerprint", G),
    ("sent-attempt-mismatch", "attempt_evidence.message_fingerprint", G),
    ("sent-provider-mismatch", "send_evidence.message_fingerprint", G),
    ("invalid-confirmed-buyer-claim", "opportunity.category", "BUYER_CONFIRMED"),
    ("sent-extra-undeclared-field", "secret", "SYNTHETIC"),
]
errors = []
for label, record in positive.items():
    if not valid(record):
        errors.append("Valid case rejected: " + label)
for label, path, value in negative:
    record = deepcopy(sent)
    mutate(record, path, value)
    if valid(record):
        errors.append("Invalid case accepted: " + label)
# A failed or uncertain send must also have a real attempt and authorization record.
for status in ("SEND_UNCERTAIN", "SEND_FAILED", "SEND_ATTEMPTED"):
    record = deepcopy(sent)
    record["outreach_status"] = status
    record["attempt_evidence"] = None
    record["send_evidence"] = None
    if valid(record):
        errors.append(status + " without attempt accepted")

if errors:
    print("SCHEMA GUARDS: FAIL")
    for error in errors:
        print(" - " + error)
    sys.exit(1)

print("SCHEMA GUARDS: PASS")
print(f"{len(positive)} positive, {len(negative) + 3} negative synthetic state cases")
print("Schema and fingerprints do not authenticate approval ownership or provider events.")
