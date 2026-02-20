import pytest
from core.authentication import authenticate
from core.exceptions import AuthenticationRequiredError
from core.models import UserDB

# ----------------------------
# Dummy repository tests
# ----------------------------
class DummyRepo:
    def __init__(self, users):
        self.users = users

    def get_by_username(self, username):
        return self.users.get(username)

# ----------------------------
# Test authentication successful
# ----------------------------
def test_authenticate_success(monkeypatch, ip):
    user = UserDB(
        id="1",
        username="test",
        password_hash="hashed",
        role="USER",
        is_active=True
    )
    users = {"test": user}

    # Patch repository and verify password
    monkeypatch.setattr(
        "core.authentication.UserRepository",
        lambda db: DummyRepo(users)
    )
    monkeypatch.setattr("core.authentication.verify_password", lambda pw, hash_: True)

    # Called function
    result = authenticate("test", "any", db_session=object(), ip=ip)

    # Verify result is the same objet of user
    assert isinstance(result, UserDB)
    assert result.id == user.id
    assert result.username == "test"


# ----------------------------
# Test wrong password
# ----------------------------
def test_authenticate_wrong_password(monkeypatch, ip):
    user = UserDB(
        id="1",
        username="test",
        password_hash="hashed",
        role="USER",
        is_active=True
    )
    users = {"test": user}

    monkeypatch.setattr(
        "core.authentication.UserRepository",
        lambda db: DummyRepo(users)
    )
    monkeypatch.setattr("core.authentication.verify_password", lambda pw, hash_: False)

    with pytest.raises(AuthenticationRequiredError):
        authenticate("test", "wrong", db_session=object(), ip=ip)