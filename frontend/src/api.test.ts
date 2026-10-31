import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, setAccessCode } from "./api";

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setAccessCode("");
});

describe("api", () => {
  it("returns the parsed body and sends JSON", async () => {
    const fetchMock = stubFetch(200, { id: 7 });
    await expect(api("/api/submissions", { method: "POST", body: { a: 1 } })).resolves.toEqual({ id: 7 });
    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"a":1}');
  });

  it("sends the access code once it is set", async () => {
    const fetchMock = stubFetch(200, {});
    setAccessCode("letmein");
    await api("/api/config");
    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.headers).toMatchObject({ "X-Access-Code": "letmein" });
  });

  it("uses the API's message on an error", async () => {
    stubFetch(429, { detail: "Too many screenings" });
    await expect(api("/x")).rejects.toMatchObject({ status: 429, message: "Too many screenings" });
  });

  it("joins validation messages", async () => {
    stubFetch(422, { detail: [{ msg: "bad email" }, { msg: "too short" }] });
    await expect(api("/x")).rejects.toThrow("bad email; too short");
  });

  it("falls back to the status when the error is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>", { status: 502 })));
    const error = await api<never>("/x").catch((e: ApiError) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Request failed (502)");
  });
});
