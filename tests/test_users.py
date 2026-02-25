import pytest
from core.user_services import UserService
from core.security import Role
from core.exceptions import InvalidUserError, UsernameTakenError, MissingDataError

# ---------------------------
# Test create_user success
# ---------------------------

@pytest.mark.parametrize("username,password", [
    ("validuser1", "Password123!@#01"),
    ("UserTwo", "Password123!@#02"),
])
def test_create_user_success(db_session, username, password):
    user = UserService.create_user(
        username=username,
        password=password,
        db_session=db_session,
    )
    assert user.id is not None
    assert user.username == username.strip().lower()
    assert user.role_enum == Role.USER
    assert user.is_active is True

# ---------------------------
# Test invalid usernames
# ---------------------------

def test_create_user_invalid_username_too_short(db_session):
    with pytest.raises(InvalidUserError):
        UserService.create_user(
            username="ab",
            password="Password123!@#01",
            db_session=db_session,
        )

def test_create_user_invalid_username_non_alnum(db_session):
    with pytest.raises(InvalidUserError):
        UserService.create_user(
            username="user!!",
            password="Password123!@#01",
            db_session=db_session,
        )

# ---------------------------
# Test username already taken
# ---------------------------

def test_create_user_username_taken(db_session):
    username = "duplicateuser"
    password = "Password123!@#01"
    
    # Create user
    UserService.create_user(
        username=username,
        password=password,
        db_session=db_session,
    )

    # Attempt must failed
    with pytest.raises(UsernameTakenError):
        UserService.create_user(
            username=username,
            password=password,
            db_session=db_session,
        )

# ---------------------------
# Test missing db_session
# ---------------------------

def test_create_user_missing_db_session():
    with pytest.raises(MissingDataError):
        UserService.create_user(
            username="user",
            password="Password123!@#01",
            db_session=None,
        )

# ---------------------------
# Test get_user_by_id success
# ---------------------------

def test_get_user_by_id_success(db_session):
    user = UserService.create_user(
        username="findme",
        password="Password123!@#01",
        db_session=db_session,
    )

    found = UserService.get_user_by_id(user.id, db_session=db_session)
    assert found is not None
    assert found.username == user.username
    assert found.id == user.id

# ---------------------------
# Test get_user_by_id missing db_session
# ---------------------------

def test_get_user_by_id_missing_db_session():
    with pytest.raises(MissingDataError):
        UserService.get_user_by_id("any-id", db_session=None)

# ---------------------------
# Test get_user_by_id not found
# ---------------------------

def test_get_user_by_id_not_found(db_session):
    user = UserService.get_user_by_id("non-existent-id", db_session=db_session)
    assert user is None