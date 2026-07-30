"""FinGraph Sentinel — GenAI Graph Engineering Agent for BFSI.

POST a BFSI problem, get a complete Graph Engineering + Gen AI solution.
Supports Neo4j graph persistence, LLM reasoning (Ollama/OpenAI), and
deterministic playbook fallback for CI/CD without GPU/API keys.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..agent.sentinel import get_playbooks, solve
from ..graph.algorithms import CATALOG, CATALOG_BY_CATEGORY
from ..graph.neo4j_client import health as neo4j_health
from ..graph.schema import DOMAIN_SCHEMAS


# ─── Request / Response schemas ───────────────────────────────────────────────
class SolveRequest(BaseModel):
    problem: str = Field(
        ...,
        min_length=20,
        max_length=4000,
        examples=["Detect money-mule networks across 2M accounts with real-time transaction screening"],
    )
    domain: Literal["aml_fraud", "credit_risk", "insurance", "kyc_compliance", ""] = ""
    use_llm: bool | None = None


class SolutionResponse(BaseModel):
    domain: str
    problem: str
    problem_decomposition: str
    knowledge_graph_schema: str
    algorithms_and_methodology: str
    kpis_measurement_compliance: str


class HealthResponse(BaseModel):
    status: str
    agent: str
    neo4j: dict
    graph_engine: str
    playbooks_loaded: int


class AlgorithmCard(BaseModel):
    name: str
    category: str
    description: str
    bfsi_applications: list[str]
    cypher: str
    kpi_target: str


# ─── App ──────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="FinGraph Sentinel",
    version="1.0.0",
    description="GenAI Graph Engineering Agent — Neo4j, Graph RAG, GNNs for Banking, Finance & Insurance",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/api/v1/solve", response_model=SolutionResponse, tags=["🧠 Agent"])
async def solve_endpoint(req: SolveRequest):
    """Submit a BFSI problem and receive a complete Graph Engineering + Gen AI solution."""
    sol = solve(req.problem, req.domain, req.use_llm)
    return SolutionResponse(**sol.to_dict())


@app.get("/api/v1/playbooks", tags=["📚 Playbooks"])
async def playbooks_endpoint():
    """List all known BFSI playbook domains."""
    return {"playbooks": get_playbooks()}


@app.get("/api/v1/schemas", tags=["📐 Schema"])
async def schemas_endpoint():
    """Return the four domain-specific Cypher schema DDL blocks."""
    return {"domains": list(DOMAIN_SCHEMAS.keys())}


@app.get("/api/v1/schema/{domain}", tags=["📐 Schema"])
async def schema_domain(domain: str):
    """Return the Cypher DDL for a specific BFSI domain."""
    mapped = domain if domain in DOMAIN_SCHEMAS else "general_bfsi"
    schema = DOMAIN_SCHEMAS[mapped]
    return {"domain": mapped, "cypher_ddl": schema}


@app.get("/api/v1/algorithms", tags=["📊 Graph Algorithms"])
async def algorithms_endpoint(
    category: str | None = Query(default=None, description="Filter: centrality, community, pathfinding, pattern, gnn"),
):
    """Return the curated graph algorithm catalog, optionally filtered by category."""
    if category:
        algs = CATALOG_BY_CATEGORY.get(category, [])
    else:
        algs = CATALOG
    return {"algorithms": [a.to_card() for a in algs], "total": len(algs)}


@app.get("/api/v1/algorithm/{name}", response_model=AlgorithmCard, tags=["📊 Graph Algorithms"])
async def algorithm_detail(name: str):
    """Get a specific algorithm by name (case-insensitive)."""
    from ..graph.algorithms import CATALOG_BY_NAME

    alg = CATALOG_BY_NAME.get(name.lower())
    if alg is None:
        from fastapi import HTTPException

        raise HTTPException(404, f"Algorithm '{name}' not found.")
    return AlgorithmCard(**alg.to_card())


@app.get("/api/v1/health", response_model=HealthResponse, tags=["⚙️ System"])
async def health_endpoint():
    """System health: agent status, Neo4j connectivity, graph engine mode."""
    neo4j_status = await neo4j_health()
    return HealthResponse(
        status="healthy",
        agent="FinGraph Sentinel v1.0.0",
        neo4j=neo4j_status,
        graph_engine="Neo4j + APOC + GDS" if neo4j_status.get("neo4j") == "connected" else "in-memory catalog",
        playbooks_loaded=len(get_playbooks()),
    )
