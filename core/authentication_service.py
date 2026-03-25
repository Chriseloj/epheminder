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
from core.hash_utils import hash_sensitive
from core.exceptions import InvalidCredentialsError
from config import REFRESH_TOKEN_EXPIRE_DAYS


logger = logging.getLogger(__name__)

class AuthenticationService:
    """
    Application service responsible for user authentication
    and token issuance.

    Responsibilities:
        - Validate login input
        - Delegate credential verification
        - Issue access and refresh tokens
        - Persist hashed refresh tokens
        - Apply rate limiting via decorator

    Security considerations:
        - Refresh tokens are stored hashed
        - Sensitive data is hashed in logs
        - Deny-by-default error handling
    """

    @staticmethod
    @rate_limited(user_param="username", ip_param="ip")
    def login(username: str, password: str, ip: str, db_session=None):
        """
        Authenticate user credentials and issue JWT access and refresh tokens.

        Args:
            username (str): User identifier.
            password (str): Plaintext password.
            ip (str): Client IP address for rate limiting and auditing.
            db_session: Active database session.

        Returns:
            dict: {
                "access_token": str,
                "refresh_token": str,
                "token_type": "bearer"
            }

        Raises:
            MissingDataError
            AuthenticationRequiredError
            Exception (database failures)
        """
        if db_session is None:
            raise MissingDataError()

        if not username or len(username) < 3:
            raise MissingDataError("Invalid username")
        
        username = username.strip().lower()
        if not password:
            raise MissingDataError("Invalid password")
        
        try:
            user = authenticate(username, password, db_session=db_session, ip=ip)
            user_hash = hash_sensitive(user.id)
            ip_hash = hash_sensitive(ip)
            
            logger.info(
                "login_success | user_hash=%s | ip=%s",
                user_hash,
                ip_hash,
            
            )

        except InvalidCredentialsError:
            ip_hash = hash_sensitive(ip)
            
            logger.warning(
                "login_failed | ip=%s | reason=auth_failed",
                ip_hash
            )
            raise
        except Exception:
            ip_hash = hash_sensitive(ip)
            

            logger.exception(
                "login_failed | ip=%s | reason=unexpected_error",
                ip_hash
            )
            raise


        # 1️⃣ JWT access token
        access_token = create_access_token(user)

        # 2️⃣ Refresh token
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
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