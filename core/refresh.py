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
    """
    try:
        # Decode and verifiy token
        payload = decode_token(refresh_token)
        verify_token_type(payload, "refresh")

        token_hash = hash_token(refresh_token)

        # Search token on DB and validate active user
        stored_token = (
            db_session.query(RefreshTokenDB)
            .filter_by(token_hash=token_hash, revoked=False)
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

        if expires_at < now:
            raise AuthenticationRequiredError("Refresh token expired")

        # ROTATION: revoke old token 
        stored_token.revoked = True
        db_session.flush()  # sincronize changes before create new token

        # Create nee tokens
        new_access = create_access_token(stored_token.user)
        new_refresh = create_refresh_token(stored_token.user)

        # Save new refresh token on DB
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
            f"Refresh token rotated | user_hash={hash_sensitive(stored_token.user.id)} | old_token={token_hash}"
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
        logger.exception(f"Unexpected error during token refresh: {str(e)}")
        raise AuthenticationRequiredError("An error occurred during token refresh")