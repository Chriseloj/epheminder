import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ===============================
# JWT CONFIGURATION
# ===============================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS512")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# ===============================
# Password policy
# ===============================
MIN_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", 15))
MIN_UPPER = int(os.getenv("MIN_UPPERCASE", 1))
MIN_LOWER = int(os.getenv("MIN_LOWERCASE", 1))
MIN_DIGITS = int(os.getenv("MIN_DIGITS", 1))
MIN_SYMBOLS = int(os.getenv("MIN_SYMBOLS", 1))
SYMBOLS = os.getenv("PASSWORD_SYMBOLS", "!@#$%^&*()-_=+[]{};:'\",.<>/?")

# ===============================
# Reminder limits
# ===============================
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", 100))
MAX_EXPIRATION_DAYS = int(os.getenv("MAX_EXPIRATION_DAYS", 7))
MAX_EXPIRATION_MINUTES = int(os.getenv("MAX_EXPIRATION_MINUTES", 7 * 24 * 60))
MAX_REMINDERS_PER_USER = int(os.getenv("MAX_REMINDERS_PER_USER", 23))

# ===============================
# Redis / DB URLs (if apply)
# ===============================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")

# ===============================
# Security parameters
# ===============================

MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 5))                    # Max login attempts per IP before lock
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", 60))          # Min seconds between attempts (rate limiting)
LOCK_MINUTES = int(os.getenv("LOCK_MINUTES", 15))                # Base lock duration in minutes
MAX_LOCK_MINUTES = int(os.getenv("MAX_LOCK_MINUTES", 24 * 60))       # Max lock duration in minutes
BACKOFF_MULTIPLIER = int(os.getenv("BACKOFF_MULTIPLIER", 2))           # Exponential backoff multiplier
KEY_TTL_SECONDS = int(os.getenv("KEY_TTL_SECONDS", 24 * 60 * 60 ))  # Redis key TTL (24h)
GLOBAL_MAX_ATTEMPTS = int(os.getenv("GLOBAL_MAX_ATTEMPTS", MAX_ATTEMPTS * 3))  # Global attempts limit across IPs