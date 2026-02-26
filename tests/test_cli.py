import pytest
from core.cli import (
    register_user, login_user, create_reminder, list_reminders,
    delete_reminder, logout, exit_app)
from core.cli_utils import log_event
from core.hash_utils import hash_sensitive
from core.session import session_manager
from core.exceptions import AuthenticationRequiredError
from core.decorators import require_login
from core.registration import RegistrationService
from unittest.mock import patch
from core.exceptions import (
    InvalidPasswordError,
    ReminderTextTooLongError,
    MaxRemindersReachedError,
    InvalidExpirationError,
    PermissionDeniedError,
    AuthenticationRequiredError,
    CLIExit
)
from config import MAX_TEXT_LENGTH


# ------------------------
# REGISTER USER
# ------------------------
def test_register_user(db_session, sample_user):
    with patch("core.cli.safe_input", side_effect=["newuser", "Password_0ne_hash"]), \
         patch("core.cli.safe_print") as mock_print:

        register_user(db_session=db_session)

        mock_print.assert_any_call("User 'newuser' registered successfully!")

# ------------------------
# LOGIN USER
# ------------------------
def test_create_reminder_without_login(db_session):
    session_manager.clear()

    # Decorator
    wrapped = require_login()(create_reminder)

    with patch("core.decorators.safe_print") as mock_print:
        wrapped(db_session=db_session)

    mock_print.assert_any_call("Please login first.")

# ------------------------
# LOGOUT
# ------------------------
def test_logout_resets_session(db_session, sample_user):

    session_manager.set(sample_user, "access_token", "refresh_token")
    with patch("core.cli.safe_print") as mock_print:
        logout(db_session=db_session)


        assert session_manager.current_user is None
        assert session_manager.access_token is None
        assert session_manager.refresh_token is None
        mock_print.assert_any_call("Logged out successfully.")
    

