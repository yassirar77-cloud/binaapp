"""
The cron runner's environment gate.

`python cron_runner.py design-stats` exited 1 with "Missing required
environment variables: SUPABASE_SERVICE_ROLE_KEY" while the rest of the
backend (app/main.py, design_plan_store) happily accepts SUPABASE_SERVICE_KEY
or SUPABASE_KEY for the same secret. The gate now accepts every alias and
normalises the winner into SUPABASE_SERVICE_ROLE_KEY for app.config.settings.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cron_runner


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("SUPABASE_URL",) + cron_runner.SERVICE_KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    yield


def test_accepts_the_canonical_name(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "role-key")

    assert cron_runner.verify_environment() is True
    assert os.environ["SUPABASE_SERVICE_ROLE_KEY"] == "role-key"


@pytest.mark.parametrize("alias", ["SUPABASE_SERVICE_KEY", "SUPABASE_KEY"])
def test_alias_is_accepted_and_normalised(monkeypatch, alias):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv(alias, "alias-key")

    assert cron_runner.verify_environment() is True
    # settings.SUPABASE_SERVICE_ROLE_KEY only reads the canonical name.
    assert os.environ["SUPABASE_SERVICE_ROLE_KEY"] == "alias-key"


def test_blank_value_does_not_count(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "   ")

    assert cron_runner.verify_environment() is False


def test_missing_key_fails(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")

    assert cron_runner.verify_environment() is False


def test_missing_url_fails(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "role-key")

    assert cron_runner.verify_environment() is False
