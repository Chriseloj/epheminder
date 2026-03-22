import pytest
import logging

from cli.cli_utils import normalize_time_unit
from cli.cli_utils import safe_input
from cli.cli_exceptions import CLIExit
from cli.cli_utils import log_event

# -----------------------------
# normalize_time_unit
# -----------------------------

def test_normalize_time_unit_shortcuts():
    assert normalize_time_unit("m") == "minutes"
    assert normalize_time_unit("h") == "hours"
    assert normalize_time_unit("d") == "days"


def test_normalize_time_unit_full_words():
    assert normalize_time_unit("minutes") == "minutes"
    assert normalize_time_unit(" HOURS ") == "hours"
    assert normalize_time_unit("Days") == "days"


# -----------------------------
# safe_input
# -----------------------------

def test_safe_input_returns_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "  hello  ")
    assert safe_input("prompt") == "hello"


def test_safe_input_keyboard_interrupt(monkeypatch):
    def raise_interrupt(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr("builtins.input", raise_interrupt)

    with pytest.raises(CLIExit):
        safe_input("prompt")


def test_safe_input_eof(monkeypatch):
    def raise_eof(_):
        raise EOFError()

    monkeypatch.setattr("builtins.input", raise_eof)

    with pytest.raises(CLIExit):
        safe_input("prompt")


# -----------------------------
# log_event
# -----------------------------

def test_log_event_full(caplog):
    with caplog.at_level(logging.INFO):
        log_event(
            "info",
            "login",
            user_id="user123",
            ip="127.0.0.1",
            extra_info="test"
        )

    record = caplog.records[0]

    assert "action=login" in record.message
    assert "user_hash=" in record.message
    assert "ip_hash=" in record.message
    assert "info=test" in record.message
    assert "ts=" in record.message


def test_log_event_warning(caplog):
    with caplog.at_level(logging.WARNING):
        log_event("warning", "warn_action")

    assert any("action=warn_action" in record.message for record in caplog.records)


def test_log_event_includes_user_hash(caplog):
    with caplog.at_level(logging.INFO):
        log_event("info", "test", user_id="user123")

    assert any("user_hash=" in record.message for record in caplog.records)