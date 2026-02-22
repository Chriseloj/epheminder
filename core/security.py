from enum import Enum, auto
from core.exceptions import PermissionDeniedError, AuthenticationRequiredError
import jwt
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
import logging
import os
from dotenv import load_dotenv
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

load_dotenv() 
HASH_SALT = os.getenv("HASH_SALT")

if not HASH_SALT:
    raise RuntimeError("HASH_SALT not defined")

def hash_sensitive(data) -> str:
    """Hash a sensitive value (UUID, str, etc.) usando SHA256 + salt seguro."""
    if isinstance(data, uuid.UUID):
        data = str(data)
    elif not isinstance(data, str):
        data = str(data)

    salted = f"{HASH_SALT}{data}"  # salt
    return hashlib.sha256(salted.encode()).hexdigest()

def has_permission(role: Role, action: str, own: bool = False) -> bool:
    """Check if the role can perform the action."""
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
    - Automatically determine ownership (if applicable).
    - Enforce deny-by-default policy.
    - Raise appropriate security exceptions when needed.
    """

    # 🔐 Enforce authentication (deny-by-default)
    if user is None:
        raise AuthenticationRequiredError()
    
    # Defensive check
    if not hasattr(user, "role") or not hasattr(user, "id"):
        raise AuthenticationRequiredError("Invalid user context")
    
    try:

        role_enum = user.role_enum

    except ValueError as e:
        logger.error(
            f"invalid_role | user_hash={hash_sensitive(getattr(user, 'id', 'unknown'))} | reason={str(e)} | ts={datetime.now(timezone.utc).isoformat()}"
        )
        raise AuthenticationRequiredError("Invalid user role")
    
    own = resource_owner_id is not None and user.id == resource_owner_id

    # Permission check
    if not has_permission(role_enum, action, own=own):
        logger.warning(
            f"permission_denied | user_hash={hash_sensitive(user.id)} | action={action} | ts={datetime.now(timezone.utc).isoformat()}"
        )
        raise PermissionDeniedError(role_enum.name, action)

    return True

# ===============================
# TOKEN UTILITIES
# ===============================

def generate_jti() -> str:
    return str(uuid.uuid4())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationRequiredError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationRequiredError("Invalid token")


def verify_token_type(payload: dict, expected_type: str):
    if payload.get("type") != expected_type:
        raise AuthenticationRequiredError("Invalid token type")