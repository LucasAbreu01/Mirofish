from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_HEAVY: str = "gpt-5-mini"
    OPENAI_MODEL_LIGHT: str = "gpt-5-nano"
    DEBUG: bool = True
    UPLOAD_DIR: str = "./uploads"
    DATABASE_URL: str = "sqlite+aiosqlite:///./mirofish.db"
    DEFAULT_MAX_ROUNDS: int = 10
    DEFAULT_AGENT_COUNT: int = 5
    AGENT_MEMORY_LIMIT: int = 20
    MAX_DOCUMENT_CHARS: int = 30000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
