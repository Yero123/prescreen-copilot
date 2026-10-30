export type Verdict = "meets" | "does_not_meet" | "not_enough_evidence" | "needs_review";
export type Bucket = "invite" | "more_info" | "not_a_fit" | "needs_review";

export interface Candidate {
  id: number;
  name: string;
  email: string;
}

export interface Mark {
  criterion_id: string;
  importance: string;
  text: string;
  verdict: Verdict | null;
}

export interface Row {
  id: number;
  status: "processing" | "done" | "error";
  received_at: string;
  candidate: Candidate;
  country: string | null;
  rate: string | null;
  marks: Mark[];
  flags: string[];
  not_an_application: boolean;
  suggested_bucket: Bucket | null;
  decision: Bucket | null;
  email_approved: boolean;
}

export interface EvidenceQuote {
  source: string;
  quote: string;
}

export interface Assessment {
  criterion_id: string;
  importance: string;
  criterion_text: string;
  verdict: Verdict;
  model_verdict: string | null;
  evidence: EvidenceQuote[];
  signals_found: string[];
  rationale: string;
  follow_up_question: string | null;
  notes: string[];
}

export interface RuleCheck {
  rule: string;
  label: string;
  status: "pass" | "fail" | "unknown";
  detail: string;
}

export interface EmailParagraph {
  text: string;
  based_on: string[];
}

export interface EmailDraft {
  template: Bucket;
  written_by: "code" | "llm";
  subject: string;
  body: string;
  paragraphs: EmailParagraph[];
  sources: Record<string, string>;
  checks: { name: string; passed: boolean; detail: string | null }[];
}

export interface ScreenResult {
  gate: { ok: boolean; code: string; message: string; checked_by: string; language: string | null };
  read: {
    ok: boolean;
    answers: Record<string, string>;
    facts: Record<string, string | number | null> | null;
    warnings: string[];
    model: string | null;
  } | null;
  rules: { checks: RuleCheck[]; any_fail: boolean; unknown: string[] } | null;
  evaluation: {
    ok: boolean;
    assessments: Assessment[];
    quotes_total: number;
    quotes_invalid: number;
    model: string | null;
  } | null;
  flags: { code: string; message: string }[];
  bucket: Bucket | null;
  reasons: string[];
  email: EmailDraft | null;
  warnings: string[];
  seconds: Record<string, number>;
}

export interface Detail {
  id: number;
  role_id: string;
  status: "processing" | "done" | "error";
  received_at: string;
  candidate: Candidate;
  reply: string;
  cv: string;
  history: { id: number; received_at: string; status: string }[];
  overrides: Record<string, { criterion_id: string; verdict: Verdict; reason: string }>;
  decision: Bucket | null;
  result: ScreenResult | null;
  suggested_bucket: Bucket | null;
  model_bucket: Bucket | null;
  reasons: string[];
  email: EmailDraft | null;
  email_edited_body: string | null;
  email_approved: boolean;
  email_outdated: boolean;
}

export interface Role {
  id: string;
  title: string;
  version: number;
  questionnaire: { id: string; text: string }[];
  criteria: { id: string; importance: string; text: string; evidence_signals: string[]; main_questions: string[] }[];
  hard_rules: {
    allowed_country_codes: string[];
    max_rate_usd_per_hour: number;
    min_english_self_rating: number;
    min_overlap_hours_us_eastern: number;
  };
}

export interface Sample {
  id: string;
  tags: string[];
  name: string;
  email: string;
  cv: string;
  reply: string;
  why: string;
}
