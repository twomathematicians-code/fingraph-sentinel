"""Neo4j integration tests — requires a running Neo4j instance."""

import pytest

from src.graph.neo4j_client import get_driver, health, run_cypher


pytestmark = pytest.mark.skip(reason="Neo4j not available in this environment")


class TestNeo4jIntegration:
    async def test_health_connected(self):
        status = await health()
        assert status["neo4j"] == "connected"

    async def test_run_cypher_returns_records(self):
        records = await run_cypher("MATCH (n) RETURN n LIMIT 1")
        assert isinstance(records, list)
