from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class ICPSettings(BaseModel):
    MIN_EMPLOYEES: int = 10
    MAX_EMPLOYEES: int = 200
    TARGET_INDUSTRIES: list[str] = [
        "SaaS", "B2B", "Fintech", "Agtech", "Agency", "Software Development",
        "Technology", "Software"
    ]


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./lead_intelligence.db"

    # Discovery API Keys
    SERPER_API_KEY: str = "mock_key_if_empty"
    NEWS_API_KEY: str = "mock_key_if_empty"
    GEMINI_API_KEY: str = "mock_key_if_empty"
    CLAUDE_API_KEY: str = ""
    # ICP Blueprint Constants
    ICP: ICPSettings = ICPSettings()

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__"
    )


settings = Settings()
