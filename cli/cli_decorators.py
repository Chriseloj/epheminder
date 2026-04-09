from functools import wraps
from core.session import session_manager
from core.security import decode_token
from core.exceptions import AuthenticationRequiredError
from core.hash_utils import hash_sensitive
import logging

logger = logging.getLogger(__name__)


def require_login(func=None):
    """
    Decorator that ensures a user is authenticated before executing a CLI action.

    Behavior:
    - Checks if a user is present in the session
    - Validates the access token
    - Clears the session if the token is invalid or expired
    - Returns a standardized error response if authentication fails

    Returns:
        dict:
            On failure:
                {
                    "success": False,
                    "error": str
                }

    Notes:
        - Designed for CLI handlers that follow the standard response contract
        - Prevents execution of the wrapped function if authentication fails
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session_manager.current_user
            user_safe = hash_sensitive(user) if user else "unknown"

            # 🚫 Not logged in
            if not user:
                logger.info(
                    "Unauthorized CLI access attempt (user=%s)",
                    user_safe
                )
                return {
                    "success": False,
                    "error": "Please login first."
                }

            # 🔐 Validate token
            try:
                decode_token(session_manager.access_token)

            except AuthenticationRequiredError:
                session_manager.clear()
                logger.warning(
                    "Authentication required: session cleared for user %s",
                    user_safe
                )
                return {
                    "success": False,
                    "error": "Please login again."
                }

            except Exception:
                session_manager.clear()
                logger.exception(
                    "Unexpected login error for user %s",
                    user_safe
                )
                return {
                    "success": False,
                    "error": "Invalid session. Please login again."
                }

            # ✅ All good → execute real function
            return f(*args, **kwargs)

        return wrapper

    if callable(func):
        return decorator(func)
    return decorator