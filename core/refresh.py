from core.models import UserDB, RefreshTokenDB
from datetime import datetime, timedelta, timezone
from core.security import (
    decode_token,
    verify_token_type,
    hash_token,
    create_access_token,
    create_refresh_token
)
from core.hash_utils import hash_sensitive
import uuid
from core.exceptions import AuthenticationRequiredError
from config import REFRESH_TOKEN_EXPIRE_DAYS
import logging

logger = logging.getLogger(__name__)

def refresh(refresh_token: str, db_session):
    """
    Rotate a refresh token: invalidates the old token, create a new one, and returns the access and refresh tokens.
    Implements detection of refresh token reuse.
    """
    try:
        # Decode and verify token
        payload = decode_token(refresh_token)
        verify_token_type(payload, "refresh")

        token_hash = hash_token(refresh_token)

        # Search token on DB and validate active user
        stored_token = (
            db_session.query(RefreshTokenDB)
            .filter_by(token_hash=token_hash)
            .join(UserDB)
            .filter(UserDB.id == uuid.UUID(payload["sub"]), UserDB.is_active == True)
            .first()
        )

        if not stored_token:
            raise AuthenticationRequiredError("Invalid refresh token")

        now = datetime.now(timezone.utc)
        expires_at = stored_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        # Check expiration first
        if expires_at < now:
            stored_token.revoked = True
            db_session.commit()
            raise AuthenticationRequiredError("Refresh token expired")

        # 🔴 Detect reuse
        if stored_token.revoked:
            logger.warning(
                "Detected reuse of refresh token | user_hash=%s | token_hash=%s",
                hash_sensitive(stored_token.user.id),
                token_hash
            )
            # Revoke all active tokens of the user
            db_session.query(RefreshTokenDB).filter_by(user_id=stored_token.user.id, revoked=False).update({"revoked": True})
            db_session.commit()
            raise AuthenticationRequiredError("Refresh token reuse detected")

        # ROTATION: revoke old token
        stored_token.revoked = True
        db_session.flush()  # ensure DB sees the change before inserting new token

        # Create new tokens
        new_access = create_access_token(stored_token.user)
        new_refresh = create_refresh_token(stored_token.user)

        # Save new refresh token in DB
        new_refresh_db = RefreshTokenDB(
            id=uuid.uuid4(),
            user_id=stored_token.user.id,
            token_hash=hash_token(new_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False
        )

        db_session.add(new_refresh_db)
        db_session.commit()

        logger.info(
            "Refresh token rotated | user_hash=%s | old_token=%s",
            hash_sensitive(stored_token.user.id),
            token_hash
        )

        return {
            "access_token": new_access,
            "refresh_token": new_refresh
        }

    except AuthenticationRequiredError:
        db_session.rollback()
        raise
    except Exception as e:
        db_session.rollback()
        logger.exception("Unexpected error during token refresh: %s", str(e))
        raise AuthenticationRequiredError("An error occurred during token refresh")