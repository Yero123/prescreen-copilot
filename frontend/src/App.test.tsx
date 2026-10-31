import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { setAccessCode } from "./api";

function row(id: number, name: string, over: object = {}) {
  return {
    id,
    status: "done",
    received_at: new Date().toISOString(),
    candidate: { id, name, email: `${id}@example.com` },
    country: "Peru",
    rate: "$30/h",
    marks: [],
    flags: [],
    not_an_application: false,
    suggested_bucket: "invite",
    decision: null,
    email_approved: false,
    ...over,
  };
}

const ROWS = [row(1, "Ana Test"), row(2, "Luis Test", { suggested_bucket: "not_a_fit" }), row(3, "Sol Test", { suggested_bucket: "more_info", decision: "invite" })];

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status });
}

function stubApi(code = "") {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      const sent = (init.headers as Record<string, string>)["X-Access-Code"] ?? "";
      if (code && sent !== code) return respond(401, { detail: "Enter the demo access code to continue." });
      return respond(200, url.endsWith("/api/submissions") ? ROWS : {});
    }),
  );
}

beforeEach(() => {
  window.location.hash = "";
  setAccessCode("");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("lists the candidates when the API is open", async () => {
    stubApi();
    render(<App />);
    expect(await screen.findByText("Ana Test")).toBeTruthy();
    expect(screen.queryByText("Demo access")).toBeNull();
  });

  it("asks for the access code, and rejects a wrong one", async () => {
    stubApi("letmein");
    render(<App />);
    const input = await screen.findByLabelText("Access code");
    fireEvent.change(input, { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Enter the demo access code to continue.")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Access code"), { target: { value: " letmein " } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Ana Test")).toBeTruthy();
  });

  it("files a candidate under the recruiter's decision, not the suggestion", async () => {
    stubApi();
    render(<App />);
    await screen.findByText("Ana Test");
    const tabs = within(screen.getByRole("tablist"));
    fireEvent.click(tabs.getByRole("tab", { name: /Invite to call/ }));
    expect(screen.getByText("Sol Test")).toBeTruthy();
    expect(screen.queryByText("Luis Test")).toBeNull();
    fireEvent.click(tabs.getByRole("tab", { name: /Needs more info/ }));
    expect(screen.queryByText("Sol Test")).toBeNull();
  });

  it("hides names in blind mode", async () => {
    stubApi();
    render(<App />);
    await screen.findByText("Ana Test");
    fireEvent.click(screen.getByRole("button", { name: "Blind mode" }));
    expect(screen.queryByText("Ana Test")).toBeNull();
    expect(screen.getByText("Candidate #001")).toBeTruthy();
  });
});
