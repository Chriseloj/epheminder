from core.models import UserDB, RevokedTokenDB
from core.security import decode_token, verify_token_type
from core.exceptions import AuthenticationRequiredError
from datetime import datetime, timezone
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# --------------------------- Token Revocation ---------------------------

def revoke_access_token(access_token: str, db_session):
    """
    Mark access token as revoked on DB.
    """
    try:
        payload = decode_token(access_token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            if expires_at > now:
                token = db_session.query(RevokedTokenDB).filter_by(jti=jti).first()
                if not token:
                    token = RevokedTokenDB(jti=jti, expires_at=expires_at)
                    db_session.add(token)
                else:
                    token.expires_at = expires_at
                db_session.commit()
                logger.info("Access token revoked")
    except Exception as e:
        logger.warning(f"Failed to revoke access token: {type(e).__name__}")

def is_token_revoked(jti: str, db_session) -> bool:
    if not jti:
        return False
    now = datetime.now(timezone.utc)
    try:
        token = db_session.query(RevokedTokenDB).filter_by(jti=jti).first()
        if not token:
            return False
        if token.expires_at < now:
            db_session.delete(token)
            db_session.commit()
            return False
        return True
    except Exception:
        return True

# --------------------------- Current User ---------------------------

def get_current_user(token: str, db_session):
    payload = decode_token(token)
    verify_token_type(payload, "access")

    # 🔐 Check blacklist
    jti = payload.get("jti")
    if jti and is_token_revoked(jti, db_session):
        raise AuthenticationRequiredError("Access token revoked")

    # Transform sub to UUID
    user_id = UUID(payload["sub"])
    user = db_session.query(UserDB).filter_by(id=user_id).first()

    if not user or not user.is_active:
        raise AuthenticationRequiredError()

    return user