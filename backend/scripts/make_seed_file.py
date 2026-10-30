"""Build backend/data/demo_seed.json from the last dev eval run (no model calls).

Usage (from the repo root):  make seed-file
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.seed import SEED_FILE  # noqa: E402
from evals.cases import load_cases  # noqa: E402

NAME = sys.argv[1] if len(sys.argv) > 1 else "dev-effort-low"
RESULTS = Path(__file__).resolve().parents[1] / "evals" / "results" / f"{NAME}.json"

cases = {c.id: c for c in load_cases("dev")}
rows = json.loads(RESULTS.read_text(encoding="utf-8"))
items = []
for r in rows:
    case = cases.get(r["case"])
    if case is None or r["result"] is None:
        continue
    items.append({"name": case.candidate.name, "email": case.candidate.email, "role_id": "ai-engineer-latam",
                  "cv": case.cv, "reply": case.reply, "result": r["result"], "provider": config.LLM_PROVIDER})
SEED_FILE.parent.mkdir(exist_ok=True)
SEED_FILE.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(items)} seed submissions to {SEED_FILE}")
