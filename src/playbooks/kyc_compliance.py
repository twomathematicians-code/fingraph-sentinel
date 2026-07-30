"""KYC / Compliance — solved playbook.

Problem: Entity resolution, ultimate beneficial ownership (UBO) identification,
and sanctions screening using knowledge graphs.
"""

KYC_COMPLIANCE_PLAYBOOK = """
## 1. PROBLEM DECOMPOSITION

### Current State Failure Analysis
Traditional KYC systems are **document-centric** (scan passport → verify against sanctions list → store PDF). This fails in several ways:
- **Entity resolution**: "Maersk Line A/S" and "A.P. Moller Maersk" are the same entity but stored as separate records because the legal entity identifier (LEI) was entered differently, or a subsidiary was onboarded under its trading name.
- **UBO transparency**: A 5-layer ownership chain (HoldCo → IntermediateCo1 → IntermediateCo2 → OpCo → TargetCo) with each layer <25% individually but aggregating to >75% control cannot be detected by threshold-based screening alone.
- **Sanctions evasion**: An entity delists from OFAC on Monday, incorporates under a new name on Tuesday, and opens an account on Wednesday — the bank's batch screening (nightly) catches it 18 hours too late.

### Graph Theoretic Nature
- **Nodes**: Parties, Documents, SanctionsListEntries, Accounts.
- **Edges**: RELATED_TO (UBO, director), HAS_DOCUMENT, MATCHES (fuzzy name match to sanctions list), OWNS, INCORPORATED_IN (jurisdiction).
- **Patterns**: Ownership path length >3 (UBO obfuscation), shared director across seemingly-unrelated entities, rapid reincorporation chains.

## 2. KNOWLEDGE GRAPH SCHEMA

```cypher
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT sanction_id IF NOT EXISTS FOR (s:SanctionList) REQUIRE s.id IS UNIQUE;

CREATE INDEX party_jurisdiction FOR (p:Party) ON (p.country);
CREATE INDEX doc_type_idx FOR (d:Document) ON (d.type);
CREATE INDEX sanction_list FOR (s:SanctionList) ON (s.list_name);

// Party:          {id, name, type:INDIVIDUAL|COMPANY|TRUST|FOUNDATION,
//                  country, incorporation_date, lei_number, risk_score:0-100,
//                  is_pep:bool, onboarding_date}
// Document:       {id, type:PASSPORT|ID_CARD|INCORPORATION|UTILITY_BILL|TAX_RETURN|BANK_STATEMENT,
//                  issue_date, expiry_date, 
//                  verification:VERIFIED|PENDING|EXPIRED|REJECTED}
// SanctionList:   {id, list_name:OFAC|EU|UN|HMT|DFAT, entity_name, match_type:EXACT|FUZZY|ALIAS,
//                  risk_category:HIGH|MEDIUM|LOW, listed_date, sanctions_program}

// Relationships
// (p:Party)-[:HAS_DOCUMENT]->(d:Document)
// (p1:Party)-[:RELATED_TO {type:'DIRECTOR|UBO|BENEFICIAL_OWNER|SUBSIDIARY|TRUSTEE',
//                          ownership_pct:0.0-1.0, since_date}]->(p2:Party)
// (p:Party)-[:MATCHES {confidence:0.0-1.0, method:'EXACT_NAME|FUZZY|ALIAS|LEI_CROSSWALK'}]->(s:SanctionList)
// (p:Party)-[:INCORPORATED_IN]->(country:Jurisdiction)

CALL gds.graph.project('kyc_compliance_graph',
  ['Party', 'Document', 'SanctionList'],
  {
    RELATED_TO: {orientation:'NATURAL', properties:['ownership_pct']},
    HAS_DOCUMENT: {orientation:'NATURAL'},
    MATCHES: {orientation:'UNDIRECTED', properties:['confidence']}
  }
);
```

## 3. ALGORITHMS & METHODOLOGY

### 3.1 UBO Resolution — Ownership Path Aggregation

```cypher
// For a given TargetCo, find ALL ultimate beneficial owners (>25% aggregate)
MATCH path = (ubo:Party)-[:RELATED_TO*1..5 {type:'BENEFICIAL_OWNER|UBO'}]->(target:Party {id:'TARGET-001'})
WITH ubo, target, relationships(path) AS rels
UNWIND rels AS r
WITH ubo, SUM(r.ownership_pct) AS aggregate_stake
WHERE aggregate_stake >= 0.25
RETURN ubo.id, ubo.name, aggregate_stake
ORDER BY aggregate_stake DESC;
```

### 3.2 Entity Resolution — Fuzzy Deduplication

1. **Name embeddings**: Compute character n-gram TF-IDF embeddings for all party names.
2. **Approximate Nearest Neighbors (ANN)**: For each party, find top-5 similar names using cosine similarity > 0.85.
3. **Graph-based disambiguation**: If two similar-name parties share the same jurisdiction, same director, or same LEI fragment → **MERGE** with a `SAME_AS` edge.
4. **Connected Components (WCC) on SAME_AS graph** → each component = one real-world entity.

### 3.3 Sanctions Screening — Real-Time Graph

- On every new account onboarding, run a 2-hop neighborhood query anchored on the new Party node.
- If ANY node within 2 hops has a `MATCHES` edge to a SanctionsList entry → block onboarding.
- Monthly batch: re-screen all Parties against updated sanctions lists, computing delta alerts.

### 3.4 Graph RAG for KYC Investigation

- On a KYC alert, construct a **graph subgraph** of the entity's neighborhood (ownership, directorships, sanctions matches).
- Serialize the subgraph as natural-language triples and feed into an LLM via a **Graph RAG** retrieval chain.
- LLM produces a plain-English summary: "Company X is 42% owned by Person Y (PEP, UAE), who also directs Company Z (sanctioned entity under OFAC SDN List)."

## 4. KPIs, MEASUREMENT & COMPLIANCE

| KPI | Target | Measurement |
|:----|:------|:------------|
| Sanctions screening recall | 100% (zero false negatives) | Audit against regulatory list version |
| Screening latency | <5 seconds per onboarding | API response time P95 |
| Entity resolution precision | >95% | Manual review of merged entities |
| UBO path completeness | >99% for paths ≤5 hops | Audit against corporate registries |
| Graph RAG accuracy | >90% faithful to subgraph | Human evaluator rating (1-5) |
| Periodic review cycle | 100% of high-risk within 30 days | Automated workflow tracking |

### Regulatory Alignment
- **4AMLD/5AMLD (EU)**: Graph-based UBO traversal directly addresses the requirement to "identify and verify the beneficial owner(s)" — the Cypher query output is a defensible audit artifact.
- **FATF Rec. 24**: "Competent authorities should have access to adequate, accurate and timely information on the beneficial ownership" — the ownership graph is the information architecture.
- **GDPR**: Graph queries for KYC run on data held for a legal obligation (Art. 6(1)(c)); personal data is not exported — only aggregated compliance conclusions leave the graph.
- **PSD2 / PSR**: Strong customer authentication (SCA) can be enhanced by graph-based behavioral profiling — a login from a new device + a 1-hop anomaly in the transaction graph → step-up authentication.
""".strip()
