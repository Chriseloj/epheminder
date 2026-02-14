from datetime import datetime, timedelta
from core.exceptions import AuthenticationRequiredError

FAILED_ATTEMPTS = {}
MAX_ATTEMPTS = 5
RATE_LIMIT_SECONDS = 60
LOCK_MINUTES = 15
BACKOFF_MULTIPLIER = 2

FAILED_LOGINS = {
    "username_or_ip": {
        "attempt_count": 3,
        "last_attempt": datetime.utcnow(),
        "locked_until": datetime.utcnow() + timedelta(minutes=5)
    }
}

def check_lock(key: str):
    record = FAILED_ATTEMPTS.get(key)
    if record and record.get("locked_until") and datetime.utcnow() < record["locked_until"]:
        raise AuthenticationRequiredError("Account temporarily locked")

def check_rate_limit(key: str):
    record = FAILED_ATTEMPTS.get(key)
    if not record:
        return
    if (datetime.utcnow() - record["last_attempt"]).seconds < RATE_LIMIT_SECONDS and \
       record["attempt_count"] >= MAX_ATTEMPTS:
        raise AuthenticationRequiredError("Too many attempts, slow down")

def apply_backoff(key: str):
    record = FAILED_ATTEMPTS.setdefault(
        key, {"attempt_count": 0, "last_attempt": None, "locked_until": None}
    )

    record["attempt_count"] += 1
    record["last_attempt"] = datetime.utcnow()

    if record["attempt_count"] >= MAX_ATTEMPTS:
        record["locked_until"] = datetime.utcnow() + timedelta(minutes=LOCK_MINUTES)

def reset_attempts(key: str):
    FAILED_ATTEMPTS.pop(key, None)