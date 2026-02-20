import redis
from datetime import datetime, timedelta, timezone
from core.exceptions import AuthenticationRequiredError
import hashlib
from dotenv import load_dotenv
import logging
from config import (REDIS_URL,
MAX_ATTEMPTS,
RATE_LIMIT_SECONDS,
LOCK_MINUTES,
MAX_LOCK_MINUTES,
BACKOFF_MULTIPLIER,
KEY_TTL_SECONDS,
GLOBAL_MAX_ATTEMPTS)

logger = logging.getLogger(__name__)

# 🔹 Redis Configuration

load_dotenv(override=True)
REDIS_URL
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set in the environment")


def get_redis_client() -> redis.Redis:
    """
    Returns a Redis client connected to the configured REDIS_URL.
    Includes timeouts, health check, and decode_responses=True.

    Returns:
        redis.Redis: Redis client instance
    """
    return redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )

def _get_redis():
    return get_redis_client()

def get_redis():
    """Return a Redis client instance."""
    return _get_redis()

# --------------------------- Helper Functions ---------------------------

def _parse_datetime_safe(value: str, redis_key: str, field_name: str) -> datetime | None:
    """
    Safely parse an ISO-formatted datetime string from Redis.
    Returns None if value is None or malformed.

    Args:
        value (str): ISO datetime string
        redis_key (str): Key in Redis (used for logging)
        field_name (str): Name of the field for logging

    Returns:
        datetime | None: timezone-aware datetime in UTC or None if invalid
    """
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value)
        # Ensure timezone-aware (UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError) as e:
        logger.warning(
            f"Invalid {field_name} format in Redis",
            extra={"user_hash": redis_key, "exception": str(e)}
        )
        return None


def _get_global_key(user_id: str) -> str:
    """
    Generate a Redis key for tracking global login attempts across IPs.

    Args:
        user_id (str): User ID

    Returns:
        str: Redis key for global attempt tracking
    """
    hashed = hashlib.sha256(f"{user_id}".encode()).hexdigest()
    return f"login_attempt:global:{hashed}"


def _get_key(user_id: str, ip: str) -> str:
    """
    Generate a Redis key for a specific user and IP.

    Args:
        user_id (str): User ID
        ip (str): IP address

    Returns:
        str: Namespaced Redis key for this user/IP combination
    """
    hashed = hashlib.sha256(f"{user_id}:{ip}".encode()).hexdigest()
    return f"login_attempt:{hashed}"


# --------------------------- Lock & Rate Limiting ---------------------------

def check_lock(user_id: str, ip: str):
    """
    Checks whether a user/IP combination is currently locked due to failed login attempts,
    including both IP-specific and global locks.

    Implements fail-closed behavior: if Redis cannot be reached, login is blocked.
    Uses a Redis client obtained via get_redis().

    Args:
        user_id (str): The unique identifier of the user.
        ip (str): The IP address of the client. Required for IP-specific lock checks.

    Raises:
        ValueError: If user_id or ip are missing.
        AuthenticationRequiredError: If the account is temporarily locked (IP-specific or global),
            or if Redis verification fails.
    """
    if not user_id or not ip:
        raise ValueError("user_id and ip are required")

    redis_client = get_redis()

    redis_key = _get_key(user_id, ip)
    lock_key = f"{redis_key}:lock"
    now = datetime.now(timezone.utc)

    try:

        # 🔹 IP-specific lock check
        locked_until_raw = redis_client.get(lock_key)
        if locked_until_raw:
            locked_until = _parse_datetime_safe(locked_until_raw, lock_key, "locked_until")
            if locked_until and now < locked_until:
                raise AuthenticationRequiredError("Account temporarily locked")

        # 🔹 Global attempts lock
        global_key = _get_global_key(user_id)
        global_lock_key = f"{global_key}:lock"

        global_locked_until_raw = redis_client.get(global_lock_key)
        global_locked_until = None

        if global_locked_until_raw:
            global_locked_until = _parse_datetime_safe(
                global_locked_until_raw,
                global_lock_key,
                "global_locked_until"
            )

        if global_locked_until and now < global_locked_until:
            raise AuthenticationRequiredError("Account temporarily locked (global)")
        

    except redis.RedisError:
        logger.error("Redis error during lock check", exc_info=True)
        # Fail-close for security
        raise AuthenticationRequiredError("Unable to verify login attempts")

