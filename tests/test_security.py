import pytest
from core.security import Role, has_permission, authorize
from core.exceptions import PermissionDeniedError, AuthenticationRequiredError

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