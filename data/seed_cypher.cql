// ── FinGraph Sentinel — Seed BFSI Graph ──────────────────────────
// Run: cypher-shell -u neo4j -p fingraph-demo -f seed_cypher.cql
// Or from docker: docker exec -i fingraph-neo4j cypher-shell -u neo4j -p fingraph-demo < seed_cypher.cql

// ── Constraints ───────────────────────────────────────────────────
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT txn_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT loan_id IF NOT EXISTS FOR (l:Loan) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (po:Policy) REQUIRE po.id IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE;

// ── Indexes ────────────────────────────────────────────────────────
CREATE INDEX txn_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX txn_amount IF NOT EXISTS FOR (t:Transaction) ON (t.amount);
CREATE INDEX party_risk IF NOT EXISTS FOR (p:Party) ON (p.risk_score);

// ── Parties ────────────────────────────────────────────────────────
CREATE (p1:Party {id:'P-001', name:'Mahesh Solanki', type:'INDIVIDUAL', risk_score:5, country:'BE', is_pep:false, is_sanctioned:false});
CREATE (p2:Party {id:'P-002', name:'Acme Holdings Ltd', type:'COMPANY', risk_score:15, country:'LU', is_pep:false, is_sanctioned:false});
CREATE (p3:Party {id:'P-003', name:'Jane Doe', type:'INDIVIDUAL', risk_score:72, country:'KY', is_pep:true, is_sanctioned:false});
CREATE (p4:Party {id:'P-004', name:'ShellCo Gamma LLC', type:'COMPANY', risk_score:88, country:'PA', is_pep:false, is_sanctioned:true});
CREATE (p5:Party {id:'P-005', name:'Global Insurance Group', type:'COMPANY', risk_score:8, country:'DE', is_pep:false, is_sanctioned:false});

// ── Accounts ───────────────────────────────────────────────────────
CREATE (a1:Account {id:'ACC-001', number:'BE68-1234-5678-9012', type:'CHECKING', currency:'EUR', opened_date:date('2023-01-15'), balance:12500});
CREATE (a2:Account {id:'ACC-002', number:'LU12-3456-7890-1234', type:'SAVINGS', currency:'EUR', opened_date:date('2024-06-01'), balance:850000});
CREATE (a3:Account {id:'ACC-003', number:'KY98-7654-3210-5678', type:'BROKERAGE', currency:'USD', opened_date:date('2025-02-10'), balance:2400000});
CREATE (a4:Account {id:'ACC-004', number:'PA11-2233-4455-6677', type:'CHECKING', currency:'USD', opened_date:date('2025-11-20'), balance:35000});

// ── Ownership ──────────────────────────────────────────────────────
CREATE (p1)-[:OWNS {since_date:date('2023-01-15')}]->(a1);
CREATE (p2)-[:OWNS {since_date:date('2024-06-01')}]->(a2);
CREATE (p3)-[:OWNS {since_date:date('2025-02-10')}]->(a3);
CREATE (p4)-[:OWNS {since_date:date('2025-11-20')}]->(a4);

// ── UBO Relationships ──────────────────────────────────────────────
CREATE (p2)-[:RELATED_TO {type:'BENEFICIAL_OWNER', ownership_pct:0.65, since_date:date('2019-03-01')}]->(p1);
CREATE (p3)-[:RELATED_TO {type:'DIRECTOR', since_date:date('2020-07-15')}]->(p2);
CREATE (p4)-[:RELATED_TO {type:'BENEFICIAL_OWNER', ownership_pct:1.0, since_date:date('2022-01-01')}]->(p2);

// ── Transactions (simplified) ──────────────────────────────────────
CREATE (t1:Transaction {id:'TXN-001', amount:15000, currency:'EUR', method:'WIRE', timestamp:datetime('2026-07-25T10:30:00Z')});
CREATE (t2:Transaction {id:'TXN-002', amount:15000, currency:'EUR', method:'WIRE', timestamp:datetime('2026-07-25T10:32:00Z')});
CREATE (t3:Transaction {id:'TXN-003', amount:14500, currency:'EUR', method:'WIRE', timestamp:datetime('2026-07-25T10:35:00Z')});
CREATE (a1)-[:SENDS {timestamp:datetime('2026-07-25T10:30:00Z')}]->(t1);
CREATE (t1)-[:RECEIVES {timestamp:datetime('2026-07-25T10:30:00Z')}]->(a2);
CREATE (a2)-[:SENDS {timestamp:datetime('2026-07-25T10:32:00Z')}]->(t2);
CREATE (t2)-[:RECEIVES {timestamp:datetime('2026-07-25T10:32:00Z')}]->(a3);
CREATE (a3)-[:SENDS {timestamp:datetime('2026-07-25T10:35:00Z')}]->(t3);
CREATE (t3)-[:RECEIVES {timestamp:datetime('2026-07-25T10:35:00Z')}]->(a1);

// ── Loan ───────────────────────────────────────────────────────────
CREATE (l1:Loan {id:'LOAN-001', principal:500000, interest_rate:0.045, term_months:60, status:'PERFORMING', origination_date:date('2024-01-10')});
CREATE (p1)-[:HAS_LOAN]->(l1);

// ── Policy ─────────────────────────────────────────────────────────
CREATE (po1:Policy {id:'POL-001', type:'AUTO', premium:1200, coverage_limit:100000, effective_date:date('2025-06-01')});
CREATE (p1)-[:HAS_POLICY]->(po1);

// ── Alert (sample) ─────────────────────────────────────────────────
CREATE (al1:Alert {id:'ALT-001', type:'CYCLE', risk_level:'CRITICAL', timestamp:datetime('2026-07-25T10:36:00Z'), reason:'3-hop payment cycle detected — potential layering'});
CREATE (t3)-[:TRIGGERS {score:0.92}]->(al1);

// ── Graph Projection for GDS ───────────────────────────────────────
CALL gds.graph.project(
  'fingraph_seed',
  ['Party', 'Account'],
  {
    OWNS: {orientation:'UNDIRECTED'},
    SENDS: {orientation:'NATURAL'},
    RECEIVES: {orientation:'NATURAL'},
    RELATED_TO: {orientation:'UNDIRECTED', properties:['type']}
  }
);
