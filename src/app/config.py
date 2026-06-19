from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load from src/.env by default when running locally.
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Build DSN in code so you don't have to provide a single POSTGRES_DSN value.
    @property
    def POSTGRES_DSN(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )


settings = Settings()



