from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    api_host: str = "127.0.0.1"
    api_port: int = 8081
    console_origin: str = "http://localhost:5174"

    # mock = localhost dev · jwt = prod (never mock on ops.)
    founder_auth_mode: str = "mock"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    vex_operator_emails: str = "sysadmin@vexraptor.com,edu@vexraptor.com"

    # mock | sql — sql when DATABASE_URL is set (unless forced mock)
    data_source: str = "auto"
    founder_dataset: str = "scale"
    founder_seed: int = 20260907
    founder_dev_stub: bool = True

    database_url: str = ""
    raptor_health_url: str = "http://127.0.0.1:8080/health"
    serve_static: bool = False
    static_dir: str = "static"

    @property
    def resolved_data_source(self) -> str:
        if self.data_source == "mock":
            return "mock"
        if self.data_source == "sql":
            return "sql"
        return "sql" if self.database_url else "mock"

    @property
    def resolved_dataset(self) -> str:
        if self.resolved_data_source == "sql" and self.app_env in ("prod", "staging"):
            return "pre_revenue"
        return self.founder_dataset

    @property
    def operator_emails(self) -> frozenset[str]:
        return frozenset(e.strip().lower() for e in self.vex_operator_emails.split(",") if e.strip())


settings = Settings()
