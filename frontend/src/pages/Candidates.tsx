import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Bucket, Row } from "../types";
import { BucketPill, Spinner, VERDICT, displayName, timeAgo } from "../ui";

type Tab = "all" | Bucket | "other";

const TABS: { id: Tab; label: string }[] = [
  { id: "all", label: "All" },
  { id: "invite", label: "Invite to call" },
  { id: "more_info", label: "Needs more info" },
  { id: "needs_review", label: "Needs your review" },
  { id: "not_a_fit", label: "Not a fit" },
  { id: "other", label: "Not applications" },
];

function nextStep(r: Row): Tab {
  if (r.status !== "done" || r.not_an_application) return "other";
  return (r.decision ?? r.suggested_bucket ?? "other") as Tab;
}

export default function Candidates({ blind, onToggleBlind }: { blind: boolean; onToggleBlind: () => void }) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("all");

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    const load = () =>
      api<Row[]>("/api/submissions")
        .then((data) => {
          if (!alive) return;
          setRows(data);
          setError("");
          if (data.some((r) => r.status === "processing")) timer = window.setTimeout(load, 4000);
        })
        .catch((e) => alive && setError(e.message));
    load();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: rows?.length ?? 0 };
    rows?.forEach((r) => (c[nextStep(r)] = (c[nextStep(r)] ?? 0) + 1));
    return c;
  }, [rows]);

  const shown = (rows ?? []).filter((r) => tab === "all" || nextStep(r) === tab);

  return (
    <main>
      <div className="funnel" aria-label="Hiring stages">
        <span className="stage">Applied</span>
        <span aria-hidden="true" className="muted">→</span>
        <span className="stage stage-live">
          Pre-screen <span className="mono">{counts.all}</span>
        </span>
        <span aria-hidden="true" className="muted">→</span>
        <span className="stage">HR call</span>
        <span aria-hidden="true" className="muted">→</span>
        <span className="stage">Technical</span>
        <span aria-hidden="true" className="muted">→</span>
        <span className="stage">Submitted</span>
        <span className="muted small" style={{ marginLeft: 4 }}>
          Only pre-screen is part of this tool.
        </span>
      </div>

      <div className="review-head">
        <div>
          <h1>Pre-screen</h1>
          <p className="muted">Replies to the screening questionnaire for AI Engineer (LatAm)</p>
        </div>
        <div className="row-wrap">
          <button className="btn" aria-pressed={blind} onClick={onToggleBlind}>
            {blind ? "Blind mode on" : "Blind mode"}
          </button>
          <a className="btn btn-primary" href="#/add" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}>
            Add a reply
          </a>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Filter by next step">
        {TABS.map((t) => (
          <button key={t.id} className="tab" role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
            <span className="count">{counts[t.id] ?? 0}</span>
          </button>
        ))}
      </div>

      {error && <div className="banner banner-bad">{error}</div>}

      <div className="table-wrap">
        <div className="table">
          <div className="trow thead">
            <span>Candidate</span>
            <span>Location</span>
            <span>Rate</span>
            <span>Criteria</span>
            <span>Flags</span>
            <span>Next step</span>
            <span />
          </div>
          {rows === null && !error && (
            <div className="empty" role="status">
              <Spinner />
              Loading replies…
            </div>
          )}
          {rows !== null && shown.length === 0 && <p className="empty">Nobody in this group right now.</p>}
          {shown.map((r) => (
            <a key={r.id} className="trow" href={`#/c/${r.id}`}>
              <span style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
                <span style={{ fontWeight: 600 }}>{displayName(r.candidate.name, r.candidate.id, blind)}</span>
                <span className="muted small">{timeAgo(r.received_at)}</span>
              </span>
              <span>{r.country ?? <span className="muted">—</span>}</span>
              <span className="mono">{r.rate ?? <span className="muted">—</span>}</span>
              <span className="marks">
                {r.status === "done" && !r.not_an_application
                  ? r.marks.map((m) => {
                      const v = m.verdict ? VERDICT[m.verdict] : null;
                      return (
                        <span key={m.criterion_id} className={`mark ${v?.cls ?? ""}`} title={`${m.importance.toUpperCase()} · ${m.text}: ${v?.label ?? "no verdict"}`}>
                          {v?.sym ?? "·"}
                        </span>
                      );
                    })
                  : null}
              </span>
              <span className="flag">{r.flags[0] ? `⚠ ${r.flags[0].slice(0, 70)}${r.flags[0].length > 70 ? "…" : ""}` : <span className="muted">—</span>}</span>
              <span>
                {r.status === "processing" && <span className="pill b-none"><Spinner />Screening…</span>}
                {r.status === "error" && <span className="pill v-no">Failed · open to retry</span>}
                {r.status === "done" && <BucketPill bucket={r.not_an_application ? null : r.decision ?? r.suggested_bucket} decided={!!r.decision} />}
              </span>
              <span aria-hidden="true" className="muted" style={{ fontSize: 18 }}>
                ›
              </span>
            </a>
          ))}
        </div>
      </div>
      <p className="muted small">
        One mark per criterion, in the order set in Role setup: ✓ meets · ? not enough evidence · ✗ does not meet · ! needs your review. The copilot never scores or ranks candidates.
      </p>
    </main>
  );
}
