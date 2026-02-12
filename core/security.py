from enum import Enum, auto

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

    if role not in PERMISSIONS:
        return False  # deny by default
    if own:
        action = f"{action}_own"
    return action in PERMISSIONS[role]