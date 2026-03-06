import pytest
from datetime import datetime, timedelta, timezone
from core.protection import (
    check_lock,
    check_rate_limit,
    apply_backoff,
    reset_attempts,
    cleanup_expired_attempts,
    check_global_attempts,
    apply_global_backoff,
)
from core.exceptions import AuthenticationRequiredError
from core.models import LoginAttemptDB
from config import RATE_LIMIT_SECONDS, MAX_ATTEMPTS, GLOBAL_MAX_ATTEMPTS, MAX_LOCK_MINUTES, MAX_REGISTER_ATTEMPTS

from core.protection import (
    check_register_rate_limit,
    apply_register_backoff,
    reset_register_attempts,
)
from core.models import RegisterAttemptDB

TEST_IP = "127.0.0.1"

# ---------------------------
# Helper UTC aware
# ---------------------------
def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# ---------------------------
# check_lock
# ---------------------------
def test_check_lock_raises_when_locked(db_session, sample_user):
    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=MAX_ATTEMPTS,
        lock_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db_session.add(attempt)
    db_session.commit()

    with pytest.raises(AuthenticationRequiredError):
        check_lock(sample_user.id, TEST_IP, db_session)


def test_check_lock_allows_when_not_locked(db_session, sample_user):
    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=1,
        lock_until=None
    )
    db_session.add(attempt)
    db_session.commit()

    # MUSTN'T
    check_lock(sample_user.id, TEST_IP, db_session)


# ---------------------------
# check_rate_limit
# ---------------------------
def test_check_rate_limit_blocks_recent_attempt(db_session, sample_user):
    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=MAX_ATTEMPTS, 
        updated_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    db_session.add(attempt)
    db_session.commit()

    attempt_from_db = db_session.query(LoginAttemptDB).filter_by(
        user_id=sample_user.id, ip=TEST_IP
    ).first()
    attempt_from_db.updated_at = aware(attempt_from_db.updated_at)

    with pytest.raises(AuthenticationRequiredError):
        check_rate_limit(sample_user.id, TEST_IP, db_session)


def test_check_rate_limit_allows_after_window(db_session, sample_user):
    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=1,
        updated_at=datetime.now(timezone.utc) - timedelta(seconds=RATE_LIMIT_SECONDS + 1),
    )
    db_session.add(attempt)
    db_session.commit()

    attempt_from_db = db_session.query(LoginAttemptDB).filter_by(
        user_id=sample_user.id, ip=TEST_IP
    ).first()
    attempt_from_db.updated_at = aware(attempt_from_db.updated_at)

    # MUSTN'T
    check_rate_limit(sample_user.id, TEST_IP, db_session)


# ---------------------------
# apply_backoff
# ---------------------------
def test_apply_backoff_increments_attempts_and_sets_lock(db_session, sample_user):
    for _ in range(MAX_ATTEMPTS):
        apply_backoff(sample_user.id, TEST_IP, db_session)

    attempt = db_session.query(LoginAttemptDB).filter_by(
        user_id=sample_user.id, ip=TEST_IP
    ).first()
    attempt.lock_until = aware(attempt.lock_until)

    assert attempt.attempts >= 1
    assert attempt.lock_until is not None
    assert attempt.lock_until > datetime.now(timezone.utc)


def test_apply_backoff_creates_attempt_if_none(db_session, sample_user):
    apply_backoff(sample_user.id, TEST_IP, db_session)

    attempt = db_session.query(LoginAttemptDB).filter_by(
        user_id=sample_user.id, ip=TEST_IP
    ).first()
    attempt.lock_until = aware(attempt.lock_until)

    assert attempt is not None
    assert attempt.attempts == 1
    assert attempt.lock_until is None or isinstance(attempt.lock_until, datetime)


# ---------------------------
# reset_attempts
# ---------------------------
def test_reset_attempts_clears_attempt(db_session, sample_user):
    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=1
    )
    db_session.add(attempt)
    db_session.commit()

    reset_attempts(sample_user.id, TEST_IP, db_session)

    attempt_from_db = db_session.query(LoginAttemptDB).filter_by(
        user_id=sample_user.id, ip=TEST_IP
    ).first()
    assert attempt_from_db is None


# ---------------------------
# cleanup_expired_attempts
# ---------------------------
def test_cleanup_expired_attempts_removes_old(db_session, sample_user, monkeypatch):
    old_attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=1,
        updated_at=datetime.now(timezone.utc) - timedelta(seconds=3600)
    )
    db_session.add(old_attempt)
    db_session.commit()

    monkeypatch.setattr("core.protection.KEY_TTL_SECONDS", 60)

    deleted_count = cleanup_expired_attempts(db_session)

    assert deleted_count == 1


# ---------------------------
# check_global_attempts
# ---------------------------
def test_check_global_attempts_blocks_when_limit_reached(db_session, sample_user):
    for _ in range(GLOBAL_MAX_ATTEMPTS):
        attempt = LoginAttemptDB(
            user_id=sample_user.id,
            ip=f"{TEST_IP}",
            attempts=1
        )
        db_session.add(attempt)
    db_session.commit()

    with pytest.raises(AuthenticationRequiredError):
        check_global_attempts(sample_user.id, db_session)


def test_check_global_attempts_allows_below_limit(db_session, sample_user):
    for _ in range(GLOBAL_MAX_ATTEMPTS - 1):
        attempt = LoginAttemptDB(
            user_id=sample_user.id,
            ip=f"{TEST_IP}",
            attempts=1
        )
        db_session.add(attempt)
    db_session.commit()

    # MUSTN'T
    check_global_attempts(sample_user.id, db_session)


