import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BucketPill, LoadButton, displayName, timeAgo } from "./ui";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("displayName", () => {
  it("shows the name normally and hides it in blind mode", () => {
    expect(displayName("Ana Test", 7, false)).toBe("Ana Test");
    expect(displayName("Ana Test", 7, true)).toBe("Candidate #007");
  });
});

describe("timeAgo", () => {
  it("describes recent times", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-31T12:00:00Z"));
    expect(timeAgo("2026-10-31T11:59:50Z")).toBe("just now");
    expect(timeAgo("2026-10-31T11:30:00Z")).toBe("30 min ago");
    expect(timeAgo("2026-10-31T09:00:00Z")).toBe("3 h ago");
  });
});

describe("BucketPill", () => {
  it("marks a recruiter's own decision", () => {
    render(<BucketPill bucket="invite" decided />);
    expect(screen.getByText("Invite to call · you decided")).toBeTruthy();
  });

  it("names replies without a bucket", () => {
    render(<BucketPill bucket={null} />);
    expect(screen.getByText("Not an application")).toBeTruthy();
  });
});

describe("LoadButton", () => {
  it("shows its normal label when idle", () => {
    render(<LoadButton loading={false} loadingText="Saving…">Save</LoadButton>);
    const button = screen.getByRole("button", { name: "Save" }) as HTMLButtonElement;
    expect(button.disabled).toBe(false);
  });

  it("swaps the label and blocks clicks while loading", () => {
    render(<LoadButton loading loadingText="Saving…">Save</LoadButton>);
    const button = screen.getByRole("button", { name: "Saving…" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe("true");
  });
});
