from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
import uuid
from core.models import LoginAttemptDB, RegisterAttemptDB
from core.exceptions import AuthenticationRequiredError
from config import (
    MAX_ATTEMPTS,
    RATE_LIMIT_SECONDS,
    LOCK_MINUTES,
    MAX_LOCK_MINUTES,
    BACKOFF_MULTIPLIER,
    KEY_TTL_SECONDS,
    GLOBAL_MAX_ATTEMPTS,
    MAX_REGISTER_ATTEMPTS,
    REGISTER_LOCK_MINUTES
)

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _calculate_lock(attempt_count: int) -> datetime | None:
    """
    Calculate the exponential blocking time
    """
    if attempt_count < MAX_ATTEMPTS:
        return None

    exponent = attempt_count - MAX_ATTEMPTS
    lock_minutes = min(
        LOCK_MINUTES * (BACKOFF_MULTIPLIER ** exponent),
        MAX_LOCK_MINUTES
    )

    return _now() + timedelta(minutes=lock_minutes)


def cleanup_expired_attempts(db_session: Session) -> int:
    """
    Remove expired attempts for TTL.
    Return the number of rows deleted.
    """
    cutoff = _now() - timedelta(seconds=KEY_TTL_SECONDS)

    stmt = delete(LoginAttemptDB).where(
        LoginAttemptDB.updated_at < cutoff
    )

    result = db_session.execute(stmt)
    db_session.commit()

    return result.rowcount or 0


# ============================================================
# Per-IP Protection
# ============================================================

def check_lock(user_id, ip, db_session: Session) -> None:
    """
    AuthenticationRequiredError if user is blocked.
    """
    if not user_id or not ip:
        raise ValueError("user_id and ip are required")

    cleanup_expired_attempts(db_session)

    attempt = db_session.execute(
        select(LoginAttemptDB).where(
            LoginAttemptDB.user_id == user_id,
            LoginAttemptDB.ip == ip
        )
    ).scalar_one_or_none()

    if attempt and attempt.lock_until and _aware(attempt.lock_until) > _now():
        raise AuthenticationRequiredError("Account temporarily locked")


def check_rate_limit(user_id, ip, db_session: Session) -> None:
    """
    AuthenticationRequiredError if try to log earlier than rate-limit.
    """
    if not user_id or not ip:
        raise ValueError("user_id and ip are required")

    cleanup_expired_attempts(db_session)

    attempt = db_session.execute(
        select(LoginAttemptDB).where(
            LoginAttemptDB.user_id == user_id,
            LoginAttemptDB.ip == ip
        )
    ).scalar_one_or_none()

    if attempt and attempt.updated_at and (_now() - _aware(attempt.updated_at)).total_seconds() < RATE_LIMIT_SECONDS:
        raise AuthenticationRequiredError("Too many attempts, slow down")


def apply_backoff(user_id, ip, db_session: Session) -> None:
    """
    Increment count of attempts and apply lock exponencial.
    """
    if not user_id or not ip:
        raise ValueError("user_id and ip are required")

    cleanup_expired_attempts(db_session)

    attempt = db_session.execute(
        select(LoginAttemptDB).where(
            LoginAttemptDB.user_id == user_id,
            LoginAttemptDB.ip == ip
        )
    ).scalar_one_or_none()

    if not attempt:
        attempt = LoginAttemptDB(
            user_id=user_id,
            ip=ip,
            attempts=1,
            lock_until=None,
        )
        db_session.add(attempt)
    else:
        attempt.attempts += 1
        attempt.updated_at = _now()

    attempt.lock_until = _calculate_lock(attempt.attempts)

    db_session.commit()

    if attempt.lock_until:
        logger.warning(
            "User %s locked until %s",
            user_id,
            attempt.lock_until
        )

def reset_attempts(user_id: uuid.UUID, ip: str, db_session):
    """
    Delete attempt log for one usuario/IP.
    """
    attempt = db_session.query(LoginAttemptDB).filter_by(user_id=user_id, ip=ip).first()
    if attempt:
        db_session.delete(attempt)
        db_session.commit()

# ============================================================
# Global Protection (across IPs)
# ============================================================

def check_global_attempts(user_id, db_session: Session) -> None:
    """
    Verify if user surpass the global limit of attempts.
    """
    if not user_id:
        raise ValueError("user_id is required")

    total_attempts = db_session.query(LoginAttemptDB)\
        .filter(LoginAttemptDB.user_id == user_id)\
        .count()

    if total_attempts >= GLOBAL_MAX_ATTEMPTS:
        raise AuthenticationRequiredError(
            "Global attempt limit reached, account locked."
        )

def apply_global_backoff(user_id, ip, db_session: Session) -> None:
    """
    Increment count of global attempts and apply blocked per IP,
    after verify if has been reached global limit.
    """
    if not user_id or not ip:
        raise ValueError("user_id and ip are required")

    cleanup_expired_attempts(db_session)

    attempt = db_session.execute(
        select(LoginAttemptDB).where(
            LoginAttemptDB.user_id == user_id,
            LoginAttemptDB.ip == ip
        )
    ).scalar_one_or_none()

    if not attempt:
        attempt = LoginAttemptDB(
            user_id=user_id,
            ip=ip,
            attempts=1
        )
        db_session.add(attempt)
    else:
        attempt.attempts += 1
        attempt.updated_at = _now()

    db_session.commit()

    # Verify global (without IP) after increment
    check_global_attempts(user_id, db_session)

    # Apply lock per IP
    attempt.lock_until = _calculate_lock(attempt.attempts)
    db_session.commit()

    if attempt.lock_until:
        logger.warning(
            "User %s globally locked until %s",
            user_id,
            attempt.lock_until
        )

# ============================================================
# REGISTER
# ============================================================
def check_register_rate_limit(username: str, ip: str, db_session):
    attempt = db_session.execute(
        select(RegisterAttemptDB).where(
            RegisterAttemptDB.username == username,
            RegisterAttemptDB.ip == ip
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if attempt:
        if attempt.lock_until and attempt.lock_until > now:
            raise Exception("Too many registration attempts. Try later.")
    else:
        attempt = RegisterAttemptDB(
            id=uuid.uuid4(),
            username=username,
            ip=ip,
            attempts=0
        )
        db_session.add(attempt)
        db_session.commit()

def apply_register_backoff(username: str, ip: str, db_session):
    attempt = db_session.execute(
        select(RegisterAttemptDB).where(
            RegisterAttemptDB.username == username,
            RegisterAttemptDB.ip == ip
        )
    ).scalar_one()

    attempt.attempts += 1

    if attempt.attempts >= MAX_REGISTER_ATTEMPTS:
        attempt.lock_until = datetime.now(timezone.utc) + timedelta(minutes=REGISTER_LOCK_MINUTES)

    db_session.commit()

def reset_register_attempts(username: str, ip: str, db_session):
    attempt = db_session.execute(
        select(RegisterAttemptDB).where(
            RegisterAttemptDB.username == username,
            RegisterAttemptDB.ip == ip
        )
    ).scalar_one_or_none()

    if attempt:
        db_session.delete(attempt)
        db_session.commit()