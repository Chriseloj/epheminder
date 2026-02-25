import pytest
from core.registration import RegistrationService
from unittest.mock import MagicMock, patch


DECORATOR_PATCHES = [
    patch("core.decorators.check_register_rate_limit", return_value=None),
    patch("core.decorators.apply_register_backoff", return_value=None),
    patch("core.decorators.reset_register_attempts", return_value=None),
]


# -------------------------------
# Test: db_session None
# -------------------------------
def test_register_no_db_session_raises():
    with pytest.raises(ValueError, match="db_session is required"):
        RegistrationService.register(
            username="user1",
            password="ValidPass123!",
            ip="127.0.0.1",
            db_session=None
        )


# -------------------------------
# Test: password validation fails
# -------------------------------
def test_register_invalid_password_raises():
    db_mock = MagicMock()

    with DECORATOR_PATCHES[0], DECORATOR_PATCHES[1], DECORATOR_PATCHES[2], \
         patch("core.registration.validate_password") as mock_validate:

        mock_validate.side_effect = ValueError("Password too weak")

        with pytest.raises(ValueError, match="Password too weak"):
            RegistrationService.register(
                username="user2",
                password="weak",
                ip="127.0.0.1",
                db_session=db_mock
            )


# -------------------------------
# Test: UserService.create_user fails
# -------------------------------
def test_register_create_user_raises():
    db_mock = MagicMock()

    with DECORATOR_PATCHES[0], DECORATOR_PATCHES[1], DECORATOR_PATCHES[2], \
         patch("core.registration.validate_password", return_value=None), \
         patch("core.registration.UserService.create_user") as mock_create:

        mock_create.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError, match="DB error"):
            RegistrationService.register(
                username="user3",
                password="ValidPass123!",
                ip="127.0.0.1",
                db_session=db_mock
            )


# -------------------------------
# Test: logging on failed call
# -------------------------------
def test_register_logs_on_call(caplog):
    db_mock = MagicMock()

    with DECORATOR_PATCHES[0], DECORATOR_PATCHES[1], DECORATOR_PATCHES[2], \
         patch("core.registration.validate_password", return_value=None), \
         patch("core.registration.UserService.create_user", side_effect=RuntimeError):

        with pytest.raises(RuntimeError):
            RegistrationService.register(
                username="user4",
                password="ValidPass123!",
                ip="127.0.0.1",
                db_session=db_mock
            )

    assert all("Registered user" not in rec.message for rec in caplog.records)