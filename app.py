from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from environment import SolidityGuardEnv


app = FastAPI(title="SolidityGuard")
env = SolidityGuardEnv()


class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(default=None)


class StepRequest(BaseModel):
    action: List[Dict[str, Any]]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
def reset(request: ResetRequest) -> Dict[str, Any]:
    try:
        return env.reset(task_id=request.task_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/step")
def step(request: StepRequest) -> Dict[str, Any]:
    try:
        return env.step(request.action)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/state")
def state() -> Dict[str, Any]:
    try:
        return env.state()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
