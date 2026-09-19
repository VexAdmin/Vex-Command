"""Sprint 2 (S2, S3, S4, S6) — fail-closed prod hardening.

No live Postgres required: db.py's migration control flow is exercised with a
fake engine/connection (see _FakeEngine below), same functions the real
_run_migrations() calls, just swapping out I/O.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import app.db as db
import app.main as main
from app.config import settings


# --- fakes for _run_migrations() without a real DB --------------------------


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeConn:
    def __init__(self, value):
        self._value = value

    async def execute(self, *_args, **_kwargs):
        return _FakeResult(self._value)


class _FakeConnCtx:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return _FakeConn(self._value)

    async def __aexit__(self, *_exc):
        return False


class _FakeEngine:
    """`has_raptor_value=None` simulates public.organizations missing; any
    other value simulates it being found."""

    def __init__(self, has_raptor_value):
        self._value = has_raptor_value

    def connect(self):
        return _FakeConnCtx(self._value)

    async def dispose(self):
        pass


@pytest.fixture
def fake_migration_files(monkeypatch):
    """Replace real SQL execution with a call-log so tests can assert which
    migration files _run_migrations() actually tried to run."""
    calls: list[str] = []

    async def fake_run_sql_file_tx(path, engine=None):
        calls.append(Path(path).name)

    monkeypatch.setattr(db, "_run_sql_file_tx", fake_run_sql_file_tx)
    monkeypatch.setattr(db, "_engine", object())
    return calls


def _use_fake_migration_engine(monkeypatch, has_raptor_value):
    monkeypatch.setattr(db, "_migration_engine", lambda: _FakeEngine(has_raptor_value))


# --- S2: dev stub forbidden in prod ------------------------------------------


def test_dev_stub_allowed_only_outside_prod_staging(monkeypatch):
    monkeypatch.setattr(settings, "founder_dev_stub", True)
    monkeypatch.setattr(settings, "app_env", "dev")
    assert db._dev_stub_allowed() is True
    monkeypatch.setattr(settings, "app_env", "prod")
    assert db._dev_stub_allowed() is False
    monkeypatch.setattr(settings, "app_env", "staging")
    assert db._dev_stub_allowed() is False


def test_dev_stub_never_allowed_when_flag_false(monkeypatch):
    monkeypatch.setattr(settings, "founder_dev_stub", False)
    monkeypatch.setattr(settings, "app_env", "dev")
    assert db._dev_stub_allowed() is False


async def test_run_migrations_raises_in_prod_when_raptor_missing(monkeypatch, fake_migration_files):
    # S2: FOUNDER_DEV_STUB=true must NOT matter in prod — the flag alone used
    # to be enough to apply 004/005 against a real Raptor production Postgres.
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "founder_dev_stub", True)
    _use_fake_migration_engine(monkeypatch, None)

    with pytest.raises(RuntimeError, match="refusing to apply the dev stub"):
        await db._run_migrations()

    assert "004_dev_raptor_stub.sql" not in fake_migration_files
    assert "005_dev_seed.sql" not in fake_migration_files
    assert "002_aggregate_views.sql" not in fake_migration_files


async def test_run_migrations_raises_in_staging_when_raptor_missing(monkeypatch, fake_migration_files):
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "founder_dev_stub", True)
    _use_fake_migration_engine(monkeypatch, None)

    with pytest.raises(RuntimeError, match="refusing to apply the dev stub"):
        await db._run_migrations()

    assert "004_dev_raptor_stub.sql" not in fake_migration_files


async def test_run_migrations_applies_stub_in_dev(monkeypatch, fake_migration_files):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "founder_dev_stub", True)
    _use_fake_migration_engine(monkeypatch, None)

    await db._run_migrations()  # must not raise

    assert "004_dev_raptor_stub.sql" in fake_migration_files
    assert "005_dev_seed.sql" in fake_migration_files
    assert "002_aggregate_views.sql" in fake_migration_files


async def test_run_migrations_skips_stub_and_views_without_flag_in_dev(monkeypatch, fake_migration_files):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "founder_dev_stub", False)
    _use_fake_migration_engine(monkeypatch, None)

    await db._run_migrations()  # must not raise

    assert "004_dev_raptor_stub.sql" not in fake_migration_files
    assert "002_aggregate_views.sql" not in fake_migration_files


async def test_run_migrations_normal_path_when_raptor_present_in_prod(monkeypatch, fake_migration_files):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "founder_dev_stub", False)
    _use_fake_migration_engine(monkeypatch, 1)

    await db._run_migrations()  # must not raise — real Raptor tables present

    assert "002_aggregate_views.sql" in fake_migration_files
    assert "004_dev_raptor_stub.sql" not in fake_migration_files


async def test_run_migrations_roles_failure_fails_loud_in_prod(monkeypatch, fake_migration_files):
    monkeypatch.setattr(settings, "app_env", "prod")
    _use_fake_migration_engine(monkeypatch, 1)

    async def fake_run_sql_file_tx(path, engine=None):
        if Path(path).name == "003_roles.sql":
            raise OSError("permission denied for schema founder")
        fake_migration_files.append(Path(path).name)

    monkeypatch.setattr(db, "_run_sql_file_tx", fake_run_sql_file_tx)

    with pytest.raises(RuntimeError, match="003_roles.sql failed in prod"):
        await db._run_migrations()


# --- S3: migrations only via MIGRATION_DATABASE_URL in prod/staging ---------


def test_migration_engine_requires_explicit_url_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "migration_database_url", "")
    monkeypatch.setattr(settings, "database_url", "postgresql://vex_founder_ro:x@host/db")
    with pytest.raises(RuntimeError, match="MIGRATION_DATABASE_URL"):
        db._migration_engine()


def test_migration_engine_requires_explicit_url_in_staging(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "migration_database_url", "")
    monkeypatch.setattr(settings, "database_url", "postgresql://vex_founder_ro:x@host/db")
    with pytest.raises(RuntimeError, match="MIGRATION_DATABASE_URL"):
        db._migration_engine()


# --- S4: admin surface (docs/openapi/redoc) ---------------------------------


def test_docs_disabled_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    assert main._docs_urls() == (None, None, None)


def test_docs_disabled_in_staging(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    assert main._docs_urls() == (None, None, None)


def test_docs_enabled_in_dev(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    assert main._docs_urls() == ("/api/founder/docs", "/redoc", "/openapi.json")


# --- S6: CORS ----------------------------------------------------------------


def test_cors_prod_excludes_localhost(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "console_origin", "https://ops.vexraptor.com")
    origins = main._cors_origins()
    assert origins == ["https://ops.vexraptor.com"]
    assert "http://127.0.0.1:5174" not in origins


def test_cors_staging_excludes_localhost(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "console_origin", "https://ops.vexraptor.com")
    origins = main._cors_origins()
    assert origins == ["https://ops.vexraptor.com"]


def test_cors_dev_includes_localhost(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "console_origin", "http://localhost:5174")
    origins = main._cors_origins()
    assert "http://127.0.0.1:5174" in origins
    assert "http://localhost:5174" in origins


# --- deploy artifacts (S2, S3, nginx) ----------------------------------------


def test_dockerfile_pins_founder_dev_stub_false():
    dockerfile = Path(__file__).resolve().parents[2] / "deploy" / "Dockerfile.vex-founder"
    text = dockerfile.read_text()
    assert "ENV FOUNDER_DEV_STUB=false" in text


def test_run_script_refuses_rw_database_url():
    script = Path(__file__).resolve().parents[2] / "deploy" / "run-vex-founder.sh"
    text = script.read_text()
    assert "vex_founder_rw" in text
    assert "exit 1" in text
    assert "MIGRATION_DATABASE_URL" in text


def test_nginx_example_has_login_rate_limit_zone():
    conf = Path(__file__).resolve().parents[2] / "deploy" / "nginx-ops.vexraptor.com.conf.example"
    text = conf.read_text()
    assert "limit_req_zone" in text and "founder_login" in text
    assert "location = /api/founder/v1/auth/login" in text
    assert "limit_req zone=founder_login" in text


def test_backup_founder_script_exists():
    script = Path(__file__).resolve().parents[2] / "deploy" / "backup-founder-schema.sh"
    text = script.read_text()
    assert "pg_dump" in text and "-n founder" in text


def test_validate_prod_settings_rejects_http_origin(monkeypatch):
    from app.prod_checks import validate_prod_settings

    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "console_origin", "http://ops.vexraptor.com")
    monkeypatch.setattr(settings, "founder_auth_mode", "jwt")
    monkeypatch.setattr(settings, "data_source", "sql")
    monkeypatch.setattr(settings, "database_url", "postgresql://x")
    with pytest.raises(RuntimeError, match="https"):
        validate_prod_settings()


def test_validate_prod_settings_ok(monkeypatch):
    from app.prod_checks import validate_prod_settings

    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "console_origin", "https://ops.vexraptor.com")
    monkeypatch.setattr(settings, "founder_auth_mode", "jwt")
    monkeypatch.setattr(settings, "data_source", "sql")
    monkeypatch.setattr(settings, "database_url", "postgresql://x")
    validate_prod_settings()


def test_roles_sql_audit_log_insert_only():
    roles = Path(__file__).resolve().parents[2] / "sql" / "003_roles.sql"
    text = roles.read_text()
    assert "GRANT INSERT ON founder.audit_log TO vex_founder_ro" in text
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES" not in text
