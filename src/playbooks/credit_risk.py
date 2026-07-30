"""Credit Risk — solved playbook.

Problem: Model credit contagion and borrower-guarantor exposure networks to
predict default cascades and set risk-based capital allocations.
"""

CREDIT_RISK_PLAYBOOK = """
## 1. PROBLEM DECOMPOSITION

### Current State Failure Analysis
Credit risk models (Altman Z-score, Merton structural model, even modern PD/LGD ML models) typically treat borrowers as **independent** entities. This fails catastrophically when:
- **Guarantor chains**: Company A guarantees B's loan, B guarantees C's. If A defaults, B's credit quality deteriorates, triggering C's covenant breach — a cascade invisible to independent PD models.
- **Sectoral concentration**: 15 SMEs in the same supply chain are linked through a single anchor buyer. Tabular models see 15 uncorrelated risks; a graph sees 1 exposure with 15 paths.
- **Cross-border corporate structures**: A parent in jurisdiction X, subsidiaries in Y and Z, with inter-company loans that net to zero at group level — but liquidity cannot transfer across borders in a crisis.

### Graph Theoretic Nature
- **Nodes**: Parties (borrowers, guarantors, parent companies), Loans, CollateralAssets.
- **Edges**: HAS_LOAN, GUARANTEES, PARENT_OF, OWNS_COLLATERAL, PAYS, SETTLES.
- **Patterns**: Exposure fan-out from a defaulted node through guarantor edges, cycle detection in cross-guarantee structures, community detection for sectoral clusters.

## 2. KNOWLEDGE GRAPH SCHEMA

```cypher
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT loan_id IF NOT EXISTS FOR (l:Loan) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT collateral_id IF NOT EXISTS FOR (c:CollateralAsset) REQUIRE c.id IS UNIQUE;

CREATE INDEX loan_status FOR (l:Loan) ON (l.status);
CREATE INDEX party_cs FOR (p:Party) ON (p.credit_score);

// Party:   {id, name, credit_score:300-850, annual_revenue, sector, country,
//            pd_estimate, is_listed:bool}
// Loan:    {id, principal, interest_rate, term_months, status:PERFORMING|DELINQUENT|DEFAULTED,
//            ltv_ratio, collateral_value, origination_date, pd_1y, lgd_estimate}
// CollateralAsset:{id, type:REAL_ESTATE|EQUIPMENT|SECURITIES|GUARANTEE, market_value, haircut_pct}

// Relationships
// (b:Party)-[:HAS_LOAN]->(l:Loan)
// (g:Party)-[:GUARANTEES]->(l:Loan)
// (p:Party)-[:PARENT_OF]->(s:Party)
// (l:Loan)-[:SECURED_BY]->(c:CollateralAsset)

CALL gds.graph.project('credit_risk_graph',
  ['Party', 'Loan'],
  {
    HAS_LOAN: {orientation:'NATURAL'},
    GUARANTEES: {orientation:'NATURAL'},
    PARENT_OF: {orientation:'NATURAL'},
    RELATED_TO: {orientation:'UNDIRECTED'}
  }
);
```

## 3. ALGORITHMS & METHODOLOGY

### 3.1 Contagion Simulation (Monte Carlo over graph)

```
Input: seed default event on Party X
1. Mark X as DEFAULTED, propagating to all Loans where X is borrower
2. For each GUARANTEES edge from affected loans → guarantor G:
   - G's contingent liability increases; if > 2× G's equity → G is STRESSED
3. Recurse: STRESSED parties become DEFAULTED with probability p = 1/(1+e^(-β·leverage_ratio))
4. Run 5000 Monte Carlo reps → expected loss distribution
```

### 3.2 Graph Algorithms

- **Louvain Community Detection**: Group borrowers into natural clusters by guarantee/ownership links → if one defaults, monitor the entire cluster.
- **PageRank (Personalized)**: Restart vector seeded on DISTRESSED parties → propagation scores show exposure intensity.
- **Label Propagation**: Seed DISTRESSED labels on known-defaulted borrowers → propagate to their guarantor/owner network → identify hidden-at-risk entities.

### 3.3 GNN Architecture

- **RGCN (Relational Graph Convolutional Network)**: Different weight matrices for HAS_LOAN, GUARANTEES, PARENT_OF — learns that a GUARANTEES edge transmits risk differently than a PARENT_OF edge.
- **TGN (Temporal Graph Network)**: When a loan status transitions (PERFORMING→DELINQUENT), a temporal event updates the neighborhood via message-passing — real-time risk dashboards.

## 4. KPIs, MEASUREMENT & COMPLIANCE

| KPI | Target | Measurement |
|:----|:------|:------------|
| Default prediction AUC | >0.88 | GNN vs baseline logistic regression on hold-out |
| Contagion cascade recall | >85% of 2nd-order defaults predicted | Compare simulated vs actual cascades |
| Risk-weighted asset (RWA) accuracy | ±5% vs regulatory calculation | Basel III standardized approach benchmark |
| Graph traversal latency | <100ms for 6-hop exposure query | EXPLAIN PROFILE |
| Concentration risk | Cluster-level HHI <0.10 | Herfindahl-Hirschman Index on Louvain communities |

### Regulatory Alignment
- **Basel III/IV**: Graph-based exposure aggregation addresses "single-name concentration" and "contagion risk" (Pillar 2).
- **IFRS 9**: ECL staging can incorporate graph-propagated PD estimates that capture forward-looking interconnected risk.
- **ECB TRIM**: Graph audit trail demonstrates that related-party lending is identified through ownership/guarantor network traversal.
""".strip()
