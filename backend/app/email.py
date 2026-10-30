"""Step 6 of the harness: draft the next email.

- not_a_fit: written by code from a template. The reason comes from the failed
  rules, word for word, so the model cannot soften, invent or leak anything.
- invite / more_info: written by the model from numbered, verified material
  (E = evidence, M = missing must-have, R = missing rule fact). Each paragraph
  must say which ids it uses, and code checks the draft before it is shown.
- needs_review: no draft. A person decides first.
"""

import os
import re

from app import llm
from app.checks import mentions_protected_attribute
from app.roles import Role
from app.rules import RulesResult
from app.schemas import Bucket, EmailCheck, EmailDraft, EmailLLM, EmailParagraphLLM, EvaluateResult

SIGNATURE = os.getenv("RECRUITER_SIGNATURE", "Best,\nThe recruiting team")
SUBJECT = "Next step for the {title} role"

_RULE_REQUIREMENT = {
    "location": "being based in one of the countries this role hires from",
    "rate": "an hourly rate within the budget of ${max:g}",
    "english": "a self-rated English level of {min_english} or higher",
    "overlap": "at least {min_overlap:g} hours of daily overlap with US Eastern time",
}
_RULE_QUESTION = {
    "location": "Where are you based?",
    "rate": "What is your hourly rate in USD?",
    "english": "How would you rate your English from 1 to 10?",
    "overlap": "How many hours a day can you overlap with US Eastern time?",
}

_FORBIDDEN = [
    r"\bsalar(y|ies)\b", r"\bcompensation\b", r"\boffer(s|ed)?\b", r"\bguarantee", r"\$\s?\d",
    r"\bhired\b", r"\bscor(e|es|ed|ing)\b", r"\brank(ed|ing)?\b", r"\bcriteri(on|a)\b",
    # Revealing that software judged them. "AI" alone is allowed: the role is "AI Engineer".
    r"\b(our|an|the|this) (ai|automated|automatic) (tool|system|screen\w*|review\w*|assistant|check\w*)\b",
    r"\b(screened|reviewed|evaluated|assessed) by (an? )?(ai|model|algorithm|software)\b",
    r"\blanguage model\b", r"\balgorithm\w*\b",
]

WRITE_SYSTEM = """You write short, warm, plain emails from a recruiter to a candidate.
Write in English. Do not write a greeting or a sign-off; they are added later.

Use only the numbered material you are given:
- E items are verified evidence from the candidate's own answers.
- M and R items are missing information to ask for.

For an invite: 2 or 3 short paragraphs. Mention one specific thing from an E
item, in your own words, and invite them to book a 30-minute call at
[SCHEDULING LINK].
For more_info: 2 to 4 short paragraphs. Thank them, optionally mention one E
item, then ask every M and R item as a clear question, and say we will reply
within two business days.

Each paragraph lists in based_on the ids it uses (empty for logistics only).
Never mention criteria, scores, rankings, AI, other candidates, salary,
offers, guarantees, or anything about the candidate's age, gender,
nationality, accent, religion, family or health."""


def first_name(full_name: str | None) -> str | None:
    if not full_name or not full_name.strip():
        return None
    return full_name.strip().split()[0]


def _assemble(name: str | None, paragraphs: list[str]) -> str:
    greeting = f"Hi {name}," if name else "Hi,"
    return "\n\n".join([greeting, *paragraphs, SIGNATURE])


def _rejection(role: Role, rules: RulesResult, name: str | None) -> EmailDraft:
    hr = role.hard_rules
    reqs = [
        _RULE_REQUIREMENT[c.rule].format(max=hr.max_rate_usd_per_hour, min_english=hr.min_english_self_rating,
                                         min_overlap=hr.min_overlap_hours_us_eastern)
        for c in rules.failed()
    ]
    reason = "This role requires " + " and ".join(reqs) + ", so we can't move forward with this application."
    paragraphs = [
        EmailParagraphLLM(text="Thank you for taking the time to answer our questions.", based_on=[]),
        EmailParagraphLLM(text=reason, based_on=[f"rule:{c.rule}" for c in rules.failed()]),
        EmailParagraphLLM(text="We'll keep your profile in mind for future roles that match.", based_on=[]),
    ]
    return EmailDraft(
        template="not_a_fit", written_by="code", subject=SUBJECT.format(title=role.title),
        body=_assemble(name, [p.text for p in paragraphs]), paragraphs=paragraphs,
        sources={f"rule:{c.rule}": f"{c.label}: {c.detail}" for c in rules.failed()},
        checks=[EmailCheck(name="Reason comes from the role's rules, not from the AI", passed=True)],
    )


