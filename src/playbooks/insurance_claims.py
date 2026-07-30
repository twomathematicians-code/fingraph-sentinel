"""Insurance Claims — solved playbook.

Problem: Detect organized claim rings (staged accidents, provider collusion)
and triage suspicious claims for SIU investigation.
"""

INSURANCE_CLAIMS_PLAYBOOK = """
## 1. PROBLEM DECOMPOSITION

### Current State Failure Analysis
Insurance fraud detection traditionally relies on claim-level heuristics (red flags: claim filed day after policy inception, injury inconsistent with vehicle damage). These miss:
- **Provider rings**: a clinic, a law firm, and a body shop that always appear together across claims, each filing separately.
- **Staged accident rings**: 4-6 claimants who rotate roles (driver, passenger, witness) across multiple accidents, connected by shared phone numbers or addresses.
- **Soft fraud**: legitimate claims that are inflated — undetectable at the individual claim level, but visible as a cluster of similar claims from the same provider.

### Graph Theoretic Nature
- **Nodes**: Claimants, Providers (clinics, body shops, law firms), Vehicles, Policies, Claims, Witnesses.
- **Edges**: FILES_CLAIM, TREATED_BY, REPAIRED_AT, REPRESENTED_BY, INVOLVES_VEHICLE, WITNESSED_BY, SHARES_ADDRESS, SHARES_PHONE.
- **Patterns**: Dense bipartite subgraphs (multiple claimants → same set of providers), small-world clusters, provider centrality (a single clinic in 40% of all high-value claims).

## 2. KNOWLEDGE GRAPH SCHEMA

```cypher
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (po:Policy) REQUIRE po.id IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT vehicle_id IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.id IS UNIQUE;

CREATE INDEX claim_filed FOR (c:Claim) ON (c.filed_date);
CREATE INDEX claim_amount FOR (c:Claim) ON (c.claimed_amount);

// Party:    {id, name, type:CLAIMANT|PROVIDER|WITNESS|ADJUSTER|BROKER, 
//            address, phone, date_of_birth, fraud_score}
// Policy:   {id, type:AUTO|HOME|HEALTH|COMMERCIAL, premium, coverage_limit, 
//            effective_date, expiration_date, is_active}
// Claim:    {id, claimed_amount, filed_date, incident_date, injury_severity:0-10,
//            status:PENDING|INVESTIGATION|APPROVED|DENIED|SETTLED|LITIGATED,
//            fraud_flag:bool, siu_score:0-100}
// Vehicle:  {id, vin, make, model, year, color, is_totaled:bool}

// Relationships
// (c:Claim)-[:FILED_BY]->(p:Party)
// (c:Claim)-[:AGAINST_POLICY]->(po:Policy)
// (p:Party)-[:TREATED_AT]->(provider:Party)
// (p:Party)-[:REPRESENTED_BY]->(provider:Party)
// (c:Claim)-[:INVOLVES]->(v:Vehicle)
// (p1:Party)-[:KNOWS]->(p2:Party)
// (p1:Party)-[:SHARES_ADDRESS]->(p2:Party)
// (p1:Party)-[:SHARES_PHONE]->(p2:Party)

CALL gds.graph.project('insurance_claims_graph',
  ['Party', 'Claim', 'Vehicle', 'Policy'],
  {
    FILED_BY: {orientation:'NATURAL'},
    AGAINST_POLICY: {orientation:'NATURAL'},
    TREATED_AT: {orientation:'NATURAL'},
    REPRESENTED_BY: {orientation:'NATURAL'},
    INVOLVES: {orientation:'NATURAL'},
    KNOWS: {orientation:'UNDIRECTED'},
    SHARES_ADDRESS: {orientation:'UNDIRECTED'},
    SHARES_PHONE: {orientation:'UNDIRECTED'}
  }
);
```

## 3. ALGORITHMS & METHODOLOGY

### 3.1 Ring Detection Pipeline

1. **Bipartite projection**: Project Claimant–Provider graph to a **Claimant-Claimant similarity graph** where edge weight = #shared providers.
2. **Louvain community detection** on the similarity graph → candidate rings.
3. For each community, compute:
   - **Ring density**: #actual_edges / #possible_edges in the subgraph
   - **Provider concentration**: top provider's % share of community's claims
   - **Temporal burst**: claims filed within a 90-day window
4. Flag communities exceeding all 3 thresholds → **SIU Alert (Priority 1)**.

### 3.2 GNN Architecture

- **GraphSAGE on heterogeneous graph**: learn claimant embeddings from provider co-occurrence, temporal patterns, and claim amounts.
- **Edge prediction head**: given a (claimant, provider) pair, predict the probability they appear together in a future claim → if high for unrelated pairs, that's a collusion signal.

### 3.3 Link Prediction for Hidden Relationships

Train a GNN link predictor on the full graph. It will surface **predicted-but-not-declared** relationships like:
- Two claimants who *should* be connected by SHARES_PHONE (based on other structural similarity) but currently are not → potential hidden co-conspirators.

## 4. KPIs, MEASUREMENT & COMPLIANCE

| KPI | Target | Measurement |
|:----|:------|:------------|
| Ring detection precision | >75% | Confirmed fraud / SIU-referred cases |
| Claim review time | Reduced by 40% vs non-graph triage | A/B test SIU throughput |
| Undetected relationships surfaced | >50 confirmed/year | Link prediction → manual investigation |
| Provider SIU referral rate | <5% false-positive | Quarterly audit |
| Graph query latency | <200ms for 4-hop ring query | Profile EXPLAIN |

### Regulatory Alignment
- **Solvency II**: Graph-based fraud detection improves loss ratio forecasts (Pillar I) and operational risk quantification (Pillar II).
- **IAIS ICP 21**: Graph-originated SIU flags with SHAP explainability meet "fair treatment of customers" requirements by documenting why a claim was escalated.
- **GDPR**: SHARES_ADDRESS/SHARES_PHONE edges are derived only from claims data already held for legitimate business purposes — no external data without consent.
""".strip()
