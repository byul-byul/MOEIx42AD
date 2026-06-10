# /backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "moei"
    postgres_user: str = "moei"
    postgres_password: str = "changeme"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    # OpenAI
    openai_api_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""  # e.g. https://<ngrok>.ngrok.io/telegram/webhook

    # Inter-service
    backend_url: str = "http://backend:8000"

    # ElevenLabs
    elevenlabs_api_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
