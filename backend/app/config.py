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
    # Owner/superuser URL for on-startup DDL migrations only (sql/001-003). Falls
    # back to database_url when unset — local dev keeps working with one URL.
    migration_database_url: str = ""
    raptor_health_url: str = "http://127.0.0.1:8080/health"
    raptor_auth_url: str = "http://127.0.0.1:8000/api/v1/auth"
    linear_workspace_url: str = ""
    serve_static: bool = False
    static_dir: str = "static"

    # S5: reverse proxies (nginx in front of Command) allowed to set
    # X-Forwarded-For for login rate-limiting. Never trust the header from an
    # untrusted peer — that would let any client spoof its way past the limit.
    trusted_proxy_ips: str = "127.0.0.1,::1"

    @property
    def resolved_migration_url(self) -> str:
        return self.migration_database_url or self.database_url

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

    @property
    def trusted_proxies(self) -> frozenset[str]:
        return frozenset(ip.strip() for ip in self.trusted_proxy_ips.split(",") if ip.strip())


settings = Settings()
