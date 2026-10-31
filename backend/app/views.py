"""What the recruiter sees: the stored result with their own overrides and decisions applied.

An override changes a verdict; the suggested next step is then recomputed by the
same triage rules in code, without calling a model.
"""

from app.pipeline import ScreenResult
from app.roles import Role
from app.rules import COUNTRY_NAMES
from app.schemas import EmailDraft
from app.triage import triage


def _events(sub: dict):
    overrides, decision, edited, approved, regenerated = {}, None, None, False, None
    for e in sub["events"]:
        p = e["payload"]
        if e["kind"] == "override":
            if p.get("verdict") is None:
                overrides.pop(p["criterion_id"], None)
            else:
                overrides[p["criterion_id"]] = p
        elif e["kind"] == "decision":
            decision = p.get("bucket")
        elif e["kind"] == "email_edited":
            edited = p.get("body")
            approved = False  # the approval covered the previous text
        elif e["kind"] == "email_approved":
            approved = True
        elif e["kind"] == "email_regenerated":
            regenerated = p.get("draft")
            edited, approved = None, False
    return overrides, decision, edited, approved, regenerated


def detail(sub: dict, role: Role) -> dict:
    overrides, decision, edited, approved, regenerated = _events(sub)
    raw = sub["result"]
    view = {
        "id": sub["id"], "role_id": sub["role_id"], "status": sub["status"], "received_at": sub["received_at"],
        "candidate": sub["candidate"], "reply": sub["reply"], "cv": sub["cv"], "history": sub["history"],
        "overrides": overrides, "decision": decision,
        "result": None, "suggested_bucket": None, "model_bucket": None, "reasons": [],
        "email": None, "email_edited_body": edited, "email_approved": approved, "email_outdated": False,
    }
    if raw is None:
        return view

    result = ScreenResult.model_validate(raw)
    view["model_bucket"] = result.bucket
    suggested, reasons = result.bucket, result.reasons
    if result.evaluation is not None and result.evaluation.ok and result.rules is not None:
        for a in result.evaluation.assessments:
            o = overrides.get(a.criterion_id)
            if o:
                a.notes.append(f"overridden_from:{a.verdict}")
                a.verdict = o["verdict"]
        suggested, reasons = triage(role, result.rules, result.evaluation, result.flags)
    view["result"] = result.model_dump(mode="json")
    view["suggested_bucket"] = suggested
    view["reasons"] = reasons

    email = EmailDraft.model_validate(regenerated) if regenerated else result.email
    view["email"] = email.model_dump(mode="json") if email else None
    current = decision or suggested
    view["email_outdated"] = bool(email) and email.template != current
    return view


def row(sub: dict, role: Role) -> dict:
    d = detail(sub, role)
    result = d["result"] or {}
    facts = ((result.get("read") or {}).get("facts")) or {}
    rate = None
    lo, hi = facts.get("rate_min_usd_per_hour"), facts.get("rate_max_usd_per_hour")
    if lo is not None:
        rate = f"${lo:g}/h" if lo == hi or hi is None else f"${lo:g}–{hi:g}/h"
    marks = []
    evaluation = result.get("evaluation") or {}
    by_id = {a["criterion_id"]: a for a in evaluation.get("assessments", [])}
    for c in role.criteria:
        a = by_id.get(c.id)
        marks.append({"criterion_id": c.id, "importance": c.importance, "text": c.text,
                      "verdict": a["verdict"] if a else None})
    flags = [f["message"] for f in result.get("flags", [])]
    return {
        "id": d["id"], "status": d["status"], "received_at": d["received_at"], "candidate": d["candidate"],
        "country": COUNTRY_NAMES.get(facts.get("country_code"), facts.get("country_code")), "rate": rate,
        "marks": marks, "flags": flags,
        "not_an_application": d["status"] == "done" and result.get("bucket") is None and not result.get("evaluation"),
        "suggested_bucket": d["suggested_bucket"], "decision": d["decision"],
        "email_approved": d["email_approved"],
    }
