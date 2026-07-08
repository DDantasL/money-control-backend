from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production-use-openssl-rand-hex-32"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/money_control"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    jwt_secret_key: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    def validate_security(self) -> None:
        if self.is_production and self.jwt_secret_key == DEFAULT_JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET_KEY inseguro em produção. "
                "Gere um valor com: openssl rand -hex 32"
            )


settings = Settings()
