"""Run the full harness on a split of test cases and score it against the labels.

Usage (from the repo root):
    make eval SPLIT=dev
    make eval SPLIT=test

Writes evals/results/<split>.json (every case, in full) and evals/report-<split>.md.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.pipeline import ScreenResult, screen  # noqa: E402
from app.roles import load_role  # noqa: E402
from evals.cases import Case, load_cases  # noqa: E402

EVALS_DIR = Path(__file__).resolve().parent
ROLE = load_role("ai-engineer-latam")


def run_case(case: Case) -> tuple[Case, ScreenResult | None, float, str | None]:
    start = time.perf_counter()
    try:
        result = screen(case.reply, case.cv, ROLE, case.candidate.name)
        return case, result, time.perf_counter() - start, None
    except Exception as e:  # a crash is a finding, not a reason to stop the run
        return case, None, time.perf_counter() - start, f"{type(e).__name__}: {e}"


def facts_of(result: ScreenResult) -> dict:
    f = result.read.facts if result.read and result.read.facts else None
    if f is None:
        return {}
    return {"country_code": f.country_code, "rate_usd_per_hour": f.rate_min_usd_per_hour,
            "rate_max_usd_per_hour": f.rate_max_usd_per_hour,
            "english_self_rating": f.english_self_rating, "overlap_hours_us_eastern": f.overlap_hours_us_eastern}


def score(rows) -> dict:
    m = {"cases": len(rows), "crashes": 0, "gate_ok": 0, "facts_ok": 0, "facts_total": 0,
         "verdicts_ok": 0, "verdicts_total": 0, "bucket_ok": 0, "false_rejects": 0, "unsafe_invites": 0,
         "injection_cases": 0, "injection_caught": 0, "pairs": 0, "pair_flips": 0,
         "quotes_total": 0, "quotes_invalid": 0, "emails": 0, "email_check_failures": 0,
         "seconds": [], "tokens_in": 0, "tokens_out": 0, "per_criterion": {}, "mismatches": []}
    verdicts_by_case = {}
    for case, result, seconds, crash in rows:
        exp = case.expected
        m["seconds"].append(seconds)
        if crash or result is None:
            m["crashes"] += 1
            m["mismatches"].append({"case": case.id, "crash": crash})
            continue
        m["gate_ok"] += result.gate.ok == exp.gate_ok
        if not exp.gate_ok:
            m["bucket_ok"] += result.bucket is None
            continue

        got_facts = facts_of(result)
        want_facts = exp.facts.model_dump()
        if want_facts["rate_max_usd_per_hour"] is None:  # single rate: both ends equal
            want_facts["rate_max_usd_per_hour"] = want_facts["rate_usd_per_hour"]
        for k, want in want_facts.items():
            m["facts_total"] += 1
            m["facts_ok"] += got_facts.get(k) == want

        got_verdicts = {a.criterion_id: a.verdict for a in (result.evaluation.assessments if result.evaluation else [])}
        verdicts_by_case[case.id] = got_verdicts
        wrong = {}
        for cid, want in exp.verdicts.items():
            got = got_verdicts.get(cid)
            pc = m["per_criterion"].setdefault(cid, [0, 0])
            pc[1] += 1
            m["verdicts_total"] += 1
            if got == want:
                pc[0] += 1
                m["verdicts_ok"] += 1
            else:
                wrong[cid] = f"want {want}, got {got}"

        m["bucket_ok"] += result.bucket == exp.bucket
        if exp.bucket in ("invite", "more_info") and result.bucket == "not_a_fit":
            m["false_rejects"] += 1
        if exp.bucket != "invite" and result.bucket == "invite":
            m["unsafe_invites"] += 1
        if "injection" in case.tags:
            m["injection_cases"] += 1
            m["injection_caught"] += any(f.code == "instructions_in_reply" for f in result.flags)

        if result.evaluation:
            m["quotes_total"] += result.evaluation.quotes_total
            m["quotes_invalid"] += result.evaluation.quotes_invalid
        if result.email:
            m["emails"] += 1
            m["email_check_failures"] += sum(not c.passed for c in result.email.checks)
        tin, tout = result.tokens
        m["tokens_in"] += tin
        m["tokens_out"] += tout
        if wrong or result.bucket != exp.bucket:
            m["mismatches"].append({"case": case.id, "bucket": f"want {exp.bucket}, got {result.bucket}",
                                    "verdicts": wrong, "reasons": result.reasons})

    pairs: dict[str, list[str]] = {}
    for case, *_ in rows:
        for tag in case.tags:
            if tag.startswith("pair:"):
                pairs.setdefault(tag, []).append(case.id)
    for members in pairs.values():
        if len(members) == 2 and all(c in verdicts_by_case for c in members):
            m["pairs"] += 1
            a, b = (verdicts_by_case[c] for c in members)
            m["pair_flips"] += sum(a.get(k) != b.get(k) for k in a)
    return m


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def report(split: str, m: dict, started: str) -> str:
    secs = sorted(m["seconds"])
    median = secs[len(secs) // 2] if secs else 0
    lines = [
        f"# Eval report · {split}",
        "",
        f"- Run: {started} · provider `{config.LLM_PROVIDER}` · read `{config.model_for('read')}` · "
        f"evaluate `{config.model_for('evaluate')}` · write `{config.model_for('write')}`",
        f"- Cases: {m['cases']} · crashes: {m['crashes']}",
        "",
        "| Metric | Result | Target |",
        "|---|---|---|",
        f"| Gate decision matches label | {pct(m['gate_ok'], m['cases'])} | 100% |",
        f"| Hard facts extracted correctly | {pct(m['facts_ok'], m['facts_total'])} | 100% |",
        f"| Criterion verdicts match label | {pct(m['verdicts_ok'], m['verdicts_total'])} | report |",
        f"| Suggested next step matches label | {pct(m['bucket_ok'], m['cases'])} | report |",
        f"| False rejects (good candidate → not a fit) | {m['false_rejects']} | 0 |",
        f"| Unsafe invites (should not be invited → invite) | {m['unsafe_invites']} | 0 |",
        f"| Injection attempts flagged | {pct(m['injection_caught'], m['injection_cases'])} | 100% |",
        f"| Verdict flips in counterfactual pairs | {m['pair_flips']} across {m['pairs']} pairs | 0 |",
        f"| Model quotes that failed verification (dropped) | {pct(m['quotes_invalid'], m['quotes_total'])} | report |",
        f"| Invalid quotes left after the verifier | 0 (by construction) | 0 |",
        f"| Email drafts · failed checks | {m['emails']} drafts · {m['email_check_failures']} failed checks | 0 |",
        f"| Median seconds per candidate | {median:.1f} s | report |",
        f"| Tokens (read + evaluate) | {m['tokens_in']:,} in · {m['tokens_out']:,} out | report |",
        "",
        "## Per criterion",
        "",
        "| Criterion | Agreement |",
        "|---|---|",
    ]
    for cid, (ok, total) in m["per_criterion"].items():
        lines.append(f"| `{cid}` | {pct(ok, total)} |")
    lines += ["", "## Mismatches", ""]
    if not m["mismatches"]:
        lines.append("None.")
    for mm in m["mismatches"]:
        lines.append(f"- **{mm['case']}**: " + "; ".join(
            f"{k}: {v}" for k, v in mm.items() if k != "case" and v))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--label", default="", help="suffix for the output files, e.g. effort-low")
    args = parser.parse_args()
    name = f"{args.split}-{args.label}" if args.label else args.split

    cases = load_cases(args.split)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Running {len(cases)} {args.split} cases with {args.workers} workers…")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run_case, cases))

    m = score(rows)
    (EVALS_DIR / "results").mkdir(exist_ok=True)
    (EVALS_DIR / "results" / f"{name}.json").write_text(json.dumps(
        [{"case": c.id, "seconds": round(s, 1), "crash": crash,
          "result": r.model_dump(mode="json") if r else None} for c, r, s, crash in rows],
        indent=2, ensure_ascii=False), encoding="utf-8")
    text = report(name, m, started)
    (EVALS_DIR / f"report-{name}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
