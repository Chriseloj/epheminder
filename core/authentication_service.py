import logging
import uuid
from core.decorators import rate_limited
from core.exceptions import MissingDataError
from core.security import (
    create_access_token,
)
from core.models import RefreshTokenDB
from datetime import datetime, timedelta, timezone
from core.authentication import authenticate
from core.security import hash_sensitive
from core.exceptions import AuthenticationRequiredError


logger = logging.getLogger(__name__)

class AuthenticationService:

    @staticmethod
    @rate_limited(user_param="username", ip_param="ip")
    def login(username: str, password: str, ip: str, db_session=None):
        if db_session is None:
            raise MissingDataError()

        if not username or len(username) < 3:
            raise MissingDataError("Invalid username")
        
        username = username.strip().lower()
        try: 
            user = authenticate(username, password, db_session=db_session, ip=ip)
            logger.info(
            f"login_success | user_hash={hash_sensitive(user.id)} | ip={hash_sensitive(ip)} | ts={datetime.now(timezone.utc).isoformat()}"
        )
        except AuthenticationRequiredError as e:
            logger.warning(
                f"login_failed | ip={hash_sensitive(ip)} | reason=auth_failed | ts={datetime.now(timezone.utc).isoformat()}"
            )
            raise
        except Exception as e:
            logger.error(
                f"login_failed | ip={hash_sensitive(ip)} | reason={type(e).__name__} | ts={datetime.now(timezone.utc).isoformat()}"
            )
            raise


        # 1️⃣ JWT access token
        access_token = create_access_token(user)

        # 2️⃣ Refresh token
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        token_value = uuid.uuid4().hex  # token string hexadecimal
        token_hash = hash_sensitive(token_value)  # hash 

        refresh_token_db = RefreshTokenDB(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,  # ✅ storage hash, not token
            expires_at=expire,
            revoked=False,
            created_at=datetime.now(timezone.utc)
        )
        try:
            db_session.add(refresh_token_db)
            db_session.commit()
        except Exception:
            db_session.rollback()
            logger.exception("Error storing refresh token")
            raise

        # 3️⃣ Return both tokens
        return {
            "access_token": access_token,
            "refresh_token": token_value,  # return token 
            "token_type": "bearer"
        }