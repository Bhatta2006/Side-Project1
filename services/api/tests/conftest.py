"""Keep synthetic API tests independent of private developer deployment settings."""

import content_fixture

# Before anything imports socrat.catalog: it reads these paths once, at import.
content_fixture.install()

import pytest  # noqa: E402

from socrat.config import DatabaseSettings, Settings  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_private_dotenv(monkeypatch):
    # Explicit _env_file arguments remain usable by configuration tests.
    # Never load live credentials or rollout switches into synthetic fixtures.
    monkeypatch.setitem(DatabaseSettings.model_config, "env_file", None)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
