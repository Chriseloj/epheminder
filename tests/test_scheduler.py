import pytest
from unittest.mock import MagicMock
from infrastructure.scheduler import ReminderScheduler, TokenScheduler
from unittest.mock import MagicMock, patch

# ---------------------------
# Test without expired
# ---------------------------

@patch("infrastructure.scheduler.SessionLocal")
@patch("infrastructure.scheduler.ReminderService.auto_delete_expired_reminders")
def test_reminder_scheduler_run_no_expired(mock_service, mock_session_local):
    mock_service.return_value = []
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session

    scheduler = ReminderScheduler(interval_seconds=0)

    # Ejecutar una sola iteración
    scheduler._stop_event.is_set = MagicMock(side_effect=[False, True])
    scheduler._run()

    mock_service.assert_called_once()
    mock_session.close.assert_called_once()

# ---------------------------
# Test with expired
# ---------------------------

@patch("infrastructure.scheduler.SessionLocal")
@patch("infrastructure.scheduler.ReminderService.auto_delete_expired_reminders")
def test_reminder_scheduler_run_with_expired(mock_service, mock_session_local):
    mock_service.return_value = [MagicMock(), MagicMock()]
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session

    scheduler = ReminderScheduler(interval_seconds=0)

    scheduler._stop_event.is_set = MagicMock(side_effect=[False, True])
    scheduler._run()

    mock_service.assert_called_once()
    mock_session.close.assert_called_once()

# ---------------------------
# Test except exception
# ---------------------------

@patch("infrastructure.scheduler.SessionLocal")
@patch("infrastructure.scheduler.ReminderService.auto_delete_expired_reminders")
def test_reminder_scheduler_handles_exception(mock_service, mock_session_local):
    mock_service.side_effect = Exception("DB error")
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session

    scheduler = ReminderScheduler(interval_seconds=0)

    scheduler._stop_event.is_set = MagicMock(side_effect=[False, True])
    scheduler._run()

    mock_service.assert_called_once()
    mock_session.close.assert_called_once()

# ---------------------------
# Test start and stop
# ---------------------------

def test_reminder_scheduler_start_and_stop():
    scheduler = ReminderScheduler(interval_seconds=0)

    scheduler._thread = MagicMock()

    scheduler.start()
    scheduler._thread.start.assert_called_once()

    scheduler.stop()
    scheduler._thread.join.assert_called_once()

# ---------------------------
# Test success
# ---------------------------

@patch("infrastructure.scheduler.SessionLocal")
def test_token_scheduler_run_success(mock_session_local):
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.delete.return_value = 3

    mock_session_local.return_value = mock_session

    scheduler = TokenScheduler(interval_seconds=0)

    scheduler._stop_event.is_set = MagicMock(side_effect=[False, True])
    scheduler._run()

    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()

# ---------------------------
# Test exception
# ---------------------------

@patch("infrastructure.scheduler.SessionLocal")
def test_token_scheduler_handles_exception(mock_session_local):
    mock_session = MagicMock()
    mock_session.query.side_effect = Exception("DB error")

    mock_session_local.return_value = mock_session

    scheduler = TokenScheduler(interval_seconds=0)

    scheduler._stop_event.is_set = MagicMock(side_effect=[False, True])
    scheduler._run()

    mock_session.close.assert_called_once()

# ---------------------------
# Test clean expired token
# ---------------------------

def test_cleanup_expired_tokens():
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter

    TokenScheduler.cleanup_expired_tokens(mock_session)

    mock_session.commit.assert_called_once()