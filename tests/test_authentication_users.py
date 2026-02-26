import pytest
from unittest.mock import patch
from uuid import UUID
from core.hash_utils import hash_sensitive
from core.exceptions import AuthenticationRequiredError

# ------------------------
# PATCH RATE_LIMITED
# ------------------------
with patch("core.decorators.rate_limited", lambda *a, **k: lambda f: f):
    from core.authentication_service import AuthenticationService

from core.exceptions import AuthenticationRequiredError, MissingDataError
from core.models import RefreshTokenDB

# ------------------------
# LOGIN SUCCESSFUL
# ------------------------
def test_login_success(db_session, sample_user):
    with patch("core.authentication_service.authenticate") as mock_auth, \
         patch("core.authentication_service.create_access_token") as mock_access_token:

        mock_auth.return_value = sample_user
        mock_access_token.return_value = "access123"

        result = AuthenticationService.login(
            username="alice",
            password="secret",
            ip="127.0.0.1",
            db_session=db_session
        )

        assert result["access_token"] == "access123"
        assert result["token_type"] == "bearer"
        assert "refresh_token" in result

        token_in_db = db_session.query(RefreshTokenDB).filter_by(user_id=sample_user.id).first()
        assert token_in_db is not None
        assert isinstance(token_in_db.id, UUID)
        assert token_in_db.revoked is False

# ------------------------
# LOGIN WITHOUT DB SESSION
# ------------------------
def test_login_missing_db_session():
    with pytest.raises(MissingDataError):
        AuthenticationService.login(
            username="alice",
            password="secret",
            ip="127.0.0.1",
            db_session=None
        )

# ------------------------
# LOGIN INVALID CREDENTIALS
# ------------------------
def test_login_invalid_credentials(db_session):
    with patch("core.authentication_service.authenticate") as mock_auth:
        mock_auth.side_effect = AuthenticationRequiredError("Invalid credentials")

        with pytest.raises(AuthenticationRequiredError):
            AuthenticationService.login(
                username="alice",
                password="wrong",
                ip="127.0.0.1",
                db_session=db_session
            )

# ------------------------
# HASH REFRESH TOKEN
# ------------------------
def test_refresh_token_hash_stored_correctly(db_session, sample_user):
    """
    Verifica que el refresh token se guarde correctamente en la DB
    con hash consistente usando hash_sensitive().
    """

    # Mock authenticate and create_access_token 
    with patch("core.authentication_service.authenticate") as mock_auth, \
         patch("core.authentication_service.create_access_token") as mock_access_token:

        mock_auth.return_value = sample_user
        mock_access_token.return_value = "access123"

        # login
        result = AuthenticationService.login(
            username="alice",
            password="secret",
            ip="127.0.0.1",
            db_session=db_session
        )

        # Obtain real value from refresh token
        refresh_token_value = result["refresh_token"]

        # Obtain token save on DB
        token_in_db = db_session.query(RefreshTokenDB).filter_by(user_id=sample_user.id).first()

        # Calculate hash using same function app
        expected_hash = hash_sensitive(refresh_token_value)

        # ✅ Assert final
        assert token_in_db.token_hash == expected_hash
        assert isinstance(token_in_db.id, UUID)
        assert token_in_db.revoked is False