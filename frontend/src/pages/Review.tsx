import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api";
import type { Assessment, Bucket, Detail, Role, Verdict } from "../types";
import { BUCKET_LABEL, BucketPill, VERDICT, VerdictPill, displayName, timeAgo } from "../ui";

type Quote = { key: string; quote: string };

function quotePattern(quote: string): RegExp | null {
  const words = quote.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  const esc = words.map((w) =>
    w
      .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
      .replace(/['’‘]/g, "['’‘]")
      .replace(/["“”]/g, '["“”]')
      .replace(/[-–—]/g, "[-–—]"),
  );
  return new RegExp(esc.join("\\s+"), "i");
}

function highlight(text: string, quotes: Quote[], focus: string | null): ReactNode[] {
  const ranges: { start: number; end: number; key: string }[] = [];
  for (const q of quotes) {
    const re = quotePattern(q.quote);
    const m = re ? re.exec(text) : null;
    if (m && !ranges.some((r) => m.index < r.end && m.index + m[0].length > r.start)) {
      ranges.push({ start: m.index, end: m.index + m[0].length, key: q.key });
    }
  }
  ranges.sort((a, b) => a.start - b.start);
  const out: ReactNode[] = [];
  let at = 0;
  for (const r of ranges) {
    if (r.start > at) out.push(text.slice(at, r.start));
    out.push(
      <mark key={r.key} id={`q-${r.key}`} className={focus === r.key ? "focus" : undefined}>
        {text.slice(r.start, r.end)}
      </mark>,
    );
    at = r.end;
  }
  out.push(text.slice(at));
  return out;
}

const OVERRIDE_CHOICES: Verdict[] = ["meets", "not_enough_evidence", "does_not_meet", "needs_review"];

function CriterionCard({
  a,
  overridden,
  onFocus,
  onOverride,
  busy,
}: {
  a: Assessment;
  overridden?: { verdict: Verdict; reason: string };
  onFocus: (key: string) => void;
  onOverride: (verdict: Verdict | null, reason: string) => void;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<Verdict>(a.verdict);
  const [reason, setReason] = useState("");
  const original = a.notes.find((n) => n.startsWith("overridden_from:"))?.split(":")[1] as Verdict | undefined;
  return (
    <div className="crit">
      <div className="crit-top">
        <span>
          <span className="tag">{a.importance}</span>
          {a.criterion_text}
        </span>
        <button className="btn-link small" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          {open ? "Close" : "Override"}
        </button>
      </div>
      <div className="row-wrap">
        <VerdictPill verdict={a.verdict} />
        {a.evidence.map((e, i) => (
          <button key={i} className="chip" onClick={() => onFocus(`${a.criterion_id}-${i}`)} title={e.quote}>
            {e.source} →
          </button>
        ))}
      </div>
      <p className="small muted">{a.rationale}</p>
      {a.follow_up_question && (
        <p className="small">
          <span className="muted">Ask: </span>
          {a.follow_up_question}
        </p>
      )}
      {overridden && (
        <p className="small" style={{ color: "var(--accent)" }}>
          Changed by you{original ? ` (the model said “${VERDICT[original].label}”)` : ""}
          {overridden.reason ? `: ${overridden.reason}` : ""}. Saved as a correction for the evals.
        </p>
      )}
      {open && (
        <div className="stack" style={{ gap: 8 }}>
          <div className="row-wrap">
            {OVERRIDE_CHOICES.map((v) => (
              <button key={v} className="btn small" aria-pressed={choice === v} onClick={() => setChoice(v)}>
                {VERDICT[v].label}
              </button>
            ))}
          </div>
          <input
            type="text"
            aria-label="Reason for the change"
            placeholder="Why? (optional, helps the evals)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="row-wrap">
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={() => {
                onOverride(choice, reason);
                setOpen(false);
              }}
            >
              Save correction
            </button>
            {overridden && (
              <button className="btn" disabled={busy} onClick={() => onOverride(null, "")}>
                Undo my correction
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Review({ id, blind }: { id: number; blind: boolean }) {
  const [d, setD] = useState<Detail | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [focus, setFocus] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    const load = () =>
      api<Detail>(`/api/submissions/${id}`)
        .then((data) => {
          if (!alive) return;
          setD(data);
          if (data.status === "processing") timer = window.setTimeout(load, 3000);
        })
        .catch((e) => alive && setError(e.message));
    load();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [id]);

  useEffect(() => {
    if (d && !role) api<{ role: Role }>(`/api/roles/${d.role_id}`).then((r) => setRole(r.role)).catch(() => {});
  }, [d, role]);

  useEffect(() => {
    if (focus) document.getElementById(`q-${focus}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus]);

  const act = async (path: string, body?: unknown) => {
    setBusy(true);
    setError("");
    try {
      setD(await api<Detail>(path, { method: "POST", body }));
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };

  const result = d?.result ?? null;
  const assessments = result?.evaluation?.assessments ?? [];
  const quotesBySource = useMemo(() => {
    const map: Record<string, Quote[]> = {};
    assessments.forEach((a) =>
      a.evidence.forEach((e, i) => (map[e.source] ??= []).push({ key: `${a.criterion_id}-${i}`, quote: e.quote })),
    );
    return map;
  }, [assessments]);

  if (error && !d) return <main><div className="banner banner-bad">{error}</div></main>;
  if (!d) return <main><p className="muted">Loading…</p></main>;

  const name = displayName(d.candidate.name, d.candidate.id, blind);
  const current: Bucket | null = d.decision ?? d.suggested_bucket;
  const questionText = (qid: string) => role?.questionnaire.find((q) => q.id === qid)?.text ?? "";
  const answers = result?.read?.answers ?? {};
  const facts = result?.read?.facts;

  return (
    <main>
      <div className="review-head">
        <div className="row-wrap">
          <a className="btn" href="#/" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}>
            ← All candidates
          </a>
          <div>
            <h1>{name}</h1>
            <p className="muted small">
              {blind ? "Email hidden in blind mode" : d.candidate.email} · received {timeAgo(d.received_at)}
              {d.history.length > 1 ? ` · reply ${d.history.findIndex((h) => h.id === d.id) + 1} of ${d.history.length}` : ""}
            </p>
          </div>
        </div>
        {d.status === "done" && <span>Suggested: <BucketPill bucket={d.suggested_bucket} /></span>}
      </div>

      {error && <div className="banner banner-bad">{error}</div>}
      {d.status === "processing" && (
        <div className="banner banner-info">Screening this reply: reading, checking the rules and the evidence. This takes about 20–40 seconds.</div>
      )}
      {d.status === "error" && <div className="banner banner-bad">Screening failed for this reply. Add it again or read it yourself.</div>}

      {result && !result.gate.ok && (
        <div className="banner banner-warn">
          <strong>Not an application:</strong> {result.gate.message} <span className="small">({result.gate.checked_by === "code" ? "checked by code" : "checked by the model"})</span>
        </div>
      )}

      {result?.flags.map((f) => (
        <div key={f.code} className="banner banner-warn">
          <strong>Why it needs you:</strong> {f.message}
        </div>
      ))}
      {d.suggested_bucket && d.suggested_bucket !== "invite" && !result?.flags.length && d.reasons.length > 0 && (
        <div className={`banner ${d.suggested_bucket === "needs_review" ? "banner-warn" : "banner-info"}`}>
          <strong>{BUCKET_LABEL[d.suggested_bucket]}:</strong> {d.reasons.join(" · ")}
        </div>
      )}

      {d.status === "done" && (
        <div className="split">
          <section className="panel" aria-labelledby="answers-title">
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <h2 id="answers-title">Answers and CV</h2>
              <span className="muted small">Highlights are the quotes used as evidence</span>
            </div>
            {Object.keys(answers).length > 0 ? (
              Object.entries(answers)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([qid, text]) => (
                  <div key={qid} className="answer">
                    <span className="answer-label">
                      <span className="mono">{qid}</span> · {questionText(qid)}
                    </span>
                    <p>{highlight(text, quotesBySource[qid] ?? [], focus)}</p>
                  </div>
                ))
            ) : (
              <div className="answer">
                <span className="answer-label">Original email</span>
                <p>{d.reply}</p>
              </div>
            )}
            {role && result?.read?.ok && role.questionnaire.filter((q) => !(q.id in answers)).length > 0 && (
              <p className="small muted">
                Not answered: {role.questionnaire.filter((q) => !(q.id in answers)).map((q) => q.id).join(", ")}
              </p>
            )}
            <div className="answer" style={{ borderTop: "1px dashed #d5d9e0", paddingTop: 12 }}>
              <span className="answer-label">CV</span>
              <p>{highlight(d.cv || "(no CV)", quotesBySource["CV"] ?? [], focus)}</p>
            </div>
          </section>

          <div className="stack">
            {assessments.length > 0 && (
              <section className="panel" aria-labelledby="criteria-title">
                <h2 id="criteria-title">Criteria</h2>
                {assessments.map((a) => (
                  <CriterionCard
                    key={a.criterion_id}
                    a={a}
                    overridden={d.overrides[a.criterion_id]}
                    busy={busy}
                    onFocus={setFocus}
                    onOverride={(verdict, reason) =>
                      act(`/api/submissions/${d.id}/overrides`, { criterion_id: a.criterion_id, verdict, reason })
                    }
                  />
                ))}
              </section>
            )}

            {result?.rules && (
              <section className="panel panel-rules" aria-labelledby="rules-title">
                <h2 id="rules-title">Rules · checked by code, not AI</h2>
                {result.rules.checks.map((c) => (
                  <div key={c.rule} className="rule-line">
                    <span className={`rule-${c.status}`}>{c.status === "pass" ? "✓" : c.status === "fail" ? "✗" : "?"}</span>
                    <span>
                      <strong style={{ fontWeight: 600 }}>{c.label}</strong> <span className="muted">{c.detail}</span>
                    </span>
                  </div>
                ))}
              </section>
            )}

            {result?.gate.ok && (
              <section className="panel" aria-labelledby="decision-title">
                <h2 id="decision-title">Your decision</h2>
                <div className="row-wrap">
                  {(["invite", "more_info", "not_a_fit"] as Bucket[]).map((b) => (
                    <button
                      key={b}
                      className="btn"
                      aria-pressed={d.decision === b}
                      disabled={busy}
                      onClick={() => act(`/api/submissions/${d.id}/decision`, { bucket: d.decision === b ? null : b })}
                    >
                      {b === "invite" ? "Invite to call" : b === "more_info" ? "Ask for more info" : "Not a fit"}
                    </button>
                  ))}
                </div>
                <p className="small muted">The copilot suggests. You decide. It never rejects anyone on its own.</p>
              </section>
            )}

            {result?.gate.ok && (
              <section className="panel" aria-labelledby="email-title">
                <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                  <h2 id="email-title">Email draft{d.email ? ` · ${BUCKET_LABEL[d.email.template]}` : ""}</h2>
                  {d.email && !editing && (
                    <button
                      className="btn small"
                      onClick={() => {
                        setDraft(d.email_edited_body ?? d.email!.body);
                        setEditing(true);
                      }}
                    >
                      Edit
                    </button>
                  )}
                </div>
                {d.email_outdated && current && (
                  <div className="banner banner-info small">
                    This draft was written for “{BUCKET_LABEL[d.email!.template]}”, but the next step is now “{BUCKET_LABEL[current]}”.{" "}
                    <button className="btn-link" disabled={busy} onClick={() => act(`/api/submissions/${d.id}/email/regenerate`)}>
                      {busy ? "Writing…" : "Write a new draft"}
                    </button>
                  </div>
                )}
                {!d.email && current && current !== "needs_review" && (
                  <div className="row-wrap">
                    <p className="muted">No draft yet for this step.</p>
                    <button className="btn" disabled={busy} onClick={() => act(`/api/submissions/${d.id}/email/regenerate`)}>
                      {busy ? "Writing… (about 10 seconds)" : "Write a draft"}
                    </button>
                  </div>
                )}
                {!d.email && current === "needs_review" && (
                  <p className="muted">This one needs your call first. Choose a decision above, then write a draft.</p>
                )}
                {d.email && (
                  <>
                    <p className="small muted">To: {blind ? "hidden" : d.candidate.email} · Subject: {d.email.subject}</p>
                    {editing ? (
                      <>
                        <label htmlFor="email-body">Email text</label>
                        <textarea id="email-body" rows={12} value={draft} onChange={(e) => setDraft(e.target.value)} />
                        <div className="row-wrap">
                          <button
                            className="btn btn-primary"
                            disabled={busy || !draft.trim()}
                            onClick={async () => (await act(`/api/submissions/${d.id}/email/edit`, { body: draft })) && setEditing(false)}
                          >
                            Save text
                          </button>
                          <button className="btn" onClick={() => setEditing(false)}>
                            Cancel
                          </button>
                        </div>
                      </>
                    ) : d.email_edited_body ? (
                      <>
                        <p className="email-para">{d.email_edited_body}</p>
                        <p className="small" style={{ color: "var(--warn)" }}>Edited by you.</p>
                      </>
                    ) : (
                      <div className="stack" style={{ gap: 6 }}>
                        {d.email.body.split("\n\n").map((para, i) => {
                          const p = d.email!.paragraphs.find((x) => x.text === para);
                          const ids = p?.based_on ?? [];
                          const cls = ids.some((x) => x.startsWith("E")) ? "grounded" : ids.some((x) => /^[MR]/.test(x)) ? "ask" : "";
                          return (
                            <div key={i} className={`email-para ${cls}`}>
                              {para}
                              {ids.length > 0 && (
                                <span className="row-wrap" style={{ display: "inline-flex", marginLeft: 6 }}>
                                  {ids.map((x) => (
                                    <span key={x} className="mono small" title={d.email!.sources[x]} style={{ border: "1px solid #c9d2f5", borderRadius: 5, padding: "0 6px", background: "#fff" }}>
                                      {x}
                                    </span>
                                  ))}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                    <div className="stack" style={{ gap: 2, background: "#f7f8fa", borderRadius: 8, padding: "10px 12px" }}>
                      <span className="small muted">
                        Checked before sending · written by {d.email.written_by === "code" ? "a template (code)" : "the model"}
                      </span>
                      {d.email.checks.map((c) => (
                        <span key={c.name} className={c.passed ? "check-ok" : "check-bad"}>
                          {c.passed ? "✓" : "✗"} {c.name}
                          {c.detail ? ` (${c.detail})` : ""}
                        </span>
                      ))}
                    </div>
                    <div className="row-wrap">
                      <button
                        className="btn btn-primary"
                        disabled={busy || d.email_approved || d.email.checks.some((c) => !c.passed) && !d.email_edited_body}
                        onClick={() => act(`/api/submissions/${d.id}/email/approve`)}
                      >
                        {d.email_approved ? "Approved ✓" : "Approve & send"}
                      </button>
                      <span className="small muted">Sending is a stub in this prototype.</span>
                    </div>
                  </>
                )}
              </section>
            )}

            {result && (
              <details className="panel">
                <summary>How this was checked</summary>
                <div className="kv">
                  <span className="muted">Gate</span>
                  <span>{result.gate.code} · {result.gate.checked_by}</span>
                  <span className="muted">Models</span>
                  <span className="mono">read {result.read?.model ?? "—"} · evaluate {result.evaluation?.model ?? "—"}</span>
                  <span className="muted">Seconds</span>
                  <span>{Object.entries(result.seconds).map(([k, v]) => `${k} ${v}s`).join(" · ")}</span>
                  <span className="muted">Model quotes dropped</span>
                  <span>{result.evaluation ? `${result.evaluation.quotes_invalid} of ${result.evaluation.quotes_total}` : "—"}</span>
                  <span className="muted">Facts kept</span>
                  <span className="mono">
                    {facts ? `${facts.country_code ?? "?"} · ${facts.rate_min_usd_per_hour ?? "?"}–${facts.rate_max_usd_per_hour ?? "?"} USD/h · English ${facts.english_self_rating ?? "?"} · overlap ${facts.overlap_hours_us_eastern ?? "?"}h` : "—"}
                  </span>
                  <span className="muted">Warnings</span>
                  <span className="mono small">{result.warnings.length ? result.warnings.join(", ") : "none"}</span>
                </div>
              </details>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
