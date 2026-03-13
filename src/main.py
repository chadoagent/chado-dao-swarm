from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import settings
from src.agents.orchestrator import Orchestrator
from src.protocols.a2a import handle_a2a_request
from src.utils.logging import ExecutionLogger

app = FastAPI(title="Chado DAO Swarm", version="0.1.0")
orchestrator = Orchestrator()
logger = ExecutionLogger()


class AnalyzeRequest(BaseModel):
    proposal_url: str | None = None
    proposal_text: str | None = None
    protocol: str = "curve"


class AnalyzeResponse(BaseModel):
    recommendation: str
    confidence: float
    analysis: dict
    execution_log_id: str


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "chado-dao-swarm", "version": "0.1.0"}


@app.get("/api/v1/status")
async def status():
    return {
        "agents": orchestrator.agent_status(),
        "chain": settings.chain_name,
        "registry": settings.identity_registry,
    }


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    log_entry = logger.start("analyze", {"protocol": req.protocol})

    result = await orchestrator.run({
        "proposal_url": req.proposal_url,
        "proposal_text": req.proposal_text,
        "protocol": req.protocol,
    })

    logger.end(log_entry, result)

    return AnalyzeResponse(
        recommendation=result["recommendation"],
        confidence=result["confidence"],
        analysis=result["analysis"],
        execution_log_id=log_entry["id"],
    )


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A (Agent-to-Agent) JSON-RPC 2.0 endpoint."""
    data = await request.json()
    handlers = {
        "analyze": lambda params: orchestrator.run(params),
        "status": lambda _: orchestrator.agent_status(),
    }
    result = await handle_a2a_request(data, handlers)
    return JSONResponse(content=result)


@app.get("/.well-known/agent.json")
async def agent_card():
    """Serve agent.json for A2A discovery."""
    return {
        "format": "Registration-v1",
        "name": "Chado DAO Swarm",
        "description": "Multi-agent swarm for DAO decision support",
        "services": [{"type": "api", "url": f"http://localhost:8716/api/v1"}],
        "supportedTrust": ["execution-logs"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8716)
