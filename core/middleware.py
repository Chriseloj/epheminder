from core.models import UserDB
from core.security import (decode_token,
verify_token_type,)
from core.exceptions import AuthenticationRequiredError
from core.security import decode_token
from core.protection import get_redis ,KEY_TTL_SECONDS
from datetime import datetime, timezone, timedelta
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

def revoke_access_token(access_token: str):

    redis_client = get_redis()
    try:
        payload = decode_token(access_token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl_seconds = int(exp - datetime.now(timezone.utc).timestamp())
            if ttl_seconds > 0:
                redis_client.set(f"revoked_access:{jti}", "1", ex=ttl_seconds)
                logger.info(f"Access token revoked | jti={jti}")
    except Exception as e:
        logger.warning(f"Failed to revoke access token: {e}")


def get_current_user(token: str, db_session):
    redis_client = get_redis()
    payload = decode_token(token)
    verify_token_type(payload, "access")

    # 🔐 Check blacklist
    jti = payload.get("jti")
    if jti and redis_client.get(f"revoked_access:{jti}"):
        raise AuthenticationRequiredError("Access token revoked")

    # Transform sub to UUID
    user_id = UUID(payload["sub"])
    user = db_session.query(UserDB).filter_by(id=user_id).first()

    if not user or not user.is_active:
        raise AuthenticationRequiredError()

    return user