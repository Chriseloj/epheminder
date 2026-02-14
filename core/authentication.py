from datetime import datetime, timedelta, timezone
from core.models import UserDB
from core.exceptions import AuthenticationRequiredError, MissingDataError
from core.passwords import verify_password
from infrastructure.repositories import UserRepository
from core.protection import MAX_ATTEMPTS, LOCK_MINUTES, BACKOFF_MULTIPLIER, FAILED_ATTEMPTS
import logging

logger = logging.getLogger(__name__)

def authenticate(username: str, password: str, db_session=None) -> "UserDB":
    """
    Authenticate a user with protection against brute force attacks:
    - Rate limiting by username
    - Lockout after multiple failed attempts
    - Exponential backoff effect on further attempts
    """

    if db_session is None:
        raise MissingDataError()

    repo = UserRepository(db_session)

    # Initialize tracking for this username
    attempts = FAILED_ATTEMPTS.get(username, {"count": 0, "last_attempt": None, "locked_until": None})
    now = datetime.now(timezone.utc)

    # Check if user is currently locked
    if attempts.get("locked_until") and now < attempts["locked_until"]:
        raise AuthenticationRequiredError("Account temporarily locked due to repeated failed login attempts")

    # Fetch user from DB
    user = repo.get_by_username(username)

    # Verify credentials
    if not user or not user.is_active or not verify_password(password, getattr(user, "password_hash", "")):
        # Increment failed attempts
        attempts["count"] += 1
        attempts["last_attempt"] = now

        logger.warning(f"Failed login for {username}, count={attempts['count']}")

        # Apply lock if max attempts exceeded
        if attempts["count"] >= MAX_ATTEMPTS:
            MAX_LOCK_MINUTES = 60
            lock_seconds = min(
                LOCK_MINUTES * 60 * (BACKOFF_MULTIPLIER ** (attempts["count"] - MAX_ATTEMPTS)),
                MAX_LOCK_MINUTES * 60
            )
            attempts["locked_until"] = now + timedelta(seconds=lock_seconds)

        FAILED_ATTEMPTS[username] = attempts
        raise AuthenticationRequiredError("Invalid credentials.")

    # Successful login → reset failed attempts
    if username in FAILED_ATTEMPTS:
        del FAILED_ATTEMPTS[username]

    return user