import pytest
from core.models import Reminder, User
from core.security import Role
from core.services import create_reminder, read_reminder, update_reminder, delete_reminder, parse_expiration
from core.exceptions import ReminderTextTooLongError, PermissionDeniedError, InvalidExpirationError

superadmin = User(user_id=1, role=Role.SUPERADMIN)
admin = User(user_id=2, role=Role.ADMIN)
user1 = User(user_id=3, role=Role.USER)
user2 = User(user_id=4, role=Role.USER)
guest = User(user_id=5, role=Role.GUEST)

@pytest.fixture
def reminders_list():
    return []

# ----------Create----------
def test_create_reminder_valid(reminders_list):
    r = create_reminder(user1, "some", 10, "minutes", reminders_list)
    assert r.text == "some"
    assert r.owner_id == user1.user_id
    assert r in reminders_list

def test_create_reminder_text_too_long(reminders_list):
    long_text = "a" * 101
    with pytest.raises(ReminderTextTooLongError):
        create_reminder(user1, long_text, 10, "minutes", reminders_list)

def test_create_reminder_invalid_expiration(reminders_list):
    with pytest.raises(InvalidExpirationError):
        create_reminder(user1, "some", 10081, "minutes", reminders_list)

def test_create_reminder_no_permission(reminders_list):
    with pytest.raises(PermissionDeniedError):
        create_reminder(guest, "some", 10, "minutes", reminders_list)

# ----------Read----------
def test_read_reminder_allowed(reminders_list):
    r = create_reminder(user1, "Check", 10, "minutes", reminders_list)
    result = read_reminder(user1, r)
    assert result == r

def test_read_reminder_denied(reminders_list):
    r = create_reminder(user1, "Check", 10, "minutes", reminders_list)
    with pytest.raises(PermissionDeniedError):
        read_reminder(user2, r)

# ----------Updater----------
def test_update_reminder_allowed(reminders_list):
    r = create_reminder(user1, "Original", 10, "minutes", reminders_list)
    updated = update_reminder(user1, r, "New text")
    assert updated.text == "New text"

def test_update_reminder_text_too_long(reminders_list):
    r = create_reminder(user1, "Original", 10, "minutes", reminders_list)
    with pytest.raises(ReminderTextTooLongError):
        update_reminder(user1, r, "a" * 101)

def test_update_reminder_no_permission(reminders_list):
    r = create_reminder(user1, "Original", 10, "minutes", reminders_list)
    with pytest.raises(PermissionDeniedError):
        update_reminder(user2, r, "New text")

# ----------Delete----------
def test_delete_reminder_manual_allowed(reminders_list):
    r = create_reminder(user1, "Delete", 10, "minutes", reminders_list)
    assert delete_reminder(user1, r, reminders_list=reminders_list)
    assert r not in reminders_list

def test_delete_reminder_no_permission(reminders_list):
    r = create_reminder(user1, "Delete", 10, "minutes", reminders_list)
    with pytest.raises(PermissionDeniedError):
        delete_reminder(user2, r, reminders_list=reminders_list)

def test_delete_reminder_auto(reminders_list):
    r = create_reminder(user1, "Auto", 10, "minutes", reminders_list)
    assert delete_reminder(user1, r, auto=True, reminders_list=reminders_list)

# ----------Parse_expiration----------
def test_parse_expiration_valid():
    assert parse_expiration(10, "minutes") == 10
    assert parse_expiration(2, "hours") == 120
    assert parse_expiration(1, "days") == 1440

def test_parse_expiration_invalid_unit():
    with pytest.raises(InvalidExpirationError):
        parse_expiration(10, "weeks")

def test_parse_expiration_out_of_range():
    with pytest.raises(InvalidExpirationError):
        parse_expiration(0, "minutes")
    with pytest.raises(InvalidExpirationError):
        parse_expiration(10081, "minutes")