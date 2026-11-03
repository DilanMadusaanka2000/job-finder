from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Software Engineer Job Aggregator"
    database_url: str = "postgresql+psycopg://jobs:jobs@localhost:5432/jobs"
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "gb"
    request_timeout_seconds: int = 20
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
