import pytest
from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.exceptions import UsernameTakenError, InvalidUserError, MissingDataError, InvalidPasswordError
from infrastructure.storage import SessionLocal
from core.security import Role
from core.services import UserService

# ========================
# Register
# ========================

def test_register_success(db_session):
    user = RegistrationService.register(
        username="TestUser",
        password="PasswordSegura123!@#",
        ip="127.0.0.1",
        db_session=db_session
    )
    assert user.username == "testuser"  # normalize to lowercase
    assert user.id is not None
    assert user.role == Role.USER.name


def test_register_duplicate_username(db_session):
    RegistrationService.register(
        username="DuplicateUser",
        password="PasswordSegura123!@#",
        ip="127.0.0.1",
        db_session=db_session
    )
    with pytest.raises(UsernameTakenError):
        RegistrationService.register(
            username="DuplicateUser",
            password="OtraPassword123!@#",
            ip="127.0.0.1",
            db_session=db_session
        )


def test_register_invalid_password(db_session):
    with pytest.raises(InvalidPasswordError):
        RegistrationService.register(
            username="UserInvalidPassword",
            password="short",  
            ip="127.0.0.1",
            db_session=db_session
        )


# ========================
# Login
# ========================

def test_login_success(db_session):
    username = "LoginUser"
    password = "PasswordSegura123!@#"
    
    # registrer
    user_registered = RegistrationService.register(
        username=username,
        password=password,
        ip="127.0.0.1",
        db_session=db_session
    )
    
    # login
    user_logged = AuthenticationService.login(
        username=username,
        password=password,
        ip="127.0.0.1",
        db_session=db_session
    )
    
    # obtain ID to verify
    user_db = UserService.get_user_by_id(user_registered.id, db_session=db_session)

    assert user_logged.id == user_db.id

def test_login_wrong_username(db_session):
    with pytest.raises(InvalidUserError):
        AuthenticationService.login(
            username="NoExiste",
            password="Password123!@#",
            ip="127.0.0.1",
            db_session=db_session
        )

def test_login_wrong_password(db_session):
    username = "LoginFailUser"
    password = "PasswordSegura123!@#"
    
    RegistrationService.register(
        username=username,
        password=password,
        ip="127.0.0.1",
        db_session=db_session
    )

    with pytest.raises(InvalidUserError):
        AuthenticationService.login(
            username=username,
            password="WrongPassword!23",
            ip="127.0.0.1",
            db_session=db_session
        )