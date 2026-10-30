import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from app import config, store, views
from app.email import draft_email
from app.gate import run_gate
from app.pipeline import ScreenResult, screen
from app.roles import Role, bias_warnings, list_role_ids, load_role
from app.schemas import Bucket, GateRequest, GateResponse, Verdict
from app.security import check_screen_budget, require_access

log = logging.getLogger("prescreen")


@asynccontextmanager
async def lifespan(_app):
    if os.getenv("SEED_DEMO", "1") == "1" and not store.list_latest_submissions():
        from app.seed import load_seed
        log.info("Seeded %s demo submissions", load_seed())
    yield


app = FastAPI(title="Pre-screen Copilot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_methods=["*"], allow_headers=["*"],
)
DEFAULT_ROLE = "ai-engineer-latam"
guarded = [Depends(require_access)]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": config.LLM_PROVIDER}


@app.get("/api/config", dependencies=guarded)
def app_config() -> dict:
    return {"provider": config.LLM_PROVIDER, "role_id": DEFAULT_ROLE,
            "models": {r: config.model_for(r) for r in ("read", "evaluate", "write")}}


@app.post("/api/gate", response_model=GateResponse, dependencies=guarded + [Depends(check_screen_budget)])
def gate(body: GateRequest) -> GateResponse:
    return run_gate(body.text)


@app.get("/api/roles", dependencies=guarded)
def roles() -> list[str]:
    return list_role_ids()


@app.get("/api/roles/{role_id}", dependencies=guarded)
def role(role_id: str) -> dict:
    try:
        r: Role = load_role(role_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown role {role_id!r}")
    return {"role": r, "bias_warnings": bias_warnings(r)}


# ---------- submissions ----------


class NewSubmission(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    cv: str = Field(default="", max_length=20_000)
    reply: str = Field(min_length=1, max_length=20_000)
    role_id: str = DEFAULT_ROLE


def _process(submission_id: int, body: NewSubmission) -> None:
    try:
        result: ScreenResult = screen(body.reply, body.cv, load_role(body.role_id), body.name)
        store.save_evaluation(submission_id, result.model_dump(mode="json"), result.bucket, config.LLM_PROVIDER)
    except Exception:
        log.exception("Screening failed for submission %s", submission_id)
        store.mark_error(submission_id)


@app.post("/api/submissions", status_code=202, dependencies=guarded + [Depends(check_screen_budget)])
def create_submission(body: NewSubmission, tasks: BackgroundTasks) -> dict:
    try:
        load_role(body.role_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown role {body.role_id!r}")
    submission_id = store.create_submission(body.email, body.name, body.role_id, body.reply, body.cv)
    tasks.add_task(_process, submission_id, body)
    return {"id": submission_id, "status": "processing"}


@app.get("/api/submissions", dependencies=guarded)
def list_submissions() -> list[dict]:
    rows = []
    for sub in store.list_latest_submissions():
        rows.append(views.row(sub, load_role(sub["role_id"])))
    return rows


def _get(submission_id: int) -> dict:
    sub = store.get_submission(submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@app.get("/api/submissions/{submission_id}", dependencies=guarded)
def get_submission(submission_id: int) -> dict:
    sub = _get(submission_id)
    return views.detail(sub, load_role(sub["role_id"]))


class Override(BaseModel):
    criterion_id: str
    verdict: Verdict | None  # None removes the override
    reason: str = Field(default="", max_length=500)


@app.post("/api/submissions/{submission_id}/overrides", dependencies=guarded)
def override(submission_id: int, body: Override) -> dict:
    sub = _get(submission_id)
    role_ = load_role(sub["role_id"])
    if body.criterion_id not in {c.id for c in role_.criteria}:
        raise HTTPException(status_code=422, detail="Unknown criterion")
    store.add_event(submission_id, "override", body.model_dump())
    return views.detail(_get(submission_id), role_)


class Decision(BaseModel):
    bucket: Bucket | None  # None clears the decision


@app.post("/api/submissions/{submission_id}/decision", dependencies=guarded)
def decide(submission_id: int, body: Decision) -> dict:
    sub = _get(submission_id)
    store.add_event(submission_id, "decision", body.model_dump())
    return views.detail(_get(submission_id), load_role(sub["role_id"]))


class EmailEdit(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


@app.post("/api/submissions/{submission_id}/email/edit", dependencies=guarded)
def edit_email(submission_id: int, body: EmailEdit) -> dict:
    sub = _get(submission_id)
    store.add_event(submission_id, "email_edited", body.model_dump())
    return views.detail(_get(submission_id), load_role(sub["role_id"]))


@app.post("/api/submissions/{submission_id}/email/approve", dependencies=guarded)
def approve_email(submission_id: int) -> dict:
    """Sending is a stub: the approval is recorded, nothing leaves the system."""
    sub = _get(submission_id)
    store.add_event(submission_id, "email_approved", {})
    return views.detail(_get(submission_id), load_role(sub["role_id"]))


@app.post("/api/submissions/{submission_id}/email/regenerate",
          dependencies=guarded + [Depends(check_screen_budget)])
def regenerate_email(submission_id: int) -> dict:
    sub = _get(submission_id)
    role_ = load_role(sub["role_id"])
    view = views.detail(sub, role_)
    if view["result"] is None:
        raise HTTPException(status_code=409, detail="This reply has not been screened yet.")
    result = ScreenResult.model_validate(view["result"])
    bucket = view["decision"] or view["suggested_bucket"]
    draft, warnings = draft_email(role_, bucket, result.rules, result.evaluation, sub["candidate"]["name"])
    if draft is None:
        raise HTTPException(status_code=409, detail="No draft for this next step. " + "; ".join(warnings))
    store.add_event(submission_id, "email_regenerated", {"draft": draft.model_dump(mode="json")})
    return views.detail(_get(submission_id), role_)


@app.get("/api/samples", dependencies=guarded)
def samples() -> list[dict]:
    """Dev cases the recruiter can paste in the 'Add a reply' form to try the harness."""
    from evals.cases import load_cases
    return [{"id": c.id, "tags": c.tags, "name": c.candidate.name, "email": c.candidate.email,
             "cv": c.cv, "reply": c.reply, "why": c.expected.why} for c in load_cases("dev")]
