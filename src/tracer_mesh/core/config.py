from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    system configuration load from environmental variables or .env file
    """

    redis_url: str = "redis://localhost:6379"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama3"
    embedding_model: str = "nomic-embed-text"
    db_path: str = "data/cve_db/nvd_mirror.db"
    chroma_path: str = "data/cve_db/chroma"

    # config environment lookup settings
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# instantiate single state settings settings
settings = Settings()
