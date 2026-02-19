import pytest
from core.authentication import authenticate
from core.exceptions import AuthenticationRequiredError
from core.models import UserDB

# ----------------------------
# Dummy repository para tests
# ----------------------------
class DummyRepo:
    def __init__(self, users):
        self.users = users

    def get_by_username(self, username):
        return self.users.get(username)

# ----------------------------
# Test de autenticación exitosa
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

    # Patch de repositorio y verificación de password
    monkeypatch.setattr(
        "core.authentication.UserRepository",
        lambda db: DummyRepo(users)
    )
    monkeypatch.setattr("core.authentication.verify_password", lambda pw, hash_: True)

    # Llamada a la función
    result = authenticate("test", "any", db_session=object(), ip=ip)

    # Verificamos que el resultado es el mismo objeto de usuario
    assert isinstance(result, UserDB)
    assert result.id == user.id
    assert result.username == "test"


# ----------------------------
# Test de contraseña incorrecta
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