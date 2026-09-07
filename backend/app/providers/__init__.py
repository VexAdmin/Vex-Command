from __future__ import annotations

from app.config import settings
from app.providers.mock import MockProvider, build_mock_provider
from app.providers.sql import SqlProvider


def build_provider():
    if settings.resolved_data_source == "sql":
        return SqlProvider()
    return build_mock_provider(settings.founder_seed, settings.resolved_dataset)
