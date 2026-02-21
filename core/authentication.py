from core.models import UserDB
from core.exceptions import AuthenticationRequiredError, MissingDataError
from core.passwords import verify_password
from infrastructure.repositories import UserRepository
from core.protection import check_lock, check_rate_limit, apply_backoff, reset_attempts
import logging
from core.security import hash_sensitive

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
        raise AuthenticationRequiredError("IP is required for authentication")

    repo = UserRepository(db_session)

    # Fetch user from DB
    user = repo.get_by_username(username)
    user_id = getattr(user, "id", username)  # fallback to username if user doesn't exist

    # 1️⃣ Check if the user/IP is locked
    check_lock(user_id, ip)

    # 2️⃣ Check rate limit
    check_rate_limit(user_id, ip)

    # 3️⃣ Verify credentials
    if not user or not user.is_active or not verify_password(password, getattr(user, "password_hash", "")):
        # Apply backoff
        apply_backoff(user_id, ip)
        logger.warning(f"Failed login attempt for {hash_sensitive(username)}from IP {hash_sensitive(ip)}")
        raise AuthenticationRequiredError("Invalid credentials.")

    # 4️⃣ Success → reset attempts
    reset_attempts(user_id, ip)  # optionally, or implement a reset function if needed
    logger.info(f"User {hash_sensitive(username)} authenticated successfully from IP {hash_sensitive(ip)}")

    return user