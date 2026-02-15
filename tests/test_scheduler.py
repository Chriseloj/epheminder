import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from core.services import ReminderService
import threading
from core.services import ReminderService
from infrastructure.scheduler import ReminderScheduler
from unittest.mock import MagicMock, patch

def test_list_reminders_returns_only_active():
    # Arrange
    user_id = "user-123"
    mock_repo = MagicMock()
    
    now = datetime.now(timezone.utc)
    reminders = [
        MagicMock(expires_at=now + timedelta(minutes=10)),  # active
        MagicMock(expires_at=now - timedelta(minutes=10)),  # expired
    ]
    mock_repo.list_by_user.return_value = reminders

    # Act
    active = ReminderService.list_reminders(user=MagicMock(id=user_id), reminder_repo=mock_repo)

    # Assert
    assert len(active) == 1
    assert active[0].expires_at > now

def test_auto_delete_expired_reminders_calls_repo(monkeypatch):
    # Arrange
    mock_repo = MagicMock()
    expired_list = [MagicMock(), MagicMock()]
    mock_repo.delete_expired.return_value = expired_list

    # Act
    result = ReminderService.auto_delete_expired_reminders(reminder_repo=mock_repo)

    # Assert
    mock_repo.delete_expired.assert_called_once()
    assert result == expired_list

def test_scheduler_run_calls_service_and_stops():
    # Arrange
    mock_repo = MagicMock()
    mock_repo.delete_expired.return_value = []

    scheduler = ReminderScheduler(interval_seconds=0.1)

    # Patch Service method para usar nuestro repo mock
    with patch.object(ReminderService, 'auto_delete_expired_reminders', return_value=[]) as mock_service:
        # Run scheduler in background
        scheduler.start()
        # Let it run a little
        threading.Event().wait(0.3)
        # Stop the scheduler
        scheduler.stop()

        # Assert service was called at least once
        assert mock_service.called