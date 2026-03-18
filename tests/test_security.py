import pytest
from core.security import Role, has_permission, authorize
from core.exceptions import PermissionDeniedError, AuthenticationRequiredError
import jwt
from datetime import datetime, timedelta, timezone

from core.middleware import revoke_access_token, is_token_revoked, get_current_user

from core.security import (
    create_access_token,
    decode_token,
    generate_jti,
)
from config import SECRET_KEY, ALGORITHM

# ---------------------------
# TEST has_permission()
# ---------------------------

@pytest.mark.parametrize("role,action,own,expected", [
    (Role.SUPERADMIN, "create", False, True),
    (Role.ADMIN, "delete", False, True),
    (Role.USER, "create", True, True),    # _own permission applies
    (Role.USER, "create", False, False),
    (Role.USER, "update", True, True),
    (Role.USER, "update", False, False),
    (Role.USER, "delete", False, False),
    (Role.USER, "delete", True, True),
    (Role.USER, "read", True, True),
    (Role.USER, "read", False, False),
    (Role.GUEST, "read", False, False),
])
def test_has_permission(role, action, own, expected):
    result = has_permission(role, action, own=own)
    assert result is expected


# ---------------------------
# TEST authorize() - success
# ---------------------------

class DummyUser:
    def __init__(self, role_enum, id_):
        self.role_enum = role_enum
        self.role = role_enum   # needed for authorize()
        self.id = id_

def test_authorize_superadmin_allows():
    user = DummyUser(Role.SUPERADMIN, "1")
    # Should not raise
    assert authorize(user, "delete") is True

def test_authorize_user_own_resource():
    user = DummyUser(Role.USER, "abc")
    # '_own' implied by resource_owner_id
    assert authorize(user, "update", resource_owner_id="abc") is True

def test_authorize_user_denied_other_resource():
    user = DummyUser(Role.USER, "abc")
    with pytest.raises(PermissionDeniedError):
        authorize(user, "update", resource_owner_id="xyz")


# ---------------------------
# TEST authorize() - AuthenticationRequiredError
# ---------------------------

def test_authorize_none_user():
    with pytest.raises(AuthenticationRequiredError):
        authorize(None, "read")

def test_authorize_invalid_user_obj():
    class BadUser:
        pass
    with pytest.raises(AuthenticationRequiredError):
        authorize(BadUser(), "read")

# ---------------------------
# TEST decode_token() - security hardening
# ---------------------------

class DummyJWTUser:
    def __init__(self, id_):
        self.id = id_
        self.role = "user"

def test_revoked_token_is_rejected(db_session): 
    user = DummyJWTUser(generate_jti())

    token = create_access_token(user)
    
    revoke_access_token(token, db_session)

    with pytest.raises(AuthenticationRequiredError):
        get_current_user(token, db_session)

def test_token_with_future_iat_is_rejected():
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)

    payload = {
        "sub": str(generate_jti()),
        "type": "access",
        "jti": generate_jti(),
        "iat": int(future_time.timestamp()),
        "exp": future_time + timedelta(minutes=5),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(AuthenticationRequiredError):
        decode_token(token)

def test_token_with_future_nbf_is_rejected():
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)

    payload = {
        "sub": str(generate_jti()),
        "type": "access",
        "jti": generate_jti(),
        "nbf": int(future_time.timestamp()),
        "exp": future_time + timedelta(minutes=5),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(AuthenticationRequiredError):
        decode_token(token)

def test_valid_token_with_iat_and_nbf():
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(generate_jti()),
        "type": "access",
        "jti": generate_jti(),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": now + timedelta(minutes=5),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    decoded = decode_token(token, expected_type="access")

    assert "sub" in decoded