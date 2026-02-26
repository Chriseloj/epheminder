import logging
from functools import wraps
from core.models import UserDB
from core.protection import (check_register_rate_limit,
apply_register_backoff,
reset_register_attempts,
check_rate_limit,
apply_backoff,
reset_attempts)
from core.session import session_manager
from core.security import decode_token
from core.exceptions import AuthenticationRequiredError
from core.cli_utils import safe_print
import logging
from functools import wraps


logger = logging.getLogger(__name__)

def rate_limited(user_param: str, ip_param: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get(user_param)
            ip = kwargs.get(ip_param)
            db_session = kwargs.get("db_session")

            if not db_session:
                raise ValueError("db_session is required")

            if isinstance(user_id, str):
                user_obj = db_session.query(UserDB).filter_by(username=user_id).first()
                user_id = user_obj.id if user_obj else user_id

            check_rate_limit(user_id, ip, db_session=db_session)

            try:
                result = func(*args, **kwargs)
            except Exception:
                apply_backoff(user_id, ip, db_session=db_session)
                raise
            else:
                reset_attempts(user_id, ip, db_session=db_session)
                return result
        return wrapper
    return decorator

def register_rate_limited(user_param: str, ip_param: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = kwargs.get(user_param)
            ip = kwargs.get(ip_param)
            db_session = kwargs.get("db_session")

            if not db_session:
                raise ValueError("db_session is required")

            check_register_rate_limit(username, ip, db_session)

            try:
                result = func(*args, **kwargs)
            except Exception:
                apply_register_backoff(username, ip, db_session)
                raise
            else:
                reset_register_attempts(username, ip, db_session)
                return result

        return wrapper
    return decorator

def require_login(arg=None):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db_session = kwargs.get("db_session")
            if not db_session:
                raise RuntimeError("db_session must be passed to CLI functions")

            if not session_manager.current_user:
                safe_print("Please login first.")
                return

            try:
                decode_token(session_manager.access_token)
            except AuthenticationRequiredError:
                session_manager.clear()
                safe_print("Please login again.")
                return
            except Exception:
                session_manager.clear()
                safe_print("Invalid. Please login again.")
                return

            return func(*args, **kwargs)

        return wrapper

    if callable(arg):
        return decorator(arg)
    else:
        return decorator