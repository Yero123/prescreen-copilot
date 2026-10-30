"""Feedback loop: turn recruiter overrides into new draft eval cases.

Each submission with at least one override becomes a dev case whose label uses
the recruiter's verdict for the overridden criteria and the model's verdict for
the rest. Labels stay "draft" until reviewed.

Usage (from the repo root):  make export-overrides
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import store, views  # noqa: E402
from app.roles import load_role  # noqa: E402
from evals.cases import CASES_DIR  # noqa: E402

written = 0
for sub in store.list_latest_submissions():
    role = load_role(sub["role_id"])
    view = views.detail(sub, role)
    if not view["overrides"] or view["result"] is None:
        continue
    result = view["result"]
    facts = (result.get("read") or {}).get("facts") or {}
    verdicts = {a["criterion_id"]: a["verdict"] for a in result["evaluation"]["assessments"]}
    slug = re.sub(r"[^a-z0-9]+", "-", sub["candidate"]["email"].split("@")[0].lower()).strip("-")
    case_id = f"override-{slug}-{sub['id']}"
    case = {
        "id": case_id, "split": "dev", "tags": ["from_override"],
        "candidate": {"name": sub["candidate"]["name"], "email": sub["candidate"]["email"]},
        "cv": sub["cv"], "reply": sub["reply"],
        "expected": {
            "gate_ok": True,
            "facts": {"country_code": facts.get("country_code"), "rate_usd_per_hour": facts.get("rate_min_usd_per_hour"),
                      "rate_max_usd_per_hour": facts.get("rate_max_usd_per_hour")
                      if facts.get("rate_max_usd_per_hour") != facts.get("rate_min_usd_per_hour") else None,
                      "english_self_rating": facts.get("english_self_rating"),
                      "overlap_hours_us_eastern": facts.get("overlap_hours_us_eastern")},
            "verdicts": verdicts,
            "bucket": view["decision"] or view["suggested_bucket"],
            "why": "From recruiter overrides: " + "; ".join(
                f"{cid} → {o['verdict']} ({o.get('reason') or 'no reason given'})" for cid, o in view["overrides"].items()),
        },
        "label_status": "draft",
    }
    path = CASES_DIR / "dev" / f"{case_id}.json"
    path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written += 1
    print(f"wrote {path.name}")
print(f"{written} case(s) exported. Review their labels before counting them.")
