"""
Tests for slot-lookup logging in template injection.

The `_log_slot_lookup` helper + the inject_* hooks emit a single
[slot_lookup] line per slot lookup so we can aggregate the AI's
slot-emission rate from production logs. These tests pin:

1. The log tag, fields, and ordering — log search queries depend on it.
2. INFO vs DEBUG level routing — INFO when slot found (interesting),
   DEBUG when not (noisy fallback case).
3. website_id / generation_count are surfaced when threaded through, and
   render as "-" when omitted (so the log line is always parseable).
4. The slot-aware injectors call `_log_slot_lookup` exactly once per run.
"""

import logging

import pytest
from loguru import logger as loguru_logger

from app.services.templates import (
    TemplateService,
    _log_slot_lookup,
)


@pytest.fixture
def caplog_loguru(caplog):
    """Bridge loguru → stdlib logging so pytest's caplog can capture the
    log lines. Without this, loguru's sink is unrelated to caplog and
    every assertion would fail silently.
    """

    class PropagateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = loguru_logger.add(
        PropagateHandler(),
        level="DEBUG",
        format="{message}",
    )
    caplog.set_level(logging.DEBUG)
    yield caplog
    loguru_logger.remove(handler_id)


class TestLogSlotLookupHelper:
    """The single helper that emits the tagged log line."""

    def test_slot_found_emits_info_with_all_fields(self, caplog_loguru):
        _log_slot_lookup(
            "maps",
            slot_found=True,
            website_id="ws-42",
            generation_count=3,
        )
        # Expect exactly one record at INFO level with the tag.
        records = [r for r in caplog_loguru.records if "[slot_lookup]" in r.message]
        assert len(records) == 1
        rec = records[0]
        assert rec.levelname == "INFO"
        assert "widget=maps" in rec.message
        assert "slot_found=True" in rec.message
        assert "website_id=ws-42" in rec.message
        assert "generation_count=3" in rec.message

    def test_slot_missed_emits_debug_not_info(self, caplog_loguru):
        # Slot-miss is the common fallback case — we don't want it
        # spamming INFO since most legacy generations don't have slots.
        _log_slot_lookup(
            "contact",
            slot_found=False,
            website_id="ws-99",
            generation_count=1,
        )
        records = [r for r in caplog_loguru.records if "[slot_lookup]" in r.message]
        assert len(records) == 1
        rec = records[0]
        assert rec.levelname == "DEBUG"
        assert "widget=contact" in rec.message
        assert "slot_found=False" in rec.message

    def test_missing_optional_fields_render_as_dash(self, caplog_loguru):
        # Some call sites won't have website_id (legacy /api/publish path
        # without uploads) or generation_count. We render "-" so the line
        # stays parseable by a single regex.
        _log_slot_lookup("maps", slot_found=True)
        rec = [r for r in caplog_loguru.records if "[slot_lookup]" in r.message][0]
        assert "website_id=-" in rec.message
        assert "generation_count=-" in rec.message

    def test_generation_count_zero_is_not_treated_as_missing(self, caplog_loguru):
        # 0 is a legitimate count (legacy rows from before migration 039
        # default to 0). It must not be coerced to "-" by a truthy check.
        _log_slot_lookup(
            "maps",
            slot_found=True,
            website_id="ws-zero",
            generation_count=0,
        )
        rec = [r for r in caplog_loguru.records if "[slot_lookup]" in r.message][0]
        assert "generation_count=0" in rec.message


class TestSlotLookupInjectorIntegration:
    """The two slot-aware injectors must emit exactly one [slot_lookup]
    line per call, regardless of whether the AI emitted the slot.
    """

    def _slot_lookup_records(self, caplog):
        return [r for r in caplog.records if "[slot_lookup]" in r.message]

    def test_inject_google_maps_logs_slot_found(self, caplog_loguru):
        ts = TemplateService()
        html = '<html><body><div id="binaapp-maps-slot"></div></body></html>'
        ts.inject_google_maps(
            html,
            "Kuala Lumpur",
            website_id="ws-found-maps",
            generation_count=2,
        )
        records = self._slot_lookup_records(caplog_loguru)
        assert len(records) == 1
        msg = records[0].message
        assert "widget=maps" in msg
        assert "slot_found=True" in msg
        assert "website_id=ws-found-maps" in msg
        assert "generation_count=2" in msg
        assert records[0].levelname == "INFO"

    def test_inject_google_maps_logs_slot_missed(self, caplog_loguru):
        ts = TemplateService()
        # No slot div in body — should fall back and log DEBUG.
        html = "<html><body></body></html>"
        ts.inject_google_maps(html, "Kuala Lumpur")
        records = self._slot_lookup_records(caplog_loguru)
        assert len(records) == 1
        assert "widget=maps" in records[0].message
        assert "slot_found=False" in records[0].message
        assert records[0].levelname == "DEBUG"

    def test_inject_contact_form_logs_slot_found(self, caplog_loguru):
        ts = TemplateService()
        html = '<html><body><div id="binaapp-contact-slot"></div></body></html>'
        ts.inject_contact_form(
            html,
            email="owner@example.com",
            website_id="ws-found-contact",
            generation_count=5,
        )
        records = self._slot_lookup_records(caplog_loguru)
        assert len(records) == 1
        msg = records[0].message
        assert "widget=contact" in msg
        assert "slot_found=True" in msg
        assert "website_id=ws-found-contact" in msg
        assert "generation_count=5" in msg
        assert records[0].levelname == "INFO"

    def test_inject_contact_form_logs_slot_missed(self, caplog_loguru):
        ts = TemplateService()
        html = "<html><body><p>no slot</p></body></html>"
        ts.inject_contact_form(html, email="owner@example.com")
        records = self._slot_lookup_records(caplog_loguru)
        assert len(records) == 1
        assert "slot_found=False" in records[0].message
        assert records[0].levelname == "DEBUG"

    def test_optional_kwargs_default_to_dash(self, caplog_loguru):
        # Backward-compat: a caller that doesn't pass website_id /
        # generation_count must still get a parseable log line.
        ts = TemplateService()
        ts.inject_google_maps('<div id="binaapp-maps-slot"></div>', "KL")
        rec = self._slot_lookup_records(caplog_loguru)[0]
        assert "website_id=-" in rec.message
        assert "generation_count=-" in rec.message
