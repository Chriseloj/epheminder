import os
import logging
import pytest
from infrastructure.logging import configure_logging

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    
    monkeypatch.delenv("LOG_TO_CONSOLE", raising=False)
    monkeypatch.delenv("LOG_TO_FILE", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_FORCE", raising=False)
  
    logging.getLogger().handlers = []

def test_logging_console_enabled(monkeypatch, caplog):
    monkeypatch.setenv("LOG_TO_CONSOLE", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    configure_logging()
    
    logger = logging.getLogger("test")
    with caplog.at_level(logging.DEBUG):
        logger.debug("debug message")
    
    assert "debug message" in caplog.text
    
    assert any(isinstance(h, logging.StreamHandler) for h in logging.getLogger().handlers)

def test_logging_fallback_nullhandler(caplog):

    logging.getLogger().handlers = []

    configure_logging()
    logger = logging.getLogger("test")

    assert any(isinstance(h, logging.NullHandler) for h in logging.getLogger().handlers)

    with caplog.at_level(logging.INFO):
        logger.info("info message")  