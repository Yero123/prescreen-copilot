import { useEffect, useState } from "react";
import { api } from "../api";
import type { Sample } from "../types";
import { LoadButton, Loading } from "../ui";

// Not in the demo seed, so it shows up as a new candidate; the injection is the most telling thing to watch live.
const DEMO_FIRST = "injection-ps-dev";

export default function AddReply() {
  const [loaded, setLoaded] = useState<Sample | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [cv, setCv] = useState("");
  const [reply, setReply] = useState("");
  const [samples, setSamples] = useState<Sample[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Sample[]>("/api/samples")
      .then(setSamples)
      .catch(() => {})
      .finally(() => setSamplesLoading(false));
  }, []);

  const load = (s: Sample) => {
    setName(s.name);
    setEmail(s.email);
    setCv(s.cv);
    setReply(s.reply);
    setLoaded(s);
  };

  const loadNext = () => {
    const order = [...samples.filter((s) => s.id === DEMO_FIRST), ...samples.filter((s) => s.id !== DEMO_FIRST)];
    const at = order.findIndex((s) => s.id === loaded?.id);
    load(order[(at + 1) % order.length]);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api<{ id: number }>("/api/submissions", { method: "POST", body: { name, email, cv, reply } });
      window.location.hash = `#/c/${res.id}`;
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <div>
        <h1>Add a reply</h1>
        <p className="muted">Paste a candidate's email reply to the questionnaire and their CV. The copilot screens it in about 30 seconds.</p>
      </div>
      <div className="split">
        <form className="panel" onSubmit={submit}>
          <div className="demo-box">
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <span>
                <span className="demo-tag">Demo only</span>
                <span className="small">Fill the form with a synthetic candidate.</span>
              </span>
              <LoadButton className="btn" type="button" loading={samplesLoading} loadingText="Loading examples…" disabled={samples.length === 0} onClick={loadNext}>
                {loaded ? "Autofill next example" : "Autofill example"}
              </LoadButton>
            </div>
            {loaded && (
              <p className="small">
                <span className="mono">{loaded.id}</span> · {loaded.why}
              </p>
            )}
          </div>
          <div className="row-wrap" style={{ alignItems: "flex-start" }}>
            <div className="field" style={{ flex: "1 1 200px" }}>
              <label htmlFor="name">Candidate name</label>
              <input id="name" type="text" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="field" style={{ flex: "1 1 220px" }}>
              <label htmlFor="email">Candidate email</label>
              <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
          </div>
          <p className="small muted">Replies from the same email are kept on one candidate, with their history.</p>
          <div className="field">
            <label htmlFor="reply">Email reply</label>
            <textarea id="reply" rows={12} required value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Paste the whole reply. Quoted text from the original message is ignored." />
          </div>
          <div className="field">
            <label htmlFor="cv">CV (text)</label>
            <textarea id="cv" rows={5} value={cv} onChange={(e) => setCv(e.target.value)} />
          </div>
          {error && <div className="banner banner-bad">{error}</div>}
          <div className="row-wrap">
            <LoadButton className="btn btn-primary" type="submit" loading={busy} loadingText="Sending…" disabled={!reply.trim() || !name.trim() || !email.trim()}>
              Screen this reply
            </LoadButton>
            <span className="small muted">Uses the role “AI Engineer (LatAm)”.</span>
          </div>
        </form>
        <section className="panel" aria-labelledby="samples-title">
          <h2 id="samples-title">Try an example</h2>
          <p className="small muted">Test cases from the dev set, including the tricky ones. Load one, change it, or write your own and try to trick it.</p>
          {samplesLoading && <Loading>Loading examples…</Loading>}
          {samples.map((s) => (
            <button key={s.id} className="btn" style={{ textAlign: "left", display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 2 }} onClick={() => load(s)}>
              <span className="mono">{s.id}</span>
              <span className="small muted" style={{ fontWeight: 400 }}>{s.why}</span>
            </button>
          ))}
        </section>
      </div>
    </main>
  );
}
