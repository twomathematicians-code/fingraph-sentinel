"""Pydantic v2 settings — environment-driven config for FinGraph Sentinel."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    environment: str = "development"
    log_level: str = "INFO"

    # LLM
    fs_llm_provider: str = Field(default="", alias="FS_LLM_PROVIDER")
    fs_llm_model: str = Field(default="llama3.2", alias="FS_LLM_MODEL")
    fs_llm_api_base: str = Field(default="http://localhost:11434", alias="FS_LLM_API_BASE")
    fs_llm_api_key: str = Field(default="", alias="FS_LLM_API_KEY")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="fingraph-demo", alias="NEO4J_PASSWORD")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
