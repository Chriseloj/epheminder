import logging
from functools import wraps
from core.models import UserDB
from core.protection import check_rate_limit, apply_backoff, reset_attempts
from core.protection import check_register_rate_limit, apply_register_backoff, reset_register_attempts

logger = logging.getLogger(__name__)

def rate_limited(user_param: str, ip_param: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            user_id = kwargs.get(user_param)
            ip = kwargs.get(ip_param)
            db_session = kwargs.get("db_session")

            if not db_session:
                raise ValueError("db_session is required")

            # username to UUID
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