from core.hash_utils import hash_sensitive
from datetime import datetime, timezone
from core.exceptions import CLIExit
import logging

logger = logging.getLogger(__name__)

def safe_input(prompt):
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        raise CLIExit()

def log_event(level, action, user_id=None, ip=None, extra_info=None):
    parts = [f"action={action}"]
    
    if user_id is not None:
        parts.append(f"user_hash={hash_sensitive(user_id)}")
    if ip is not None:
        parts.append(f"ip_hash={hash_sensitive(ip)}")
    if extra_info:
        parts.append(f"info={extra_info}")
    
    parts.append(f"ts={datetime.now(timezone.utc).isoformat()}")
    msg = " | ".join(parts)
    
    if level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.debug(msg)

def safe_print(msg):
    print(msg, flush=True)

def current_user_id(current_user=None):
    if current_user is None:
        return None
    return getattr(current_user, "id", None)