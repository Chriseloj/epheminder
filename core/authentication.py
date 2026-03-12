from core.models import UserDB
from core.exceptions import AuthenticationRequiredError, MissingDataError
from core.passwords import verify_password
from infrastructure.repositories import UserRepository
from core.protection import check_lock, check_rate_limit, apply_backoff, reset_attempts
import logging
from core.hash_utils import hash_sensitive
import uuid

logger = logging.getLogger(__name__)

def authenticate(username: str, password: str, db_session=None, ip: str = None) -> "UserDB":
    """
    Authenticate a user with brute-force protection mechanisms.

    Security mechanisms:
        - Rate limiting per IP and user
        - Temporary lockout after repeated failures
        - Exponential backoff on failed attempts
        - Protection against user enumeration

    Args:
        username (str): Username identifier.
        password (str): Plaintext password.
        db_session: Active database session.
        ip (str): Client IP address.

    Returns:
        UserDB: Authenticated user object.

    Raises:
        MissingDataError: If db_session is not provided.
        AuthenticationRequiredError: If authentication fails.
    """

    if db_session is None:
        raise MissingDataError()
    if not ip:
        raise AuthenticationRequiredError("IP is required")

    repo = UserRepository(db_session)

    if not username:
        raise MissingDataError("Username is required")
    
    user = repo.get_by_username(username)

    username_hash = hash_sensitive(username)
    ip_hash = hash_sensitive(ip)

    if user is None:
        # ✅  apply backoff UUID temporal
        fake_user_id = uuid.uuid4()
        apply_backoff(fake_user_id, ip, db_session=db_session)
        logger.warning(
            "login_failed | user_hash=%s | ip=%s | reason=invalid_credentials",
            username_hash,
            ip_hash,
        )
        raise AuthenticationRequiredError("Invalid credentials.")

    user_id = user.id

    # 1️⃣ Blocked and rate limit
    check_lock(user_id, ip, db_session=db_session)
    check_rate_limit(user_id, ip, db_session=db_session)

    # 2️⃣ Verify password and active status 
    if not user.is_active or not verify_password(password, getattr(user, "password_hash", "")):
        apply_backoff(user_id, ip, db_session=db_session)
        logger.warning(
            "login_failed | user_hash=%s | ip=%s | reason=invalid_credentials",
            username_hash,
            ip_hash,
        )
        raise AuthenticationRequiredError("Invalid credentials.")

    # 3️⃣ Login successful: delete attempts previouss completly
    reset_attempts(user_id, ip, db_session=db_session)
    logger.info(
        "login_success | user_hash=%s | ip=%s",
        username_hash,
        ip_hash,
    )

    return user