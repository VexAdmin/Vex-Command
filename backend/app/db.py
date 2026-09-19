from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger("vex.command.db")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

_default_sql = Path(__file__).resolve().parents[2] / "sql"
SQL_DIR = Path(os.environ.get("SQL_DIR", _default_sql))


def _async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def init_db() -> None:
    global _engine, _session_factory
    if not settings.database_url:
        return
    _engine = create_async_engine(_async_url(settings.database_url), pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    await _run_migrations()


def _is_prod_like(app_env: str) -> bool:
    return app_env in ("prod", "staging")


def _migration_engine() -> AsyncEngine:
    """Separate engine for DDL migrations — owner URL when configured, otherwise
    falls back to the runtime engine (local dev keeps working with one URL).

    S3: prod/staging must always set MIGRATION_DATABASE_URL explicitly — the
    fallback exists for local dev only. Without this check an operator who
    forgets it in prod would silently try to run schema DDL over the
    least-privilege runtime DATABASE_URL (vex_founder_ro), which fails with a
    confusing permission-denied deep inside migration SQL instead of a clear
    startup error.
    """
    if _is_prod_like(settings.app_env) and not settings.migration_database_url:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL is required when APP_ENV is prod/staging — "
            "refusing to run schema migrations over the runtime DATABASE_URL."
        )
    migration_url = settings.resolved_migration_url
    if migration_url and migration_url != settings.database_url:
        return create_async_engine(_async_url(migration_url), pool_pre_ping=True)
    assert _engine is not None
    return _engine


def _dev_stub_allowed() -> bool:
    """S2: the dev stub/seed SQL (004/005) creates throwaway Raptor-shaped
    tables and fake seed data. It must NEVER run against prod/staging — those
    always point at the real Raptor Postgres, and applying the stub there
    would silently mask a real Raptor schema/connectivity failure instead of
    crashing loudly. FOUNDER_DEV_STUB=true never overrides this."""
    return settings.founder_dev_stub and not _is_prod_like(settings.app_env)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("database not initialized")
    return _session_factory


def _split_sql(sql: str) -> list[str]:
    """Split SQL on semicolons, ignoring comment lines and dollar-quoted blocks."""
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    text = "\n".join(lines)

    parts: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""

    while i < len(text):
        if not in_dollar and text[i] == "$":
            j = i + 1
            while j < len(text) and text[j] != "$":
                j += 1
            if j < len(text):
                dollar_tag = text[i : j + 1]
                in_dollar = True
                buf.append(dollar_tag)
                i = j + 1
                continue

        if in_dollar and text.startswith(dollar_tag, i):
            buf.append(dollar_tag)
            i += len(dollar_tag)
            in_dollar = False
            continue

        ch = text[i]
        if ch == ";" and not in_dollar:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


async def _run_sql_file(conn, path: Path) -> None:
    sql = path.read_text()
    for stmt in _split_sql(sql):
        if stmt.strip():
            await conn.execute(text(stmt))


async def _run_sql_file_tx(path: Path, engine: AsyncEngine | None = None) -> None:
    eng = engine or _engine
    assert eng is not None
    async with eng.begin() as conn:
        await _run_sql_file(conn, path)


async def _run_migrations() -> None:
    assert _engine is not None
    mig_engine = _migration_engine()
    owns_mig_engine = mig_engine is not _engine
    try:
        await _run_sql_file_tx(SQL_DIR / "001_founder_schema.sql", mig_engine)
        await _run_sql_file_tx(SQL_DIR / "006_account_ops.sql", mig_engine)
        await _run_sql_file_tx(SQL_DIR / "007_account_checklist.sql", mig_engine)

        # Probe with mig_engine (owner role), not the runtime engine: the runtime
        # role (vex_founder_ro) only sees organizations/users in information_schema
        # once 003_roles.sql has granted it SELECT there, but 003 runs AFTER this
        # check in the same pass — using the owner avoids that first-boot race.
        async with mig_engine.connect() as conn:
            r = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'organizations' LIMIT 1"
                )
            )
            has_raptor = r.scalar() is not None

        if not has_raptor:
            if _is_prod_like(settings.app_env):
                # S2: fail loudly — never fall through to the dev stub, and
                # never silently skip the aggregate views, on a prod/staging
                # DB that doesn't actually have Raptor's tables. A quiet "no
                # aggregate views" boot here previously looked like a healthy
                # start with an empty dashboard, not a broken DB connection —
                # no silent stub DDL on Raptor production Postgres, ever.
                raise RuntimeError(
                    "public.organizations not found in prod/staging DB — "
                    "refusing to apply the dev stub. Check that DATABASE_URL/"
                    "MIGRATION_DATABASE_URL point at the real Raptor Postgres."
                )
            if _dev_stub_allowed():
                logger.warning("Raptor tables missing — applying dev stub")
                await _run_sql_file_tx(SQL_DIR / "004_dev_raptor_stub.sql", mig_engine)
                await _run_sql_file_tx(SQL_DIR / "005_dev_seed.sql", mig_engine)
                has_raptor = True

        if has_raptor:
            await _run_sql_file_tx(SQL_DIR / "002_aggregate_views.sql", mig_engine)
            await _run_sql_file_tx(SQL_DIR / "008_alembic_head_fn.sql", mig_engine)
        else:
            logger.warning("Skipping aggregate views")

        try:
            await _run_sql_file_tx(SQL_DIR / "003_roles.sql", mig_engine)
        except Exception as exc:
            if _is_prod_like(settings.app_env):
                raise RuntimeError(
                    f"sql/003_roles.sql failed in {settings.app_env} — "
                    "refusing to start with broken DB grants"
                ) from exc
            logger.info("roles migration skipped: %s", exc)
    finally:
        if owns_mig_engine:
            await mig_engine.dispose()
