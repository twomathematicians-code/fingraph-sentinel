"FinGraph Sentinel — BFSI Graph + GenAI Agent API tests."

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


# ── Health ──────────────────────────────────────────────────────────
def test_health_returns_200():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["agent"] == "FinGraph Sentinel v1.0.0"
    assert "playbooks_loaded" in data
    assert "graph_engine" in data


# ── Solve (deterministic — no LLM needed) ───────────────────────────
def test_solve_aml_problem():
    resp = client.post(
        "/api/v1/solve",
        json={
            "problem": "Detect money-mule networks across 2M accounts with real-time transaction screening for layering rings and smurfing patterns across 4 jurisdictions.",
            "domain": "aml_fraud",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "aml_fraud"
    assert len(data["problem_decomposition"]) > 100
    assert len(data["knowledge_graph_schema"]) > 100
    assert len(data["algorithms_and_methodology"]) > 100
    assert len(data["kpis_measurement_compliance"]) > 100
    assert "Cypher" in data["knowledge_graph_schema"] or "CREATE" in data["knowledge_graph_schema"]


def test_solve_credit_risk_problem():
    resp = client.post(
        "/api/v1/solve",
        json={
            "problem": "Model credit contagion across borrower-guarantor networks to predict default cascades in SME lending portfolios and calculate risk-weighted asset exposure.",
            "domain": "credit_risk",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "credit_risk"
    assert len(data["problem_decomposition"]) > 80


def test_solve_insurance_problem():
    resp = client.post(
        "/api/v1/solve",
        json={
            "problem": "Detect organized claim rings involving staged accidents and provider collusion across auto insurance policies, with SIU triage integration.",
            "domain": "insurance",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "insurance"
    assert len(data["kpis_measurement_compliance"]) > 80


def test_solve_kyc_problem():
    resp = client.post(
        "/api/v1/solve",
        json={
            "problem": "Build an ultimate beneficial ownership resolution system for a global bank with 50M+ customers across 40 jurisdictions, integrating sanctions screening and PEP detection.",
            "domain": "kyc_compliance",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "kyc_compliance"
    assert len(data["knowledge_graph_schema"]) > 100


def test_solve_auto_detect_domain():
    resp = client.post(
        "/api/v1/solve",
        json={
            "problem": "We need to detect complex money laundering patterns including circular payments and mule accounts in our SWIFT transaction data."
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] in ("aml_fraud", "general_bfsi")


def test_solve_rejects_short_problem():
    resp = client.post("/api/v1/solve", json={"problem": "too short"})
    assert resp.status_code == 422


# ── Playbooks ───────────────────────────────────────────────────────
def test_playbooks_list():
    resp = client.get("/api/v1/playbooks")
    assert resp.status_code == 200
    assert "playbooks" in resp.json()


# ── Schemas ─────────────────────────────────────────────────────────
def test_schemas_list():
    resp = client.get("/api/v1/schemas")
    assert resp.status_code == 200
    domains = resp.json()["domains"]
    assert "aml_fraud" in domains
    assert "kyc_compliance" in domains


def test_schema_domain_aml():
    resp = client.get("/api/v1/schema/aml_fraud")
    assert resp.status_code == 200
    data = resp.json()
    assert "CREATE CONSTRAINT" in data["cypher_ddl"]


def test_schema_domain_notfound():
    resp = client.get("/api/v1/schema/nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert "general_bfsi" in data["domain"]


# ── Algorithms ──────────────────────────────────────────────────────
def test_algorithms_list():
    resp = client.get("/api/v1/algorithms")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 8
    assert len(data["algorithms"]) >= 8
    names = [a["name"] for a in data["algorithms"]]
    assert "PageRank" in names
    assert "Louvain Community Detection" in names


def test_algorithms_filter_category():
    resp = client.get("/api/v1/algorithms?category=centrality")
    assert resp.status_code == 200
    data = resp.json()
    assert all(a["category"] == "centrality" for a in data["algorithms"])


def test_algorithm_detail():
    resp = client.get("/api/v1/algorithm/pagerank")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "PageRank"
    assert len(data["bfsi_applications"]) > 0
    assert "CALL gds" in data["cypher"] or "gds." in data["cypher"]


def test_algorithm_not_found():
    resp = client.get("/api/v1/algorithm/nonexistent")
    assert resp.status_code == 404
