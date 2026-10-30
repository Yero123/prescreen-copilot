from fastapi import FastAPI, HTTPException

from app.gate import run_gate
from app.roles import Role, bias_warnings, list_role_ids, load_role
from app.schemas import GateRequest, GateResponse

app = FastAPI(title="Pre-screen Copilot")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/gate", response_model=GateResponse)
def gate(body: GateRequest) -> GateResponse:
    return run_gate(body.text)


@app.get("/api/roles")
def roles() -> list[str]:
    return list_role_ids()


@app.get("/api/roles/{role_id}")
def role(role_id: str) -> dict:
    try:
        r: Role = load_role(role_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown role {role_id!r}")
    return {"role": r, "bias_warnings": bias_warnings(r)}
