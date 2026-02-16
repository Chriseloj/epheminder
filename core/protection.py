import redis
from datetime import datetime, timedelta, timezone
from core.exceptions import AuthenticationRequiredError
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

# 🔹 Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL environment variable is not set")

# 🔹 Security parameters
MAX_ATTEMPTS = 5                 # Max login attempts per IP before lock
RATE_LIMIT_SECONDS = 60          # Min seconds between attempts (rate limiting)
LOCK_MINUTES = 15                # Base lock duration in minutes
MAX_LOCK_MINUTES = 24 * 60       # Max lock duration in minutes
BACKOFF_MULTIPLIER = 2           # Exponential backoff multiplier
KEY_TTL_SECONDS = 24 * 60 * 60   # Redis key TTL (24h)
GLOBAL_MAX_ATTEMPTS = MAX_ATTEMPTS * 3  # Global attempts limit across IPs

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

# Global Redis client
r = get_redis_client()


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
    Check if a user/IP combination is currently locked or globally blocked.
    Raises AuthenticationRequiredError if locked.

    Args:
        user_id (str): User ID
        ip (str): IP address

    Raises:
        AuthenticationRequiredError: If the account is locked or cannot verify
    """
    redis_key = _get_key(user_id, ip)
    lock_key = f"{redis_key}:lock"
    now = datetime.now(timezone.utc)

    try:
        # 🔹 IP-specific lock check
        locked_until_raw = r.get(lock_key)
        if locked_until_raw:
            locked_until = _parse_datetime_safe(locked_until_raw, lock_key, "locked_until")
            if locked_until and now < locked_until:
                raise AuthenticationRequiredError("Account temporarily locked")

        # 🔹 Global attempts lock
        global_key = _get_global_key(user_id)
        global_attempts = int(r.get(global_key) or 0)
        if global_attempts >= GLOBAL_MAX_ATTEMPTS:
            raise AuthenticationRequiredError("Account temporarily locked (global)")

    except redis.RedisError:
        logger.error("Redis error during lock check", exc_info=True)
        # Fail-close for security
        raise AuthenticationRequiredError("Unable to verify login attempts")


def check_rate_limit(user_id: str, ip: str):
    """
    Enforces a minimum time between login attempts to prevent rapid retries.

    Args:
        user_id (str): User ID
        ip (str): IP address

    Raises:
        AuthenticationRequiredError: If attempts are too frequent
    """
    redis_key = _get_key(user_id, ip)
    last_key = f"{redis_key}:last"
    now = datetime.now(timezone.utc)

    try:
        last_attempt_raw = r.get(last_key)
        if last_attempt_raw:
            last_attempt = _parse_datetime_safe(last_attempt_raw, last_key, "last_attempt")
            if last_attempt and (now - last_attempt).total_seconds() < RATE_LIMIT_SECONDS:
                raise AuthenticationRequiredError("Too many attempts, slow down")
    except redis.RedisError:
        logger.error("Redis error during rate limit check", exc_info=True)
        raise AuthenticationRequiredError("Unable to verify rate limit")


def apply_backoff(user_id: str, ip: str):
    """
    Increments attempt counters and applies exponential backoff locks
    if the number of failed login attempts exceeds limits.

    Args:
        user_id (str): User ID
        ip (str): IP address
    """
    redis_key = _get_key(user_id, ip)
    global_key = _get_global_key(user_id)
    now = datetime.now(timezone.utc)

    try:
        # 🔹 Increment IP-specific attempts
        attempt_count = r.incr(redis_key)
        r.expire(redis_key, KEY_TTL_SECONDS)

        # 🔹 Record last attempt timestamp
        r.set(f"{redis_key}:last", now.isoformat(), ex=KEY_TTL_SECONDS)

        # 🔹 Increment global attempts
        global_attempts = r.incr(global_key)
        r.expire(global_key, KEY_TTL_SECONDS)

        # 🔹 Apply exponential backoff lock per IP
        if attempt_count >= MAX_ATTEMPTS:
            exponent = attempt_count - MAX_ATTEMPTS
            lock_minutes = min(LOCK_MINUTES * (BACKOFF_MULTIPLIER ** exponent), MAX_LOCK_MINUTES)
            locked_until = now + timedelta(minutes=lock_minutes)
            r.set(f"{redis_key}:lock", locked_until.isoformat(), ex=KEY_TTL_SECONDS)
            logger.warning(
                "User locked (IP)",
                extra={"user_hash": redis_key, "attempt_count": attempt_count, "lock_minutes": lock_minutes},
            )

        # 🔹 Apply global lock if exceeded
        if global_attempts >= GLOBAL_MAX_ATTEMPTS:
            locked_until = now + timedelta(minutes=MAX_LOCK_MINUTES)
            r.set(f"{redis_key}:lock", locked_until.isoformat(), ex=KEY_TTL_SECONDS)
            logger.warning(
                "User globally locked",
                extra={"user_hash": redis_key, "global_attempts": global_attempts},
            )

    except redis.RedisError:
        logger.error("Redis error in apply_backoff", exc_info=True)


def reset_attempts(user_id: str, ip: str):
    """
    Clears login attempt counters and locks for a specific user/IP combination
    and the global attempt counter.

    Args:
        user_id (str): User ID
        ip (str): IP address
    """
    redis_key = _get_key(user_id, ip)
    global_key = _get_global_key(user_id)

    try:
        r.delete(redis_key)
        r.delete(f"{redis_key}:lock")
        r.delete(f"{redis_key}:last")
        r.delete(global_key)
    except redis.RedisError:
        logger.error("Redis error during reset", exc_info=True)