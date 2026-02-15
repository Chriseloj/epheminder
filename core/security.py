from enum import Enum, auto
from core.exceptions import PermissionDeniedError, AuthenticationRequiredError

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

    # Defensive check: ensure user has required attributes
    if not hasattr(user, "role") or not hasattr(user, "id"):
        raise AuthenticationRequiredError("Invalid user context")

    # Determine whether the user owns the target resource
    own = False
    if resource_owner_id is not None:
        own = user.id == resource_owner_id

    # Check if the user's role has permission for the action
    if not has_permission(user.role_enum, action, own=own):
        raise PermissionDeniedError(user.role_enum.name, action)

    # Authorization successful
    return True