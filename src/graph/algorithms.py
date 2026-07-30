"""Graph algorithm catalog for BFSI — each entry maps an algorithm to BFSI use-cases, Cypher invocation, and a KPI target."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphAlgorithm:
    name: str
    category: str  # centrality, community, pathfinding, pattern
    description: str
    bfsi_applications: list[str]
    cypher_example: str
    kpi_target: str

    def to_card(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "bfsi_applications": self.bfsi_applications,
            "cypher": self.cypher_example,
            "kpi_target": self.kpi_target,
        }


CATALOG: list[GraphAlgorithm] = [
    GraphAlgorithm(
        name="PageRank",
        category="centrality",
        description="Iterative algorithm that scores nodes by the number and quality of incoming edges — identifies influential entities in a financial network.",
        bfsi_applications=[
            "Identify money-mule hub accounts (high in-degree from many disparate accounts)",
            "Score corporate entities by ownership depth for ultimate-beneficial-owner (UBO) analysis",
            "Rank insurance providers by claim volume in a provider network to detect claim concentration",
        ],
        cypher_example="""// Top-20 accounts by PageRank in the transaction graph
CALL gds.pageRank.stream('aml_graph')
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, score
WHERE n:Account
RETURN n.id, n.number, score
ORDER BY score DESC LIMIT 20""",
        kpi_target="Mule hub detection: >95% of top-20 by PageRank should be flagged for review.",
    ),
    GraphAlgorithm(
        name="Louvain Community Detection",
        category="community",
        description="Modularity-maximization algorithm that partitions the graph into densely-connected communities — reveals natural clusters like fraud rings or exposure groups.",
        bfsi_applications=[
            "Detect AML layering rings: tightly-knit subgraphs of accounts with circular money flows",
            "Identify credit-risk contagion clusters: groups of borrowers connected by guarantees/ownership",
            "Reveal staged-accident rings in insurance: interconnected claimants, providers, and witnesses",
        ],
        cypher_example="""// Detect fraud-ring communities
CALL gds.louvain.stream('aml_graph')
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS n, communityId
WHERE n:Party
RETURN communityId, collect(n.id)[0..5] AS sample_parties, count(*) AS size
ORDER BY size DESC LIMIT 10""",
        kpi_target="Community homogeneity: >80% of members in a flagged community share a risk signal.",
    ),
    GraphAlgorithm(
        name="Betweenness Centrality",
        category="centrality",
        description="Measures how often a node lies on the shortest path between other nodes — identifies bridge entities critical to financial flows.",
        bfsi_applications=[
            "Find choke-point accounts for AML: if these are monitored, most laundering flows are intercepted",
            "Identify systemic-risk nodes in interbank lending: whose failure would fragment the network",
            "KYC: pinpoint persons who connect otherwise-separate corporate ownership clusters",
        ],
        cypher_example="""// Top betweenness accounts in transaction graph
CALL gds.betweenness.stream('aml_graph')
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, score
WHERE n:Account
RETURN n.id, n.number, score
ORDER BY score DESC LIMIT 20""",
        kpi_target="Intercept potential: monitoring the top-5% by betweenness should cover >60% of transaction volume.",
    ),
    GraphAlgorithm(
        name="Cycle Detection (Johnson's)",
        category="pattern",
        description="Finds simple cycles in a directed graph — critical for detecting circular payment patterns (a hallmark of money laundering).",
        bfsi_applications=[
            "Detect circular fund flows: A→B→C→A layered to obscure the source",
            "Identify reinsurance spirals: circular risk transfer between related insurers",
            "Spot circular ownership: company A owns B, B owns C, C owns A — masking true UBO",
        ],
        cypher_example="""// Find short payment cycles (layering indicator)
MATCH (a:Account)-[:SENDS]->(:Transaction)-[:RECEIVES]->(b:Account)
MATCH path = shortestPath((b)-[:SENDS*..3]->(a))
WHERE a <> b
RETURN a.id AS source, [n IN nodes(path) | n.id] AS cycle_path, 
       length(path) AS hops
