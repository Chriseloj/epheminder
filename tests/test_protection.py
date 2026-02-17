import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from core.exceptions import AuthenticationRequiredError
import core.protection as protection

USER_ID = "testuser"
IP = "127.0.0.1"

def test_apply_backoff_sets_lock(mock_redis_client):
    # Simulate already have MAX_ATTEMPTS-1 
    mock_redis_client.incr.side_effect = [protection.MAX_ATTEMPTS, 1]  # ip count, global count
    protection.apply_backoff(USER_ID, IP)
    
    lock_key = f"{protection._get_key(USER_ID, IP)}:lock"
    assert mock_redis_client.set.called
    called_keys = [call[1]["nx"] if "nx" in call[1] else None for call in mock_redis_client.set.call_args_list]
    assert any(call is True or call is None for call in called_keys)

def test_check_lock_raises_when_locked(mock_redis_client):
    lock_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    mock_redis_client.get.return_value = lock_time
    with pytest.raises(AuthenticationRequiredError):
        protection.check_lock(USER_ID, IP)

def test_check_rate_limit_raises(mock_redis_client):
    last_attempt = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    mock_redis_client.get.return_value = last_attempt
    with pytest.raises(AuthenticationRequiredError):
        protection.check_rate_limit(USER_ID, IP)

def test_reset_attempts_calls_delete(mock_redis_client):
    protection.reset_attempts(USER_ID, IP)
    redis_keys = [
        protection._get_key(USER_ID, IP),
        f"{protection._get_key(USER_ID, IP)}:lock",
        f"{protection._get_key(USER_ID, IP)}:last"
    ]
    for key in redis_keys:
        mock_redis_client.delete.assert_any_call(key)

# ------------------ check_lock ------------------

def test_check_lock_ip_locked(mock_redis_client):
    # IP lock 
    lock_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    mock_redis_client.get.return_value = lock_time
    with pytest.raises(AuthenticationRequiredError):
        protection.check_lock(USER_ID, IP)

def test_check_lock_global_locked(mock_redis_client):
    # Not IP lock, but lock global
    mock_redis_client.get.side_effect = [None, (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()]
    with pytest.raises(AuthenticationRequiredError):
        protection.check_lock(USER_ID, IP)

def test_check_lock_passes_when_no_lock(mock_redis_client):
    mock_redis_client.get.return_value = None
    # No terror means success
    protection.check_lock(USER_ID, IP)

# ------------------ check_rate_limit ------------------

def test_check_rate_limit_raises(mock_redis_client):
    last_attempt = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    mock_redis_client.get.return_value = last_attempt
    with pytest.raises(AuthenticationRequiredError):
        protection.check_rate_limit(USER_ID, IP)

def test_check_rate_limit_passes(mock_redis_client):
    last_attempt = (datetime.now(timezone.utc) - timedelta(seconds=protection.RATE_LIMIT_SECONDS + 1)).isoformat()
    mock_redis_client.get.return_value = last_attempt
    protection.check_rate_limit(USER_ID, IP)  # No error = pass

# ------------------ apply_backoff ------------------

def test_apply_backoff_sets_ip_and_global_lock(mock_redis_client):
    # Simulate attemptd to lock IP and global
    mock_redis_client.incr.side_effect = [protection.MAX_ATTEMPTS, protection.GLOBAL_MAX_ATTEMPTS]
    protection.apply_backoff(USER_ID, IP)

    ip_lock_key = f"{protection._get_key(USER_ID, IP)}:lock"
    global_lock_key = f"{protection._get_global_key(USER_ID)}:lock"

    # Verify  attempts set locks
    keys_set = [call[0][0] for call in mock_redis_client.set.call_args_list]
    assert ip_lock_key in keys_set
    assert global_lock_key in keys_set

# ------------------ reset_attempts ------------------

def test_reset_attempts_calls_delete(mock_redis_client):
    protection.reset_attempts(USER_ID, IP)
    redis_keys = [
        protection._get_key(USER_ID, IP),
        f"{protection._get_key(USER_ID, IP)}:lock",
        f"{protection._get_key(USER_ID, IP)}:last"
    ]
    for key in redis_keys:
        mock_redis_client.delete.assert_any_call(key)

# ------------------ _parse_datetime_safe ------------------

def test_parse_datetime_safe_valid_and_invalid():
    dt = datetime.now(timezone.utc).isoformat()
    parsed = protection._parse_datetime_safe(dt, "key", "field")
    assert parsed.isoformat() == dt

    # Malformed string returns None
    assert protection._parse_datetime_safe("not-a-date", "key", "field") is None
    # None input returns None
    assert protection._parse_datetime_safe(None, "key", "field") is None