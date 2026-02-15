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

MAX_TEXT_LENGTH = 100  #  core/utils.py
VALID_PASSWORD = "Password123!@#01"  # ≥15 characters

# ---------------------------
# Fixtures
# ---------------------------

@pytest.fixture
def user(db_session):
    
    username = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    
    user = UserService.create_user(
        username=username,
        password=VALID_PASSWORD,
        db_session=db_session
    )
    
    return user

@pytest.fixture
def reminder_repo(db_session):
    from infrastructure.repositories import ReminderRepository
    return ReminderRepository(db_session)

# ---------------------------
# Test creation
# ---------------------------

def test_create_reminder_success(user, reminder_repo):
    text = "My first reminder"
    reminder = ReminderService.create_reminder(user, text, 1, "days", reminder_repo)
    assert reminder.id is not None
    assert reminder.text == text
    assert reminder.owner_id == user.id

    expires_at = reminder.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    assert expires_at > datetime.now(timezone.utc)

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
    read = ReminderService.read_reminder(user, reminder.id, reminder_repo)
    assert read.id == reminder.id

def test_read_reminder_invalid_uuid(user, reminder_repo):
    with pytest.raises(InvalidUUIDError):
        ReminderService.read_reminder(user, "invalid-uuid", reminder_repo)

# ---------------------------
# Test update
# ---------------------------

def test_update_reminder_success(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "Old text", 1, "days", reminder_repo)
    updated = ReminderService.update_reminder(user, reminder.id, "New text", reminder_repo)
    assert updated.text == "New text"

def test_update_reminder_text_too_long(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "Old text", 1, "days", reminder_repo)
    with pytest.raises(ReminderTextTooLongError):
        ReminderService.update_reminder(user, reminder.id, "A"*(MAX_TEXT_LENGTH+1), reminder_repo)

# ---------------------------
# Test delete
# ---------------------------

def test_delete_reminder_success(user, reminder_repo):
    reminder = ReminderService.create_reminder(user, "To delete", 1, "days", reminder_repo)
    result = ReminderService.delete_reminder(user, reminder.id, reminder_repo)
    assert result is True

def test_delete_reminder_not_found(user, reminder_repo):
    result = ReminderService.delete_reminder(user, "00000000-0000-0000-0000-000000000000", reminder_repo)
    assert result is False

# ---------------------------
# Test list and auto-delete expired
# ---------------------------

def test_list_reminders(user, reminder_repo):
    # Create two reminders
    r1 = ReminderService.create_reminder(user, "R1", 1, "days", reminder_repo)
    r2 = ReminderService.create_reminder(user, "R2", 1, "days", reminder_repo)
    reminders = ReminderService.list_reminders(user, reminder_repo)
    ids = [r.id for r in reminders]
    assert r1.id in ids and r2.id in ids

def test_auto_delete_expired_reminders(user, reminder_repo):
    # Create expired reminder
    reminder = ReminderDB(
        id="expired-uuid",
        owner_id=user.id,
        text="Expired",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        updated_at=datetime.now(timezone.utc) - timedelta(days=2),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    reminder_repo.add(reminder)
    # Auto delete
    ReminderService.auto_delete_expired_reminders(reminder_repo)
    all_reminders = reminder_repo.list_by_user(user.id)
    assert reminder.id not in [r.id for r in all_reminders]