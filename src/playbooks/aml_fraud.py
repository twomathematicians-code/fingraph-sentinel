"""AML / Fraud Detection — solved playbook.

Problem: Detect money-mule networks and layering rings in a real-time payment graph.
"""

AML_FRAUD_PLAYBOOK = """
## 1. PROBLEM DECOMPOSITION

### Current State Failure Analysis
Traditional rule-based AML systems (threshold-based, static risk scores) miss:
- **Layering**: funds move through 5-15 intermediate accounts in rapid succession, each transfer below the alert threshold.
- **Mule recruitment**: newly-opened accounts receive small "test" deposits before large inflows, invisible to overnight batch jobs.
- **Structural obfuscation**: criminals use corporate shells with nested beneficial ownership, making single-entity screening useless.

### Why Non-Graph Approaches Fail
- SQL recursive CTEs cannot answer "find all accounts within 3 hops of this SAR-flagged account" at scale (500M+ transactions) — requires materialized paths or exponential join explosion.
- Tabular feature engineering flattens relationship topology; a mule account's risk depends on its neighborhood, not its own balance.

### Graph Theoretic Nature
- **Nodes**: Parties (individuals, shell companies), Accounts, Transactions, Alerts.
- **Edges**: OWNS, SENDS, RECEIVES, RELATED_TO (beneficial owner, director, family).
- **Patterns**: Short cycles (layering), high in-degree hubs (mule accounts), low-diameter communities (fraud rings).
- **Temporal**: Edge timestamps enable velocity analysis; a dormant account that suddenly receives 50 transfers in 2 hours is a strong signal even if each transfer is $500.

## 2. KNOWLEDGE GRAPH SCHEMA

```cypher
// ── Core constraints ──
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT txn_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE;

// ── Indexes ──
CREATE INDEX party_name IF NOT EXISTS FOR (p:Party) ON (p.name);
CREATE INDEX txn_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX txn_amount IF NOT EXISTS FOR (t:Transaction) ON (t.amount);
CREATE INDEX alert_ts IF NOT EXISTS FOR (al:Alert) ON (al.timestamp);

// ── Node properties ──
// Party:  {id, name, type: INDIVIDUAL|COMPANY, risk_score:0-100, jurisdiction, is_pep, is_sanctioned}
// Account:{id, number, type: CHECKING|SAVINGS|CRYPTO, currency, opened_date, balance, is_closed}
// Transaction:{id, amount, currency, method: WIRE|ACH|CARD|CRYPTO, timestamp, velocity_flag, is_sar_flagged}
// Alert:  {id, type: STRUCTURAL|VELOCITY|CYCLE|THRESHOLD, risk_level: LOW|MED|HIGH|CRITICAL, timestamp, reason}

// ── Relationships ──
// (p:Party)-[:OWNS]->(a:Account)
// (a1:Account)-[:SENDS]->(t:Transaction)-[:RECEIVES]->(a2:Account)
// (p1:Party)-[:RELATED_TO {type:'DIRECTOR|UBO|FAMILY|GUARANTOR'}]->(p2:Party)
// (t:Transaction)-[:TRIGGERS]->(al:Alert)

// ── GDS projection for GNN training ──
CALL gds.graph.project(
  'aml_fraud_graph',
  ['Party', 'Account'],
  {
    OWNS: {orientation:'UNDIRECTED'},
    SENDS: {orientation:'NATURAL'},
    RECEIVES: {orientation:'NATURAL'},
    RELATED_TO: {orientation:'UNDIRECTED', properties:['type']}
  }
);
```

## 3. ALGORITHMS & METHODOLOGY

### 3.1 Real-Time Mule Detection Pipeline (streaming)

```
Kafka transaction stream → Neo4j (upsert edge)
    ├── Velocity check: COUNT{(a)-[:SENDS]->(:Transaction)} in last 60 min
    │   If >30 → CREATE Alert {type:'VELOCITY', level:'HIGH'}
    ├── Cycle detection: shortestPath(a,b) WHERE a→…→a length ≤4
    │   If cycle found → CREATE Alert {type:'CYCLE', level:'CRITICAL'}
    └── PageRank delta: re-rank accounts every 5 min
        Top-100 by PR → flag for SAR review
```

### 3.2 Offline Graph ML (daily batch)

1. **FastRP embeddings** (256-dim) on `aml_fraud_graph` → account node embeddings.
2. **GraphSAGE** fine-tuned on 3 years of historical SAR labels (supervised).
3. **XGBoost classifier** takes [GraphSAGE_embedding + transaction-stats + velocity-features] → fraud probability.
4. **SHAP explainer** on top features → audit-ready justification for each alert.

### 3.3 GNN Architecture

- **GraphSAGE** (2-layer, mean aggregator): learns to transfer risk signal from labeled SAR accounts to unlabeled neighbors.
- **Temporal Graph Attention (TGAT)**: optional extension for time-respecting walks — captures that a transaction chain over 2 hours is riskier than over 2 months.

### 3.4 Cypher Playbook Queries

```cypher
// Find top mule-candidate accounts (high in-degree + low balance)
MATCH (a:Account)<-[:RECEIVES]-(:Transaction)<-[:SENDS]-(src:Account)
WITH a, count(src) AS in_degree, a.balance AS bal
WHERE in_degree > 20 AND bal < 5000
RETURN a.id, a.number, in_degree, bal ORDER BY in_degree DESC LIMIT 20;

// Detect 3-hop layering cycles
MATCH p=(a:Account)-[:SENDS]->(:Transaction)-[:RECEIVES]->(b:Account)-[:SENDS]->
  (:Transaction)-[:RECEIVES]->(c:Account)-[:SENDS]->(:Transaction)-[:RECEIVES]->(a)
WHERE a.id < b.id AND a.id < c.id
RETURN a.id AS node1, b.id AS node2, c.id AS node3;
```

## 4. KPIs, MEASUREMENT & COMPLIANCE

| KPI | Target | Measurement Method |
|:----|:------|:-------------------|
| **SAR detection recall** | >90% | Compare against 3-year historical confirmed SAR labels |
| **False Positive Rate (FPR)** | <5% | SAR filing rate / confirmed true-positive rate |
| **Alert-to-decision latency** | <2 min from transaction to alert | Kafka lag + Neo4j query elapsed |
| **Mule account interception** | 80% within 24h of first test deposit | Compare to known mule timelines |
| **Graph traversal depth** | 5 hops in <50ms | `EXPLAIN` on shortestPath queries |
| **Model explainability (SHAP)** | Top-3 features explain >60% of decision | SHAP beeswarm plot per prediction |
| **Regulatory audit** | Full trace per alert (entity→graph→model→decision) | Audit log: {alert_id, cypher_query, model_version, shap_values} |

### Regulatory Alignment
- **GDPR Art. 22**: Automated decisions have human-in-the-loop override; SHAP values serve as "meaningful information about the logic involved."
- **6AMLD (EU)**: Graph-based entity resolution addresses the requirement to identify "all natural persons involved" — ownership graph traverses UBO chains.
- **FATF Rec. 10**: CDD requires "identifying the beneficial owner" — Neo4j ownership traversal answers `[:RELATED_TO*1..5 {type:'UBO'}]`.
""".strip()
