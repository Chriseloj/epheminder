from functools import wraps
from core.session import session_manager
from core.security import decode_token
from core.exceptions import AuthenticationRequiredError
from core.hash_utils import hash_sensitive
import logging

logger = logging.getLogger(__name__)


def require_login(func=None):

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