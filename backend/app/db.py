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


async def _run_sql_file_tx(path: Path) -> None:
    assert _engine is not None
    async with _engine.begin() as conn:
        await _run_sql_file(conn, path)


async def _run_migrations() -> None:
    assert _engine is not None
    await _run_sql_file_tx(SQL_DIR / "001_founder_schema.sql")

    async with _engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'organizations' LIMIT 1"
            )
        )
        has_raptor = r.scalar() is not None

    if not has_raptor and settings.founder_dev_stub:
        logger.warning("Raptor tables missing — applying dev stub")
        await _run_sql_file_tx(SQL_DIR / "004_dev_raptor_stub.sql")
        await _run_sql_file_tx(SQL_DIR / "005_dev_seed.sql")
        has_raptor = True

    if has_raptor:
        await _run_sql_file_tx(SQL_DIR / "002_aggregate_views.sql")
    else:
        logger.warning("Skipping aggregate views")

    try:
        await _run_sql_file_tx(SQL_DIR / "003_roles.sql")
    except Exception as exc:
        logger.info("roles migration skipped: %s", exc)
