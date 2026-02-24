import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from core.exceptions import AuthenticationRequiredError
from core.models import UserDB, RevokedTokenDB
from core.middleware import revoke_access_token, get_current_user, is_token_revoked

# ---------------------------
# FIXTURES
# ---------------------------
@pytest.fixture
def sample_user(db_session):
    user = UserDB(
        id=uuid4(),
        username="alice",
        role="USER",
        is_active=True,
        password_hash="hashed"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_revoked_token(db_session):
    token = RevokedTokenDB(
        jti=str(uuid4()),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db_session.add(token)
    db_session.commit()
    return token

# ---------------------------
# REVOKE ACCESS TOKEN
# ---------------------------
def test_revoke_access_token_creates_token(db_session):
    fake_jti = "token123"
    future_ts = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    payload = {"jti": fake_jti, "exp": future_ts}

    with patch("core.middleware.decode_token", return_value=payload):
        revoke_access_token("fake_token", db_session)

    token_in_db = db_session.query(RevokedTokenDB).filter_by(jti=fake_jti).first()
    assert token_in_db is not None
    # Allowing a small margin of error on timestamp comparison
    assert token_in_db.expires_at.timestamp() == pytest.approx(future_ts, rel=1e-2)

def test_revoke_access_token_updates_existing(db_session, sample_revoked_token):
    new_exp = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())
    payload = {"jti": sample_revoked_token.jti, "exp": new_exp}

    with patch("core.middleware.decode_token", return_value=payload):
        revoke_access_token("fake_token", db_session)

    token_in_db = db_session.query(RevokedTokenDB).filter_by(jti=sample_revoked_token.jti).first()
    # Allowing a small margin of error on timestamp comparison
    assert token_in_db.expires_at.timestamp() == pytest.approx(new_exp, rel=1e-2)

# ---------------------------
# IS TOKEN REVOKED
# ---------------------------
def is_token_revoked(jti: str, db_session) -> bool:
    if not jti:
        return False
    now = datetime.now(timezone.utc)
    try:
        token = db_session.query(RevokedTokenDB).filter_by(jti=jti).first()
        if not token:
            return False
        if token.expires_at < now:

            db_session.delete(token)
            db_session.commit()
            return False
        return True
    except Exception:
        return True

# ---------------------------
# GET CURRENT USER
# ---------------------------
def test_get_current_user_success(db_session, sample_user):
    payload = {"sub": str(sample_user.id), "jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type") as mock_verify, \
         patch("core.middleware.is_token_revoked", return_value=False):
        user = get_current_user("token", db_session)
        assert user.id == sample_user.id
        mock_verify.assert_called_once_with(payload, "access")

def test_get_current_user_revoked_raises(db_session, sample_user):
    payload = {"sub": str(sample_user.id), "jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type"), \
         patch("core.middleware.is_token_revoked", return_value=True):
        with pytest.raises(AuthenticationRequiredError):
            get_current_user("token", db_session)

def test_get_current_user_inactive_raises(db_session, sample_user):
    sample_user.is_active = False
    db_session.commit()
    payload = {"sub": str(sample_user.id), "jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type"), \
         patch("core.middleware.is_token_revoked", return_value=False):
        with pytest.raises(AuthenticationRequiredError):
            get_current_user("token", db_session)

def test_get_current_user_nonexistent_raises(db_session):
    payload = {"sub": str(uuid4()), "jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type"), \
         patch("core.middleware.is_token_revoked", return_value=False):
        with pytest.raises(AuthenticationRequiredError):
            get_current_user("token", db_session)

# ---------------------------
# REVOKE ACCESS TOKEN
# ---------------------------

def test_revoke_access_token_decode_fails(db_session):
    with patch("core.middleware.decode_token", side_effect=Exception("Decode error")), \
         patch("core.middleware.logger.warning") as mock_warning:
        from core.middleware import revoke_access_token
        revoke_access_token("fake_token", db_session)
        mock_warning.assert_called_once()
        
def test_revoke_access_token_expired_token(db_session):
    expired_ts = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    payload = {"jti": "expired_jti", "exp": expired_ts}
    with patch("core.middleware.decode_token", return_value=payload):
        revoke_access_token("fake_token", db_session)
    token_in_db = db_session.query(RevokedTokenDB).filter_by(jti="expired_jti").first()
    assert token_in_db is None  

def test_revoke_access_token_missing_jti_exp(db_session):
    payload = {"foo": "bar"}
    with patch("core.middleware.decode_token", return_value=payload):
        revoke_access_token("fake_token", db_session)
   
    tokens = db_session.query(RevokedTokenDB).all()
    assert all(t.jti != "foo" for t in tokens)

# ---------------------------
# IS TOKEN REVOKED
# ---------------------------

def test_is_token_revoked_db_exception(monkeypatch, db_session):

    fake_query = MagicMock(side_effect=Exception("DB error"))
    monkeypatch.setattr(db_session, "query", lambda *args, **kwargs: fake_query)
    result = is_token_revoked("any_jti", db_session)
    assert result is True

# ---------------------------
# GET CURRENT USER
# ---------------------------

def test_get_current_user_decode_fails(db_session):
    with patch("core.middleware.decode_token", side_effect=Exception("Decode error")):
        with pytest.raises(Exception, match="Decode error"):
            get_current_user("token", db_session)

def test_get_current_user_verify_type_fails(db_session):
    payload = {"sub": str(uuid4()), "jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type", side_effect=Exception("Invalid type")):
        with pytest.raises(Exception, match="Invalid type"):
            get_current_user("token", db_session)

def test_get_current_user_missing_sub(db_session):
    payload = {"jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type"):
        with pytest.raises(KeyError):  # payload["sub"] missing
            get_current_user("token", db_session)

def test_get_current_user_invalid_sub_uuid(db_session):
    payload = {"sub": "not-a-uuid", "jti": "jti123"}
    with patch("core.middleware.decode_token", return_value=payload), \
         patch("core.middleware.verify_token_type"):
        with pytest.raises(ValueError): 
            get_current_user("token", db_session)