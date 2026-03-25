import pytest
from core.authentication_service import AuthenticationService
from core.security import authorize, Role, has_permission
from core.models import RefreshTokenDB, ReminderDB, LoginAttemptDB
from core.exceptions import PermissionDeniedError, InvalidCredentialsError
from core.user_services import UserService
from datetime import datetime, timedelta, timezone
import uuid
from core.authentication import authenticate
from core.protection import reset_attempts

# ======================================
# LOGIN, REFRESH AND ROTACIÓN
# ======================================
def test_login_and_refresh_token_flow_extended(db_session, sample_user):
   
    # --- Login successful using AuthenticationService ---
    result = AuthenticationService.login(
        username=sample_user.username,
        password="Password_0ne_hash",
        ip="127.0.0.1",
        db_session=db_session
    )

    # --- Verify tokens ---
    assert isinstance(result, dict)
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"

    # --- Verify RefreshTokenDB ---
    token_db = (
        db_session.query(RefreshTokenDB)
        .filter_by(user_id=sample_user.id)
        .order_by(RefreshTokenDB.created_at.desc())
        .first()
    )

    assert token_db is not None
    assert token_db.revoked is False

    # --- expires_at to aware if SQLite return to naive ---
    expires_aware = (
        token_db.expires_at.replace(tzinfo=timezone.utc)
        if token_db.expires_at.tzinfo is None
        else token_db.expires_at
    )

    now_utc = datetime.now(timezone.utc)
    assert expires_aware > now_utc, "El refresh token debe expirar en el futuro"

# ======================================
# AUTORIZACIÓN Y PERMISOS
# ======================================
def test_authorization_with_roles(db_session, sample_user):
   
    other_user = UserService.create_user("otheruser", "Password1234@#!", db_session=db_session)

    
    reminder = ReminderDB(
        owner=sample_user,
        text="Reminder de test",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(reminder)
    db_session.commit()

    assert authorize(sample_user, "update", resource_owner_id=sample_user.id) is True

    
    with pytest.raises(PermissionDeniedError):
        authorize(sample_user, "update", resource_owner_id=other_user.id)

    
    sample_user.role = "GUEST"
    db_session.commit()
    with pytest.raises(PermissionDeniedError):
        authorize(sample_user, "read", resource_owner_id=sample_user.id)


# ======================================
# FAILED AND BACKOFF
# ======================================
def test_failed_login_and_backoff(db_session, sample_user):
    
    ip = "192.168.0.1"
    username = sample_user.username

    with pytest.raises(InvalidCredentialsError):
        authenticate(username, "wrongpassword", db_session=db_session, ip=ip)

    
    attempt = db_session.query(LoginAttemptDB).filter_by(user_id=sample_user.id, ip=ip).first()
    assert attempt is not None
    assert attempt.attempts == 1


    reset_attempts(sample_user.id, ip, db_session=db_session)
    attempt_after_reset = db_session.query(LoginAttemptDB).filter_by(user_id=sample_user.id, ip=ip).first()
    assert attempt_after_reset is None  

# ======================================
# CRUD
# ======================================
def test_reminder_crud_extended(db_session, sample_user):

    reminder = ReminderDB(
        owner=sample_user,
        text="Recordatorio integración extendido",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(reminder)
    db_session.commit()

    fetched = db_session.query(ReminderDB).filter_by(owner_id=sample_user.id).first()
    assert fetched is not None
    assert fetched.text == "Recordatorio integración extendido"

    fetched.text = "Texto actualizado"
    db_session.commit()
    updated = db_session.query(ReminderDB).filter_by(id=fetched.id).first()
    assert updated.text == "Texto actualizado"

    db_session.delete(updated)
    db_session.commit()
    deleted = db_session.query(ReminderDB).filter_by(id=fetched.id).first()
    assert deleted is None


# ======================================
# PERMISSIONS
# ======================================
def test_permissions_logic(db_session, sample_user):
    sample_user.role = "USER"
    db_session.commit()

    other_id = uuid.uuid4()
    assert has_permission(Role.USER, "delete", own=False) is False


    assert has_permission(Role.USER, "delete", own=True) is True

    assert has_permission(Role.SUPERADMIN, "delete") is True
    assert has_permission(Role.SUPERADMIN, "create_admin") is True