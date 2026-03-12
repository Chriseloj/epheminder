import logging
from functools import wraps
from core.models import UserDB
from core.protection import (check_register_rate_limit,
apply_register_backoff,
reset_register_attempts,
check_rate_limit,
apply_backoff,
reset_attempts)
from core.exceptions import RateLimitExceededError
import logging
from functools import wraps
from core.hash_utils import hash_sensitive


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

            user_obj = kwargs.get("user_obj")

            if isinstance(user_id, str) and not user_obj:
                user_obj = db_session.query(UserDB).filter_by(username=user_id).first()
            user_id = user_obj.id if user_obj else user_id

            check_rate_limit(user_id, ip, db_session=db_session)

            safe_user = hash_sensitive(user_id)
            safe_ip = hash_sensitive(str(ip)) if ip else "unknown"
            logger.info(
                "Rate-limit attempt for user %s | ip %s",
                safe_user,
                safe_ip
            )

            try:

                result = func(*args, **kwargs)

            except RateLimitExceededError as e:
                safe_user = hash_sensitive(user_id)
                safe_ip = hash_sensitive(str(ip)) if ip else "unknown"
                logger.warning(
                    "Apply backoff to user %s | ip %s: %s",
                    safe_user,
                    safe_ip,
                    str(e)
                )
                apply_backoff(user_id, ip, db_session=db_session)
                raise

            except Exception:
                raise
            else:
                reset_attempts(user_id, ip, db_session=db_session)
                logger.info(
                    "Reset attempts for user %s | ip %s",
                    safe_user,
                    safe_ip
                )
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

            safe_user = hash_sensitive(username)
            safe_ip = hash_sensitive(str(ip)) if ip else "unknown"
            logger.info(
                "Rate-limit attempt for user %s | ip %s",
                safe_user,
                safe_ip
            )

            try:
                result = func(*args, **kwargs)

            except RateLimitExceededError as e:

                safe_user = hash_sensitive(username)
                safe_ip = hash_sensitive(str(ip)) if ip else "unknown"
                logger.warning(
                    "Register backoff applied to user %s | ip %s: %s",
                    safe_user,
                    safe_ip,
                    str(e)
                )
                apply_register_backoff(username, ip, db_session=db_session)
                raise

                
            except Exception:
                logger.debug(
                    "Unexpected error in rate_limited wrapper",
                    exc_info=True
                )
                raise
            else:
                reset_register_attempts(username, ip, db_session)
                logger.info(
                    "Reset attempts for user %s | ip %s",
                    safe_user,
                    safe_ip
                )
                return result

        return wrapper
    return decorator