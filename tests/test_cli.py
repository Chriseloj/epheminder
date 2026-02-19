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

    wrapped = require_login(dummy)  # envuelve dummy con el decorador
    wrapped()  # llama a la función decorada

    assert not called

# ------------------------------
# Test create_reminder
# ------------------------------
@patch('core.cli.decode_token', return_value={"sub": "user-id"})
@patch('core.cli.safe_input', side_effect=['Reminder text', '10', 'minutes'])
@patch('core.services.ReminderService.create_reminder')
def test_create_reminder_success(mock_create, mock_input, mock_decode):
    import core.cli as cli_module
    # Asignar sesión activa
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