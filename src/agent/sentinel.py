"""FinGraph Sentinel — GenAI Graph Engineering Agent for BFSI.

Loads the system prompt, invokes an LLM (Ollama or OpenAI-compatible via env),
and enforces the 4-section response structure. Falls back to a deterministic
rule-based solver when no LLM is configured, so CI/tests work without GPU/API.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "system_prompt.md"


@dataclass
class SentinelSolution:
    """A fully-parsed FinGraph Sentinel solution with all four sections."""

    domain: str
    problem: str
    decomposition: str
    graph_schema: str  # Cypher DDL
    algorithms: str
    kpis: str

    raw: str = field(repr=False)  # raw LLM output

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "problem": self.problem,
            "problem_decomposition": self.decomposition,
            "knowledge_graph_schema": self.graph_schema,
            "algorithms_and_methodology": self.algorithms,
            "kpis_measurement_compliance": self.kpis,
        }


# ---- Deterministic fallback (no LLM needed) ---------------------------------
_BFSI_KB: dict[str, SentinelSolution] = {}


def _load_kb() -> dict[str, SentinelSolution]:
    """Pre-load solved playbooks into the deterministic knowledge-base."""
    global _BFSI_KB
    if _BFSI_KB:
        return _BFSI_KB

    base = Path(__file__).resolve().parents[2] / "examples"
    for example_file in base.glob("solved_*.json"):
        data = json.loads(example_file.read_text(encoding="utf-8"))
        key = data.get("domain", example_file.stem)
        _BFSI_KB[key.lower()] = SentinelSolution(
            domain=data.get("domain", key),
            problem=data.get("problem", ""),
            decomposition=data.get("problem_decomposition", ""),
            graph_schema=data.get("knowledge_graph_schema", ""),
            algorithms=data.get("algorithms_and_methodology", ""),
            kpis=data.get("kpis_measurement_compliance", ""),
            raw=json.dumps(data, indent=2),
        )
    return _BFSI_KB


def _rule_match(problem: str, domain: str = "") -> SentinelSolution:
    """Keyword-based match from the KB, with a generic fallback."""
    kb = _load_kb()
    # 1) Direct domain hint (explicit from API call)
    if domain and domain in kb:
        return kb[domain]
    # 2) Keyword match in problem text
    p = problem.lower()
    for key, sol in kb.items():
        if key in p:
            return sol
    # 3) Domain-to-keyword mapping for auto-inference
    if domain:
        domain_words = {"aml_fraud": "fraud", "credit_risk": "credit", "insurance": "insurance", "kyc_compliance": "kyc"}
        for dk, hint in domain_words.items():
            if hint in domain and dk in kb:
                return kb[dk]

    # Generic fallback — constructs a schema-less response
    inferred = _infer_domain(problem)
    return SentinelSolution(
        domain=inferred,
        problem=problem,
        decomposition="""The problem requires graph-based analysis because entities (parties, accounts, transactions, claims, policies) form naturally connected structures that traditional tabular approaches flatten. Relational joins cannot efficiently traverse multi-hop relationships (e.g., "find all accounts within 3 hops of a flagged entity"). Graph databases model these as first-class citizens, enabling millisecond traversals that SQL would need hundreds of recursive CTEs to match.""",
        graph_schema="""// Generic BFSI graph schema
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
// Core relationship types
(p:Party)-[:OWNS]->(a:Account)
(a1:Account)-[:SENDS]->(t:Transaction)-[:RECEIVES]->(a2:Account)
(p1:Party)-[:RELATED_TO {type:'company_director|beneficial_owner|family|guarantor'}]->(p2:Party)""",
        algorithms="""1. **Community Detection (Louvain)**: Identify tightly-knit groups in the transaction graph — candidate fraud rings.
2. **PageRank**: Score entity influence within the financial network — high scores may indicate mule hubs.
3. **Shortest Path (BFS)**: Find the minimum hops between two suspicious accounts to assess exposure distance.
4. **Cycle Detection**: Flag circular payment flows — classic layering / money-laundering indicator.
5. **Centrality (Betweenness)**: Identify bridge entities that sit on many shortest paths — potential chokepoints for controls.""",
        kpis="""| KPI | Target | Measurement |
