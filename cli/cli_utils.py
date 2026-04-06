import logging
from datetime import datetime, timezone
from cli.cli_exceptions import CLIExit
from core.hash_utils import hash_sensitive
from config import VALID_UNITS

logger = logging.getLogger(__name__)


def safe_input(prompt: str) -> str:
    
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        raise CLIExit()


def safe_print(msg: str):
    
    print(msg, flush=True)


def log_event(level: str, action: str, user_id=None, ip=None, extra_info=None):
   
    parts = [f"action={action}"]

    if user_id is not None:
        parts.append(f"user_hash={hash_sensitive(user_id)}")
    if ip is not None:
        parts.append(f"ip_hash={hash_sensitive(ip)}")
    if extra_info:
        parts.append(f"info={extra_info}")

    parts.append(f"ts={datetime.now(timezone.utc).isoformat()}")
    msg = " | ".join(parts)

    if level.lower() == "info":
        logger.info(msg)
    elif level.lower() == "warning":
        logger.warning(msg)
    elif level.lower() == "error":
        logger.error(msg)
    else:
        logger.debug(msg)


def print_section(title: str):
    """
    Print a visual section header in the CLI
    to indicate the current operation.
    """
    safe_print(f"\n=== {title.upper()} ===\n")

def current_user_id(current_user=None):
    """Return the current user's ID if available."""
    if current_user is None:
        return None
    return getattr(current_user, "id", None)


def normalize_time_unit(unit: str) -> str:
    """Convert shortcut units (m/h/d) to full names."""
    unit = unit.lower().strip()
    shortcuts = {
        "m": "minutes",
        "h": "hours",
        "d": "days",
    }
    return shortcuts.get(unit, unit)


def validate_unit(unit: str) -> bool:
    """Check if the expiration unit is valid."""
    return unit.lower() in VALID_UNITS


def format_invalid_unit_message(unit: str) -> str:
    return f"Invalid unit '{unit}', please choose m/h/d or minutes/hours/days."