"""Async Neo4j driver wrapper — provides healthcheck, schema catalog, and graceful fallback to in-memory mode."""

from __future__ import annotations

import os
from typing import Any

_DRIVER: Any = None  # neo4j.AsyncGraphDatabase.driver instance, lazy-loaded


def _get_uri() -> str:
    return os.getenv("NEO4J_URI", "bolt://localhost:7687")


def _get_auth() -> tuple[str, str]:
    return (
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "fingraph-demo"),
    )


async def get_driver():
    """Return a shared async Neo4j driver, creating it on first call."""
    global _DRIVER
    if _DRIVER is None:
        try:
            from neo4j import AsyncGraphDatabase

            uri, (user, pwd) = _get_uri(), _get_auth()
            _DRIVER = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
        except Exception:
            _DRIVER = False  # sentinel: connection failed
    return _DRIVER if _DRIVER is not False else None


async def health() -> dict[str, Any]:
    """Check Neo4j connectivity and return server info, or degraded-mode status."""
    driver = await get_driver()
    if driver is None:
        return {"neo4j": "degraded", "mode": "in-memory-catalog", "uri": _get_uri()}
    try:
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            return {
                "neo4j": "connected",
                "uri": _get_uri(),
                "server": str(record["ok"] if record else "check-failed"),
            }
    except Exception as exc:
        return {"neo4j": "unreachable", "error": str(exc), "uri": _get_uri()}


async def run_cypher(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read query against Neo4j. Falls back to empty list if unavailable."""
    driver = await get_driver()
    if driver is None:
        return []
    async with driver.session() as session:
        result = await session.run(query, params or {})
        records = await result.data()
        return records
