import pytest
from unittest.mock import patch, MagicMock
from core.cli import (
    register_user, login_user, create_reminder, list_reminders,
    delete_reminder, logout, clear_session, set_current_session,
    current_user, current_token, current_refresh_token
)
from core.exceptions import AuthenticationRequiredError
from core.models import UserDB
from unittest.mock import patch, MagicMock
from core.cli import create_reminder, set_current_session
from core.exceptions import (
    InvalidPasswordError,
    ReminderTextTooLongError,
    MaxRemindersReachedError,
    InvalidExpirationError,
    PermissionDeniedError,
    AuthenticationRequiredError
)


# ------------------------
# REGISTER USER
# ------------------------
def test_register_user(db_session):
    with patch("core.cli.safe_input", side_effect=["alice", "Password_123|@#"]), \
         patch("core.registration.RegistrationService.register") as mock_register, \
         patch("core.cli.safe_print") as mock_print:

        mock_register.return_value = UserDB(
            username="alice",
            role="USER",
            is_active=True,
            password_hash="hashed"
        )

        register_user(db_session=db_session)

        mock_register.assert_called_once()
        mock_print.assert_any_call("User 'alice' registered successfully!")

# ------------------------
# LOGIN USER
# ------------------------
def test_create_reminder_without_login(db_session):
    clear_session()

    with patch("core.cli.safe_print") as mock_print:
        create_reminder(db_session=db_session)

        mock_print.assert_any_call("You must be logged in first.")

# ------------------------
# LOGOUT
# ------------------------
def test_logout_resets_session(db_session):
    user = UserDB(username="alice", role="USER", is_active=True, password_hash="hashed")
    set_current_session(user, "token123", "refresh123")

    with patch("core.cli.safe_print") as mock_print, \
         patch("core.logout.logout") as mock_logout_service:
        logout(db_session=db_session)

        assert current_user is None
        assert current_token is None
        assert current_refresh_token is None
        mock_print.assert_any_call("Logged out successfully.")

# ------------------------
# CREATE REMINDER
# ------------------------
def test_create_reminder_success(db_session, sample_user):

    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token") as mock_decode, \
         patch("core.cli.UserService.get_user_by_id") as mock_get_user, \
         patch("core.reminder_services.ReminderService.create_reminder") as mock_create, \
         patch("core.cli.safe_input", side_effect=["Test reminder", "5", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:

        mock_decode.return_value = {"sub": str(sample_user.id)}
        mock_get_user.return_value = sample_user

        mock_create.return_value = MagicMock(id=1)

        create_reminder(db_session=db_session)

        mock_create.assert_called_once()
        mock_print.assert_any_call("Reminder created. ID: 1")
# ------------------------
# LIST REMINDERS
# ------------------------
def test_list_reminders_empty(db_session, sample_user):

    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token") as mock_decode, \
         patch("core.cli.UserService.get_user_by_id") as mock_get_user, \
         patch("core.reminder_services.ReminderService.list_reminders", return_value=[]), \
         patch("core.cli.safe_print") as mock_print:

        mock_decode.return_value = {"sub": str(sample_user.id)}
        mock_get_user.return_value = sample_user

        list_reminders(db_session=db_session)
        mock_print.assert_any_call("No active reminders.")

# ------------------------
# DELETE REMINDER
# ------------------------
def test_delete_reminder_success(db_session, sample_user):

    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token") as mock_decode, \
         patch("core.cli.UserService.get_user_by_id") as mock_get_user, \
         patch("core.reminder_services.ReminderService.delete_reminder", return_value=True), \
         patch("core.cli.safe_input", return_value="1"), \
         patch("core.cli.safe_print") as mock_print:

        mock_decode.return_value = {"sub": str(sample_user.id)}
        mock_get_user.return_value = sample_user

        delete_reminder(db_session=db_session)
        mock_print.assert_any_call("Reminder deleted successfully.")


# ------------------------
# EXPIRED TOKEN
# ------------------------
def test_create_reminder_expired_token(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token", side_effect=AuthenticationRequiredError()), \
         patch("core.cli.safe_input", side_effect=["Recordatorio expirado", "10", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Authentication required. Please login again.")


# ------------------------
# INVALID TOKEN
# ------------------------
def test_create_reminder_invalid_token(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token", side_effect=Exception()), \
         patch("core.cli.safe_input", side_effect=["Recordatorio inválido", "10", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Invalid token. Please login again.")

# ------------------------
# ALREADY LOGGED IN
# ------------------------

def test_login_user_already_logged_in(db_session):
    set_current_session(MagicMock(), "token", "refresh")

    with patch("core.cli.safe_print") as mock_print:
        login_user(db_session=db_session)

        mock_print.assert_any_call("Already logged in. Please logout first.")

# ------------------------
# RATE LIMITED
# ------------------------
def test_login_user_rate_limited(db_session):
    clear_session()

    with patch("core.cli.safe_input", return_value="alice"), \
         patch("core.cli.input", return_value="password"), \
         patch("core.authentication_service.AuthenticationService.login",
               side_effect=AuthenticationRequiredError("blocked")), \
         patch("core.cli.safe_print") as mock_print:

        login_user(db_session=db_session)

        mock_print.assert_any_call("Login blocked or rate-limited: blocked")

