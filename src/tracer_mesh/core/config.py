from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # system configuration load from environmental variable or .env file

    redis_url: str = "redis://localhost:6379"
    ollama_url: str = "http://localhost:11434"
    reasoning_model: str = Field(
        default="tinyllama",
        validation_alias=AliasChoices("REASONING_MODEL", "LLM_MODEL"),
    )
    embedding_model: str = "nomic-embed-text"
    db_path: str = "data/cve_db/nvd_mirror.db"
    chroma_path: str = "data/cve_db/chroma"

    # config environment lookup setting
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# instantiate single state setting
settings = Settings()
