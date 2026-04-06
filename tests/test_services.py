import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from core.user_services import UserService
from core.reminder_services import ReminderService
from core.exceptions import (
    MissingDataError,
    InvalidUserError,
    UsernameTakenError,
    InvalidUUIDError,
    ReminderTextTooLongError,
    MaxRemindersReachedError,
    InvalidExpirationError,
)
from config import MAX_TEXT_LENGTH, MAX_REMINDERS_PER_USER, MAX_EXPIRATION_MINUTES

# ------------------------------------------
# UserService - Bad Cases
# ------------------------------------------

def test_create_user_no_db_session():
    with pytest.raises(MissingDataError):
        UserService.create_user("user1", "ValidPass123!")

def test_create_user_invalid_username(db_session):
    with pytest.raises(InvalidUserError):
        UserService.create_user("x!", "ValidPass123!", db_session=db_session)

def test_create_user_duplicate_username(db_session, sample_user):
    with pytest.raises(UsernameTakenError):
        UserService.create_user(sample_user.username, "ValidPass123!", db_session=db_session)

def test_get_user_by_id_invalid_uuid(db_session):
    assert UserService.get_user_by_id("not-a-uuid", db_session=db_session) is None

def test_get_user_by_id_no_db_session():
    with pytest.raises(MissingDataError):
        UserService.get_user_by_id(uuid.uuid4(), db_session=None)

def test_get_user_by_username_no_db_session():
    with pytest.raises(MissingDataError):
        UserService.get_user_by_username("user", db_session=None)

# ------------------------------------------
# ReminderService - Bad Cases
# ------------------------------------------

def test_create_reminder_no_repo(sample_user):
    with pytest.raises(MissingDataError):
        ReminderService.create_reminder(sample_user, "Hello", 1, "minutes", reminder_repo=None)

def test_create_reminder_text_too_long(sample_user):
    repo_mock = MagicMock()
    # Mock count_by_user to return 0 (no reminders) to bypass max check
    repo_mock.count_by_user.return_value = 0
    long_text = "x" * (MAX_TEXT_LENGTH + 1)

    with patch("core.security.authorize", return_value=None):
        with pytest.raises(ReminderTextTooLongError):
            ReminderService.create_reminder(sample_user, long_text, 1, "minutes", reminder_repo=repo_mock)

def test_create_reminder_max_reminders(sample_user):
    repo_mock = MagicMock()
    # Mock count_by_user to simulate max reminders reached
    repo_mock.count_by_user.return_value = MAX_REMINDERS_PER_USER

    with patch("core.security.authorize", return_value=None):
        with pytest.raises(MaxRemindersReachedError):
            ReminderService.create_reminder(sample_user, "Hello", 1, "minutes", reminder_repo=repo_mock)

def test_create_reminder_invalid_expiration(sample_user):
    repo_mock = MagicMock()
    with patch("core.security.authorize", return_value=None):
        # Negative amount
        with pytest.raises(InvalidExpirationError):
            ReminderService.parse_expiration(-1, "minutes")
        # Invalid unit
        with pytest.raises(InvalidExpirationError):
            ReminderService.parse_expiration(1, "weeks")
        # Exceeds max
        with pytest.raises(InvalidExpirationError):
            ReminderService.parse_expiration(MAX_EXPIRATION_MINUTES + 1, "minutes")

def test_read_reminder_invalid_uuid(sample_user):
    repo_mock = MagicMock()
    with pytest.raises(InvalidUUIDError):
        ReminderService.read_reminder(sample_user, "not-a-uuid", reminder_repo=repo_mock)

def test_read_reminder_no_repo(sample_user):
    with pytest.raises(MissingDataError):
        ReminderService.read_reminder(sample_user, str(uuid.uuid4()), reminder_repo=None)

def test_update_reminder_invalid_uuid(sample_user):
    repo_mock = MagicMock()
    with pytest.raises(InvalidUUIDError):
        ReminderService.update_reminder(sample_user, "not-a-uuid", "new text", reminder_repo=repo_mock)

def test_update_reminder_text_too_long(sample_user):
    repo_mock = MagicMock()
    reminder_mock = MagicMock()
    
    # 🔑  owner_id real for authorize
    reminder_mock.owner_id = sample_user.id
    repo_mock.get_by_id.return_value = reminder_mock
    
    long_text = "x" * (MAX_TEXT_LENGTH + 1)

    # Patch authorize to avoid problems on permission error
    with patch("core.security.authorize", return_value=None):
        with pytest.raises(ReminderTextTooLongError):
            ReminderService.update_reminder(
                sample_user, 
                str(uuid.uuid4()), 
                long_text, 
                reminder_repo=repo_mock
            )

def test_delete_reminder_invalid_uuid(sample_user):
    repo_mock = MagicMock()
    with pytest.raises(InvalidUUIDError):
        ReminderService.delete_reminder(sample_user, "not-a-uuid", reminder_repo=repo_mock)

def test_delete_reminder_not_found(sample_user):
    repo_mock = MagicMock()
    repo_mock.get_by_id.return_value = None
    with patch("core.security.authorize", return_value=None):
        assert ReminderService.delete_reminder(sample_user, str(uuid.uuid4()), reminder_repo=repo_mock) is False

def test_auto_delete_expired_reminders_no_repo():
    with pytest.raises(MissingDataError):
        ReminderService.auto_delete_expired_reminders(reminder_repo=None)

def test_list_reminders_no_repo(sample_user):
    with pytest.raises(MissingDataError):
        ReminderService.list_reminders(sample_user, reminder_repo=None)