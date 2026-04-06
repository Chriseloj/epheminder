import pytest
from unittest.mock import MagicMock, patch

from cli.handles import  handle_login


# ------------------------
# TESTS handle_register
# ------------------------

@patch("cli.handles.register")
@patch("cli.handles.safe_input", side_effect=["user", "pass"])
@patch("cli.handles.print_section")
def test_handle_register_success(mock_section, mock_input, mock_register):
    session_service = MagicMock()
    db_session = MagicMock()

    mock_register.return_value = {
        "success": True,
        "user": MagicMock(username="user")
    }

    from cli.handles import handle_register

    result = handle_register(session_service, MagicMock(), db_session)

    assert result["success"] is True

# ------------------------
# TEST REGISTER — ERROR
# ------------------------

@patch("cli.handles.register")
@patch("cli.handles.safe_input", side_effect=["user", "pass"])
@patch("cli.handles.print_section")
def test_handle_register_failure(mock_section, mock_input, mock_register):
    session_service = MagicMock()
    db_session = MagicMock()

    mock_register.return_value = {
        "success": False,
        "error": "Invalid"
    }

    from cli.handles import handle_register

    result = handle_register(session_service, MagicMock(), db_session)

    assert result["success"] is False
    assert result["error"] == "Invalid"

# ------------------------
# TEST LOGIN — SUCCESS
# ------------------------

@patch("cli.handles.login")
@patch("cli.handles.safe_input", side_effect=["user", "pass"])
@patch("cli.handles.print_section")
def test_handle_login_success(mock_section, mock_input, mock_login):
    mock_login.return_value = {
        "success": True,
        "user": MagicMock(username="user")
    }

    session_service = MagicMock()
    db_session = MagicMock()
    authentication_service = MagicMock()
    user_service = MagicMock()

    from cli.handles import handle_login
    result = handle_login(session_service, authentication_service, user_service, db_session)

# ------------------------
# TEST CREATE REMINDER — EMPTY INPUT
# ------------------------

@patch("cli.handles.safe_input", side_effect=["", ""])
@patch("cli.handles.print_section")
def test_create_reminder_empty_text(mock_section, mock_input):
    session_service = MagicMock()
    reminder_repo = MagicMock()

    from cli.handles import handle_create_reminder

    result = handle_create_reminder(session_service, reminder_repo)

    assert result["success"] is False
    assert "cannot be empty" in result["error"]

# ------------------------
# TEST CREATE REMINDER — AMOUNT NO NUMERO
# ------------------------

@patch("cli.handles.safe_input", side_effect=["text", "abc"])
@patch("cli.handles.print_section")
def test_create_reminder_invalid_amount(mock_section, mock_input):
    session_service = MagicMock()
    reminder_repo = MagicMock()

    from cli.handles import handle_create_reminder

    result = handle_create_reminder(session_service, reminder_repo)

    assert result["success"] is False
    assert "must be a number" in result["error"]

# ------------------------
# TEST CREATE REMINDER — SUCCESS
# ------------------------

@patch("cli.handles.safe_input", side_effect=["text", "10", "m"])
@patch("cli.handles.print_section")
def test_create_reminder_success(mock_section, mock_input):
    session_service = MagicMock()
    session_service.current_user = MagicMock()

    reminder_repo = MagicMock()

    from cli.handles import handle_create_reminder

    result = handle_create_reminder(session_service, reminder_repo)

    assert "success" in result

# ------------------------
# TEST LIST REMINDERS
# ------------------------

def test_handle_list_reminders():
    session_service = MagicMock()
    session_service.current_user = MagicMock()

    reminder_repo = MagicMock()

    from cli.handles import handle_list_reminders

    result = handle_list_reminders(session_service, reminder_repo)

    assert "success" in result

# ------------------------
# TEST DELETE — CANCEL
# ------------------------

@patch("cli.handles.list_reminders")
@patch("cli.handles.safe_input", side_effect=[""])
@patch("cli.handles.safe_print")
@patch("cli.handles.print_section")
def test_delete_cancel(mock_section, mock_print, mock_input, mock_list):
    session_service = MagicMock()
    session_service.current_user = MagicMock()

    mock_list.return_value = {
        "success": True,
        "reminders": []
    }

    from cli.handles import handle_delete_reminder
    result = handle_delete_reminder(session_service, MagicMock())

    assert result == {"success": True, "data": {"cancelled": True}}


# ------------------------
# TEST DELETE — INVALID UUID 
# ------------------------

@patch("cli.handles.list_reminders")
@patch("cli.handles.safe_input", side_effect=[""])
@patch("cli.handles.safe_print")
@patch("cli.handles.print_section")
def test_delete_cancel(mock_section, mock_print, mock_input, mock_list):
    session_service = MagicMock()
    session_service.current_user = MagicMock()

    mock_list.return_value = {
        "success": True,
        "reminders": []
    }

    from cli.handles import handle_delete_reminder
    result = handle_delete_reminder(session_service, MagicMock())

    assert result == {"success": True, "data": []}