# ------------------------
# INVALID AMOUNT
# ------------------------
def test_create_reminder_invalid_amount(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.cli.safe_input", side_effect=["Text", "notnumber"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Expiration amount must be a number.")

# ------------------------
# REMINDER NOT FOUND
# ------------------------
def test_delete_reminder_not_found(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh123")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.reminder_services.ReminderService.delete_reminder", return_value=False), \
         patch("core.cli.safe_input", return_value="1"), \
         patch("core.cli.safe_print") as mock_print:

        delete_reminder(db_session=db_session)

        mock_print.assert_any_call("Reminder not found.")


# ------------------------
# NOT LOGGED IN
# ------------------------
def test_logout_not_logged_in(db_session):
    clear_session()

    with patch("core.cli.safe_print") as mock_print:
        logout(db_session=db_session)

        mock_print.assert_any_call("You are not logged in.")

# ------------------------
# EXIT
# ------------------------
def test_exit_app():
    from core.cli import exit_app
    with pytest.raises(SystemExit):
        exit_app()

# =========================================================
# REGISTER USER — ERROR PATHS
# =========================================================

def test_register_user_invalid_password(db_session):
    with patch("core.cli.safe_input", side_effect=["alice", "weak"]), \
         patch("core.registration.RegistrationService.register",
               side_effect=InvalidPasswordError("weak")), \
         patch("core.cli.safe_print") as mock_print:

        register_user(db_session=db_session)

        mock_print.assert_any_call("Registration failed: weak")


def test_register_user_unexpected_exception(db_session):
    with patch("core.cli.safe_input", side_effect=["alice", "Password123!"]), \
         patch("core.registration.RegistrationService.register",
               side_effect=Exception("DB down")), \
         patch("core.cli.safe_print") as mock_print:

        register_user(db_session=db_session)

        mock_print.assert_any_call(
            "Registration failed: An unexpected error occurred: DB down"
        )


# =========================================================
# LOGIN — GENERIC FAILURE
# =========================================================

def test_login_user_generic_exception(db_session):
    clear_session()

    with patch("builtins.input", side_effect=["alice", "Password123!"]), \
        patch("core.authentication_service.AuthenticationService.login",
           side_effect=Exception("invalid credentials")), \
        patch("core.cli.safe_print") as mock_print:
    
        login_user(db_session=db_session)

        mock_print.assert_any_call("Login failed: invalid credentials")


# =========================================================
# CREATE REMINDER — BUSINESS RULE FAILURES
# =========================================================

def test_create_reminder_text_too_long(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.reminder_services.ReminderService.create_reminder",
               side_effect=ReminderTextTooLongError(length=50, max_length=10)), \
         patch("core.cli.safe_input",
               side_effect=["very long reminder text", "5", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Reminder text too long (max 10 chars).")


def test_create_reminder_max_limit(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.reminder_services.ReminderService.create_reminder",
               side_effect=MaxRemindersReachedError(max_reminders_per_user=3)), \
         patch("core.cli.safe_input",
               side_effect=["text", "5", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call(
            "You have reached the maximum of 3 reminders."
        )


def test_create_reminder_invalid_expiration(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.reminder_services.ReminderService.create_reminder",
               side_effect=InvalidExpirationError(minutes=0, log_message="bad unit")), \
         patch("core.cli.safe_input",
               side_effect=["text", "5", "centuries"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Invalid expiration: bad unit")


# =========================================================
# DELETE REMINDER — PERMISSION ERROR
# =========================================================

def test_delete_reminder_permission_denied(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.reminder_services.ReminderService.delete_reminder",
               side_effect=PermissionDeniedError(role="user", action="delete")), \
         patch("core.cli.safe_input", return_value="1"), \
         patch("core.cli.safe_print") as mock_print:

        delete_reminder(db_session=db_session)

        mock_print.assert_any_call(
            "Permission denied for deleting reminders."
        )


# =========================================================
# LIST REMINDERS — PERMISSION ERROR
# =========================================================

def test_list_reminders_permission_denied(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token", return_value={"sub": str(sample_user.id)}), \
         patch("core.cli.UserService.get_user_by_id", return_value=sample_user), \
         patch("core.reminder_services.ReminderService.list_reminders",
               side_effect=PermissionDeniedError(role="user", action="list")), \
         patch("core.cli.safe_print") as mock_print:

        list_reminders(db_session=db_session)

        mock_print.assert_any_call(
            "Permission denied for listing reminders."
        )


# =========================================================
# REQUIRE_LOGIN — SESSION CLEANUP VALIDATION
# =========================================================

def test_invalid_token_clears_session(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token", side_effect=Exception()), \
         patch("core.cli.safe_print"):

        create_reminder(db_session=db_session)

        assert current_user is None
        assert current_token is None


def test_expired_token_clears_session(db_session, sample_user):
    set_current_session(sample_user, "token123", "refresh")

    with patch("core.cli.decode_token",
               side_effect=AuthenticationRequiredError()), \
         patch("core.cli.safe_print"):

        create_reminder(db_session=db_session)

        assert current_user is None
        assert current_token is None


# =========================================================
# REQUIRE_LOGIN CONTRACT
# =========================================================

def test_require_login_without_db_session_raises():
    
    with pytest.raises(RuntimeError):
        create_reminder()