def check_rate_limit(user_id: str, ip: str):
    """
    Enforces a minimum interval between login attempts from the same IP.
    Prevents rapid retries (rate limiting).

    Uses a Redis client obtained via get_redis().

    Args:
        user_id (str): The unique identifier of the user.
        ip (str): The IP address of the client.

    Raises:
        ValueError: If user_id or ip are missing.
        AuthenticationRequiredError: If attempts are too frequent
            or Redis cannot be queried.
    """

    if not user_id or not ip:
        raise ValueError("user_id and ip are required")
    
    redis_client = get_redis()
    
    redis_key = _get_key(user_id, ip)
    last_key = f"{redis_key}:last"
    now = datetime.now(timezone.utc)

    try:
        last_attempt_raw = redis_client.get(last_key)
        if last_attempt_raw:
            last_attempt = _parse_datetime_safe(last_attempt_raw, last_key, "last_attempt")
            if last_attempt and (now - last_attempt).total_seconds() < RATE_LIMIT_SECONDS:
                raise AuthenticationRequiredError("Too many attempts, slow down")
    except redis.RedisError:
        logger.error("Redis error during rate limit check", exc_info=True)
        raise AuthenticationRequiredError("Unable to verify rate limit")


def apply_backoff(user_id: str, ip: str):
    """
    Increments failed login attempt counters and applies locks with exponential backoff.

    Uses a Redis client obtained via get_redis().

    - IP-specific lock: triggers after MAX_ATTEMPTS from same IP.
    - Global lock: triggers after GLOBAL_MAX_ATTEMPTS across all IPs.
    - Uses Redis SET NX to avoid overwriting existing locks.

    Args:
        user_id (str): The unique identifier of the user.
        ip (str): The IP address of the client.

    Raises:
        ValueError: If user_id or ip are missing.
    """

    if not user_id or not ip:
        raise ValueError("user_id and ip are required")
    
    redis_client = get_redis()
    
    redis_key = _get_key(user_id, ip)
    global_key = _get_global_key(user_id)
    now = datetime.now(timezone.utc)

    try:
        # 🔹 Increment IP-specific attempts
        attempt_count = redis_client.incr(redis_key)
        redis_client.expire(redis_key, KEY_TTL_SECONDS)

        # 🔹 Record last attempt timestamp
        redis_client.set(f"{redis_key}:last", now.isoformat(), ex=KEY_TTL_SECONDS)

        # 🔹 Increment global attempts
        global_attempts = redis_client.incr(global_key)
        redis_client.expire(global_key, KEY_TTL_SECONDS)

        # 🔹 Apply exponential backoff lock per IP
        if attempt_count >= MAX_ATTEMPTS:
            exponent = attempt_count - MAX_ATTEMPTS
            lock_minutes = min(LOCK_MINUTES * (BACKOFF_MULTIPLIER ** exponent), MAX_LOCK_MINUTES)
            locked_until = now + timedelta(minutes=lock_minutes)
            redis_client.set(
                f"{redis_key}:lock",
                locked_until.isoformat(),
                ex=KEY_TTL_SECONDS,
                nx=True
            )

            logger.warning(
                "User locked (IP)",
                extra={"user_hash": redis_key, "attempt_count": attempt_count, "lock_minutes": lock_minutes},
            )
        global_lock_key = f"{global_key}:lock"

        # 🔹 Apply global lock if exceeded
        if global_attempts >= GLOBAL_MAX_ATTEMPTS:
            global_lock_key = f"{global_key}:lock"
            locked_until = now + timedelta(minutes=MAX_LOCK_MINUTES)

            redis_client.set(
                global_lock_key,
                locked_until.isoformat(),
                ex=KEY_TTL_SECONDS,
                nx=True
            )

            logger.warning(
                "User globally locked",
                extra={
                    "user_hash": global_key,
                    "global_attempts": global_attempts,
                },
        )
    except redis.RedisError:
        logger.error("Redis error in apply_backoff", exc_info=True)


def reset_attempts(user_id: str, ip: str):
    """
    Resets the failed login attempts and locks for a specific user/IP combination.

    Uses a Redis client obtained via get_redis().

    The global attempt counter is deliberately preserved to prevent bypassing
    security with distributed attacks.

    Args:
        user_id (str): The unique identifier of the user.
        ip (str): The IP address of the client.

    Raises:
        ValueError: If user_id or ip are missing.
    """

    redis_client = get_redis()

    if not user_id or not ip:
        raise ValueError("user_id and ip are required")
    
    redis_key = _get_key(user_id, ip)
    global_key = _get_global_key(user_id)

    try:
        redis_client.delete(redis_key)
        redis_client.delete(f"{redis_key}:lock")
        redis_client.delete(f"{redis_key}:last")
    except redis.RedisError:
        logger.error("Redis error during reset", exc_info=True)