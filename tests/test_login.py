from core.services import UserService
from core.authentication_service import AuthenticationService
from core.models import RefreshTokenDB

def test_login_success(db_session):
    # Arrange
    password = "Password1234@#!"
    user = UserService.create_user(
        "testuser",
        password,
        db_session=db_session
    )

    # Act
    tokens = AuthenticationService.login(
        username="testuser",
        password=password,  # ← misma contraseña
        ip="127.0.0.1",
        db_session=db_session
    )

    # Assert tokens
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

    # Assert DB refresh token persisted
    stored = db_session.query(RefreshTokenDB).filter_by(user_id=user.id).first()
    assert stored is not None
    assert stored.revoked is False