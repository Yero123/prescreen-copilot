import { useEffect, useState } from "react";
import { api } from "../api";
import type { Role } from "../types";

type BiasWarning = { criterion_id: string; matched: string; suggestion: string };

export default function RolePage() {
  const [role, setRole] = useState<Role | null>(null);
  const [warnings, setWarnings] = useState<BiasWarning[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ role: Role; bias_warnings: BiasWarning[] }>("/api/roles/ai-engineer-latam")
      .then((r) => {
        setRole(r.role);
        setWarnings(r.bias_warnings);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <main><div className="banner banner-bad">{error}</div></main>;
  if (!role) return <main><p className="muted">Loading…</p></main>;
  const rules = role.hard_rules;

  return (
    <main>
      <div>
        <h1>Role setup</h1>
        <p className="muted">
          {role.title} · version {role.version} · used for every reply to this role. Edit <span className="mono">backend/roles/{role.id}.json</span>; it is validated when it loads.
        </p>
      </div>
      {warnings.map((w) => (
        <div key={w.criterion_id} className="banner banner-warn">
          “{w.matched}” in criterion <span className="mono">{w.criterion_id}</span> may screen people out for who they are. Try: “{w.suggestion}”.
        </div>
      ))}
      <div className="split">
        <section className="panel" aria-labelledby="crit-title">
          <h2 id="crit-title">Criteria, in plain language</h2>
          <p className="small muted">Each criterion is checked on its own, with the candidate's exact words as evidence.</p>
          {role.criteria.map((c) => (
            <div key={c.id} className="crit">
              <span>
                <span className="tag">{c.importance}</span>
                {c.text}
              </span>
              <ul className="small muted" style={{ margin: 0, paddingLeft: 18 }}>
                {c.evidence_signals.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
              <span className="small muted">Usually answered in {c.main_questions.join(", ")}</span>
            </div>
          ))}
        </section>
        <div className="stack">
          <section className="panel panel-rules" aria-labelledby="hard-title">
            <h2 id="hard-title">Hard rules · checked by code</h2>
            <div className="kv">
              <span>Location</span>
              <span className="mono small">{rules.allowed_country_codes.join(" ")}</span>
              <span>Max rate</span>
              <span>${rules.max_rate_usd_per_hour}/h (a range passes if its low end fits)</span>
              <span>English, self-rated</span>
              <span>{rules.min_english_self_rating} or higher</span>
              <span>Overlap with US Eastern</span>
              <span>{rules.min_overlap_hours_us_eastern} hours or more</span>
            </div>
            <p className="small muted">A missing fact is never a failure: the email asks for it.</p>
          </section>
          <section className="panel" aria-labelledby="q-title">
            <h2 id="q-title">Screening questionnaire</h2>
            {role.questionnaire.map((q) => (
              <div key={q.id} className="row-wrap" style={{ alignItems: "baseline", flexWrap: "nowrap" }}>
                <span className="mono muted">{q.id}</span>
                <span>{q.text}</span>
              </div>
            ))}
          </section>
        </div>
      </div>
    </main>
  );
}
