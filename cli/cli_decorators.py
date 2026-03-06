from functools import wraps
from core.session import session_manager
from core.security import decode_token
from core.exceptions import AuthenticationRequiredError
from cli.cli_utils import safe_print
from functools import wraps
from core.hash_utils import hash_sensitive
import logging

logger = logging.getLogger(__name__)

def require_login(func=None):
    """
    Decorator to ensure a user is logged in before executing a function.

    For CLI functions:
    - Prints a message if no user is logged in.
    - Clears session if token is invalid or expired.
    - Does NOT require db_session; CLI functions handle that separately.

    Usage:
        @require_login
        def my_cli_action(*args, **kwargs):
            ...
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session_manager.current_user
            user_safe = hash_sensitive(user) if user else "unknown"

            if not user:
                logger.info("Unauthorized CLI access attempt: no user in session")
                safe_print("Please login first.")
                return

            try:
                decode_token(session_manager.access_token)
            except AuthenticationRequiredError:
                session_manager.clear()
                logger.warning(f"Authentication required: session cleared for user {user_safe}")
                safe_print("Please login again.")
                return
            except Exception as e:
                session_manager.clear()
                logger.error(f"Unexpected login error for user {user_safe}: {e}")
                safe_print("Invalid session. Please login again.")
                return

            return f(*args, **kwargs)
        return wrapper

    if callable(func):
        return decorator(func)
    return decorator