LIMIT 50""",
        kpi_target="Cycle flag rate: circular flows >$10k with ≤4 hops should trigger an alert within 60 seconds.",
    ),
    GraphAlgorithm(
        name="Shortest Path (Dijkstra / BFS)",
        category="pathfinding",
        description="Finds the minimum-weight or minimum-hop route between nodes — core to exposure-distance and contagion-path analysis.",
        bfsi_applications=[
            "AML: compute minimum hops from a flagged entity to any other account — assess exposure radius",
            "Credit risk: shortest path from a defaulted borrower to a healthy bank through guarantee chains",
            "KYC: distance from a customer to a sanctioned entity through beneficial-ownership links",
        ],
        cypher_example="""// Shortest path from a sanctioned party to any account
MATCH (sanctioned:Party {is_sanctioned: true})
MATCH (target:Account)
MATCH path = shortestPath((sanctioned)-[*..6]-(target))
RETURN sanctioned.name, target.number, length(path) AS hops,
       [n IN nodes(path) | labels(n)[0]] AS path_labels
ORDER BY hops ASC LIMIT 20""",
        kpi_target="0-hop guarantee: any sanctioned or PEP entity must be ≤0 hops away from a blocked-account flag within 5 seconds of screening.",
    ),
    GraphAlgorithm(
        name="Node Embedding (FastRP) + GraphSAGE",
        category="gnn",
        description="Fast Random Projection produces low-dim embeddings from graph structure; GraphSAGE learns node representations that generalize to unseen nodes — used as features for downstream fraud/risk classifiers.",
        bfsi_applications=[
            "Generate account embeddings for a fraud classifier (GraphSAGE fine-tuned on labeled SAR data)",
            "Learn party embeddings that encode KYC/beneficial-ownership proximity — feed into risk scoring",
            "Insurance: embed providers + claimants together; cluster to reveal organized fraud rings",
        ],
        cypher_example="""// Generate FastRP embeddings for all accounts
CALL gds.fastRP.stream('aml_graph', {embeddingDimension: 128, iterationWeights: [0.0, 1.0, 1.0]})
YIELD nodeId, embedding
WITH gds.util.asNode(nodeId) AS n, embedding
WHERE n:Account
RETURN n.id, embedding
LIMIT 10""",
        kpi_target="Classifier AUC: XGBoost on GraphSAGE embeddings + transaction features achieves >0.92 AUC on hold-out SAR labels vs 0.85 without graph features.",
    ),
    GraphAlgorithm(
        name="Label Propagation",
        category="community",
        description="Semi-supervised algorithm that spreads labels from a few known-flagged nodes to unlabeled neighbors — excellent for risk-contagion seeding.",
        bfsi_applications=[
            "Credit risk contagion: seed with known-defaulted borrowers, propagate risk labels through guarantor edges",
            "AML: seed with confirmed SAR accounts, propagate 'suspicious' labels through transaction networks",
            "Insurance: seed with known-fraudulent claims, identify similar nearby claims by provider/claimant links",
        ],
        cypher_example="""// Propagate fraud labels from known-SAR accounts
CALL gds.labelPropagation.stream('aml_graph', {seedProperty: 'is_sar_flagged'})
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS n, communityId
WHERE n:Account AND n.is_sar_flagged IS NULL
RETURN n.id, communityId, count(*) AS propagated_count
LIMIT 30""",
        kpi_target="Propagation precision: >70% of propagated 'suspicious' labels confirmed on manual review within 90 days.",
    ),
    GraphAlgorithm(
        name="Weakly Connected Components (WCC)",
        category="community",
        description="Finds maximal subgraphs where every node is reachable ignoring edge direction — top-level partition used to split massive graphs into manageable chunks.",
        bfsi_applications=[
            "Bank-wide: partition 500M+ transaction graph into connected components for parallel processing",
            "KYC: groups of parties connected by any ownership/document edge form a natural 'risk island'",
            "Insurance: separate unrelated claim networks to avoid cross-contamination in fraud models",
        ],
        cypher_example="""// Find the largest connected components in the full graph
CALL gds.wcc.stream('aml_graph')
YIELD nodeId, componentId
WITH componentId, count(*) AS compSize
ORDER BY compSize DESC LIMIT 10
RETURN componentId, compSize""",
        kpi_target="Component isolation: the largest WCC should be ≤30% of total nodes; if larger, the schema is too connected and needs edge-type filtering.",
    ),
]

CATALOG_BY_NAME: dict[str, GraphAlgorithm] = {a.name.lower(): a for a in CATALOG}
CATALOG_BY_CATEGORY: dict[str, list[GraphAlgorithm]] = {}
for a in CATALOG:
    CATALOG_BY_CATEGORY.setdefault(a.category, []).append(a)
