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
    Authenticate a user with protection against brute force attacks:
    - Rate limiting by IP and user
    - Lockout after multiple failed attempts
    - Exponential backoff effect on further attempts
    """

    if db_session is None:
        raise MissingDataError()
    if not ip:
        raise AuthenticationRequiredError("IP is required")

    repo = UserRepository(db_session)
    user = repo.get_by_username(username)

    if user is None:
        # ✅  appy backoff UUID temporal
        fake_user_id = uuid.uuid4()
        apply_backoff(fake_user_id, ip, db_session=db_session)
        logger.warning(f"Failed login attempt for {hash_sensitive(username)} from IP {hash_sensitive(ip)}")
        raise AuthenticationRequiredError("Invalid credentials.")

    user_id = user.id

    # 1️⃣ Blocked and rate limit
    check_lock(user_id, ip, db_session=db_session)
    check_rate_limit(user_id, ip, db_session=db_session)

    # 2️⃣ Verify password and active status 
    if not user.is_active or not verify_password(password, getattr(user, "password_hash", "")):
        apply_backoff(user_id, ip, db_session=db_session)
        logger.warning(f"Failed login attempt for {hash_sensitive(username)} from IP {hash_sensitive(ip)}")
        raise AuthenticationRequiredError("Invalid credentials.")

    # 3️⃣ Login successful: delete attempts previouss completly
    reset_attempts(user_id, ip, db_session=db_session)
    logger.info(f"User {hash_sensitive(username)} authenticated successfully from IP {hash_sensitive(ip)}")

    return user