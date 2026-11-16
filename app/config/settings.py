from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "GoodBooks Marketing FAQ MCP"
    APP_ENV: str = "development"
    DEBUG: str | bool = "true"
    DATABASE_URL: str
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "marketing_faq_knowledge"
    EMBEDDING_PROVIDER: str = ""
    EMBEDDING_MODEL: str = ""
    EMBEDDING_DIMENSION: str | int | None = None
    OPENAI_API_KEY: str | None = None
    OLLAMA_URL: str = "http://localhost:11434"
    MCP_SERVER_NAME: str = "GoodBooks_Marketing_FAQ"
    MCP_SERVER_HOST: str = "127.0.0.1"
    MCP_SERVER_PORT: int = 8001
    MCP_TRANSPORT: str = "streamable-http"
    UPLOAD_DIR: str = "storage/uploads"
    EXTRACTED_DIR: str = "storage/extracted"
    MAX_FILE_SIZE_MB: int = 25
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/mcp_server.log"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150
    RELEVANCE_THRESHOLD: float = 0.35
    BROWSER_FALLBACK: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
