import { useEffect, useState } from "react";
import { ApiError, api, setAccessCode } from "./api";
import AddReply from "./pages/AddReply";
import Candidates from "./pages/Candidates";
import Review from "./pages/Review";
import RolePage from "./pages/RolePage";

type Route = { page: "list" } | { page: "review"; id: number } | { page: "add" } | { page: "role" };

function parse(hash: string): Route {
  const m = hash.match(/^#\/c\/(\d+)$/);
  if (m) return { page: "review", id: Number(m[1]) };
  if (hash === "#/add") return { page: "add" };
  if (hash === "#/role") return { page: "role" };
  return { page: "list" };
}

function AccessGate({ onDone, error }: { onDone: () => void; error: string }) {
  const [code, setCode] = useState("");
  return (
    <main>
      <form
        className="panel"
        style={{ maxWidth: 420 }}
        onSubmit={(e) => {
          e.preventDefault();
          setAccessCode(code.trim());
          onDone();
        }}
      >
        <h1>Demo access</h1>
        <p className="muted">This demo calls paid models, so it is protected with an access code.</p>
        <div className="field">
          <label htmlFor="access-code">Access code</label>
          <input id="access-code" type="text" value={code} onChange={(e) => setCode(e.target.value)} autoFocus />
        </div>
        {error && <p className="check-bad">{error}</p>}
        <button className="btn btn-primary" type="submit">
          Continue
        </button>
      </form>
    </main>
  );
}

export default function App() {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash));
  const [locked, setLocked] = useState<string | null>(null);
  const [blind, setBlind] = useState(false);
  const [probe, setProbe] = useState(0);

  useEffect(() => {
    const onHash = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api("/api/config")
      .then(() => setLocked(null))
      .catch((e) => setLocked(e instanceof ApiError && e.status === 401 ? (probe ? e.message : "") : null));
  }, [probe]);

  const nav = (
    <header className="appbar">
      <div className="appbar-inner">
        <a className="brand" href="#/">
          <span className="brand-mark" aria-hidden="true">RH</span>
          <span style={{ fontWeight: 600 }}>Rad Hires</span>
          <span className="muted">Pre-screen copilot</span>
        </a>
        <nav className="nav" aria-label="Sections">
          <a href="#/" aria-current={route.page === "list" || route.page === "review" ? "page" : undefined}>
            Candidates
          </a>
          <a href="#/add" aria-current={route.page === "add" ? "page" : undefined}>
            Add a reply
          </a>
          <a href="#/role" aria-current={route.page === "role" ? "page" : undefined}>
            Role setup
          </a>
        </nav>
      </div>
    </header>
  );

  if (locked !== null) {
    return (
      <>
        {nav}
        <AccessGate error={locked} onDone={() => setProbe((n) => n + 1)} />
      </>
    );
  }

  return (
    <>
      {nav}
      {route.page === "list" && <Candidates blind={blind} onToggleBlind={() => setBlind((b) => !b)} />}
      {route.page === "review" && <Review id={route.id} blind={blind} />}
      {route.page === "add" && <AddReply />}
      {route.page === "role" && <RolePage />}
    </>
  );
}
