import pytest
from unittest.mock import MagicMock, patch
from cli.cli_exceptions import CLIExit
from app.cli import run_cli
from application.auth_flow import register as auth_register, login as auth_login
from application.reminder_flow import create_reminder as create_reminder_flow
from application.reminder_flow import list_reminders as list_reminders_flow
from application.reminder_flow import delete_reminder as delete_reminder_flow
from application.session_services import SessionService

from core.exceptions import (InvalidPasswordError,
AuthenticationRequiredError,
ReminderTextTooLongError,
MaxRemindersReachedError,
InvalidExpirationError,
PermissionDeniedError)

from datetime import datetime, timezone, timedelta

# -----------------------------
# Helpers
# -----------------------------

def make_fake_user(username="alice", user_id=1):
    user = MagicMock()
    user.username = username
    user.id = user_id
    return user

def make_fake_reminder(id=1, text="Test Reminder", expires_at="2026-03-05"):
    return MagicMock(id=id, text=text, expires_at=expires_at)

# -----------------------------
# AUTH FLOW - GOOD CASES
# -----------------------------

def make_fake_login_attempt(attempts=0, lock_until=None):
    attempt = MagicMock()
    attempt.attempts = attempts
    attempt.lock_until = lock_until
    return attempt

def test_register_success():
    user = make_fake_user("bob")
    user.id = 1 

    registration_service = MagicMock()
    registration_service.register.return_value = user

    db_session = MagicMock()
    db_session.execute.return_value.scalar_one_or_none.return_value = make_fake_login_attempt()

    result = auth_register(
        username="bob",
        password="pass123",
        db_session=db_session,
        session_service=MagicMock(),
        registration_service=registration_service
    )

    assert result["success"] is True
    assert result["user"] == user

def test_login_success():
    user = make_fake_user("bob")
    user.id = 1  

    auth_service = MagicMock()
    auth_service.login.return_value = {"access_token": "abc", "refresh_token": "xyz"}

    user_service = MagicMock()
    user_service.get_user_by_username.return_value = user

    session_service = MagicMock()

    db_session = MagicMock()
    db_session.execute.return_value.scalar_one_or_none.return_value = make_fake_login_attempt(
        attempts=0,
        lock_until=None
    )

    result = auth_login(
        username="bob",
        password="pass123",
        db_session=db_session,
        session_service=session_service,
        authentication_service=auth_service,
        user_service=user_service
    )

    assert result["success"] is True
    assert result["user"] == user


# -----------------------------
# AUTH FLOW - BAD CASES
# -----------------------------

def test_register_invalid_password():
    
    registration_service = MagicMock()
    registration_service.register.side_effect = InvalidPasswordError("Too weak")

    db_session = MagicMock()

    with patch("application.auth_flow.check_register_rate_limit") as mock_check, \
         patch("application.auth_flow.apply_register_backoff") as mock_backoff, \
         patch("application.auth_flow.reset_register_attempts") as mock_reset:

        mock_check.return_value = None

        result = auth_register(
            username="bob",
            password="123",
            db_session=db_session,
            session_service=MagicMock(),
            registration_service=registration_service
        )

    assert result["success"] is False
    assert "Too weak" in result["error"]
    mock_backoff.assert_called_once()

def test_login_blocked():
    
    user = MagicMock()
    user.username = "bob"
    user.id = 1

    auth_service = MagicMock()
    auth_service.login.side_effect = AuthenticationRequiredError("Blocked")

    user_service = MagicMock()
    user_service.get_user_by_username.return_value = user

    session_service = MagicMock()

    db_session = MagicMock()
    
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    db_session.execute.return_value.scalar_one_or_none.return_value = make_fake_login_attempt(
        attempts=5,
        lock_until=locked_until
    )

    result = auth_login(
        username="bob",
        password="pass123",
        db_session=db_session,
        session_service=session_service,
        authentication_service=auth_service,
        user_service=user_service
    )

    assert result["success"] is False
    assert "Account temporarily locked" in result["error"]

# -----------------------------
# REMINDER FLOW - GOOD CASES
# -----------------------------