def build_material(role: Role, bucket: Bucket, rules: RulesResult,
                   evaluation: EvaluateResult) -> dict[str, str]:
    material: dict[str, str] = {}
    met = [a for a in evaluation.assessments if a.verdict == "meets" and a.evidence]
    for i, a in enumerate(met, 1):
        material[f"E{i}"] = f'{a.criterion_text}: "{a.evidence[0].quote}"'
    if bucket == "more_info":
        must_ids = set(role.must_ids())
        missing = [a for a in evaluation.assessments
                   if a.criterion_id in must_ids and a.verdict == "not_enough_evidence"]
        for i, a in enumerate(missing, 1):
            material[f"M{i}"] = a.follow_up_question or f"Could you share a concrete example of: {a.criterion_text}?"
        for i, c in enumerate([c for c in rules.checks if c.status == "unknown"], 1):
            material[f"R{i}"] = _RULE_QUESTION[c.rule]
    return material


def check_email(bucket: Bucket, role: Role, material: dict[str, str], draft: EmailLLM) -> list[EmailCheck]:
    text = " ".join(p.text for p in draft.paragraphs) + " " + draft.subject
    cited = {i for p in draft.paragraphs for i in p.based_on}
    unknown_ids = sorted(cited - set(material))
    evidence_ids = {k for k in material if k.startswith("E")}
    ask_ids = {k for k in material if k[0] in "MR"}
    forbidden = [m.group(0) for pat in _FORBIDDEN for m in re.finditer(pat, text, flags=re.IGNORECASE)]
    confidential = [t for t in role.confidential_terms if t and t.lower() in text.lower()]
    protected = mentions_protected_attribute(text)

    checks = [
        EmailCheck(name="Every cited id exists", passed=not unknown_ids,
                   detail=", ".join(unknown_ids) or None),
        EmailCheck(name="No salary, offers, scores or AI-screening language", passed=not forbidden,
                   detail=", ".join(forbidden) or None),
        EmailCheck(name="No personal attributes", passed=not protected, detail=", ".join(protected) or None),
        EmailCheck(name="No confidential names", passed=not confidential, detail=", ".join(confidential) or None),
    ]
    if bucket == "invite" and evidence_ids:
        checks.append(EmailCheck(name="Personal sentence is backed by the candidate's answers",
                                 passed=bool(cited & evidence_ids)))
    if bucket == "more_info":
        not_asked = sorted(ask_ids - cited)
        checks.append(EmailCheck(name="Asks every missing item", passed=not not_asked,
                                 detail=", ".join(not_asked) or None))
    return checks


def draft_email(role: Role, bucket: Bucket, rules: RulesResult | None, evaluation: EvaluateResult | None,
                candidate_name: str | None) -> tuple[EmailDraft | None, list[str]]:
    name = first_name(candidate_name)
    if bucket == "not_a_fit" and rules is not None:
        return _rejection(role, rules, name), []
    if bucket not in ("invite", "more_info") or rules is None or evaluation is None:
        return None, []

    material = build_material(role, bucket, rules, evaluation)
    listing = "\n".join(f"{k}: {v}" for k, v in material.items()) or "(none)"
    user = f"Email type: {bucket}\nRole: {role.title}\n\nMaterial:\n{listing}"
    try:
        result = llm.parse(role="write", system=WRITE_SYSTEM, user=user, schema=EmailLLM, max_tokens=4000)
    except llm.LLMError as e:
        return None, [f"email_llm_error:{e}"]
    if not result.complete:
        return None, ["email_llm_incomplete"]

    draft: EmailLLM = result.parsed
    checks = check_email(bucket, role, material, draft)
    return EmailDraft(
        template=bucket, written_by="llm", subject=SUBJECT.format(title=role.title),
        body=_assemble(name, [p.text for p in draft.paragraphs]),
        paragraphs=draft.paragraphs, sources=material, checks=checks,
    ), []