# ------------------------
# CREATE REMINDER
# ------------------------
def test_create_reminder_success(db_session, sample_user):

    session_manager.set(sample_user, "access_token", "refresh_token")
    with patch("core.cli.safe_input", side_effect=["Recordatorio test", "15", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:
        
        create_reminder(db_session=db_session)

        calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("Reminder created. ID:" in c for c in calls)


# ------------------------
# LIST REMINDERS
# ------------------------
def test_list_reminders_empty(db_session, sample_user):

    session_manager.set(sample_user, "access_token", "refresh_token")
    with patch("core.cli.safe_print") as mock_print:
        list_reminders(db_session=db_session)

        mock_print.assert_any_call("No active reminders.")


# ------------------------
# DELETE REMINDER
# ------------------------
def test_delete_reminder_success(db_session, sample_user, sample_reminder):

    session_manager.set(sample_user, "access_token", "refresh_token")
    with patch("core.cli.safe_input", side_effect=[str(sample_reminder.id)]), \
         patch("core.cli.safe_print") as mock_print:
        
        delete_reminder(db_session=db_session)

        mock_print.assert_any_call("Reminder deleted successfully.")


# ------------------------
# EXPIRED TOKEN
# ------------------------
def test_create_reminder_expired_token(db_session, sample_user):
    session_manager.set(sample_user, "expired_access_token", "refresh_token")

    # Decorator
    create_reminder_wrapped = require_login(session_manager)(create_reminder)

    # decode_token for AuthenticationRequiredError
    with patch("core.security.decode_token", side_effect=AuthenticationRequiredError), \
         patch("core.decorators.safe_print") as mock_print:

        create_reminder_wrapped(**{"db_session": db_session})

        mock_print.assert_any_call("Please login again.")
        # Verify clean session
        assert session_manager.current_user is None
        assert session_manager.access_token is None
        assert session_manager.refresh_token is None


# ------------------------
# INVALID TOKEN
# ------------------------
def test_create_reminder_invalid_token(db_session, sample_user):
    session_manager.set(sample_user, "invalid_token", "refresh_token")
    create_reminder_wrapped = require_login(session_manager)(create_reminder)

    # Patch decode_token to error 
    with patch("core.security.decode_token", side_effect=Exception), \
         patch("core.decorators.safe_print") as mock_print:

        create_reminder_wrapped(**{"db_session": db_session})

        mock_print.assert_any_call("Please login again.")
        # Session must clean
        assert session_manager.current_user is None
        assert session_manager.access_token is None
        assert session_manager.refresh_token is None


# ------------------------
# ALREADY LOGGED IN
# ------------------------
def test_login_user_already_logged_in(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_input", side_effect=["user", "pass"]), \
         patch("core.cli.safe_print") as mock_print:
        
        login_user(db_session=db_session)

        mock_print.assert_any_call("Already logged in. Please logout first.")
    
# ------------------------
# RATE LIMITED
# ------------------------
def test_login_user_rate_limited(db_session, sample_user):
    session_manager.clear()

    with patch("core.cli.safe_input", side_effect=["user", "pass"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch("core.authentication_service.AuthenticationService.login",
               side_effect=AuthenticationRequiredError("Too many attempts")):

        login_user(db_session=db_session)

        mock_print.assert_any_call("Login blocked or rate-limited: Too many attempts")


# ------------------------
# INVALID AMOUNT
# ------------------------
def test_create_reminder_invalid_amount(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_input", side_effect=["Reminder test", "not_a_number", "minutes"]), \
         patch("core.cli.safe_print") as mock_print:

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Expiration amount must be a number.")
    

# ------------------------
# REMINDER NOT FOUND
# ------------------------
def test_delete_reminder_not_found(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    fake_id = 9999

    with patch("core.cli.safe_input", side_effect=[str(fake_id)]), \
         patch("core.cli.safe_print") as mock_print:

        delete_reminder(db_session=db_session)

        mock_print.assert_any_call("Failed to delete reminder. Please try again later.")

# ------------------------
# NOT LOGGED IN
# ------------------------
def test_logout_not_logged_in(db_session):
    session_manager.clear()  

    with patch("core.cli.safe_print") as mock_print:
        logout(db_session=db_session)

        mock_print.assert_any_call("You are not logged in.")
   
# ------------------------
# EXIT
# ------------------------
def test_exit_app():
    with pytest.raises(CLIExit):
        exit_app()
   

# =========================================================
# REGISTER USER — ERROR PATHS
# =========================================================

def test_register_user_invalid_password(db_session):
    session_manager.clear()

    with patch("core.cli.safe_input", side_effect=["newuser", "weakpass"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch.object(RegistrationService, "register", side_effect=InvalidPasswordError("Password too weak")):

        register_user(db_session=db_session)

        mock_print.assert_any_call("Registration failed: Password too weak")


def test_register_user_unexpected_exception(db_session):
    session_manager.clear()

    with patch("core.cli.safe_input", side_effect=["newuser", "ValidPass123"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch.object(RegistrationService, "register", side_effect=Exception("DB down")):

        register_user(db_session=db_session)

        mock_print.assert_any_call("Registration failed: An unexpected error occurred: DB down")
    

# =========================================================
# LOGIN — GENERIC FAILURE
# =========================================================

def test_login_user_generic_exception(db_session):
    session_manager.clear()

    with patch("core.cli.safe_input", side_effect=["user", "pass"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch("core.authentication_service.AuthenticationService.login", side_effect=Exception("Unknown error")):

        login_user(db_session=db_session)

        mock_print.assert_any_call("Login failed: Unknown error")
    

# =========================================================
# CREATE REMINDER — BUSINESS RULE FAILURES
# =========================================================

def test_create_reminder_text_too_long(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_input", side_effect=["x"*(MAX_TEXT_LENGTH+1), "10", "minutes"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch("core.reminder_services.ReminderService.create_reminder", 
               side_effect=ReminderTextTooLongError(length=MAX_TEXT_LENGTH+1)):

        create_reminder(db_session=db_session)

        
        mock_print.assert_any_call(f"Reminder text too long (max {MAX_TEXT_LENGTH} chars).")


def test_create_reminder_max_limit(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_input", side_effect=["Reminder test", "10", "minutes"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch("core.reminder_services.ReminderService.create_reminder",
               side_effect=MaxRemindersReachedError(max_reminders_per_user=5)):

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("You have reached the maximum of 5 reminders.")
  
def test_create_reminder_invalid_expiration(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_input", side_effect=["Reminder test", "10", "centuries"]), \
         patch("core.cli.safe_print") as mock_print, \
         patch("core.reminder_services.ReminderService.create_reminder", side_effect=InvalidExpirationError("Invalid unit")):

        create_reminder(db_session=db_session)

        mock_print.assert_any_call("Invalid expiration: Invalid expiration time: Invalid unit minutes. Allowed: 1-10080 minutes")
   

# =========================================================
# DELETE REMINDER — PERMISSION ERROR
# =========================================================

def test_delete_reminder_permission_denied(db_session, sample_user, sample_reminder):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_input", side_effect=[str(sample_reminder.id)]), \
         patch("core.cli.safe_print") as mock_print, \
         patch("core.reminder_services.ReminderService.delete_reminder", side_effect=PermissionDeniedError):

        delete_reminder(db_session=db_session)

        mock_print.assert_any_call("Failed to delete reminder. Please try again later.")
   

# =========================================================
# LIST REMINDERS — PERMISSION ERROR
# =========================================================

def test_list_reminders_permission_denied(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    with patch("core.cli.safe_print") as mock_print, \
         patch("core.reminder_services.ReminderService.list_reminders", side_effect=PermissionDeniedError):

        list_reminders(db_session=db_session)

        mock_print.assert_any_call("Failed to list reminder. Please check your input or try again later.")
    

# =========================================================
# REQUIRE_LOGIN — SESSION CLEANUP VALIDATION
# =========================================================

def test_invalid_token_clears_session(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    def fake_decode(token):
        raise AuthenticationRequiredError()

    @require_login
    def protected_func(db_session):
        return True

    with patch("core.decorators.decode_token", side_effect=fake_decode), \
         patch("core.decorators.safe_print") as mock_print:

        protected_func(db_session=db_session)

        assert session_manager.current_user is None
        assert session_manager.access_token is None
        assert session_manager.refresh_token is None
        mock_print.assert_any_call("Please login again.")
    


def test_expired_token_clears_session(db_session, sample_user):
    session_manager.set(sample_user, "access_token", "refresh_token")

    def fake_decode(token):
        raise Exception("Token expired")

    @require_login
    def protected_func(db_session):
        return True

    with patch("core.decorators.decode_token", side_effect=fake_decode), \
         patch("core.decorators.safe_print") as mock_print:

        protected_func(db_session=db_session)

        assert session_manager.current_user is None
        assert session_manager.access_token is None
        assert session_manager.refresh_token is None
        mock_print.assert_any_call("Invalid. Please login again.")
    

# =========================================================
# REQUIRE_LOGIN CONTRACT
# =========================================================

@require_login
def dummy_func(db_session=None):
    return True

def test_require_login_without_db_session_raises():
    with pytest.raises(RuntimeError, match="db_session must be passed to CLI functions"):
        dummy_func()

# ------------------------
# LOG EVENT
# ------------------------

def test_log_event_info_with_user_and_ip():
    user_id = "user123"
    ip = "127.0.0.1"
    
    with patch("core.cli_utils.logger.info") as mock_logger:
        log_event(level="info", action="login", user_id=user_id, ip=ip, extra_info="extra")
    
    logged_msg = mock_logger.call_args[0][0]
    assert "action=login" in logged_msg
    assert f"user_hash={hash_sensitive(user_id)}" in logged_msg
    assert f"ip_hash={hash_sensitive(ip)}" in logged_msg
    assert "info=extra" in logged_msg
    assert "ts=" in logged_msg

def test_log_event_warning_without_user_or_ip():
    with patch("core.cli_utils.logger.warning") as mock_logger:
        log_event(level="warning", action="delete_failed")
    
    logged_msg = mock_logger.call_args[0][0]
    assert "action=delete_failed" in logged_msg
    assert "user_hash=" not in logged_msg
    assert "ip_hash=" not in logged_msg
    assert "ts=" in logged_msg

def test_log_event_error_with_partial_info():
    user_id = "user123"
    with patch("core.cli_utils.logger.error") as mock_logger:
        log_event(level="error", action="create_failed", user_id=user_id)
    
    logged_msg = mock_logger.call_args[0][0]
    assert "action=create_failed" in logged_msg
    assert f"user_hash={hash_sensitive(user_id)}" in logged_msg
    assert "ip_hash=" not in logged_msg
    assert "ts=" in logged_msg

def test_log_event_debug_level():
    with patch("core.cli_utils.logger.debug") as mock_logger:
        log_event(level="debug", action="debug_test")
    
    logged_msg = mock_logger.call_args[0][0]
    assert "action=debug_test" in logged_msg
    assert "ts=" in logged_msg