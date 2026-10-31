import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Review from "./Review";

const CHECKED = {
  gate: { ok: true, code: "ok", checked_by: "code", message: "" },
  flags: [],
  warnings: [],
  seconds: {},
  read: null,
  rules: null,
  evaluation: null,
};

const EMAIL = { template: "invite", subject: "Next step", body: "Old draft text", paragraphs: [], sources: {}, checks: [], written_by: "model" };

function detail(over: object = {}) {
  return {
    id: 1,
    role_id: "ai-engineer-latam",
    status: "done",
    received_at: new Date().toISOString(),
    candidate: { id: 1, name: "Ana Test", email: "ana@example.com" },
    reply: "Hello",
    cv: "",
    history: [],
    overrides: {},
    reasons: [],
    decision: null,
    suggested_bucket: "invite",
    email: null,
    email_edited_body: null,
    email_outdated: false,
    email_approved: false,
    result: CHECKED,
    ...over,
  };
}

function respond(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

// Holds every POST open until release() so the test can look at the page mid-request.
function stubApi(first: object, after: () => Response) {
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      if (init.method === "POST") {
        await held;
        return after();
      }
      return respond(url.includes("/api/roles/") ? { role: { questionnaire: [] } } : first);
    }),
  );
  return () => release();
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Review loading states", () => {
  it("shows a screening state while the reply is processing", async () => {
    stubApi(detail({ status: "processing", result: null }), () => respond({}));
    render(<Review id={1} blind={false} />);
    expect(await screen.findByText(/Screening this reply/)).toBeTruthy();
  });

  it("shows progress while writing the first draft", async () => {
    const release = stubApi(detail(), () => respond(detail({ email: EMAIL })));
    render(<Review id={1} blind={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Write a draft" }));

    expect((await screen.findByRole("status")).textContent).toContain("Writing the draft");
    expect(screen.queryByRole("button", { name: "Write a draft" })).toBeNull();

    release();
    expect(await screen.findByText("Old draft text")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("replaces an outdated draft while the new one is written", async () => {
    const release = stubApi(detail({ email: EMAIL, email_outdated: true, decision: "more_info" }), () =>
      respond(detail({ email: { ...EMAIL, body: "New draft text" }, decision: "more_info" })),
    );
    render(<Review id={1} blind={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Write a new draft" }));

    await screen.findByRole("status");
    expect(screen.queryByText("Old draft text")).toBeNull();

    release();
    expect(await screen.findByText("New draft text")).toBeTruthy();
  });

  it("shows the error and brings the action back when writing fails", async () => {
    const release = stubApi(detail(), () => respond({ detail: "The model is busy." }, 503));
    render(<Review id={1} blind={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Write a draft" }));
    await screen.findByRole("status");

    release();
    expect((await screen.findByRole("alert")).textContent).toContain("The model is busy.");
    expect(screen.getByRole("button", { name: "Write a draft" })).toBeTruthy();
  });

  it("marks only the decision being saved", async () => {
    const release = stubApi(detail(), () => respond(detail({ decision: "invite" })));
    render(<Review id={1} blind={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Invite to call" }));

    expect(await screen.findByRole("button", { name: "Saving…" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Not a fit" }) as HTMLButtonElement).disabled).toBe(true);

    release();
    expect((await screen.findByRole("button", { name: "Invite to call" })).getAttribute("aria-pressed")).toBe("true");
  });
});
