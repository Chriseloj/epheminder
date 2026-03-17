from enum import Enum, auto
from core.exceptions import PermissionDeniedError, AuthenticationRequiredError
from core.hash_utils import hash_sensitive
import jwt
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
import logging
import hmac
from config import (SECRET_KEY,
ALGORITHM,
ACCESS_TOKEN_EXPIRE_MINUTES,
REFRESH_TOKEN_EXPIRE_DAYS)

logger = logging.getLogger(__name__)

class Role(Enum):
    SUPERADMIN = auto()
    ADMIN = auto()
    USER = auto()
    GUEST = auto()

PERMISSIONS = {
    Role.SUPERADMIN: {
        "create", "read", "update", "delete",
        "change_role", "create_admin", "delete_admin"
    },
    Role.ADMIN: {
        "create", "read", "update", "delete",
        "change_role"
    },
    Role.USER: {"create_own", "read_own", "update_own", "delete_own"},
    Role.GUEST: set()
}

def has_permission(role: Role, action: str, own: bool = False) -> bool:
    """
    Check if the role can perform the action.

    Args:
        role (Role): Role of the user.
        action (str): Action to check permission for.
        own (bool): If True, check permission for own resource.

    Returns:
        bool: True if permission is granted, False otherwise.
    """
    if not isinstance(action, str) or not action:
        return False
    if role not in PERMISSIONS:
        return False  # deny by default
    if own:
        action = f"{action}_own"
    return action in PERMISSIONS[role]

def authorize(user, action: str, resource_owner_id=None):
    """
    Centralized authorization enforcement.

    Responsibilities:
    - Ensure the user is authenticated.
    - Determine ownership automatically.
    - Enforce deny-by-default policy.
    - Raise appropriate security exceptions when needed.
    """
    # 🔐 Enforce authentication
    if user is None:
        raise AuthenticationRequiredError()
    
    if not hasattr(user, "role_enum") or not hasattr(user, "id"):
        raise AuthenticationRequiredError("Invalid user context")
    
    role_enum = user.role_enum # Not trust on token

    own = resource_owner_id is not None and user.id == resource_owner_id

    # Permission check
    if not has_permission(role_enum, action, own=own):
        logger.warning(
            "permission_denied | user_hash=%s | action=%s | resource_owner_id=%s",
            hash_sensitive(user.id),
            action,
            getattr(resource_owner_id, 'hex', resource_owner_id),
        )
        raise PermissionDeniedError(role_enum.name, action)

    return True

# ===============================
# TOKEN UTILITIES
# ===============================

def generate_jti() -> str:
    return str(uuid.uuid4())


def hash_token(token: str) -> str:
    return hmac.new(SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


# ===============================
# TOKEN CREATION
# ===============================

def create_access_token(user) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user.id),   # ✅ UUID to string
        "role": user.role,
        "type": "access",
        "jti": generate_jti(),
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user.id),    # ✅ UUID to string
        "type": "refresh",
        "jti": generate_jti(),
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ===============================
# TOKEN VALIDATION
# ===============================

def decode_token(token: str, expected_type: str = None) -> dict:
    """
    Decode and validate a JWT token.

    Validations:
    - Signature and expiration
    - Subject (sub) is valid UUID
    - Token type if expected_type is provided
    - iat (issued at) and nbf (not before) claims

    Args:
        token (str): JWT token string.
        expected_type (str, optional): 'access' or 'refresh'.

    Returns:
        dict: Decoded payload.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationRequiredError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationRequiredError("Invalid token")

    # Validate 'sub' is UUID
    sub = payload.get("sub")
    try:
        uuid.UUID(str(sub))
    except (ValueError, TypeError):
        raise AuthenticationRequiredError("Invalid subject in token")

    # Validate iat and nbf
    now = datetime.now(timezone.utc)
    iat = payload.get("iat")
    nbf = payload.get("nbf")

    if iat is not None:
        iat_dt = datetime.fromtimestamp(iat, tz=timezone.utc)
        if now < iat_dt:
            raise AuthenticationRequiredError("Token not valid yet (iat)")

    if nbf is not None:
        nbf_dt = datetime.fromtimestamp(nbf, tz=timezone.utc)
        if now < nbf_dt:
            raise AuthenticationRequiredError("Token not valid yet (nbf)")

    # Verify token type
    if expected_type is not None:
        verify_token_type(payload, expected_type)

    # Check revocation
    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise AuthenticationRequiredError("Token has been revoked")

    return payload


def verify_token_type(payload: dict, expected_type: str):
    if payload.get("type") != expected_type:
        raise AuthenticationRequiredError("Invalid token type")
    
# ===============================
# TOKEN REVOCATION
# ===============================

_revoked_tokens = {}  # jti -> expiration datetime

def revoke_token(jti: str, expires_at: datetime):
    """Add a token to the revocation list."""
    _revoked_tokens[jti] = expires_at

def is_token_revoked(jti: str) -> bool:
    """Check if a token has been revoked."""
    exp = _revoked_tokens.get(jti)
    if exp is None:
        return False
    if datetime.now(timezone.utc) >= exp:
        # Auto-clean expired revocations
        del _revoked_tokens[jti]
        return False
    return True