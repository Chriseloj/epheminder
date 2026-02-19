import pytest
from datetime import datetime, timedelta, timezone
from core.exceptions import AuthenticationRequiredError
import core.protection as protection

USER_ID = "testuser"
IP = "127.0.0.1"

# ------------------ check_lock ------------------
def test_check_lock_raises_when_locked(mock_redis_client):
    lock_key = protection._get_key(USER_ID, IP) + ":lock"
    # Simular que Redis devuelve un lock activo
    mock_redis_client.get.side_effect = lambda k: (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat() if k == lock_key else None
    with pytest.raises(AuthenticationRequiredError):
        protection.check_lock(USER_ID, IP)

def test_check_lock_global_locked(mock_redis_client):
    global_lock_key = protection._get_global_key(USER_ID) + ":lock"
    # IP no bloqueada, pero global sí
    def side_effect(k):
        if k == f"{protection._get_key(USER_ID, IP)}:lock":
            return None
        if k == global_lock_key:
            return (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        return None
    mock_redis_client.get.side_effect = side_effect
    with pytest.raises(AuthenticationRequiredError):
        protection.check_lock(USER_ID, IP)

def test_check_lock_passes_when_no_lock(mock_redis_client):
    mock_redis_client.get.side_effect = lambda k: None
    protection.check_lock(USER_ID, IP)  # No error = pass

# ------------------ check_rate_limit ------------------
def test_check_rate_limit_raises(mock_redis_client):
    last_key = f"{protection._get_key(USER_ID, IP)}:last"
    # Último intento reciente, debe bloquear
    mock_redis_client.get.side_effect = lambda k: (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat() if k == last_key else None
    with pytest.raises(AuthenticationRequiredError):
        protection.check_rate_limit(USER_ID, IP)

def test_check_rate_limit_passes(mock_redis_client):
    last_key = f"{protection._get_key(USER_ID, IP)}:last"
    mock_redis_client.get.side_effect = lambda k: (datetime.now(timezone.utc) - timedelta(seconds=protection.RATE_LIMIT_SECONDS + 1)).isoformat() if k == last_key else None
    protection.check_rate_limit(USER_ID, IP)  # No error = pass

# ------------------ apply_backoff ------------------
def test_apply_backoff_sets_ip_and_global_lock(mock_redis_client):
    mock_redis_client.incr.side_effect = [protection.MAX_ATTEMPTS, protection.GLOBAL_MAX_ATTEMPTS]
    protection.apply_backoff(USER_ID, IP)
    ip_lock_key = f"{protection._get_key(USER_ID, IP)}:lock"
    global_lock_key = f"{protection._get_global_key(USER_ID)}:lock"
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
    assert protection._parse_datetime_safe("not-a-date", "key", "field") is None
    assert protection._parse_datetime_safe(None, "key", "field") is None