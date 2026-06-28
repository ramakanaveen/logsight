from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://logsight:logsight@localhost:5432/logsight"
    anthropic_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8080

    model_config = {"env_prefix": "LOGSIGHT_", "env_file": ".env"}


settings = Settings()
