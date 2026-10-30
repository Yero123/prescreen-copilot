from fastapi import FastAPI

from app.gate import run_gate
from app.schemas import GateRequest, GateResponse

app = FastAPI(title="Pre-screen Copilot")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/gate", response_model=GateResponse)
def gate(body: GateRequest) -> GateResponse:
    return run_gate(body.text)
