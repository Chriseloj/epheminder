import pytest
import random
import string
from datetime import datetime, timedelta, timezone
from core.services import ReminderService, UserService
from core.models import ReminderDB
from core.exceptions import (
    MissingDataError,
    ReminderTextTooLongError,
    InvalidExpirationError,
    InvalidUUIDError
)

from unittest.mock import MagicMock
from core.exceptions import MaxRemindersReachedError
from core.utils import MAX_REMINDERS_PER_USER

MAX_TEXT_LENGTH = 100  # core/utils.py
VALID_PASSWORD = "Password123!@#01"  # ≥15 characters

# ---------------------------
# Fixtures
# ---------------------------

@pytest.fixture
def user(db_session, ip):
    username = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    user = UserService.create_user(
        username=username,
        password=VALID_PASSWORD,
        db_session=db_session,
        ip=ip
    )
    return user

@pytest.fixture
def reminder_repo(db_session):
    from infrastructure.repositories import ReminderRepository
    return ReminderRepository(db_session)

# ---------------------------
# Test creation
# ---------------------------

def test_create_reminder_success(user, reminder_repo, ip):
    text = "My first reminder"
    reminder = ReminderService.create_reminder(
        user, text, 1, "days", reminder_repo, ip=ip
    )
    assert reminder.id is not None
    assert reminder.text == text
    assert reminder.owner_id == user.id

def test_create_reminder_text_too_long(user, reminder_repo, ip):
    text = "A" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ReminderTextTooLongError):
        ReminderService.create_reminder(user, text, 1, "days", reminder_repo, ip=ip)

def test_create_reminder_invalid_expiration(user, reminder_repo, ip):
    with pytest.raises(InvalidExpirationError):
        ReminderService.create_reminder(user, "Reminder", 0, "days", reminder_repo, ip=ip)
    with pytest.raises(InvalidExpirationError):
        ReminderService.create_reminder(user, "Reminder", 1, "invalid_unit", reminder_repo, ip=ip)

def test_create_reminder_missing_repo(user, ip):
    with pytest.raises(MissingDataError):
        ReminderService.create_reminder(user, "Reminder", 1, "days", reminder_repo=None, ip=ip)

# ---------------------------
# Test read
# ---------------------------

def test_read_reminder_success(user, reminder_repo, ip):
    reminder = ReminderService.create_reminder(user, "Read me", 1, "days", reminder_repo, ip=ip)
    read = ReminderService.read_reminder(user, reminder.id, reminder_repo)
    assert read.id == reminder.id

def test_read_reminder_invalid_uuid(user, reminder_repo):
    with pytest.raises(InvalidUUIDError):
        ReminderService.read_reminder(user, "invalid-uuid", reminder_repo)

# ---------------------------
# Test update
# ---------------------------

def test_update_reminder_success(user, reminder_repo, ip):
    reminder = ReminderService.create_reminder(user, "Old text", 1, "days", reminder_repo, ip=ip)
    updated = ReminderService.update_reminder(
        user, reminder.id, "New text", reminder_repo, ip=ip
    )
    assert updated.text == "New text"

def test_update_reminder_text_too_long(user, reminder_repo, ip):
    reminder = ReminderService.create_reminder(user, "Old text", 1, "days", reminder_repo, ip=ip)
    with pytest.raises(ReminderTextTooLongError):
        ReminderService.update_reminder(user, reminder.id, "A"*(MAX_TEXT_LENGTH+1), reminder_repo, ip=ip)

# ---------------------------
# Test delete
# ---------------------------

def test_delete_reminder_success(user, reminder_repo, ip):
    reminder = ReminderService.create_reminder(user, "To delete", 1, "days", reminder_repo, ip=ip)
    result = ReminderService.delete_reminder(user, reminder.id, reminder_repo, ip=ip)
    assert result is True

def test_delete_reminder_not_found(user, reminder_repo, ip):
    result = ReminderService.delete_reminder(user, "00000000-0000-0000-0000-000000000000", reminder_repo, ip=ip)
    assert result is False

# ---------------------------
# Test list and auto-delete expired
# ---------------------------

def test_list_reminders(user, reminder_repo, ip):
    r1 = ReminderService.create_reminder(user, "R1", 1, "days", reminder_repo, ip=ip)
    r2 = ReminderService.create_reminder(user, "R2", 1, "days", reminder_repo, ip=ip)
    reminders = ReminderService.list_reminders(user, reminder_repo)
    ids = [r.id for r in reminders]
    assert r1.id in ids and r2.id in ids

def test_auto_delete_expired_reminders(user, reminder_repo):
    reminder = ReminderDB(
        id="expired-uuid",
        owner_id=user.id,
        text="Expired",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        updated_at=datetime.now(timezone.utc) - timedelta(days=2),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    reminder_repo.add(reminder)
    ReminderService.auto_delete_expired_reminders(reminder_repo)
    all_reminders = reminder_repo.list_by_user(user.id)
    assert reminder.id not in [r.id for r in all_reminders]

# ---------------------------
# Test max reminder per user
# ---------------------------

def test_max_reminders_per_user(monkeypatch, ip):
    user = MagicMock()
    user.id = "user-123"
    
    mock_repo = MagicMock()
    mock_repo.list_by_user.return_value = [MagicMock()] * MAX_REMINDERS_PER_USER

    monkeypatch.setattr(ReminderService, "list_reminders", lambda u, reminder_repo=None: mock_repo.list_by_user(u.id))

    with pytest.raises(MaxRemindersReachedError) as exc_info:
        ReminderService.create_reminder(
            user, text="Test", amount=1, unit="days", reminder_repo=mock_repo, ip=ip
        )

    assert str(MAX_REMINDERS_PER_USER) in str(exc_info.value)