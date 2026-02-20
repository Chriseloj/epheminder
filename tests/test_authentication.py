import pytest
from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.exceptions import UsernameTakenError, AuthenticationRequiredError, InvalidPasswordError
from core.security import Role
import uuid
from unittest.mock import patch, MagicMock

# ========================
# Register Tests
# ========================

def test_register_success(db_session, ip):
    username = "NewUser"
    password = "PasswordSegura123!@#"

    user_registered = RegistrationService.register(
        username=username,
        password=password,
        ip=ip,
        db_session=db_session
    )

    # ✅ ID must be uuid.UUID
    assert isinstance(user_registered.id, uuid.UUID)
    assert user_registered.username.lower() == username.lower()
    assert user_registered.role == Role.USER.name


def test_register_duplicate_username(db_session, ip):
    RegistrationService.register(
        username="DuplicateUser",
        password="PasswordSegura123!@#",
        ip=ip,
        db_session=db_session
    )

    with pytest.raises(UsernameTakenError):
        RegistrationService.register(
            username="DuplicateUser",
            password="OtraPassword123!@#",
            ip=ip,
            db_session=db_session
        )


def test_register_invalid_password(db_session, ip):
    with pytest.raises(InvalidPasswordError):
        RegistrationService.register(
            username="UserInvalidPassword",
            password="short",  # password too short
            ip=ip,
            db_session=db_session
        )


# ========================
# Login Tests
# ========================

@pytest.fixture(autouse=True)
def mock_auth_services():
    """
    auth:
    - authenticate -> return simulate usuers
    - JWT y hashing -> return strings dummy
    - rate_limited -> no-op
    """
    with patch("core.authentication.authenticate") as mock_auth, \
         patch("core.security.create_access_token", return_value="access_dummy"), \
         patch("core.security.create_refresh_token", return_value="refresh_dummy"), \
         patch("core.security.hash_token", return_value="hashed_dummy"), \
         patch("core.authentication_service.rate_limited", lambda *a, **k: (lambda f: f)):

        # User simulate for login
        mock_user = type("User", (object,), {"id": uuid.uuid4(), "username": "LoginUser"})()
        mock_auth.return_value = mock_user
        yield


def test_login_success(db_session, ip):
    username = "LoginUser"
    password = "PasswordSegura123!@#"

    # Register usuer (opcional, db_session not critic authenticate patch)
    user_registered = RegistrationService.register(
        username=username,
        password=password,
        ip=ip,
        db_session=db_session
    )

    tokens = AuthenticationService.login(
        username=username,
        password=password,
        ip=ip,
        db_session=db_session
    )

    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_login_wrong_username(db_session, ip):
    # Patch authenticate exception when usuer not exist
    with patch("core.authentication.authenticate", side_effect=AuthenticationRequiredError):
        with pytest.raises(AuthenticationRequiredError):
            AuthenticationService.login(
                username="NoExiste",
                password="Password123!@#",
                ip=ip,
                db_session=db_session
            )


def test_login_wrong_password(db_session, ip):
    username = "LoginFailUser"
    password = "PasswordSegura123!@#"

    # Register user
    RegistrationService.register(
        username=username,
        password=password,
        ip=ip,
        db_session=db_session
    )

    # Patch authenticate to simulate  incorrect password
    with patch("core.authentication.authenticate", side_effect=AuthenticationRequiredError):
        with pytest.raises(AuthenticationRequiredError):
            AuthenticationService.login(
                username=username,
                password="WrongPassword!23",
                ip=ip,
                db_session=db_session
            )