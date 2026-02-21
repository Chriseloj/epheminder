from core.models import UserDB, RefreshTokenDB
from datetime import datetime, timedelta, timezone
from core.security import (decode_token,
verify_token_type,
hash_token,
create_access_token,
create_refresh_token)
import uuid
from core.exceptions import AuthenticationRequiredError
from core.security import hash_sensitive
import logging

logger = logging.getLogger(__name__)

def refresh(refresh_token: str, db_session):

    payload = decode_token(refresh_token)
    verify_token_type(payload, "refresh")

    token_hash = hash_token(refresh_token)

    stored_token = db_session.query(RefreshTokenDB).filter_by(
        token_hash=token_hash,
        revoked=False
    ).first()

    if not stored_token:
        raise AuthenticationRequiredError("Invalid refresh token")

    now = datetime.now(timezone.utc)

    expires_at = stored_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise AuthenticationRequiredError("Refresh token expired")

    user = db_session.query(UserDB).filter_by(id=uuid.UUID(payload["sub"])).first()

    if not user or not user.is_active:
        raise AuthenticationRequiredError("User inactive")

    # ROTATION
    stored_token.revoked = True
    db_session.flush()

    new_access = create_access_token(user)
    new_refresh = create_refresh_token(user)

    new_refresh_db = RefreshTokenDB(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False
    )

    db_session.add(new_refresh_db)
    db_session.commit()

    logger.info(f"Refresh token rotated | user_hash={hash_sensitive(user.id)}")

    return {
        "access_token": new_access,
        "refresh_token": new_refresh
    }