# ---------------------------
# apply_global_backoff
# ---------------------------
def test_apply_global_backoff_creates_or_increments(db_session, sample_user):
    apply_global_backoff(sample_user.id, TEST_IP, db_session)

    attempt = db_session.query(LoginAttemptDB).filter_by(
        user_id=sample_user.id, ip=TEST_IP
    ).first()
    attempt.lock_until = aware(attempt.lock_until)

    assert attempt.attempts >= 1
    assert attempt.lock_until is None or isinstance(attempt.lock_until, datetime)

# ---------------------------
# _calculate_lock (critical)
# ---------------------------
from core.protection import _calculate_lock
from config import LOCK_MINUTES, MAX_ATTEMPTS, BACKOFF_MULTIPLIER, MAX_LOCK_MINUTES


def test_calculate_lock_returns_none_below_threshold():
    lock = _calculate_lock(MAX_ATTEMPTS - 1)
    assert lock is None


def test_calculate_lock_starts_at_threshold():
    lock = _calculate_lock(MAX_ATTEMPTS)
    assert lock is not None


def test_calculate_lock_exponential_growth():
    lock1 = _calculate_lock(MAX_ATTEMPTS)
    lock2 = _calculate_lock(MAX_ATTEMPTS + 1)

    delta1 = (lock1 - datetime.now(timezone.utc)).total_seconds()
    delta2 = (lock2 - datetime.now(timezone.utc)).total_seconds()

    assert delta2 > delta1


def test_calculate_lock_respects_max_cap():
    very_high_attempts = MAX_ATTEMPTS + 20
    lock = _calculate_lock(very_high_attempts)

    max_seconds = MAX_LOCK_MINUTES * 60
    delta = (lock - datetime.now(timezone.utc)).total_seconds()

    assert delta <= max_seconds + 2  # margen pequeño

def test_check_global_attempts_counts_records_not_attempt_sum(db_session, sample_user):
    # Solo 1 registro con attempts altos
    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip="1.1.1.1",
        attempts=999
    )
    db_session.add(attempt)
    db_session.commit()

    # No debería bloquear porque usa .count(), no suma attempts
    check_global_attempts(sample_user.id, db_session)

def test_apply_global_backoff_raises_when_limit_reached(db_session, sample_user):
    # Crear registros hasta justo antes del límite
    for i in range(GLOBAL_MAX_ATTEMPTS - 1):
        db_session.add(LoginAttemptDB(
            user_id=sample_user.id,
            ip=f"192.168.0.{i}",
            attempts=1
        ))
    db_session.commit()

    # Este debe disparar el límite
    with pytest.raises(AuthenticationRequiredError):
        apply_global_backoff(sample_user.id, "new-ip", db_session)

def test_check_lock_handles_naive_datetime(db_session, sample_user):

    # Creamos un lock naive (sin tzinfo) para probar _aware()
    naive_lock = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)

    attempt = LoginAttemptDB(
        user_id=sample_user.id,
        ip=TEST_IP,
        attempts=5,
        lock_until=naive_lock
    )
    db_session.add(attempt)
    db_session.commit()

    # check_lock debería reconocerlo como lock activo
    with pytest.raises(AuthenticationRequiredError):
        check_lock(sample_user.id, TEST_IP, db_session)

def test_check_register_rate_limit_creates_attempt(db_session):
    check_register_rate_limit("userx", TEST_IP, db_session)

    attempt = db_session.query(RegisterAttemptDB).filter_by(
        username="userx", ip=TEST_IP
    ).first()

    assert attempt is not None
    assert attempt.attempts == 0


def test_check_register_rate_limit_blocks_when_locked(db_session):
    attempt = RegisterAttemptDB(
        username="userx",
        ip=TEST_IP,
        attempts=MAX_REGISTER_ATTEMPTS,
        lock_until=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    db_session.add(attempt)
    db_session.commit()

    with pytest.raises(Exception):
        check_register_rate_limit("userx", TEST_IP, db_session)

def test_apply_register_backoff_increments_and_locks(db_session):
    attempt = RegisterAttemptDB(
        username="userx",
        ip=TEST_IP,
        attempts=MAX_REGISTER_ATTEMPTS - 1
    )
    db_session.add(attempt)
    db_session.commit()

    apply_register_backoff("userx", TEST_IP, db_session)

    updated = db_session.query(RegisterAttemptDB).filter_by(
        username="userx", ip=TEST_IP
    ).first()

    assert updated.attempts == MAX_REGISTER_ATTEMPTS
    assert updated.lock_until is not None

def test_reset_register_attempts_deletes_record(db_session):
    attempt = RegisterAttemptDB(
        username="userx",
        ip=TEST_IP,
        attempts=2
    )
    db_session.add(attempt)
    db_session.commit()

    reset_register_attempts("userx", TEST_IP, db_session)

    attempt = db_session.query(RegisterAttemptDB).filter_by(
        username="userx", ip=TEST_IP
    ).first()

    assert attempt is None

def test_apply_backoff_logs_when_locked(db_session, sample_user, caplog):
    for _ in range(MAX_ATTEMPTS):
        apply_backoff(sample_user.id, TEST_IP, db_session)

    assert "locked until" in caplog.text.lower()

def test_apply_global_backoff_logs_when_locked(db_session, sample_user, caplog):
    for _ in range(MAX_ATTEMPTS):
        apply_global_backoff(sample_user.id, TEST_IP, db_session)

    assert "globally locked" in caplog.text.lower()