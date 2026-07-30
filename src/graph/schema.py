"""Neo4j graph schema templates — Cypher constraints, indexes, and node/edge definitions for BFSI domains."""

from __future__ import annotations

# ─── Core BFSI node labels ────────────────────────────────────────────────────
NODE_LABELS: dict[str, str] = {
    "Party": "A natural person or legal entity (customer, company, counterparty).",
    "Account": "Bank account, trading account, or policy account.",
    "Transaction": "A monetary transfer between accounts.",
    "Loan": "A credit facility extended to a Party.",
    "Policy": "An insurance policy held by a Party.",
    "Claim": "An insurance claim filed against a Policy.",
    "Payment": "A payment event associated with a Loan or Claim.",
    "Document": "KYC document (ID, proof of address, incorporation certificate).",
    "SanctionList": "A sanctions or PEP list entry.",
    "Alert": "A system-generated alert (AML, fraud, credit).",
}

EDGE_TYPES: dict[str, tuple[str, str, str]] = {
    "OWNS": ("Party", "Account", "A party is the beneficial owner of an account."),
    "SENDS": ("Account", "Transaction", "An account originates a transfer."),
    "RECEIVES": ("Transaction", "Account", "An account receives a transfer."),
    "RELATED_TO": ("Party", "Party", "Company director, family, guarantor, or UBO relationship."),
    "HAS_LOAN": ("Party", "Loan", "A party holds a credit facility."),
    "HAS_POLICY": ("Party", "Policy", "A party is the policyholder."),
    "FILES_CLAIM": ("Party", "Claim", "A party files an insurance claim."),
    "CLAIM_AGAINST": ("Claim", "Policy", "A claim is filed against a specific policy."),
    "PAYS": ("Party", "Payment", "A party makes a payment."),
    "SETTLES": ("Payment", "Loan", "A payment settles part of a loan."),
    "HAS_DOCUMENT": ("Party", "Document", "KYC / compliance document."),
    "MATCHES": ("Party", "SanctionList", "Party appears on a sanctions/PEP list."),
    "TRIGGERS": ("Transaction", "Alert", "A transaction triggers an alert."),
}

# ─── Domain-specific Cypher schema DDL blocks ──────────────────────────────────

AML_FRAUD_SCHEMA = """// ── AML / Fraud Graph Schema ──────────────────────────────
// Core entities
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT txn_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (a:Alert) REQUIRE a.id IS UNIQUE;

// Indexes for traversal performance
CREATE INDEX party_name IF NOT EXISTS FOR (p:Party) ON (p.name);
CREATE INDEX txn_date IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX alert_date IF NOT EXISTS FOR (a:Alert) ON (a.timestamp);

// Node property taxonomies
// Party: {id, name, type: INDIVIDUAL|COMPANY|TRUST, risk_score: 0-100, 
//          jurisdiction, onboarded_date, is_pep: bool, is_sanctioned: bool}
// Account: {id, number, type: CHECKING|SAVINGS|BROKERAGE|CRYPTO, currency,
//           opened_date, balance, is_closed: bool}
// Transaction: {id, amount, currency, method: WIRE|ACH|CARD|CRYPTO|CASH,
//               timestamp, origin_geo, dest_geo, velocity_flag: bool}

// Graph projections for GNN training (fastRP + GraphSAGE)
CALL gds.graph.project(
  'aml_graph',
  ['Party', 'Account'],
  {
    OWNS: {orientation: 'UNDIRECTED'},
    SENDS: {orientation: 'NATURAL'},
    RECEIVES: {orientation: 'NATURAL'}
  }
);"""

CREDIT_RISK_SCHEMA = """// ── Credit Risk Graph Schema ─────────────────────────────
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT loan_id IF NOT EXISTS FOR (l:Loan) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT payment_id IF NOT EXISTS FOR (pm:Payment) REQUIRE pm.id IS UNIQUE;

CREATE INDEX loan_status IF NOT EXISTS FOR (l:Loan) ON (l.status);
CREATE INDEX party_credit IF NOT EXISTS FOR (p:Party) ON (p.credit_score);

// Loan: {id, principal, interest_rate, term_months, origination_date,
//        status: PERFORMING|DELINQUENT|DEFAULTED|FORECLOSED|CHARGED_OFF,
//        ltv_ratio, dti_ratio, collateral_value, pd_estimate}
// Payment: {id, amount, date, method, on_time: bool}

CALL gds.graph.project(
  'credit_graph',
  ['Party', 'Loan'],
  {
    RELATED_TO: {orientation: 'UNDIRECTED', properties: ['type']},
    HAS_LOAN: {orientation: 'NATURAL'},
    PAYS: {orientation: 'NATURAL'},
    SETTLES: {orientation: 'NATURAL'}
  }
);"""

INSURANCE_SCHEMA = """// ── Insurance Claims Graph Schema ─────────────────────────
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (po:Policy) REQUIRE po.id IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;

CREATE INDEX claim_date IF NOT EXISTS FOR (c:Claim) ON (c.filed_date);

// Policy: {id, type: AUTO|HOME|HEALTH|LIFE|COMMERCIAL, premium, coverage_limit,
//          deductible, effective_date, expiration_date, is_active: bool}
// Claim: {id, claimed_amount, approved_amount, filed_date, resolution_date,
//         status: PENDING|INVESTIGATION|APPROVED|DENIED|SETTLED|LITIGATED,
//         fraud_flag: bool, injury_severity: 0-10}

CALL gds.graph.project(
  'insurance_graph',
  ['Party', 'Policy', 'Claim'],
  {
    HAS_POLICY: {orientation: 'NATURAL'},
    FILES_CLAIM: {orientation: 'NATURAL'},
    CLAIM_AGAINST: {orientation: 'NATURAL'},
    RELATED_TO: {orientation: 'UNDIRECTED', properties: ['type']}
  }
);"""

KYC_SCHEMA = """// ── KYC / Compliance Graph Schema ──────────────────────────
CREATE CONSTRAINT party_id IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT sanction_id IF NOT EXISTS FOR (s:SanctionList) REQUIRE s.id IS UNIQUE;

CREATE INDEX party_nationality IF NOT EXISTS FOR (p:Party) ON (p.nationality);
CREATE INDEX doc_type IF NOT EXISTS FOR (d:Document) ON (d.type);

// Document: {id, type: PASSPORT|ID_CARD|UTILITY_BILL|INCORPORATION|TAX_RETURN,
//            issue_date, expiry_date, verification_status: VERIFIED|PENDING|EXPIRED|REJECTED}
// SanctionList: {id, list_name: OFAC|EU|UN|HMT, entity_name, match_type: EXACT|FUZZY|ALIAS,
//                 risk_category: HIGH|MEDIUM|LOW, listed_date}

CALL gds.graph.project(
  'kyc_graph',
  ['Party', 'Document', 'SanctionList'],
  {
    RELATED_TO: {orientation: 'UNDIRECTED', properties: ['type']},
    HAS_DOCUMENT: {orientation: 'NATURAL'},
    MATCHES: {orientation: 'UNDIRECTED'}
  }
);"""

DOMAIN_SCHEMAS: dict[str, str] = {
    "aml_fraud": AML_FRAUD_SCHEMA,
    "credit_risk": CREDIT_RISK_SCHEMA,
    "insurance": INSURANCE_SCHEMA,
    "kyc_compliance": KYC_SCHEMA,
    "general_bfsi": AML_FRAUD_SCHEMA,  # default to AML as richest example
}
