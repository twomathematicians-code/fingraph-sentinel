# `fingraph-sentinel`

[![CI](https://github.com/twomathematicians-code/fingraph-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/twomathematicians-code/fingraph-sentinel/actions)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-4581C3?logo=neo4j)](https://neo4j.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Poetry](https://img.shields.io/badge/Poetry-Package%20Manager-60A5FA?logo=python)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**GenAI Graph Engineering Agent — BFSI** · FinGraph Sentinel designs complete graph + generative AI solutions for Banking, Finance, and Insurance problems. Neo4j, Graph RAG, GNNs, real-time streaming — all with regulatory compliance built in.

> 🎯 Built for a **Machine Learning Engineer** role showcasing: Neo4j graph databases, LangChain AI agents, Graph Neural Networks, BFSI regulatory domain knowledge, and containerized deployment.

---

## 🧬 Architecture

```mermaid
graph TB
    subgraph "Docker Compose"
        API[FastAPI Agent :8000]
        NEO[Neo4j:5 :7687]
        OLL[Ollama LLM :11434]
    end

    USER[BFSI Problem] --> API
    API --> DET[Deterministic Solver]
    API --> LLM[LLM Reasoning]
    DET --> KB[Knowledge Base<br/>4 BFSI Playbooks]
    LLM --> PROMPT[System Prompt<br/>8-Section Spec]
    API --> NEO
    NEO --> GDS[GDS Plugin<br/>GraphSAGE · PageRank]
    API --> OUT[8-Section Solution<br/>Schema · Algorithms · KPIs · Compliance]

    style API fill:#2563eb,color:#fff
    style NEO fill:#4581C3,color:#fff
    style OUT fill:#059669,color:#fff
  fallback (no LLM)    (Cypher DDL)         invocations
```

---

## 📦 Project Structure

```
fingraph-sentinel/
├── src/
│   ├── api/main.py              # FastAPI: /solve, /agent, /schema, /domains, /health
│   ├── agent/sentinel.py        # LangChain agent → loads system prompt, invokes LLM
│   ├── graph/
│   │   ├── schema.py            # Cypher DDL for 4 BFSI domains
│   │   ├── algorithms.py        # 8 graph algorithms with Cypher examples + KPI targets
│   │   └── neo4j_client.py      # Async Neo4j driver with graceful fallback
│   ├── playbooks/
│   │   ├── aml_fraud.py         # Money-mule ring detection
│   │   ├── credit_risk.py       # Contagion + default cascade modeling
│   │   ├── insurance_claims.py  # Organized claim ring detection + SIU triage
│   │   └── kyc_compliance.py    # UBO resolution + sanctions screening
│   └── utils/{config.py,logging.py}
├── prompts/system_prompt.md     # FinGraph Sentinel persona (1,200+ words)
├── data/seed_cypher.cql         # Sample BFSI graph (parties, accounts, ownership chain)
├── examples/solved_aml.json     # Fully worked AML solution (1,800+ words)
├── tests/                       # 15 tests (API + graph integration)
├── configs/model_config.yaml
├── docker-compose.yml           # API + Neo4j + optional Ollama
├── Dockerfile                   # Multi-stage Python 3.11-slim
├── .gitlab-ci.yml               # lint → test → graph-test → build
├── .github/workflows/ci.yml     # GitHub Actions parity
├── pyproject.toml               # Poetry: neo4j, langchain, fastapi
└── Makefile
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local dev)
- Poetry

### Option 1: Docker (API + Neo4j)

```bash
git clone https://github.com/twomathematicians-code/fingraph-sentinel.git
cd fingraph-sentinel
docker-compose up --build
# API: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474 (neo4j / fingraph-demo)
```

### Option 2: Local Dev

```bash
poetry install --with dev
poetry run uvicorn src.api.main:app --reload

# In another terminal — seed the graph
# Start Neo4j locally or via compose, then:
make seed
```

---

## 🧠 How the Agent Works

### Mode 1: Deterministic (default — no LLM required)

The agent matches your problem against its knowledge base of solved BFSI playbooks (4 domains × full 4-section solutions). Returns a comprehensive, production-ready answer in under 100ms — ideal for CI/CD and quick prototyping.

### Mode 2: LLM-powered (Ollama or OpenAI-compatible)

Set `FS_LLM_PROVIDER=ollama` in `.env`. The agent loads the full FinGraph Sentinel system prompt, invokes the LLM, and parses the output into the canonical 4-section structure. Use `docker-compose --profile llm up` to also start Ollama.

### The 4-Section Canon

Every solution follows this exact structure:

| Section | Content |
|:--------|:--------|
| **Problem Decomposition** | Current-state failure analysis, why tabular/SQL approaches fail, graph-theoretic problem framing |
| **Knowledge Graph Schema** | Complete Cypher DDL (constraints, indexes, node taxonomies, relationship types) with GDS projections |
| **Algorithms & Methodology** | Streaming + batch pipelines, specific graph algorithms with runnable Cypher, GNN architectures (layers, dims, loss) |
| **KPIs & Compliance** | Numeric KPI targets with measurement methodology, regulatory alignment matrix (GDPR/6AMLD/Basel/FATF citations), audit trail specification |

---

## 📐 Domain Playbooks

| Domain | Problem Solved | Key Technique |
|:-------|:--------------|:--------------|
| **AML / Fraud** | Money-mule detection, layering rings, smurfing patterns | PageRank + cycle detection + GraphSAGE |
| **Credit Risk** | Contagion cascades, guarantor exposure, default clusters | Monte Carlo over graph + RGCN |
| **Insurance Claims** | Organized claim rings, provider collusion, SIU triage | Bipartite projection + Louvain + link prediction |
| **KYC / Compliance** | UBO resolution, sanctions screening, entity resolution | Ownership-path aggregation + Graph RAG |

---

## 📊 Graph Algorithm Catalog

The agent ships with 8 curated graph algorithms, each with BFSI use cases, a runnable Cypher example, and a KPI target:

| Algorithm | Category | Example BFSI Use |
|:----------|:---------|:-----------------|
| **PageRank** | Centrality | Mule hub accounts (high in-degree, low balance) |
| **Louvain** | Community | Fraud ring clusters | 
| **Betweenness** | Centrality | Chokepoint accounts that fragment the network |
| **Cycle Detection** | Pattern | Circular fund flows (layering indicator) |
| **Shortest Path** | Pathfinding | Sanctions proximity: hops from a PEP to an account |
| **FastRP + GraphSAGE** | GNN | Account risk embeddings → XGBoost classifier |
| **Label Propagation** | Community | Risk contagion seeding from known-defaulted nodes |
| **WCC** | Community | Graph partitioning for 500M+ node parallel processing |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/api/v1/solve` | Submit a BFSI problem → get a 4-section solution |
| `GET` | `/api/v1/playbooks` | List all domain playbooks |
| `GET` | `/api/v1/schemas` | List available domain schemas |
| `GET` | `/api/v1/schema/{domain}` | Get Cypher DDL for a specific domain |
| `GET` | `/api/v1/algorithms` | Full algorithm catalog (filterable by category) |
| `GET` | `/api/v1/algorithm/{name}` | Single algorithm detail card |
| `GET` | `/api/v1/health` | System health (agent, Neo4j, graph engine mode) |
| `GET` | `/docs` | Swagger UI |

---

## 🧪 Testing

```bash
# FastAPI + agent tests (no Neo4j needed)
make test

# All tests including graph integration
make test-all

# With coverage
poetry run pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## 👤 Author

**Mahesh Pravinsinh Solanki**
- 📍 Ghent, Belgium
- 📧 maheshsinh1910@gmail.com
- 🔗 [LinkedIn](https://linkedin.com/in/maheshsolanki-16b9a6a5)
- 🐙 [GitHub](https://github.com/twomathematicians-code)

---

## 📄 License

MIT — see [LICENSE](LICENSE).
# Community Update
