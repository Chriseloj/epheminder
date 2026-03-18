from core.user_services import UserService
from datetime import datetime, timedelta, timezone
from core.refresh import refresh
from core.models import RefreshTokenDB, UserDB
from core.security import create_refresh_token, hash_token, decode_token
import uuid
from unittest.mock import patch, MagicMock
from uuid import uuid4
from core.exceptions import AuthenticationRequiredError
import pytest

def test_refresh_token_rotation(db_session):

    db_session.query(RefreshTokenDB).delete()
    db_session.commit()

    user = UserService.create_user("testuser", "Password1234@#!", db_session=db_session)

    refresh_token = create_refresh_token(user)

    refresh_db = RefreshTokenDB(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.fromtimestamp(decode_token(refresh_token)["exp"], tz=timezone.utc),
        revoked=False
    )
    db_session.add(refresh_db)
    db_session.commit()

    tokens = refresh(refresh_token, db_session=db_session)

    assert tokens["access_token"] is not None
    assert tokens["refresh_token"] is not None
    assert tokens["refresh_token"] != refresh_token

    old_token = db_session.query(RefreshTokenDB).filter_by(token_hash=hash_token(refresh_token)).first()
    assert old_token.revoked is True

# ---------------------------
# FIXTURE
# ---------------------------
@pytest.fixture
def active_user_token(db_session):
    user = UserDB(
        id=uuid4(),
        username="alice",
        role="USER",
        is_active=True,
        password_hash="hashed"
    )
    db_session.add(user)
    db_session.flush()  # 🔹 flush, not commit

    token = RefreshTokenDB(
        id=uuid4(),
        user_id=user.id,
        token_hash="fakehash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False,
        user=user
    )
    db_session.add(token)
    db_session.flush()  # 🔹 flush, not commit

    return user, token

# ---------------------------
# TOKEN INVALID: decode failed
# ---------------------------
def test_refresh_invalid_token_decode(db_session):
    with patch("core.refresh.decode_token", side_effect=Exception("Decode error")):
        with pytest.raises(AuthenticationRequiredError):
            refresh("badtoken", db_session)

# ---------------------------
# TOKEN TIPO INCORRECT: verify_token_type failed
# ---------------------------
def test_refresh_invalid_token_type(db_session, active_user_token):
    user, token = active_user_token
    payload = {"sub": str(user.id)}
    with patch("core.refresh.decode_token", return_value=payload), \
         patch("core.refresh.verify_token_type", side_effect=Exception("Wrong type")):
        with pytest.raises(AuthenticationRequiredError):
            refresh("token", db_session)

# ---------------------------
# TOKEN NOT EXISTS ON DB
# ---------------------------
def test_refresh_token_not_in_db(db_session, active_user_token):
    user, token = active_user_token
    payload = {"sub": str(user.id)}
    with patch("core.refresh.decode_token", return_value=payload), \
         patch("core.refresh.verify_token_type"):

        # db_session.query(...).first() -> None
        with patch.object(db_session, "query", return_value=MagicMock(join=MagicMock(return_value=MagicMock(filter=MagicMock(return_value=MagicMock(first=lambda: None)))))):
            with pytest.raises(AuthenticationRequiredError):
                refresh("token", db_session)

# ---------------------------
# INACTIVE USER
# ---------------------------
def test_refresh_inactive_user(db_session, active_user_token):
    user, token = active_user_token
    user.is_active = False
    db_session.commit()
    payload = {"sub": str(user.id)}
    with patch("core.refresh.decode_token", return_value=payload), \
         patch("core.refresh.verify_token_type"), \
         patch("core.refresh.hash_token", return_value=token.token_hash):
        with pytest.raises(AuthenticationRequiredError):
            refresh("token", db_session)

# ---------------------------
# TOKEN EXPIRRED
# ---------------------------
def test_refresh_token_expired(db_session, active_user_token):
    user, token = active_user_token
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    payload = {"sub": str(user.id)}
    with patch("core.refresh.decode_token", return_value=payload), \
         patch("core.refresh.verify_token_type"), \
         patch("core.refresh.hash_token", return_value=token.token_hash):
        with pytest.raises(AuthenticationRequiredError):
            refresh("token", db_session)

# ---------------------------
# ERROR 
# ---------------------------
def test_refresh_unexpected_exception(db_session, active_user_token):
    user, token = active_user_token
    payload = {"sub": str(user.id)}
    with patch("core.refresh.decode_token", return_value=payload), \
         patch("core.refresh.verify_token_type"), \
         patch("core.refresh.hash_token", side_effect=Exception("DB failure")):
        with pytest.raises(AuthenticationRequiredError):
            refresh("token", db_session)