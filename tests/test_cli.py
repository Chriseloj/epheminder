import pytest
from unittest.mock import patch, MagicMock
from core.cli import (run_cli,
clear_session,
logout,
require_login,
create_reminder,
register_user,
list_reminders,
delete_reminder,
login_user,)
from core.exceptions import AuthenticationRequiredError

# ------------------------------
# Fixtures
# ------------------------------
@pytest.fixture(autouse=True)
def clear_session_before_tests():
    clear_session() 

# ------------------------------
# Helpers
# ------------------------------
def mock_user():
    user = MagicMock()
    user.id = 'user-id'
    user.username = 'testuser'
    user.role_enum.name = 'USER'
    return user

# ------------------------------
# Test register_user
# ------------------------------
@patch('core.cli.safe_input', side_effect=['testuser'])
@patch('core.cli.getpass', return_value='password')
@patch('core.registration.RegistrationService.register')
def test_register_user_success(mock_register, mock_getpass, mock_input):
    mock_register.return_value = mock_user()
    register_user()
    mock_register.assert_called_once()

# ------------------------------
# Test login_user
# ------------------------------
@patch('core.cli.safe_input', side_effect=['testuser'])
@patch('core.cli.getpass', return_value='password')
@patch('core.authentication_service.AuthenticationService.login')
@patch('core.services.UserService.get_user_by_username')
def test_login_user_success(mock_get_user, mock_login, mock_getpass, mock_input):
    import core.cli as cli_module
    user = mock_user()
    mock_user_obj = mock_user()
    mock_get_user.return_value = mock_user_obj
    mock_login.return_value = {'access_token':'token'}

    login_user()

    assert cli_module.current_user == mock_user_obj
    assert cli_module.current_token == 'token'

# ------------------------------
# Test require_login decorator
# ------------------------------
def test_require_login_blocks_without_token():
    called = False

    def dummy():
        nonlocal called
        called = True

    wrapped = require_login(dummy)  
    wrapped() 

    assert not called

# ------------------------------
# Test create_reminder
# ------------------------------
@patch('core.cli.decode_token', return_value={"sub": "user-id"})
@patch('core.cli.safe_input', side_effect=['Reminder text', '10', 'minutes'])
@patch('core.services.ReminderService.create_reminder')
def test_create_reminder_success(mock_create, mock_input, mock_decode):
    import core.cli as cli_module
    # Active session
    cli_module.current_user = mock_user()
    cli_module.current_token = 'token'

    mock_create.return_value = MagicMock(id='reminder-id')

    create_reminder()

    mock_create.assert_called_once()


# ------------------------------
# Test list_reminders
# ------------------------------
@patch('core.cli.decode_token', return_value={"sub": "user-id"})
@patch('core.cli.safe_print')
@patch('core.services.ReminderService.list_reminders')
def test_list_reminders(mock_list, mock_print, mock_decode):
    import core.cli as cli_module
    cli_module.current_user = mock_user()
    cli_module.current_token = 'token'

    mock_list.return_value = [MagicMock(id='1', text='Test', expires_at='tomorrow')]

    list_reminders()
    mock_print.assert_any_call('- ID: 1 | Text: Test | Expires: tomorrow')


# ------------------------------
# Test delete_reminder
# ------------------------------
@patch('core.cli.decode_token', return_value={"sub": "user-id"})
@patch('core.cli.safe_input', return_value='reminder-id')
@patch('core.services.ReminderService.delete_reminder')
def test_delete_reminder_success(mock_delete, mock_input, mock_decode):
    import core.cli as cli_module
    cli_module.current_user = mock_user()
    cli_module.current_token = 'token'

    mock_delete.return_value = True

    delete_reminder()
    mock_delete.assert_called_once()

# ------------------------------
# Test logout
# ------------------------------
def test_logout_clears_session():
    import core.cli as cli_module
    user = mock_user()
    cli_module.current_user = user
    cli_module.current_token = 'token'

    cli_module.logout()

    assert cli_module.current_user is None
    assert cli_module.current_token is None

# ------------------------------
# Test invalid token
# ------------------------------
@patch("core.cli.decode_token", side_effect=Exception("invalid"))
def test_require_login_invalid_token(mock_decode, capsys):
    import core.cli as cli

    cli.current_token = "bad-token"

    @cli.require_login
    def dummy():
        pass

    dummy()

    captured = capsys.readouterr()
    assert "Invalid session" in captured.out
    assert cli.current_token is None

# ------------------------------
# Test expired token
# ------------------------------
@patch("core.cli.decode_token", side_effect=AuthenticationRequiredError())
def test_require_login_expired_token(mock_decode, capsys):
    import core.cli as cli

    cli.current_token = "expired"

    @cli.require_login
    def dummy():
        pass

    dummy()

    captured = capsys.readouterr()
    assert "Session expired" in captured.out

# ------------------------------
# Test already logged
# ------------------------------

def test_login_user_already_logged(capsys):
    import core.cli as cli

    cli.current_token = "token"

    login_user()

    captured = capsys.readouterr()
    assert "Already logged in" in captured.out

# ------------------------------
# Test invalid expiration
# ------------------------------

@patch("core.cli.decode_token", return_value={"sub": "user-id"})
@patch("core.cli.safe_input", side_effect=["text", "abc"])
def test_create_reminder_invalid_number(mock_input, mock_decode, capsys):
    import core.cli as cli

    cli.current_user = mock_user()
    cli.current_token = "token"

    create_reminder()

    captured = capsys.readouterr()
    assert "Expiration amount must be a number." in captured.out

# ------------------------------
# Test list empty
# ------------------------------

@patch("core.cli.decode_token", return_value={"sub": "user-id"})
@patch("core.services.ReminderService.list_reminders", return_value=[])
def test_list_reminders_empty(mock_list, mock_decode, capsys):
    import core.cli as cli

    cli.current_user = mock_user()
    cli.current_token = "token"

    list_reminders()

    captured = capsys.readouterr()
    assert "No active reminders." in captured.out

# ------------------------------
# Test reminder not found
# ------------------------------

@patch("core.cli.decode_token", return_value={"sub": "user-id"})
@patch("core.cli.safe_input", return_value="123")
@patch("core.services.ReminderService.delete_reminder", return_value=False)
def test_delete_reminder_not_found(mock_delete, mock_input, mock_decode, capsys):
    import core.cli as cli
    
    cli.current_user = mock_user()
    cli.current_token = "token"

    delete_reminder()

    captured = capsys.readouterr()
    assert "Reminder not found." in captured.out

# ------------------------------
# Test without login
# ------------------------------

def test_logout_without_login(capsys):
    import core.cli as cli
    
    cli.current_token = None

    logout()

    captured = capsys.readouterr()
    assert "You are not logged in." in captured.out

# ------------------------------
# Test invalid option
# ------------------------------

@patch("core.cli.safe_input", side_effect=["999", "0"])
@patch("core.cli.exit_app", side_effect=SystemExit)
def test_run_cli_invalid_option(mock_exit, mock_input, capsys):
    try:
        run_cli()
    except SystemExit:
        pass

    captured = capsys.readouterr()
    assert "Invalid choice." in captured.out