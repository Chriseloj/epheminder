import pytest
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.services import ReminderService, UserService
from core.models import ReminderDB
from core.exceptions import (
    MissingDataError,
    ReminderTextTooLongError,
    InvalidExpirationError,
    InvalidUUIDError,
    MaxRemindersReachedError
)
from config import MAX_REMINDERS_PER_USER, MAX_TEXT_LENGTH, MAX_EXPIRATION_MINUTES

# ---------------------------
# Fixtures
# ---------------------------

@pytest.fixture
def user(db_session):
    username = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    user = UserService.create_user(
        username=username,
        password="Password123!@#01",
        db_session=db_session,
    )
    return user

@pytest.fixture
def reminder_repo(db_session):
    from infrastructure.repositories import ReminderRepository
    return ReminderRepository(db_session)

# ---------------------------
# Test list
# ---------------------------


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

# ---------------------------
# Test creation
# ---------------------------

def test_create_reminder_success(user, reminder_repo):
    text = "My first reminder"
    reminder = ReminderService.create_reminder(
        user, text, 1, "days", reminder_repo
    )
    assert isinstance(reminder.id, uuid.UUID)
    assert reminder.text == text
    assert reminder.owner_id == user.id

def test_create_reminder_text_too_long(user, reminder_repo):
    text = "A" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ReminderTextTooLongError):
        ReminderService.create_reminder(user, text, 1, "days", reminder_repo)

def test_create_reminder_invalid_expiration(user, reminder_repo):
    with pytest.raises(InvalidExpirationError):
        ReminderService.create_reminder(user, "Reminder", 0, "days", reminder_repo)
    with pytest.raises(InvalidExpirationError):
        ReminderService.create_reminder(user, "Reminder", 1, "invalid_unit", reminder_repo)

def test_create_reminder_missing_repo(user):
    with pytest.raises(MissingDataError):
        ReminderService.create_reminder(user, "Reminder", 1, "days", reminder_repo=None)

# ---------------------------
# Test read
# ---------------------------

def test_read_reminder_success(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "Read me", 1, "days", reminder_repo)
    fetched = ReminderService.read_reminder(user, str(reminder.id), reminder_repo)
    assert fetched.id == reminder.id

def test_read_reminder_invalid_uuid(user, reminder_repo):
    with pytest.raises(InvalidUUIDError):
        ReminderService.read_reminder(user, "invalid-uuid", reminder_repo)

# ---------------------------
# Test update
# ---------------------------

def test_update_reminder_success(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "Old text", 1, "days", reminder_repo)
    updated = ReminderService.update_reminder(user, str(reminder.id), "New text", reminder_repo)
    assert updated.text == "New text"

def test_update_reminder_text_too_long(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "Old text", 1, "days", reminder_repo)
    with pytest.raises(ReminderTextTooLongError):
        ReminderService.update_reminder(user, str(reminder.id), "A"*(MAX_TEXT_LENGTH+1), reminder_repo)

# ---------------------------
# Test delete
# ---------------------------

def test_delete_reminder_success(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "To delete", 1, "days", reminder_repo)
    result = ReminderService.delete_reminder(user, str(reminder.id), reminder_repo)
    assert result is True

def test_delete_reminder_not_found(user, reminder_repo):
    result = ReminderService.delete_reminder(user, str(uuid.uuid4()), reminder_repo)
    assert result is False

# ---------------------------
# Test list and auto-delete expired
# ---------------------------

def test_list_reminders(user, reminder_repo):
    r1 = ReminderService.create_reminder(user, "R1", 1, "days", reminder_repo)
    r2 = ReminderService.create_reminder(user, "R2", 1, "days", reminder_repo)
    reminders = ReminderService.list_reminders(user, reminder_repo)
    ids = [r.id for r in reminders]
    assert r1.id in ids and r2.id in ids

def test_auto_delete_expired_reminders(user, reminder_repo):
    reminder = ReminderDB(
        id=uuid.uuid4(),
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

# ---------------------------
# Test max reminders per user
# ---------------------------

def test_max_reminders_per_user(monkeypatch):
    user = MagicMock()
    user.id = uuid.uuid4()  # UUID, not string

    mock_repo = MagicMock()
    mock_repo.list_by_user.return_value = [MagicMock()] * MAX_REMINDERS_PER_USER

    monkeypatch.setattr(
        ReminderService,
        "list_reminders",
        lambda u, reminder_repo=None: mock_repo.list_by_user(u.id)
    )

    with pytest.raises(MaxRemindersReachedError) as exc_info:
        ReminderService.create_reminder(user, "Test", 1, "days", reminder_repo=mock_repo)

    assert str(MAX_REMINDERS_PER_USER) in str(exc_info.value)