def test_create_reminder_success():
    reminder_repo = MagicMock()
    reminder = make_fake_reminder()
    with patch("application.reminder_flow.ReminderService.create_reminder", return_value=reminder):
        result = create_reminder_flow(
            user=make_fake_user(),
            text="Test",
            amount=1,
            unit="days",
            reminder_repo=reminder_repo
        )
    assert result["success"] is True
    assert result["reminder_id"] == reminder.id

def test_list_reminders_success():
    reminder_repo = MagicMock()
    reminders = [make_fake_reminder()]
    with patch("application.reminder_flow.ReminderService.list_reminders", return_value=reminders):
        result = list_reminders_flow(
            user=make_fake_user(),
            reminder_repo=reminder_repo
        )
    assert result["success"] is True
    assert len(result["reminders"]) == 1
    assert result["reminders"][0]["id"] == reminders[0].id

def test_delete_reminder_success():
    reminder_repo = MagicMock()
    with patch("application.reminder_flow.ReminderService.delete_reminder", return_value=True):
        result = delete_reminder_flow(
            user=make_fake_user(),
            reminder_id=1,
            reminder_repo=reminder_repo
        )
    assert result["success"] is True

# -----------------------------
# REMINDER FLOW - BAD CASES
# -----------------------------

def test_create_reminder_text_too_long():
    reminder_repo = MagicMock()
    e = ReminderTextTooLongError()
    e.max_length = 100
    with patch("application.reminder_flow.ReminderService.create_reminder", side_effect=e):
        result = create_reminder_flow(
            user=make_fake_user(),
            text="x"*200,
            amount=1,
            unit="days",
            reminder_repo=reminder_repo
        )
    assert result["success"] is False
    assert "max" in result["error"]

def test_create_reminder_max_reached():
    reminder_repo = MagicMock()
    e = MaxRemindersReachedError()
    e.max_reminders_per_user = 5
    with patch("application.reminder_flow.ReminderService.create_reminder", side_effect=e):
        result = create_reminder_flow(
            user=make_fake_user(),
            text="Test",
            amount=1,
            unit="days",
            reminder_repo=reminder_repo
        )
    assert result["success"] is False
    assert "maximum" in result["error"]

def test_delete_reminder_permission_denied():
    reminder_repo = MagicMock()
    with patch(
        "application.reminder_flow.ReminderService.delete_reminder",
        side_effect=PermissionDeniedError(role="user", action="delete_reminder")
    ):
        result = delete_reminder_flow(
            user=make_fake_user(),
            reminder_id=1,
            reminder_repo=reminder_repo
        )
        assert result["success"] is False
        assert "Permission denied" in result["error"]

# -----------------------------
# SESSION SERVICE
# -----------------------------

def test_session_service_logged_in():
    session_manager = MagicMock()
    session_manager.current_user = make_fake_user()
    session_manager.logged_in = True
    s = SessionService(session_manager=session_manager)
    assert s.current_user.username == "alice"
    assert s.logged_in is True

def test_session_service_set_clear():
    session_manager = MagicMock()
    s = SessionService(session_manager=session_manager)
    user = make_fake_user()
    s.set_session(user, access_token="abc")
    session_manager.set.assert_called_once_with(user, "abc", None)
    s.clear_session()
    session_manager.clear.assert_called_once()

# -----------------------------
# CLI - GOOD / BAD CASES
# -----------------------------

def test_cli_exit_print_only():
    inputs = ["0"]
    with patch("app.cli.safe_input", side_effect=inputs), \
         patch("app.cli.safe_print") as mock_print:
        run_cli()
        mock_print.assert_any_call("Exiting.")

def test_cli_logout_exit_print_only():
    inputs = ["6", "0"]
    with patch("app.cli.safe_input", side_effect=inputs), \
         patch("app.cli.safe_print") as mock_print:
        run_cli()
        mock_print.assert_any_call("Exiting.")

def test_cli_invalid_choice_print_only():
    inputs = ["99", "0"]
    with patch("app.cli.safe_input", side_effect=inputs), \
         patch("app.cli.safe_print") as mock_print:
        run_cli()
        
        mock_print.assert_any_call("Invalid choice. Try again.\n")
        mock_print.assert_any_call("Exiting.")