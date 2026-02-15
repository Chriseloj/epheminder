import pytest
from core.authentication import authenticate
from core.exceptions import AuthenticationRequiredError
from core.models import UserDB

class DummyRepo:
    def __init__(self, users):
        self.users = users

    def get_by_username(self, username):
        return self.users.get(username)

def test_authenticate_success(monkeypatch):
    user = UserDB(
        id="1",
        username="test",
        password_hash="hashed",
        role="USER",
        is_active=True
    )
    users = {"test": user}

    # Monkeypatch with namespace used by authenticate
    monkeypatch.setattr(
        "core.authentication.UserRepository",
        lambda db: DummyRepo(users)
    )

    monkeypatch.setattr("core.authentication.verify_password", lambda pw, hash_: True)

    result = authenticate("test", "any", db_session=object())
    assert result == user

def test_authenticate_wrong_password(monkeypatch):
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
        authenticate("test", "wrong", db_session=object())