|:----|:------|:------------|
| False Positive Rate | < 5% | SAR filing rate vs confirmations |
| Threat Detection Time | < 2 min | Event → alert latency |
| Graph Traversal depth | 5 hops | Neo4j EXPLAIN performance |
| Model Explainability | > 0.7 SHAP | SHAP scores |
| Schema Coverage | 100% of entity types | Schema validation query |""",
        raw="{}",
    )


# ---- LLM agent --------------------------------------------------------------
_SYSTEM_PROMPT: str | None = None


def get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        if PROMPT_PATH.exists():
            _SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()
        else:
            _SYSTEM_PROMPT = "You are FinGraph Sentinel, an expert in Graph Engineering and GenAI for BFSI."
    return _SYSTEM_PROMPT


def _llm_solve(problem: str, domain: str = "") -> SentinelSolution:
    """Invoke an LLM via LangChain ChatModel abstraction."""
    model_provider = os.getenv("FS_LLM_PROVIDER", "ollama")
    model_name = os.getenv("FS_LLM_MODEL", "llama3.2")
    api_base = os.getenv("FS_LLM_API_BASE", "")
    api_key = os.getenv("FS_LLM_API_KEY", "not-needed")

    messages = [
        ("system", get_system_prompt()),
        ("human", f"Domain: {domain or 'auto-detect'}\n\nBFSI Problem: {problem}"),
    ]

    try:
        if model_provider == "openai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=model_name, base_url=api_base or None, api_key=api_key, temperature=0.2)
        else:
            from langchain_ollama import ChatOllama

            llm = ChatOllama(model=model_name, base_url=api_base or "http://localhost:11434", temperature=0.2)

        response = llm.invoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        # Fall back to rule-based on any LLM error
        sol = _rule_match(problem)
        sol.raw = f"(LLM unavailable: {exc})\n\n{_rule_match(problem).raw}"
        return sol

    return _parse_llm_output(raw, problem, domain)


# ---- Output parser — enforces 4-section structure ----------------------------
_SECTION_RX = re.compile(
    r"(?:^|\n)#{1,3}\s*(?:1\.?\s*)?(?:PROBLEM|CURRENT STATE|DECOMPOSITION|FAILURE ANALYSIS)",
    re.IGNORECASE,
)
_SECTION_NAMES = [
    "problem_decomposition",
    "knowledge_graph_schema",
    "algorithms_and_methodology",
    "kpis_measurement_compliance",
]


def _parse_llm_output(raw: str, problem: str, domain: str) -> SentinelSolution:
    """Split the LLM output into the 4 canonical sections."""
    # Find numbered/markdown section headers and split
    lines = raw.split("\n")
    sections: list[list[str]] = [[]]
    current = 0

    for line in lines:
        if re.match(r"^#{1,3}\s+(?:\d+\.?\s*)?[A-Z][A-Z\s/&-]{10,60}", line):
            current += 1
            sections.append([])
        sections[current].append(line)

    # Pad to exactly 4 sections
    while len(sections) < 4:
        sections.append([])
    # If too many (e.g. extra notes), merge tail into section 4
    if len(sections) > 4:
        for i in range(4, len(sections)):
            sections[3].extend(sections[i])

    body = ["\n".join(s) for s in sections[0:4]]

    # If no sections found, use the whole output as decomposition
    if current == 0:
        body = [raw, "", "", ""]

    return SentinelSolution(
        domain=domain or _infer_domain(problem),
        problem=problem,
        decomposition=body[0].strip() or "See raw output.",
        graph_schema=body[1].strip() or "No schema found in output.",
        algorithms=body[2].strip() or "No algorithms specified.",
        kpis=body[3].strip() or "No KPIs provided.",
        raw=raw,
    )


def _infer_domain(problem: str) -> str:
    p = problem.lower()
    if any(w in p for w in ("aml", "launder", "money laundering", "mule", "suspicious activity")):
        return "aml_fraud"
    if any(w in p for w in ("credit", "default", "loan", "borrower", "exposure")):
        return "credit_risk"
    if any(w in p for w in ("claim", "insurance", "policy", "underwr")):
        return "insurance"
    if any(w in p for w in ("kyc", "compliance", "beneficial", "sanction", "pep", "gdpr")):
        return "kyc_compliance"
    return "general_bfsi"


# ---- Public API ---------------------------------------------------------------
def solve(problem: str, domain: str = "", use_llm: bool | None = None) -> SentinelSolution:
    """Solve a BFSI graph engineering problem.

    Args:
        problem: Free-text BFSI problem description.
        domain: Optional domain hint (aml_fraud, credit_risk, insurance, kyc_compliance).
        use_llm: Force LLM (True), force deterministic (False), or auto-detect (None).
    """
    if use_llm is None:
        use_llm = bool(os.getenv("FS_LLM_PROVIDER") or os.getenv("FS_LLM_API_KEY"))

    if use_llm:
        return _llm_solve(problem, domain)
    return _rule_match(problem, domain)


def get_playbooks() -> list[dict[str, str]]:
    """Return a catalogue of known BFSI playbooks."""
    kb = _load_kb()
    return [{"domain": sol.domain, "problem": sol.problem[:120] + "…"} for sol in kb.values()]
