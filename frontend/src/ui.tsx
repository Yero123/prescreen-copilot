import type { Bucket, Verdict } from "./types";

export const BUCKET_LABEL: Record<Bucket, string> = {
  invite: "Invite to call",
  more_info: "Needs more info",
  not_a_fit: "Not a fit (rule)",
  needs_review: "Needs your review",
};

export const VERDICT: Record<Verdict, { sym: string; label: string; cls: string }> = {
  meets: { sym: "✓", label: "Meets", cls: "v-meets" },
  not_enough_evidence: { sym: "?", label: "Not enough evidence", cls: "v-unknown" },
  does_not_meet: { sym: "✗", label: "Does not meet", cls: "v-no" },
  needs_review: { sym: "!", label: "Needs your review", cls: "v-review" },
};

export function BucketPill({ bucket, decided }: { bucket: Bucket | null; decided?: boolean }) {
  if (!bucket) return <span className="pill b-none">Not an application</span>;
  return (
    <span className={`pill b-${bucket}`}>
      {BUCKET_LABEL[bucket]}
      {decided ? " · you decided" : ""}
    </span>
  );
}

export function VerdictPill({ verdict }: { verdict: Verdict }) {
  const v = VERDICT[verdict];
  return (
    <span className={`pill ${v.cls}`}>
      {v.sym} {v.label}
    </span>
  );
}

export function timeAgo(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(iso).toLocaleDateString();
}

export function displayName(name: string, id: number, blind: boolean): string {
  return blind ? `Candidate #${String(id).padStart(3, "0")}` : name;
}
